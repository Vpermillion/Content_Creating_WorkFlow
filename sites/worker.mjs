import { accountCallback, accountTool, isGatewayAccount, publishingBindings, publishingGrants, selectAccount } from './accounts.mjs';

const VERSION = '2026-07-28';
const MAX_BODY_BYTES = 128 * 1024;
const MAX_RESULT_BYTES = 512 * 1024;

const string = (description, maxLength, extra = {}) => ({ type: 'string', description, maxLength, ...extra });
const choices = (description, values) => ({ type: 'string', description, enum: values });
const object = (properties, required = Object.keys(properties)) => ({
  type: 'object', properties, required, additionalProperties: false,
});
const array = (items, description, maxItems = 16) => ({ type: 'array', description, items, minItems: 1, maxItems });

const alias = string('Exact destination alias from the account registry.', 40, { pattern: '^[a-z0-9][a-z0-9-]{0,39}$' });
const brand = string('The registered brand, such as ifverse_anime.', 40, { pattern: '^[a-z0-9][a-z0-9_]{0,39}$' });
const draftId = string('The saved draft ID.', 32, { pattern: '^[0-9a-f]{32}$' });
const sha = string('Exact SHA-256 returned by the workflow.', 64, { pattern: '^[0-9a-f]{64}$' });
const requestId = string('Checked-in media review request ID.', 80, { pattern: '^[a-z0-9][a-z0-9_-]{0,79}$' });
const destination = object({
  account: alias,
  format: choices('Use a format supported by this destination.', ['short', 'reel', 'jpeg', 'feed', 'studio']),
  title: string('Platform-specific title.', 100),
  caption: string('Platform-specific caption to show in the review.', 5000),
  media_sha256: sha,
  manifest: { type: 'object', description: 'Existing media job provenance and actual owner review evidence.' },
});

function tool(name, description, inputSchema, annotations) {
  return { name, description, inputSchema, annotations };
}

const READ = { readOnlyHint: true };
const WRITE = { readOnlyHint: false, destructiveHint: false, idempotentHint: false };
const PUBLISH = { readOnlyHint: false, destructiveHint: true, idempotentHint: true };
const tools = [
  tool('ifverse_media_prepare', 'Run the existing reviewed media job without publishing.', object({ request_id: requestId }), WRITE),
  tool('ifverse_media_status', 'Read the media job status and prepared media hash.', object({ request_id: requestId }), READ),
  tool('ifverse_media_import', 'Stage a selected render from the private Ifverse GitHub repo. For a Facebook Reel or feed image, create a separate export and show it for review. This does not publish.', object({
    brand, episode: requestId,
    export: choices('Optional export type.', ['master', 'facebook_reel', 'jpeg']),
  }, ['brand', 'episode']), WRITE),
  tool('ifverse_accounts', 'List saved social accounts, destination aliases, and the hosted connection gateway.', object({}), READ),
  tool('ifverse_connect', 'Open the hosted gateway to pick a social platform, or start provider consent for a selected platform or preset.', object({
    account: string('A platform (youtube, instagram, facebook, tiktok) for any account, or a preset Ifverse destination alias.',
      40, { pattern: '^[a-z0-9][a-z0-9-]{0,39}$' }),
    method: choices('Optional TikTok method. Choose OAuth for an approved Login Kit app, or Studio for manual publishing.', ['studio', 'oauth']),
    page_id: string('The intended Facebook Page ID if it is not configured on the Site.', 32, { pattern: '^[0-9]+$' }),
    handle: string('Optional TikTok handle. Defaults to @ifverse_anime.', 25, { pattern: '^@?[a-zA-Z0-9_.]+$' }),
  }, []), WRITE),
  tool('ifverse_verify', 'Check a saved provider connection when troubleshooting. A new connection is checked automatically during consent.', object({ account: alias }), READ),
  tool('ifverse_prepare', 'Save a draft with exact media, platform captions, and accounts. Show its preview and ID before asking for approval.', object({
    brand, destinations: array(destination, 'Accounts from ifverse_accounts and the format for each account.', 4),
  }), WRITE),
  tool('ifverse_preview', 'Retrieve a saved draft from any chat with preview, snapshot hash, and actual delivery status.', object({ draft_id: draftId }), READ),
  tool('ifverse_status', 'Refresh saved publication receipts using read-only provider checks. Does not upload, resume, or publish.', object({ draft_id: draftId }), READ),
  tool('ifverse_publish', 'Only call after explicit user approval of the shown draft and exact destinations. For Instagram only, send only that alias. Retry only the requested destination. TikTok returns a Studio handoff.', object({
    draft_id: draftId, snapshot_hash: sha,
    destinations: { ...array(alias, 'Only aliases explicitly approved for this operation.', 4), uniqueItems: true },
    approved: { type: 'boolean', const: true },
  }), PUBLISH),
  tool('ifverse_verify_tiktok', 'With an eligible Display grant, check publication without posting. For a Studio-only connection, use the private browser verification link on the handoff receipt.', object({
    draft_id: draftId, snapshot_hash: sha, account: alias,
    video_id: string('Numeric TikTok post ID.', 20, { pattern: '^[0-9]{1,20}$' }),
  }), WRITE),
];
const toolsByName = new Map(tools.map((item) => [item.name, item]));
const accountTools = new Set(['ifverse_accounts', 'ifverse_connect', 'ifverse_verify']);
const brokered = new Set(['ifverse_publish', 'ifverse_status', 'ifverse_verify_tiktok']);
const routes = new Map([
  ['ifverse_media_prepare', '/jobs/prepare'], ['ifverse_media_status', '/jobs/get'],
  ['ifverse_media_import', '/jobs/import'],
  ['ifverse_accounts', '/accounts'], ['ifverse_connect', '/connect'], ['ifverse_verify', '/verify'],
  ['ifverse_prepare', '/drafts/create'], ['ifverse_preview', '/drafts/get'],
  ['ifverse_status', '/drafts/status'],
  ['ifverse_publish', '/drafts/publish'], ['ifverse_verify_tiktok', '/tiktok/verify'],
]);

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function valid(value, schema) {
  switch (schema.type) {
    case 'object':
      return isObject(value) && (!schema.properties || (
        schema.required.every((key) => Object.hasOwn(value, key))
        && Object.entries(value).every(([key, field]) => (
          Object.hasOwn(schema.properties, key) && valid(field, schema.properties[key])
        ))));
    case 'array':
      return Array.isArray(value) && value.length >= schema.minItems && value.length <= schema.maxItems
        && (!schema.uniqueItems || new Set(value).size === value.length)
        && value.every((item) => valid(item, schema.items));
    case 'string':
      return typeof value === 'string'
        && value.length >= (schema.minLength ?? 0) && value.length <= (schema.maxLength ?? Infinity)
        && (!schema.pattern || new RegExp(schema.pattern, 'u').test(value))
        && (!schema.enum || schema.enum.includes(value));
    case 'boolean':
      return typeof value === 'boolean' && (schema.const === undefined || value === schema.const);
    default:
      return false;
  }
}

async function readBody(message, limit) {
  if (Number(message.headers.get('content-length')) > limit || !message.body) throw new Error('Invalid request body.');
  const reader = message.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let bytes = 0;
  let text = '';
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > limit) {
        await reader.cancel();
        throw new Error('Body exceeds the size limit.');
      }
      text += decoder.decode(value, { stream: true });
    }
    return text + decoder.decode();
  } finally {
    reader.releaseLock();
  }
}

async function readJson(message, limit) {
  return JSON.parse(await readBody(message, limit));
}

function reply(id, result, status = 200) {
  return Response.json({ jsonrpc: '2.0', id, ...result }, { status, headers: { 'Cache-Control': 'no-store' } });
}

function rpcError(id, code, message, status = 200, data) {
  return reply(id, { error: { code, message, ...(data ? { data } : {}) } }, status);
}

function toolError(id, message) {
  return reply(id, { result: { isError: true, content: [{ type: 'text', text: message }] } });
}

function toolResult(id, result) {
  return reply(id, { result: { content: [{ type: 'text', text: JSON.stringify(result) }],
    structuredContent: isObject(result) ? result : { result } } });
}

function isOwner(request, env) {
  const owner = env.IFVERSE_SITE_OWNER_EMAIL?.trim().toLowerCase();
  return owner && request.headers.get('oai-authenticated-user-id')
    && request.headers.get('oai-authenticated-user-email')?.trim().toLowerCase() === owner;
}

function accountPage(html, status = 200, scriptNonce) {
  const csp = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'";
  return new Response(html, {
    status,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
      'Referrer-Policy': 'same-origin',
      'Content-Security-Policy': scriptNonce ? csp + "; connect-src 'self'; script-src 'nonce-" + scriptNonce + "'" : csp },
  });
}

const escapeHtml = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');

const labels = { youtube: 'YouTube', instagram: 'Instagram', facebook: 'Facebook', tiktok: 'TikTok' };

async function accountDashboard(request, env, owner, checkout) {
  const result = await accountTool(request, env, owner, 'ifverse_accounts', {});
  if (result.error) return accountPage('Account status is unavailable. Try again.', 503);
  const nonce = crypto.randomUUID();
  const accounts = Object.values(result.accounts);
  const completed = accounts.find(item => item.connected_at &&
    item.account === new URL(request.url).searchParams.get('connected'));
  const confirmation = checkout && completed
    ? '<div class="notice" role="status"><strong>' +
      escapeHtml(completed.handle || completed.display_name || completed.account_id) +
      '</strong> connected to Ifverse. Choose a platform to add another account.</div>'
    : '';
  const title = checkout ? 'Connect social accounts' : 'Ifverse Accounts';
  const connectForm = (account, label) =>
    '<form method="post" action="/oauth/connect"><input type="hidden" name="account" value="' +
    escapeHtml(account) + '"><button>' + escapeHtml(label) +
    '</button><p class="connection-status" role="status"></p></form>';
  const statusFor = item => ({
    connected: 'Connected', refresh_due: 'Refresh due', not_connected: 'Ready to connect',
  })[item.status];
  const platforms = Object.entries(result.platforms).map(([platform, setup]) => {
    const name = labels[platform];
    const connected = accounts.filter(item => item.platform === platform && !item.preset);
    const list = connected.length ? '<ul>' + connected.map(item =>
      '<li><strong>' + escapeHtml(item.display_name || item.handle || item.account_id) + '</strong><small>' +
      escapeHtml([item.handle || item.account_id, statusFor(item)].join(' · ')) + '</small></li>').join('') + '</ul>' : '';
    const action = !checkout ? '' : setup
      ? '<div class="setup"><strong>Needs setup</strong><p>The Ifverse administrator must enable this provider.</p></div>'
      : connectForm(platform, 'Connect ' + name);
    return '<section><h3>' + name + '</h3>' + list + action + '</section>';
  }).join('');
  const workflow = accounts.filter(item => item.preset).map(item => {
    const name = labels[item.platform];
    const status = item.setup_required && item.status === 'not_connected' ? 'Setup required' : statusFor(item);
    const target = item.handle || item.display_name || item.account_id;
    const action = item.setup_required
      ? '<p class="setup">' + escapeHtml(item.setup_required) + '</p>'
      : connectForm(item.account, (item.status === 'not_connected' ? 'Connect ' : 'Reconnect ') + name);
    const studio = item.platform === 'tiktok'
      ? '<p><a href="https://www.tiktok.com/tiktokstudio/upload">Open TikTok Studio for manual publishing</a></p>' : '';
    return '<section><h3>' + name + '</h3><p>' + escapeHtml(status) +
      (target ? ' · ' + escapeHtml(target) : '') + '</p>' + action + studio + '</section>';
  }).join('');
  return accountPage(`<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${title}</title>
    <style>
      :root{color-scheme:dark;background:#13151c;color:#edf0ff;font:1rem/1.5 "DM Sans",system-ui,sans-serif}
      main{margin:clamp(1.25rem,6vw,5rem) auto;padding:0 1.25rem;max-width:56rem}
      .accounts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,19rem),1fr));gap:1rem}
      section{border:1px solid #3b4053;border-radius:.8rem;background:#1c1f2b;padding:1.25rem}
      h2{margin:1.8rem 0 .65rem;font-size:1.25rem}
      h3,p{margin:.25rem 0 .85rem}h3{font-size:1.1rem}p,small{color:#c1c7df}
      ul{list-style:none;padding:0;margin:.5rem 0 1rem}li{padding:.55rem 0;border-bottom:1px solid #3b4053}
      li small{display:block}li,small{overflow-wrap:anywhere}
      button{border:0;border-radius:.45rem;background:#bfc6ff;color:#171a3c;font:inherit;font-weight:700;padding:.6rem 1rem;cursor:pointer}
      button:disabled{opacity:.65;cursor:wait}
      button:focus-visible,a:focus-visible{outline:2px solid #fff;outline-offset:3px}a{color:#bfc6ff}
      .setup{font-size:.94rem;color:#e8c087}.setup p{margin:.25rem 0 0}
      header{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;justify-content:space-between;margin-bottom:1.6rem}
      header h1{margin:0;line-height:1.15;letter-spacing:-.035em}
      .primary{display:inline-block;border-radius:.45rem;background:#bfc6ff;color:#171a3c;font-weight:700;
        padding:.6rem 1rem;text-decoration:none}
      .notice{margin:1rem 0;padding:.75rem 1rem;border:1px solid #5f8e7a;border-radius:.55rem;background:#183029}
      .connection-status{margin-top:.75rem}.connection-status:empty{margin:0}
    </style>
    <main>
      <header><h1>${title}</h1>${checkout ? '<a href="/">Back to account manager</a>'
        : '<a class="primary" href="/connect">Connect accounts</a>'}</header>
      ${checkout
        ? '<p>Choose a platform, switch to the account you want, then approve access. Repeat to add more accounts.</p>'
        : '<p>Manage the channels, Pages, and profiles linked to Ifverse.</p>'}
      ${confirmation}
      <div class="accounts">${platforms}</div>
      ${checkout ? '' : (result.publisher_configured ? '' : '<p class="setup">The publishing service needs setup.</p>') +
        '<h2>Preset workflow accounts</h2><div class="accounts">' + workflow + '</div>'}
    </main>
    <script nonce="${nonce}">
      for (const form of document.querySelectorAll('form[action="/oauth/connect"]')) {
        const button = form.querySelector('button');
        const status = form.querySelector('.connection-status');
        form.addEventListener('submit', async event => {
          event.preventDefault();
          if (button.disabled) return;
          button.disabled = true;
          status.textContent = 'Opening provider approval…';
          try {
            const response = await fetch(form.action, {
              method: 'POST',
              headers: { Accept: 'application/json' },
              body: new URLSearchParams(new FormData(form)),
            });
            const result = await response.json();
            if (response.ok && result.authorization_url) {
              window.location.assign(result.authorization_url);
              return;
            }
            status.textContent = result.error || 'Could not start the connection. Try again.';
          } catch {
            status.textContent = 'Could not reach Ifverse. Refresh and try again.';
          }
          button.disabled = false;
        });
        window.addEventListener('pageshow', event => {
          if (!event.persisted) return;
          button.disabled = false;
          status.textContent = '';
        });
      }
    </script></html>`, 200, nonce);
}

async function connectAccount(request, env, account) {
  const wantsJson = request.headers.get('Accept') === 'application/json';
  const fail = (message, status) => wantsJson
    ? Response.json({ error: message }, { status, headers: { 'Cache-Control': 'no-store' } })
    : accountPage('<p>' + escapeHtml(message) + '</p><p><a href="/">Back to accounts</a></p>', status);
  const site = new URL(env.IFVERSE_SITE_ORIGIN || request.url);
  if (!isOwner(request, env) || request.headers.get('Origin') !== site.origin) {
    return fail('Sign in as the Ifverse Site owner and start from the account page.', 403);
  }
  if (!account) {
    const type = request.headers.get('Content-Type')?.split(';')[0];
    if (type !== 'application/x-www-form-urlencoded') return fail('Use the account dashboard.', 415);
    try {
      const form = new URLSearchParams(await readBody(request, 256));
      account = form.get('account');
    } catch {
      return fail('Use the account dashboard.', 400);
    }
  }
  const result = await accountTool(request, env, request.headers.get('oai-authenticated-user-id'),
    'ifverse_connect', { account, ...(account === 'ifverse-tiktok' ? { method: 'oauth' } : {}) });
  if (result.authorization_url) {
    if (wantsJson) return Response.json({ authorization_url: result.authorization_url }, {
      headers: { 'Cache-Control': 'no-store' },
    });
    return accountPage('<p>Continue to the provider to authorize this connection.</p><p><a rel="noreferrer" href="' +
      escapeHtml(result.authorization_url) + '">Continue to provider</a></p><p><a href="/">Back to accounts</a></p>');
  }
  return fail(result.error || 'Consent could not start.', 400);
}

async function selectDestination(request, env) {
  const site = new URL(env.IFVERSE_SITE_ORIGIN || request.url);
  if (!isOwner(request, env) || request.headers.get('Origin') !== site.origin) {
    return accountPage('<p>Sign in as the Ifverse Site owner and start from the account page.</p>', 403);
  }
  if (request.headers.get('Content-Type')?.split(';')[0] !== 'application/x-www-form-urlencoded') {
    return accountPage('<p>Choose an account from the list.</p>', 415);
  }
  try {
    const form = new URLSearchParams(await readBody(request, 256));
    return await selectAccount(env, request.headers.get('oai-authenticated-user-id'), form.get('selection'), form.get('choice'));
  } catch {
    return accountPage('<p>Choose an account from the list.</p><p><a href="/">Back to accounts</a></p>', 400);
  }
}

function backendUrl(value, route) {
  const base = new URL(value);
  if (base.protocol !== 'https:' || base.username || base.password || base.pathname !== '/' || base.search || base.hash) {
    throw new Error('Configure the private HTTPS publishing service origin.');
  }
  return new URL(route, base);
}

async function fetchBackend(env, route, args) {
  return fetch(backendUrl(env.IFVERSE_BACKEND_URL, route), {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.IFVERSE_BACKEND_TOKEN}`, 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(args),
    redirect: 'error',
    signal: AbortSignal.timeout(25_000),
  });
}

async function brokerAliases(env, operation, args) {
  if (operation === 'ifverse_publish') return args.destinations;
  if (operation === 'ifverse_verify_tiktok') return [args.account];
  const response = await fetchBackend(env, '/drafts/get', { draft_id: args.draft_id });
  if (!response.ok) throw new Error('Draft unavailable.');
  const draft = await readJson(response, MAX_RESULT_BYTES);
  return draft.deliveries.filter(item => ['submitted', 'processing', 'needs_reconciliation'].includes(item.status))
    .map(item => item.alias);
}

async function callBackend(id, operation, args, env, owner) {
  const token = env.IFVERSE_BACKEND_TOKEN;
  if (!env.IFVERSE_BACKEND_URL || !token) return toolError(id, 'The private publishing service has not been configured.');
  try {
    const brokerDraft = env.DB && operation === 'ifverse_prepare' &&
      args.destinations.some(item => isGatewayAccount(item.account));
    const useBroker = env.DB && (brokerDraft || brokered.has(operation));
    let route = routes.get(operation);
    if (useBroker) {
      const aliases = brokerDraft ? args.destinations.map(item => item.account) : await brokerAliases(env, operation, args);
      const bindings = await publishingBindings(env, owner, aliases);
      if (brokerDraft) {
        if (aliases.some(item => isGatewayAccount(item) && !Object.hasOwn(bindings, item))) {
          return toolError(id, 'Connect the selected account in the Ifverse gateway before creating a draft.');
        }
        args = { ...args, account_bindings: bindings };
      } else {
        args = { ...args, account_grants: await publishingGrants(env, owner, aliases),
          ...(Object.keys(bindings).length ? { account_bindings: bindings } : {}) };
      }
      route = '/broker' + route;
    }
    const response = await fetchBackend(env, route, args);
    if (response.status === 401 || response.status === 403) return toolError(id, 'The private publishing service rejected its Site credential.');
    if (response.status >= 500 || response.redirected) throw new Error('Backend unavailable.');
    const result = await readJson(response, MAX_RESULT_BYTES);
    if (!response.ok) {
      const message = useBroker
        ? 'The publishing service rejected the broker request. Check the deployed publisher version and the selected account connection.'
        : typeof result?.error === 'string' ? result.error : 'The publishing service rejected the request.';
      return toolError(id, message.slice(0, 1000));
    }
    return toolResult(id, result);
  } catch {
    return toolError(id, 'The private publishing service did not respond. Check the draft status before repeating a write.');
  }
}

async function mcp(request, env) {
  let message;
  try {
    message = await readJson(request, MAX_BODY_BYTES);
  } catch {
    return rpcError(null, -32700, 'Invalid JSON request.', 400);
  }
  if (!isObject(message) || message.jsonrpc !== '2.0' || typeof message.method !== 'string'
      || !(typeof message.id === 'string' || Number.isSafeInteger(message.id))) {
    return rpcError(null, -32600, 'Invalid JSON-RPC request.', 400);
  }

  const { id, method, params } = message;
  const headerMethod = request.headers.get('mcp-method');
  const headerVersion = request.headers.get('mcp-protocol-version');
  const metaVersion = params?._meta?.['io.modelcontextprotocol/protocolVersion'];
  const requestedVersion = headerVersion ?? metaVersion;
  if ((headerMethod && headerMethod !== method) || (headerVersion && metaVersion && headerVersion !== metaVersion)) {
    return rpcError(id, -32600, 'MCP request headers do not match the request body.', 400);
  }
  if (method === 'server/discover') {
    return reply(id, { result: { supportedVersions: [VERSION], capabilities: { tools: {} },
      serverInfo: { name: 'ifverse-publishing', version: '1.0.0' } } });
  }
  if (requestedVersion && requestedVersion !== VERSION) {
    return rpcError(id, -32022, 'Unsupported protocol version', 400, { supported: [VERSION], requested: requestedVersion });
  }
  if (method === 'tools/list') return reply(id, { result: { tools } });
  if (method === 'ping') return reply(id, { result: {} });
  if (method !== 'tools/call') return rpcError(id, -32601, 'Method not found.');
  if (!isOwner(request, env)) return rpcError(id, -32000, 'Only the authenticated Site owner can use publishing tools.', 403);

  const descriptor = toolsByName.get(params?.name);
  const headerName = request.headers.get('mcp-name');
  const args = params?.arguments ?? {};
  if (!descriptor || (headerName && headerName !== descriptor.name) || !valid(args, descriptor.inputSchema)) {
    return rpcError(id, -32602, 'Unknown tool or invalid tool arguments.');
  }
  if (env.DB && accountTools.has(descriptor.name)) {
    const result = await accountTool(request, env, request.headers.get('oai-authenticated-user-id'), descriptor.name, args);
    return result.error ? toolError(id, result.error) : toolResult(id, result);
  }
  return callBackend(id, descriptor.name, args, env, request.headers.get('oai-authenticated-user-id'));
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (['/', '/connect'].includes(path) && request.method === 'GET') {
      if (!isOwner(request, env)) return accountPage('Sign in as the Ifverse Site owner.', 403);
      return accountDashboard(request, env, request.headers.get('oai-authenticated-user-id'), path === '/connect');
    }
    if (request.method === 'POST' && env.DB && ['/oauth/connect', '/oauth/connect/youtube'].includes(path)) {
      return connectAccount(request, env, path.endsWith('/youtube') ? 'ifverse-anime' : undefined);
    }
    if (path === '/oauth/select' && request.method === 'POST' && env.DB) return selectDestination(request, env);
    if (path === '/oauth/callback' && request.method === 'GET' && env.DB) {
      if (!isOwner(request, env)) return new Response('Sign in as the Site owner to connect an account.', {
        status: 403, headers: { 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' },
      });
      return accountCallback(request, env, request.headers.get('oai-authenticated-user-id'));
    }
    if (path !== '/mcp') return new Response('Not found.', { status: 404 });
    if (request.method !== 'POST') return new Response('Method not allowed.', { status: 405, headers: { Allow: 'POST' } });
    return mcp(request, env);
  },
};
