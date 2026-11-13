import { accountCallback, accountTool } from './accounts.mjs';

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
  tool('ifverse_accounts', 'List intended destinations and supported formats.', object({}), READ),
  tool('ifverse_connect', 'Open provider consent to connect an Ifverse account. The callback checks the account and saves the connection automatically. If TikTok Login Kit is unavailable, return the Studio link.', object({
    account: alias,
    method: choices('Optional TikTok method. Choose OAuth for an approved Login Kit app, or Studio for manual publishing.', ['studio', 'oauth']),
    page_id: string('The intended Facebook Page ID, required when connecting Facebook.', 32, { pattern: '^[0-9]+$' }),
    handle: string('The intended TikTok handle, required for TikTok OAuth.', 25, { pattern: '^@?[a-zA-Z0-9_.]+$' }),
  }, ['account']), WRITE),
  tool('ifverse_verify', 'Check a saved provider connection when troubleshooting. A new connection is checked automatically during consent.', object({ account: alias }), READ),
  tool('ifverse_prepare', 'Save a draft with exact media, platform captions, and accounts. Show its preview and ID before asking for approval.', object({
    brand, destinations: array(destination, 'The selected destination accounts and formats.', 4),
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

async function readJson(message, limit) {
  if (Number(message.headers.get('content-length')) > limit || !message.body) throw new Error('Invalid JSON body.');
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
        throw new Error('JSON body exceeds the size limit.');
      }
      text += decoder.decode(value, { stream: true });
    }
    return JSON.parse(text + decoder.decode());
  } finally {
    reader.releaseLock();
  }
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

function backendUrl(value, route) {
  const base = new URL(value);
  if (base.protocol !== 'https:' || base.username || base.password || base.pathname !== '/' || base.search || base.hash) {
    throw new Error('Configure the private HTTPS publishing service origin.');
  }
  return new URL(route, base);
}

async function callBackend(id, operation, args, env) {
  const token = env.IFVERSE_BACKEND_TOKEN;
  if (!env.IFVERSE_BACKEND_URL || !token) return toolError(id, 'The private publishing service has not been configured.');
  try {
    const response = await fetch(backendUrl(env.IFVERSE_BACKEND_URL, routes.get(operation)), {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(args),
      redirect: 'error',
      signal: AbortSignal.timeout(25_000),
    });
    if (response.status === 401 || response.status === 403) return toolError(id, 'The private publishing service rejected its Site credential.');
    if (response.status >= 500 || response.redirected) throw new Error('Backend unavailable.');
    const result = await readJson(response, MAX_RESULT_BYTES);
    if (!response.ok) {
      const message = typeof result?.error === 'string' ? result.error : 'The publishing service rejected the request.';
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
  return callBackend(id, descriptor.name, args, env);
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path === '/' && request.method === 'GET') {
      return new Response('Ifverse Publishing. Open the private Ifverse Publishing app in ChatGPT to use its publishing tools.');
    }
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

