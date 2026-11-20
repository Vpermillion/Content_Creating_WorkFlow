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

class AccountError extends Error {}

function requireValue(value, message) {
  if (!value) throw new AccountError(message);
  return value;
}

function base64(bytes) {
  return btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
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
    'Add the ' + provider + ' OAuth client in the private Ifverse Site settings.');
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
  const row = Object.hasOwn(accounts, account) ? accounts[account] : null;
  requireValue(row, 'Choose an Ifverse account alias from the account list.');
  if (row.platform === 'facebook') {
    const pageId = env.IFVERSE_FACEBOOK_PAGE_ID || args.page_id || '';
    requireValue(/^[0-9]{1,32}$/.test(pageId), 'Set the intended Facebook Page ID before connecting Facebook.');
    requireValue(!args.page_id || args.page_id === pageId, 'Select the configured Ifverse Facebook Page.');
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
  requireValue(/^[A-Za-z0-9_-]{43}$/.test(secret), 'Set the Ifverse account storage key in private Site settings.');
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
    throw new AccountError('Ifverse could not reach the provider. Try connecting again.');
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

async function youtubeIdentity(token, target) {
  const result = await providerJson('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true&maxResults=50', { token });
  const match = result.items?.find(item => item.id === target.account_id);
  requireValue(match, 'Google authorized a different YouTube channel. Choose @ifverse_anime during consent.');
  const handleMatch = await providerJson(urlWith('https://www.googleapis.com/youtube/v3/channels',
    { part: 'id', forHandle: target.handle }), { token });
  requireValue(handleMatch.items?.length === 1 && handleMatch.items[0].id === match.id,
    'Google authorized a different YouTube channel. Choose @ifverse_anime during consent.');
  return { id: match.id, handle: target.handle, name: match.snippet?.title || target.handle };
}

async function metaIdentity(platform, base, id, token, expectedHandle) {
  const fields = platform === 'instagram' ? 'id,username' : 'id,name';
  const result = await providerJson(urlWith(base + '/' + id, { fields }), { token });
  requireValue(result.id === id && (platform !== 'instagram' || handleKey(result.username) === handleKey(expectedHandle)),
    'Meta returned a different account. Check the Page and its linked Instagram profile.');
  return { id, handle: result.username ? '@' + result.username : '', name: result.name || result.username || '' };
}

async function tiktokIdentity(token, handle, expectedId) {
  const response = await providerJson('https://open.tiktokapis.com/v2/user/info/?fields=open_id,username,display_name', { token });
  const user = response.data?.user;
  requireValue(user?.open_id === expectedId && handleKey(user.username) === handleKey(handle),
    'TikTok authorized a different account. Choose the requested handle during consent.');
  return { id: user.open_id, handle: '@' + user.username, name: user.display_name || user.username };
}

async function metaPage(base, platform, target, token) {
  const fields = platform === 'instagram' ? 'id,access_token,instagram_business_account{id,username}' : 'id,access_token';
  const params = { fields, limit: '100' };
  const matches = new Map();
  const seen = new Set();
  for (;;) {
    const result = await providerJson(urlWith(base + '/me/accounts', params), { token });
    for (const page of result.data || []) {
      const instagram = page.instagram_business_account;
      const matchesTarget = platform === 'facebook' ? page.id === target.account_id
        : instagram?.id && handleKey(instagram.username) === handleKey(target.handle);
      if (matchesTarget && /^[0-9]+$/.test(page.id) && page.access_token) matches.set(page.id, page);
    }
    if (!result.paging?.next) break;
    const after = result.paging.cursors?.after;
    requireValue(after && !seen.has(after) && seen.size < 10, 'Meta could not finish listing the authorized Pages.');
    seen.add(after);
    params.after = after;
  }
  requireValue(matches.size === 1, 'Consent did not include the intended Facebook Page or its linked Instagram profile.');
  return matches.values().next().value;
}

async function exchange(target, config, code, redirect, verifier) {
  const { platform } = target;
  const client = { client_id: config.client_id, client_secret: config.client_secret };
  const common = { code, redirect_uri: redirect, grant_type: 'authorization_code' };
  if (platform === 'youtube') {
    const result = await providerJson(googleToken, { form: { ...client, ...common, code_verifier: verifier } });
    requireValue(result.access_token && result.refresh_token && hasScopes(result.scope, googleScopes),
      'Google consent must include YouTube access, upload permission, and offline access.');
    return { identity: await youtubeIdentity(result.access_token, target),
      grant: { token: result.access_token, refresh: result.refresh_token, client: config.client_id },
      expiresAt: expiry(result.expires_in) };
  }
  if (platform === 'tiktok') {
    const result = await providerJson(tiktokToken, { form: { ...common, client_key: config.client_id, client_secret: config.client_secret } });
    requireValue(result.access_token && result.refresh_token && result.open_id && hasScopes(result.scope, tiktokScopes),
      'TikTok consent must include profile and video access.');
    return { identity: await tiktokIdentity(result.access_token, target.handle, result.open_id),
      grant: { token: result.access_token, refresh: result.refresh_token, client: config.client_id },
      expiresAt: expiry(result.expires_in) };
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
  const page = await metaPage(base, platform, target, durable.access_token);
  const id = platform === 'facebook' ? page.id : page.instagram_business_account.id;
  requireValue(/^[0-9]+$/.test(id), 'Meta did not return a valid account ID.');
  const identity = await metaIdentity(platform, base, id, page.access_token, target.handle);
  return { identity, grant: { token: page.access_token, client: config.client_id, page_id: page.id }, expiresAt: null };
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
    Object.assign(query, { client_key: config.client_id, scope: tiktokScopes.join(',') });
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
  const { platform, account_id, handle } = accounts[account];
  return {
    account, platform, brand, account_id: row?.provider_id || account_id || null,
    handle: row?.handle || handle || null, display_name: row?.display_name || null,
    status: !row ? 'not_connected' : row.expires_at && row.expires_at <= Date.now() ? 'refresh_due' : 'connected',
    connected_at: row ? new Date(row.connected_at).toISOString() : null,
    ...(platform === 'tiktok' ? { publishing: 'studio_handoff' } : {}),
  };
}

async function activeGrant(env, owner, account, minimumLifetime) {
  requireValue(Object.hasOwn(accounts, account), 'Choose an Ifverse account alias from the account list.');
  const row = await env.DB.prepare('SELECT * FROM account_connections WHERE owner_id = ? AND account = ?')
    .bind(owner, account).first();
  if (!row) return null;
  const platform = accounts[account].platform;
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
  if (platform === 'youtube') await youtubeIdentity(grant.token, accounts[account]);
  else if (platform === 'tiktok') await tiktokIdentity(grant.token, row.handle, row.provider_id);
  else await metaIdentity(platform, 'https://graph.facebook.com/' + config.graph_version, row.provider_id, grant.token, row.handle);
  return { ...publicAccount(account, row), verified: true };
}

// Only used for server-to-server requests to the configured publishing service.
export async function publishingGrants(env, owner, aliases) {
  const grants = {};
  for (const alias of new Set(aliases)) {
    if (!Object.hasOwn(accounts, alias)) continue;
    let connection;
    try {
      connection = await activeGrant(env, owner, alias, 15 * 60_000);
    } catch (error) {
      if (!(error instanceof AccountError)) throw error;
      continue;
    }
    if (!connection) continue;
    const { row, grant, config, platform } = connection;
    if (platform === 'facebook' && env.IFVERSE_FACEBOOK_PAGE_ID && row.provider_id !== env.IFVERSE_FACEBOOK_PAGE_ID) continue;
    grants[alias] = { platform, account_id: row.provider_id, token: grant.token,
      ...(platform in metaScopes ? { graph_version: config.graph_version,
        ...(platform === 'instagram' ? { page_id: grant.page_id } : {}) } : {}) };
  }
  return grants;
}

function connectionSetup(env, platform) {
  try {
    oauthSettings(env, platform);
  } catch (error) {
    return error instanceof AccountError ? error.message : 'Check the private OAuth client settings.';
  }
  if (platform === 'facebook' && !/^[0-9]{1,32}$/.test(env.IFVERSE_FACEBOOK_PAGE_ID || '')) {
    return 'Set the intended Facebook Page ID in the private Site settings.';
  }
  return null;
}

export async function accountTool(request, env, owner, name, args) {
  try {
    if (name === 'ifverse_connect') return await begin(request, env, owner, args);
    if (name === 'ifverse_verify') return await verify(env, owner, args.account);
    const saved = await env.DB.prepare('SELECT account, provider_id, handle, display_name, expires_at, connected_at FROM account_connections WHERE owner_id = ?')
      .bind(owner).all();
    const records = new Map(saved.results.map(row => [row.account, row]));
    return {
      accounts: Object.fromEntries(Object.keys(accounts).map(account => {
        const item = publicAccount(account, records.get(account));
        return [account, { ...item, setup_required: connectionSetup(env, item.platform) }];
      })),
      formats,
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
    <title>Connection needs attention · Ifverse</title>
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
    requireValue(session, 'This connection link expired or was already used. Open the dashboard to start a fresh connection.');
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
    const { identity, grant, expiresAt } = await exchange(target, config, code, callbackUrl(request, env), session.verifier);
    stage = 'save verified connection';
    const result = await env.DB.prepare(
      `INSERT INTO account_connections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(owner_id, account) DO UPDATE SET provider_id = excluded.provider_id, handle = excluded.handle,
       display_name = excluded.display_name, grant = excluded.grant, expires_at = excluded.expires_at,
       started_at = excluded.started_at, connected_at = excluded.connected_at
       WHERE excluded.started_at >= account_connections.started_at`,
    ).bind(owner, session.account, identity.id, identity.handle, identity.name,
      await encryptGrant(key, owner, session.account, grant), expiresAt, session.started_at, Date.now()).run();
    requireValue(result.meta.changes === 1, 'A newer account connection is already active.');
    return new Response(null, {
      status: 303,
      headers: { Location: '/', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' },
    });
  } catch (error) {
    if (error instanceof AccountError) return connectionError(error.message);
    // Log a fixed stage label only. Provider bodies and OAuth parameters can contain credentials.
    console.error('Ifverse OAuth callback failed at ' + stage);
    return connectionError('Ifverse could not ' + stage + '. Open the dashboard to try again.');
  }
}
