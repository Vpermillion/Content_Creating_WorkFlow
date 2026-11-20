const brand = 'ifverse_anime';
const googleToken = 'https://oauth2.googleapis.com/token';
const tiktokToken = 'https://open.tiktokapis.com/v2/oauth/token/';
const studioUrl = 'https://www.tiktok.com/tiktokstudio/upload';
const googleScopes = ['youtube.readonly', 'youtube.upload'].map(scope => 'https://www.googleapis.com/auth/' + scope);
const metaScopes = {
  instagram: 'pages_show_list,pages_read_engagement,instagram_basic,instagram_content_publish',
  facebook: 'pages_show_list,pages_read_engagement,pages_manage_posts',
};
const tiktokScopes = ['user.info.basic', 'user.info.profile', 'video.list'];
const accounts = {
  'ifverse-anime': { platform: 'youtube', account_id: 'UCpB_wi5MlernpSJxUf7zWcw', handle: '@ifverse_anime' },
  'ifverse-instagram': { platform: 'instagram', handle: '@ifverse_anime' },
  'ifverse-facebook': { platform: 'facebook' },
  'ifverse-tiktok': { platform: 'tiktok', handle: '@ifverse_anime' },
};
const formats = { youtube: ['short'], instagram: ['reel', 'jpeg'], facebook: ['reel', 'feed'], tiktok: ['studio'] };
const encoder = new TextEncoder();
const decoder = new TextDecoder();
const stateLifetime = 30 * 60;
const selectionLifetime = 10 * 60 * 1000;
const selectionAccount = 'choose-destination';
const platforms = Object.keys(formats);
const savedAccount = /^(youtube|instagram|facebook|tiktok)-[0-9a-f]{24}$/;
export const isGatewayAccount = account => savedAccount.test(account);
const platformFor = account => Object.hasOwn(accounts, account) ? accounts[account].platform : savedAccount.exec(account)?.[1];

class AccountError extends Error {}

function requireValue(value, message) {
  if (!value) throw new AccountError(message);
  return value;
}

function base64(bytes) {
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 16_384) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 16_384));
  }
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}

function unbase64(value) {
  return Uint8Array.from(atob(value.replaceAll('-', '+').replaceAll('_', '/')), char => char.charCodeAt(0));
}

async function hash(value) {
  return base64(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(value))));
}

function oauthSettings(env, platform) {
  const provider = platform in metaScopes ? 'meta' : platform;
  const config = JSON.parse(env.IFVERSE_OAUTH_CONFIG || '{}')[provider];
  requireValue(config?.client_id && config.client_secret,
    'Add the ' + provider + ' OAuth client in the private site settings.');
  if (provider === 'meta') {
    requireValue(/^v[0-9]+\.[0-9]+$/.test(config.graph_version), 'Set the supported Meta Graph API version in Site settings.');
    requireValue(!config.login_config_id || /^[0-9]+$/.test(config.login_config_id), 'Check the Meta login configuration ID.');
  }
  return config;
}

function callbackUrl(request, env) {
  const origin = new URL(env.IFVERSE_SITE_ORIGIN || request.url);
  requireValue(origin.protocol === 'https:' && !origin.username && !origin.password, 'Use the private HTTPS Site.');
  return origin.origin + '/oauth/callback';
}

function urlWith(base, query) {
  return base + '?' + new URLSearchParams(query);
}

function targetFor(account, args, env) {
  if (platforms.includes(account)) return { platform: account };
  const row = Object.hasOwn(accounts, account) ? accounts[account] : null;
  requireValue(row, 'Choose an account alias from the account list.');
  if (row.platform === 'facebook') {
    const pageId = env.IFVERSE_FACEBOOK_PAGE_ID || args.page_id || '';
    requireValue(/^[0-9]{1,32}$/.test(pageId), 'Set the intended Facebook Page ID before connecting Facebook.');
    requireValue(!args.page_id || args.page_id === pageId, 'Select the configured Facebook Page.');
    return { ...row, account_id: pageId };
  }
  if (row.platform === 'tiktok') {
    const name = (args.handle || row.handle).replace(/^@/, '');
    requireValue(/^[a-zA-Z0-9_.]{1,24}$/.test(name), 'Use the intended TikTok @handle when connecting TikTok.');
    return { ...row, handle: '@' + name };
  }
  return row;
}

async function keyFor(env) {
  const secret = env.IFVERSE_ACCOUNT_KEY || '';
  requireValue(/^[A-Za-z0-9_-]{43}$/.test(secret), 'Set the account storage key in private Site settings.');
  return crypto.subtle.importKey('raw', unbase64(secret), 'AES-GCM', false, ['encrypt', 'decrypt']);
}

function grantContext(owner, account) {
  return encoder.encode(JSON.stringify([owner, account]));
}

async function encryptGrant(key, owner, account, grant) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv, additionalData: grantContext(owner, account) },
    key, encoder.encode(JSON.stringify(grant)),
  );
  return base64(iv) + '.' + base64(new Uint8Array(encrypted));
}

async function decryptGrant(key, owner, account, stored) {
  const [iv, ciphertext] = stored.split('.');
  const bytes = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: unbase64(iv), additionalData: grantContext(owner, account) },
    key, unbase64(ciphertext),
  );
  return JSON.parse(decoder.decode(bytes));
}

async function providerJson(url, { form, token } = {}) {
  const endpoint = new URL(url);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  let response;
  try {
    response = await fetch(endpoint.toString(), {
      method: form ? 'POST' : 'GET',
      headers: {
        Accept: 'application/json',
        ...(form ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {}),
        ...(token ? { Authorization: 'Bearer ' + token } : {}),
      },
      body: form ? new URLSearchParams(form).toString() : undefined,
      redirect: 'manual',
      signal: controller.signal,
    });
  } catch (error) {
    const reason = controller.signal.aborted ? 'timeout' : error instanceof TypeError ? 'network or runtime error' : 'request error';
    console.error('Ifverse provider request failed: ' + endpoint.hostname + endpoint.pathname + ' (' + reason + ')');
    throw new AccountError('The account service could not reach the provider. Try connecting again.');
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) console.warn('Ifverse provider returned HTTP ' + response.status + ': ' + endpoint.hostname);
  requireValue(response.ok, 'The provider declined the request. Check the selected account and app permissions.');
  const result = await response.json();
  requireValue(!result.error || result.error.code === 'ok',
    'The provider declined the request. Check the selected account and app permissions.');
  return result;
}

const handleKey = value => String(value || '').replace(/^@/, '').toLowerCase();
const hasScopes = (scope, needed) => needed.every(item => String(scope || '').split(/[ ,]+/).includes(item));
const expiry = seconds => Number.isFinite(Number(seconds)) && Number(seconds) > 0 ? Date.now() + Number(seconds) * 1000 : null;

async function youtubeChannels(token) {
  const endpoint = 'https://www.googleapis.com/youtube/v3/channels';
  const params = { part: 'snippet', mine: 'true', maxResults: '50' };
  const channels = new Map();
  const seen = new Set();
  do {
    const result = await providerJson(urlWith(endpoint, params), { token });
    for (const item of result.items || []) {
      if (!/^UC[A-Za-z0-9_-]{22}$/.test(item.id)) continue;
      const handle = item.snippet?.customUrl?.startsWith('@') ? item.snippet.customUrl : '';
      channels.set(item.id, { id: item.id, handle, name: item.snippet?.title || handle || item.id });
    }
    params.pageToken = result.nextPageToken;
    if (params.pageToken) {
      requireValue(!seen.has(params.pageToken) && seen.size < 10, 'YouTube could not finish listing the authorized channels.');
      seen.add(params.pageToken);
    }
  } while (params.pageToken);
  return [...channels.values()];
}

async function youtubeIdentity(token, target) {
  const match = (await youtubeChannels(token)).find(item => item.id === target.account_id);
  const mismatch = target.handle ? 'Google authorized a different YouTube channel. Choose @ifverse_anime during consent.'
    : 'Google authorized a different YouTube channel. Reconnect this channel.';
  requireValue(match, mismatch);
  if (!target.handle) return match;
  const handleMatch = await providerJson(urlWith('https://www.googleapis.com/youtube/v3/channels',
    { part: 'id', forHandle: target.handle }), { token });
  requireValue(handleMatch.items?.length === 1 && handleMatch.items[0].id === match.id, mismatch);
  return { ...match, handle: target.handle };
}

async function metaIdentity(platform, base, id, token, expectedHandle) {
  const fields = platform === 'instagram' ? 'id,username' : 'id,name';
  const result = await providerJson(urlWith(base + '/' + id, { fields }), { token });
  requireValue(result.id === id && (!expectedHandle || platform !== 'instagram' || handleKey(result.username) === handleKey(expectedHandle)),
    'Meta returned a different account. Check the Page and its linked Instagram profile.');
  return { id, handle: result.username ? '@' + result.username : '', name: result.name || result.username || '' };
}

async function tiktokIdentity(token, handle, expectedId) {
  const response = await providerJson('https://open.tiktokapis.com/v2/user/info/?fields=open_id,username,display_name', { token });
  const user = response.data?.user;
  requireValue(user?.open_id === expectedId && (!handle || handleKey(user.username) === handleKey(handle)),
    'TikTok authorized a different account. Choose the requested handle during consent.');
  return { id: user.open_id, handle: user.username ? '@' + user.username : '', name: user.display_name || user.username || user.open_id };
}

async function metaPages(base, platform, target, token) {
  const fields = platform === 'instagram' ? 'id,access_token,instagram_business_account{id,username}' : 'id,name,access_token';
  const params = { fields, limit: '100' };
  const matches = new Map();
  const seen = new Set();
  for (;;) {
    const result = await providerJson(urlWith(base + '/me/accounts', params), { token });
    for (const page of result.data || []) {
      const instagram = page.instagram_business_account;
      const matchesTarget = platform === 'facebook' ? !target.account_id || page.id === target.account_id
        : /^[0-9]+$/.test(instagram?.id || '') && (!target.handle || handleKey(instagram.username) === handleKey(target.handle));
      if (matchesTarget && /^[0-9]+$/.test(page.id) && page.access_token) matches.set(page.id, page);
    }
    if (!result.paging?.next) break;
    const after = result.paging.cursors?.after;
    requireValue(after && !seen.has(after) && seen.size < 10, 'Meta could not finish listing the authorized Pages.');
    seen.add(after);
    params.after = after;
  }
  return [...matches.values()];
}

async function exchange(target, config, code, redirect, verifier) {
  const { platform } = target;
  const client = { client_id: config.client_id, client_secret: config.client_secret };
  const common = { code, redirect_uri: redirect, grant_type: 'authorization_code' };
  if (platform === 'youtube') {
    const result = await providerJson(googleToken, { form: { ...client, ...common, code_verifier: verifier } });
    requireValue(result.access_token && result.refresh_token && hasScopes(result.scope, googleScopes),
      'Google consent must include YouTube access, upload permission, and offline access.');
    const channels = target.account_id ? [await youtubeIdentity(result.access_token, target)]
      : await youtubeChannels(result.access_token);
    requireValue(channels.length, 'Google did not authorize a YouTube channel. Choose an account with a channel.');
    return channels.map(identity => ({ identity,
      grant: { token: result.access_token, refresh: result.refresh_token, client: config.client_id },
      expiresAt: expiry(result.expires_in) }));
  }
  if (platform === 'tiktok') {
    const result = await providerJson(tiktokToken, { form: { ...common, client_key: config.client_id, client_secret: config.client_secret } });
    requireValue(result.access_token && result.refresh_token && result.open_id && hasScopes(result.scope, tiktokScopes),
      'TikTok consent must include profile and video access.');
    return [{ identity: await tiktokIdentity(result.access_token, target.handle, result.open_id),
      grant: { token: result.access_token, refresh: result.refresh_token, client: config.client_id },
      expiresAt: expiry(result.expires_in) }];
  }
  const base = 'https://graph.facebook.com/' + config.graph_version;
  const endpoint = base + '/oauth/access_token';
  const result = await providerJson(endpoint, { form: { ...client, code, redirect_uri: redirect } });
  requireValue(result.access_token, 'Meta did not grant access.');
  const durable = await providerJson(urlWith(endpoint,
    { ...client, grant_type: 'fb_exchange_token', fb_exchange_token: result.access_token }));
  requireValue(durable.access_token, 'Meta did not grant offline access.');
  const permissions = await providerJson(base + '/me/permissions', { token: durable.access_token });
  const granted = new Set((permissions.data || []).filter(item => item.status === 'granted').map(item => item.permission));
  requireValue(metaScopes[platform].split(',').every(scope => granted.has(scope)),
    'Meta consent did not include the permissions required for this destination.');
  const pages = await metaPages(base, platform, target, durable.access_token);
  const pinned = Boolean(target.account_id || target.handle);
  requireValue(pinned ? pages.length === 1 : pages.length > 0,
    pinned ? 'Consent did not include the intended Facebook Page or its linked Instagram profile.'
      : platform === 'instagram' ? 'Choose a Facebook Page linked to an Instagram professional account.'
        : 'Consent did not include a Facebook Page you manage.');
  const candidates = new Map();
  for (const page of pages) {
    const instagram = page.instagram_business_account;
    const id = platform === 'facebook' ? page.id : instagram.id;
    const identity = pinned ? await metaIdentity(platform, base, id, page.access_token, target.handle)
      : { id, handle: instagram?.username ? '@' + instagram.username : '', name: page.name || instagram?.username || id };
    candidates.set(id, { identity, grant: { token: page.access_token, client: config.client_id, page_id: page.id },
      expiresAt: null });
  }
  return [...candidates.values()];
}

async function begin(request, env, owner, args) {
  if (args.account === 'ifverse-tiktok' && (args.method === 'studio' ||
    (!args.method && !JSON.parse(env.IFVERSE_OAUTH_CONFIG || '{}').tiktok))) {
    return { account: args.account, status: 'studio_handoff', studio_url: studioUrl };
  }
  const target = targetFor(args.account, args, env);
  const config = oauthSettings(env, target.platform);
  await keyFor(env);
  const state = base64(crypto.getRandomValues(new Uint8Array(32)));
  const verifier = base64(crypto.getRandomValues(new Uint8Array(48)));
  const redirect = callbackUrl(request, env);
  const query = { redirect_uri: redirect, state, response_type: 'code', client_id: config.client_id };
  let authorize;
  if (target.platform === 'youtube') {
    authorize = 'https://accounts.google.com/o/oauth2/v2/auth';
    Object.assign(query, { scope: googleScopes.join(' '), access_type: 'offline', prompt: 'consent select_account',
      code_challenge_method: 'S256', code_challenge: await hash(verifier) });
  } else if (target.platform === 'tiktok') {
    authorize = 'https://www.tiktok.com/v2/auth/authorize/';
    delete query.client_id;
    Object.assign(query, { client_key: config.client_id, scope: tiktokScopes.join(','), disable_auto_auth: '1' });
  } else {
    authorize = 'https://www.facebook.com/' + config.graph_version + '/dialog/oauth';
    if (config.login_config_id) Object.assign(query, { config_id: config.login_config_id, override_default_response_type: 'true' });
    else query.scope = metaScopes[target.platform];
  }
  const now = Date.now();
  await env.DB.batch([
    env.DB.prepare('DELETE FROM oauth_sessions WHERE expires_at < ?').bind(now),
    env.DB.prepare('INSERT INTO oauth_sessions VALUES (?, ?, ?, ?, ?, ?, ?)')
      .bind(await hash(state), owner, args.account, JSON.stringify(target), verifier, now, now + stateLifetime * 1000),
  ]);
  return { account: args.account, authorization_url: urlWith(authorize, query), expires_in: stateLifetime };
}

function publicAccount(account, row) {
  const preset = Object.hasOwn(accounts, account);
  const { account_id, handle } = preset ? accounts[account] : {};
  const platform = platformFor(account);
  return {
    account, platform, brand, preset,
    workflow_destination: preset || Boolean(row && (platform !== 'tiktok' || row.handle)), account_id: row?.provider_id || account_id || null,
    handle: row?.handle || handle || null, display_name: row?.display_name || null,
    status: !row ? 'not_connected' : row.expires_at && row.expires_at <= Date.now() ? 'refresh_due' : 'connected',
    connected_at: row ? new Date(row.connected_at).toISOString() : null,
    ...(platform === 'tiktok' ? { publishing: 'studio_handoff' } : {}),
  };
}

async function activeGrant(env, owner, account, minimumLifetime) {
  const platform = requireValue(platformFor(account), 'Choose an account alias from the account list.');
  const row = await env.DB.prepare('SELECT * FROM account_connections WHERE owner_id = ? AND account = ?')
    .bind(owner, account).first();
  if (!row) return null;
  const config = oauthSettings(env, platform);
  const key = await keyFor(env);
  let grant = await decryptGrant(key, owner, account, row.grant);
  requireValue(grant.client === config.client_id, 'The provider app changed. Reconnect this account.');
  let expiresAt = row.expires_at;
  if (expiresAt && expiresAt < Date.now() + minimumLifetime) {
    const youtube = platform === 'youtube';
    const form = { client_secret: config.client_secret, refresh_token: grant.refresh, grant_type: 'refresh_token',
      [youtube ? 'client_id' : 'client_key']: config.client_id };
    const refreshed = await providerJson(youtube ? googleToken : tiktokToken, { form });
    requireValue(refreshed.access_token && (youtube || !refreshed.open_id || refreshed.open_id === row.provider_id),
      'The saved grant expired. Reconnect this account.');
    grant = { ...grant, token: refreshed.access_token, refresh: refreshed.refresh_token || grant.refresh };
    expiresAt = expiry(refreshed.expires_in);
    const update = await env.DB.prepare(
      'UPDATE account_connections SET grant = ?, expires_at = ? WHERE owner_id = ? AND account = ? AND grant = ?',
    ).bind(await encryptGrant(key, owner, account, grant), expiresAt, owner, account, row.grant).run();
    requireValue(update.meta.changes === 1, 'The connection changed while it was checked. Check it again.');
  }
  return { row: { ...row, expires_at: expiresAt }, grant, config, platform };
}

async function verify(env, owner, account) {
  const connection = await activeGrant(env, owner, account, 60_000);
  if (!connection) return publicAccount(account);
  const { row, grant, config, platform } = connection;
  const pinned = Object.hasOwn(accounts, account);
  if (platform === 'youtube') await youtubeIdentity(grant.token, pinned ? accounts[account] : { account_id: row.provider_id });
  else if (platform === 'tiktok') await tiktokIdentity(grant.token, pinned ? row.handle : '', row.provider_id);
  else await metaIdentity(platform, 'https://graph.facebook.com/' + config.graph_version, row.provider_id, grant.token, pinned ? row.handle : '');
  return { ...publicAccount(account, row), verified: true };
}

// Only the Site can attach bindings to authenticated publisher requests.
export async function publishingBindings(env, owner, aliases) {
  const selected = [...new Set(aliases)].filter(isGatewayAccount);
  if (!selected.length) return {};
  const placeholders = selected.map(() => '?').join(', ');
  const saved = await env.DB.prepare(
    'SELECT account, provider_id, handle FROM account_connections WHERE owner_id = ? AND account IN (' + placeholders + ')',
  ).bind(owner, ...selected).all();
  return Object.fromEntries(saved.results.map(row => {
    const platform = platformFor(row.account);
    return [row.account, { brand, platform, account_id: row.provider_id,
      ...(row.handle ? { handle: row.handle } : {}) }];
  }));
}

// Only used for server-to-server requests to the configured publishing service.
export async function publishingGrants(env, owner, aliases) {
  const grants = {};
  for (const alias of new Set(aliases)) {
    if (!platformFor(alias)) continue;
    let connection;
    try {
      connection = await activeGrant(env, owner, alias, 15 * 60_000);
    } catch (error) {
      if (!(error instanceof AccountError)) throw error;
      continue;
    }
    if (!connection) continue;
    const { row, grant, config, platform } = connection;
    if (alias === 'ifverse-facebook' && env.IFVERSE_FACEBOOK_PAGE_ID && row.provider_id !== env.IFVERSE_FACEBOOK_PAGE_ID) continue;
    grants[alias] = { platform, account_id: row.provider_id, token: grant.token,
      ...(platform in metaScopes ? { graph_version: config.graph_version,
        ...(platform === 'instagram' ? { page_id: grant.page_id } : {}) } : {}) };
  }
  return grants;
}

function connectionSetup(env, platform, pinned = false) {
  try {
    oauthSettings(env, platform);
    requireValue(/^[A-Za-z0-9_-]{43}$/.test(env.IFVERSE_ACCOUNT_KEY || ''), 'Account storage needs setup.');
  } catch (error) {
    return error instanceof AccountError ? error.message : 'Check the private OAuth client settings.';
  }
  if (pinned && platform === 'facebook' && !/^[0-9]{1,32}$/.test(env.IFVERSE_FACEBOOK_PAGE_ID || '')) {
    return 'Set the intended Facebook Page ID in the private Site settings.';
  }
  return null;
}

export async function accountTool(request, env, owner, name, args) {
  try {
    const gatewayUrl = new URL('/connect', callbackUrl(request, env)).href;
    if (name === 'ifverse_connect') return args.account ? await begin(request, env, owner, args)
      : { status: 'choose_platform', gateway_url: gatewayUrl };
    if (name === 'ifverse_verify') return await verify(env, owner, args.account);
    const saved = await env.DB.prepare('SELECT account, provider_id, handle, display_name, expires_at, connected_at FROM account_connections WHERE owner_id = ?')
      .bind(owner).all();
    const records = new Map(saved.results.map(row => [row.account, row]));
    return {
      accounts: Object.fromEntries([...Object.keys(accounts), ...[...records.keys()].filter(account => savedAccount.test(account))]
        .map(account => {
          const item = publicAccount(account, records.get(account));
          return [account, { ...item, setup_required: connectionSetup(env, item.platform, item.preset) }];
        })),
      platforms: Object.fromEntries(platforms.map(platform => [platform, connectionSetup(env, platform)])),
      formats,
      gateway_url: gatewayUrl,
      publisher_configured: Boolean(env.IFVERSE_BACKEND_URL && env.IFVERSE_BACKEND_TOKEN),
      callback_url: callbackUrl(request, env),
    };
  } catch (error) {
    return { error: error instanceof AccountError ? error.message : 'The account connection service could not complete the request.' };
  }
}

function connectionError(message) {
  const safeMessage = message.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  return new Response(`<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Connection needs attention</title>
    <style>
      :root{color-scheme:dark;background:#13151c;color:#edf0ff;font:1rem/1.5 "DM Sans",system-ui,sans-serif}
      main{margin:clamp(1.25rem,6vw,5rem) auto;padding:0 1.25rem;max-width:32rem}
      a{display:inline-block;background:#bfc6ff;color:#171a3c;border-radius:.45rem;padding:.6rem 1rem;font-weight:700}
    </style>
    <main><h1>Connection needs attention</h1><p>${safeMessage}</p><a href="/">Back to accounts</a></main></html>`, {
    status: 400, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
      'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'" },
  });
}

async function saveConnection(env, key, owner, session, { identity, grant, expiresAt }) {
  const account = session.account;
  const result = await env.DB.prepare(
    `INSERT INTO account_connections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(owner_id, account) DO UPDATE SET provider_id = excluded.provider_id, handle = excluded.handle,
     display_name = excluded.display_name, grant = excluded.grant, expires_at = excluded.expires_at,
     started_at = excluded.started_at, connected_at = excluded.connected_at
     WHERE excluded.started_at >= account_connections.started_at`,
  ).bind(owner, account, identity.id, identity.handle, identity.name,
    await encryptGrant(key, owner, account, grant), expiresAt, session.started_at, Date.now()).run();
  requireValue(result.meta.changes === 1, 'A newer account connection is already active.');
  return new Response(null, {
    status: 303,
    headers: { Location: isGatewayAccount(account) ? '/connect?' + new URLSearchParams({ connected: account }) : '/',
      'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' },
  });
}

async function savePlatformConnection(env, key, owner, platform, startedAt, candidate) {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(candidate.identity.id));
  const id = [...new Uint8Array(digest).slice(0, 12)].map(byte => byte.toString(16).padStart(2, '0')).join('');
  const config = oauthSettings(env, platform);
  requireValue(candidate.grant.client === config.client_id, 'The provider app changed. Start a new connection.');
  if (platform in metaScopes) {
    candidate.identity = await metaIdentity(platform, 'https://graph.facebook.com/' + config.graph_version,
      candidate.identity.id, candidate.grant.token);
  }
  return saveConnection(env, key, owner, { account: platform + '-' + id, started_at: startedAt }, candidate);
}

async function requestSelection(env, key, owner, target, session, candidates) {
  const selection = base64(crypto.getRandomValues(new Uint8Array(32)));
  const now = Date.now();
  const encrypted = await encryptGrant(key, owner, selection, { platform: target.platform, candidates });
  await env.DB.prepare('INSERT INTO oauth_sessions VALUES (?, ?, ?, ?, ?, ?, ?)')
    .bind(await hash(selection), owner, selectionAccount, encrypted, '', session.started_at, now + selectionLifetime).run();
  const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  const list = candidates.map(({ identity }, index) =>
    `<li><button name="choice" value="${index}"><strong>${escape(identity.name || identity.id)}</strong>
      <span>${escape(identity.handle || identity.id)}</span></button></li>`).join('');
  return new Response(`<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1"><title>Choose an account</title>
    <style>
      :root{color-scheme:dark;background:#13151c;color:#edf0ff;font:1rem/1.5 system-ui,sans-serif}
      main{margin:clamp(1.25rem,6vw,5rem) auto;padding:0 1.25rem;max-width:32rem}
      ul{padding:0;list-style:none}li{margin:.6rem 0}
      button{width:100%;text-align:left;padding:1rem;border:1px solid #3b4053;border-radius:.6rem;
        background:#1c1f2b;color:inherit;font:inherit;cursor:pointer}
      span{display:block;color:#c1c7df;overflow-wrap:anywhere}a{color:#bfc6ff}
    </style><main><h1>Choose an account</h1>
    <form method="post" action="/oauth/select"><input type="hidden" name="selection" value="${selection}">
    <ul>${list}</ul></form><p><a href="/connect">Cancel</a></p></main></html>`, {
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
      'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" },
  });
}

export async function selectAccount(env, owner, selection, choice) {
  try {
    requireValue(/^[A-Za-z0-9_-]{43}$/.test(selection || '') && /^[0-9]{1,4}$/.test(choice || ''),
      'Choose an account from the list.');
    const sessionKey = [await hash(selection), owner, Date.now(), selectionAccount];
    const condition = ' WHERE state_hash = ? AND owner_id = ? AND expires_at >= ? AND account = ?';
    const session = await env.DB.prepare('SELECT * FROM oauth_sessions' + condition).bind(...sessionKey).first();
    requireValue(session, 'This account selection expired or was already used. Start a new connection.');
    const key = await keyFor(env);
    const { platform, candidates } = await decryptGrant(key, owner, selection, session.target);
    const candidate = requireValue(candidates[Number(choice)], 'Choose an account from the list.');
    const consumed = await env.DB.prepare('DELETE FROM oauth_sessions' + condition).bind(...sessionKey).run();
    requireValue(consumed.meta.changes === 1, 'This account selection was already used.');
    return await savePlatformConnection(env, key, owner, platform, session.started_at, candidate);
  } catch (error) {
    return connectionError(error instanceof AccountError ? error.message : 'Could not save the selected account. Start a new connection.');
  }
}

export async function accountCallback(request, env, owner) {
  let stage = 'load OAuth session';
  try {
    const query = new URL(request.url).searchParams;
    const state = query.get('state');
    requireValue(/^[A-Za-z0-9_-]{43}$/.test(state || '') && query.getAll('state').length === 1,
      'This connection link is invalid. Open the dashboard to start again.');
    const sessionKey = [await hash(state), owner, Date.now()];
    const session = await env.DB.prepare(
      'SELECT * FROM oauth_sessions WHERE state_hash = ? AND owner_id = ? AND expires_at >= ?',
    ).bind(...sessionKey).first();
    requireValue(session && session.account !== selectionAccount,
      'This connection link expired or was already used. Open the dashboard to start a fresh connection.');
    stage = 'consume OAuth session';
    const consumed = await env.DB.prepare(
      'DELETE FROM oauth_sessions WHERE state_hash = ? AND owner_id = ? AND expires_at >= ?',
    ).bind(...sessionKey).run();
    requireValue(consumed.meta.changes === 1,
      'This connection link expired or was already used. Open the dashboard to start a fresh connection.');
    requireValue(!query.has('error'), 'Account access was declined. Start again when you are ready to connect.');
    const code = query.get('code');
    requireValue(code && code.length <= 4096 && query.getAll('code').length === 1,
      'The provider did not return an authorization code.');
    stage = 'load provider configuration';
    const target = JSON.parse(session.target);
    const config = oauthSettings(env, target.platform);
    const key = await keyFor(env);
    stage = 'exchange and verify provider authorization';
    const candidates = await exchange(target, config, code, callbackUrl(request, env), session.verifier);
    stage = 'save verified connection';
    if (!platforms.includes(session.account)) return await saveConnection(env, key, owner, session, candidates[0]);
    if (candidates.length === 1) return await savePlatformConnection(env, key, owner, target.platform, session.started_at, candidates[0]);
    return await requestSelection(env, key, owner, target, session, candidates);
  } catch (error) {
    if (error instanceof AccountError) return connectionError(error.message);
    // Log a fixed stage label only. Provider bodies and OAuth parameters can contain credentials.
    console.error('Ifverse OAuth callback failed at ' + stage);
    return connectionError('The account service could not ' + stage + '. Open the dashboard to try again.');
  }
}
