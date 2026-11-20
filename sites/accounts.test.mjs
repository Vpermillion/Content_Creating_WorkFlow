import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { test } from 'node:test';
import worker from './worker.mjs';

const origin = 'https://ifverse.example.test';
const owner = {
  'oai-authenticated-user-id': 'owner-id',
  'oai-authenticated-user-email': 'owner@example.test',
};
const channelId = 'UCpB_wi5MlernpSJxUf7zWcw';
const scopes = 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload';

function fixture(t) {
  const db = new DatabaseSync(':memory:');
  t.after(() => db.close());
  db.exec(readFileSync(new URL('./drizzle/0000_account_connections.sql', import.meta.url), 'utf8'));
  const env = {
    DB: {
      prepare(sql) {
        const statement = db.prepare(sql);
        return {
          bind(...args) {
            return {
              first: async () => statement.get(...args),
              run: async () => ({ meta: statement.run(...args) }),
              all: async () => ({ results: statement.all(...args) }),
            };
          },
        };
      },
      batch: statements => Promise.all(statements.map(statement => statement.run())),
    },
    IFVERSE_SITE_OWNER_EMAIL: 'owner@example.test',
    IFVERSE_SITE_ORIGIN: origin,
    IFVERSE_ACCOUNT_KEY: Buffer.alloc(32, 97).toString('base64url'),
    IFVERSE_OAUTH_CONFIG: JSON.stringify({ youtube: { client_id: 'google-test', client_secret: 'fixture' } }),
  };
  async function tool(name, args) {
    const response = await worker.fetch(new Request(origin + '/mcp', {
      method: 'POST', headers: { ...owner, 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args } }),
    }), env);
    return (await response.json()).result;
  }
  async function connect() {
    const response = await tool('ifverse_connect', { account: 'ifverse-anime' });
    return new URL(response.structuredContent.authorization_url).searchParams.get('state');
  }
  function callback(state, identity = owner) {
    return worker.fetch(new Request(origin + '/oauth/callback?' + new URLSearchParams({ state, code: 'fixture-code' }),
      { headers: identity }), env);
  }
  return { db, env, tool, connect, callback };
}

test('provider consent checks the destination and persists a private grant without a separate verify action', async t => {
  const f = fixture(t);
  let exchanges = 0;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url === 'https://oauth2.googleapis.com/token') {
      exchanges += 1;
      const form = new URLSearchParams(options.body);
      assert.equal(form.get('redirect_uri'), origin + '/oauth/callback');
      assert.match(form.get('code_verifier'), /^[A-Za-z0-9_-]{64}$/);
      return Response.json({ access_token: 'test-access', refresh_token: 'test-refresh', scope: scopes, expires_in: 3600 });
    }
    assert.equal(options.headers.Authorization, 'Bearer test-access');
    return Response.json({ items: [{ id: channelId, snippet: { title: 'Ifverse' } }] });
  });
  const state = await f.connect();
  assert.equal((await f.callback(state, {})).status, 403);
  assert.equal((await f.callback(state, { ...owner, 'oai-authenticated-user-id': 'other' })).status, 400);
  const linked = await f.callback(state);
  assert.equal(linked.status, 303);
  assert.equal(linked.headers.get('Location'), '/');
  assert.equal((await f.callback(state)).status, 400);
  assert.equal(exchanges, 1);
  const saved = f.db.prepare('SELECT grant FROM account_connections').get();
  assert.doesNotMatch(saved.grant, /test-access|test-refresh/);
  const accounts = await f.tool('ifverse_accounts', {});
  assert.equal(accounts.structuredContent.accounts['ifverse-anime'].status, 'connected');
  assert.equal(accounts.structuredContent.accounts['ifverse-anime'].account_id, channelId);
  assert.doesNotMatch(JSON.stringify(accounts), /test-access|test-refresh/);
  const verified = await f.tool('ifverse_verify', { account: 'ifverse-anime' });
  assert.equal(verified.structuredContent.verified, true);
});

test('wrong account and expired or reused state cannot create a connection', async t => {
  const f = fixture(t);
  t.mock.method(globalThis, 'fetch', async url => Response.json(url === 'https://oauth2.googleapis.com/token'
    ? { access_token: 'test-access', refresh_token: 'test-refresh', scope: scopes, expires_in: 3600 }
    : { items: [{ id: 'different-channel' }] }));
  const state = await f.connect();
  assert.match(await (await f.callback(state)).text(), /different YouTube channel/);
  assert.match(await (await f.callback(state)).text(), /already used/);
  const expired = await f.connect();
  f.db.exec('UPDATE oauth_sessions SET expires_at = 0');
  const expiredResult = await f.callback(expired);
  assert.equal(expiredResult.status, 400);
  const errorPage = await expiredResult.text();
  assert.match(errorPage, /expired/);
  assert.ok(errorPage.includes('<a href="/">Back to accounts</a>'));
  assert.equal(f.db.prepare('SELECT count(*) AS total FROM account_connections').get().total, 0);
  const studio = await f.tool('ifverse_connect', { account: 'ifverse-tiktok', method: 'studio' });
  assert.equal(studio.structuredContent.status, 'studio_handoff');
});

test('one-click dashboard starts consent, survives phone verification and returns to the linked account', async t => {
  const f = fixture(t);
  t.mock.timers.enable({ apis: ['Date'], now: Date.now() });
  f.env.IFVERSE_BACKEND_URL = 'https://publisher.example.test';
  f.env.IFVERSE_BACKEND_TOKEN = 'private-publisher-test';
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url === 'https://oauth2.googleapis.com/token') {
      return Response.json({ access_token: 'test-access', refresh_token: 'test-refresh', scope: scopes, expires_in: 3600 });
    }
    if (String(url).startsWith(f.env.IFVERSE_BACKEND_URL)) {
      calls.push({ url: String(url), auth: options.headers.Authorization, body: JSON.parse(options.body) });
      return Response.json({ deliveries: [{ alias: 'ifverse-anime', status: 'submitted' }] });
    }
    return Response.json({ items: [{ id: channelId, snippet: { title: 'Ifverse' } }] });
  });
  const page = await worker.fetch(new Request(origin, { headers: owner }), f.env);
  const html = await page.text();
  assert.match(html, /Connect YouTube/);
  assert.match(html, /Instagram/);
  assert.match(html, /Facebook/);
  assert.match(html, /Open TikTok Studio/);
  const nonce = html.match(/<script nonce="([^"]+)">/)[1];
  assert.ok(page.headers.get('Content-Security-Policy').includes("'nonce-" + nonce + "'"));
  const form = (host, accept = 'application/json') => worker.fetch(new Request(origin + '/oauth/connect', {
    method: 'POST', headers: { ...owner, Origin: host, Accept: accept },
    body: new URLSearchParams({ account: 'ifverse-anime' }),
  }), f.env);
  const refused = await form('https://other.example.test');
  assert.equal(refused.status, 403);
  assert.match((await refused.json()).error, /start from the account page/);
  const fallback = await form(origin, 'text/html');
  assert.match(await fallback.text(), /Continue to provider/);
  const start = await form(origin);
  assert.equal(start.status, 200);
  const authorization = new URL((await start.json()).authorization_url);
  assert.equal(authorization.origin, 'https://accounts.google.com');
  const state = authorization.searchParams.get('state');
  t.mock.timers.tick(12 * 60 * 1000);
  const callback = await f.callback(state);
  assert.equal(callback.status, 303);
  assert.equal(callback.headers.get('Location'), '/');
  const dashboard = await worker.fetch(new Request(origin, { headers: owner }), f.env);
  assert.match(await dashboard.text(), /Connected · @ifverse_anime/);
  const args = { draft_id: 'd'.repeat(32), snapshot_hash: 'a'.repeat(64), destinations: ['ifverse-anime'], approved: true };
  const result = await f.tool('ifverse_publish', args);
  assert.equal(result.structuredContent.deliveries[0].status, 'submitted');
  assert.doesNotMatch(JSON.stringify(result), /test-access|test-refresh|private-publisher-test/);
  assert.deepEqual(calls, [{ url: f.env.IFVERSE_BACKEND_URL + '/broker/drafts/publish',
    auth: 'Bearer private-publisher-test', body: { ...args, account_grants: {
      'ifverse-anime': { platform: 'youtube', account_id: channelId, token: 'test-access' },
    } } }]);
});

async function startPlatform(f, account) {
  const result = await worker.fetch(new Request(origin + '/oauth/connect', {
    method: 'POST', headers: { ...owner, Origin: origin, Accept: 'application/json' },
    body: new URLSearchParams({ account }),
  }), f.env);
  assert.equal(result.status, 200);
  return new URL((await result.json()).authorization_url);
}

function select(f, selection, choice, headers = {}) {
  return worker.fetch(new Request(origin + '/oauth/select', {
    method: 'POST', headers: { ...owner, Origin: origin, ...headers },
    body: new URLSearchParams({ selection, choice }),
  }), f.env);
}

test('one provider login can add more than one channel with isolated, stable connections', async t => {
  const f = fixture(t);
  const channelA = 'UC' + 'a'.repeat(22);
  const channelB = 'UC' + 'b'.repeat(22);
  const rows = () => f.db.prepare('SELECT * FROM account_connections ORDER BY provider_id').all();
  t.mock.method(globalThis, 'fetch', async url => {
    const endpoint = new URL(url);
    if (endpoint.hostname === 'oauth2.googleapis.com') {
      return Response.json({ access_token: 'private-access', refresh_token: 'private-refresh', scope: scopes, expires_in: 3600 });
    }
    assert.equal(endpoint.searchParams.get('mine'), 'true');
    return Response.json(endpoint.searchParams.has('pageToken')
      ? { items: [{ id: channelB, snippet: { title: '<Second>', customUrl: '@second' } }] }
      : { items: [{ id: channelA, snippet: { title: 'First', customUrl: '@first' } }], nextPageToken: 'next' });
  });
  async function chooser() {
    const authorize = await startPlatform(f, 'youtube');
    assert.equal(authorize.searchParams.get('prompt'), 'consent select_account');
    const response = await f.callback(authorize.searchParams.get('state'));
    assert.equal(response.status, 200);
    const page = await response.text();
    assert.match(page, /Choose an account/);
    assert.match(page, /&lt;Second&gt;/);
    assert.doesNotMatch(page, /private-access|private-refresh|<Second>/);
    return page.match(/name="selection" value="([^"]+)"/)[1];
  }
  const selection = await chooser();
  assert.equal(rows().length, 0);
  assert.doesNotMatch(f.db.prepare('SELECT target FROM oauth_sessions').get().target, /private-access|private-refresh/);
  assert.equal((await select(f, selection, '0', { Origin: 'https://elsewhere.example' })).status, 403);
  assert.equal((await select(f, selection, '0', { 'oai-authenticated-user-id': 'elsewhere' })).status, 400);
  assert.equal((await select(f, selection, '50')).status, 400);
  assert.equal((await select(f, selection, '0')).status, 303);
  assert.equal((await select(f, selection, '1')).status, 400);
  assert.deepEqual(rows().map(row => row.provider_id), [channelA]);
  assert.equal((await select(f, await chooser(), '1')).status, 303);
  assert.deepEqual(rows().map(row => row.provider_id), [channelA, channelB]);
  assert.equal((await select(f, await chooser(), '0')).status, 303);
  assert.equal(rows().length, 2);
  const accounts = (await f.tool('ifverse_accounts', {})).structuredContent.accounts;
  assert.equal(accounts['ifverse-anime'].status, 'not_connected');
  for (const row of rows()) {
    assert.equal(accounts[row.account].workflow_destination, false);
    assert.equal(accounts[row.account].account_id, row.provider_id);
    assert.equal((await f.tool('ifverse_verify', { account: row.account })).structuredContent.verified, true);
  }
  const dashboard = await (await worker.fetch(new Request(origin, { headers: owner }), f.env)).text();
  assert.match(dashboard, /Add YouTube account/);
  assert.match(dashboard, /@first · Connected/);
  assert.match(dashboard, /@second · Connected/);
});

test('Facebook and Instagram derive authorized destinations without a configured Page ID', async t => {
  const f = fixture(t);
  f.env.IFVERSE_OAUTH_CONFIG = JSON.stringify({ meta: { client_id: 'meta-client', client_secret: 'fixture', graph_version: 'v25.0' } });
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    const endpoint = new URL(url);
    assert.equal(endpoint.hostname, 'graph.facebook.com');
    if (endpoint.pathname.endsWith('/oauth/access_token')) return Response.json({ access_token: 'person-token' });
    if (endpoint.pathname.endsWith('/me/permissions')) return Response.json({
      data: ['pages_show_list', 'pages_read_engagement', 'pages_manage_posts', 'instagram_basic', 'instagram_content_publish']
        .map(permission => ({ permission, status: 'granted' })),
    });
    if (endpoint.pathname.endsWith('/me/accounts')) return Response.json({ data: [
      { id: '101', name: 'First Page', access_token: 'first-token', instagram_business_account: { id: '301', username: 'instagram_first' } },
      { id: '102', name: 'Second Page', access_token: 'second-token' },
    ] });
    if (endpoint.pathname.endsWith('/301')) {
      assert.equal(options.headers.Authorization, 'Bearer first-token');
      return Response.json({ id: '301', username: 'instagram_first' });
    }
    assert.equal(endpoint.pathname, '/v25.0/102');
    assert.equal(options.headers.Authorization, 'Bearer second-token');
    return Response.json({ id: '102', name: 'Second Page' });
  });
  const instagram = await startPlatform(f, 'instagram');
  assert.equal((await f.callback(instagram.searchParams.get('state'))).status, 303);
  const facebook = await startPlatform(f, 'facebook');
  const page = await (await f.callback(facebook.searchParams.get('state'))).text();
  assert.match(page, /Second Page/);
  assert.doesNotMatch(page, /first-token|second-token/);
  const selection = page.match(/name="selection" value="([^"]+)"/)[1];
  assert.equal((await select(f, selection, '1')).status, 303);
  const linked = f.db.prepare('SELECT account, provider_id, handle FROM account_connections ORDER BY account').all();
  assert.deepEqual(linked.map(item => [item.account.split('-')[0], item.provider_id, item.handle]),
    [['facebook', '102', ''], ['instagram', '301', '@instagram_first']]);
});

test('TikTok saves the consented account without a preset handle', async t => {
  const f = fixture(t);
  f.env.IFVERSE_OAUTH_CONFIG = JSON.stringify({ tiktok: { client_id: 'tiktok-client', client_secret: 'fixture' } });
  t.mock.method(globalThis, 'fetch', async url => {
    const endpoint = new URL(url);
    assert.equal(endpoint.hostname, 'open.tiktokapis.com');
    if (endpoint.pathname.includes('/oauth/token/')) return Response.json({
      access_token: 'private-access', refresh_token: 'private-refresh', scope: 'user.info.basic,user.info.profile,video.list',
      open_id: 'stable-tiktok-id', expires_in: 3600,
    });
    return Response.json({ data: { user: { open_id: 'stable-tiktok-id', username: 'different_account' } } });
  });
  const authorize = await startPlatform(f, 'tiktok');
  assert.equal(authorize.searchParams.get('client_key'), 'tiktok-client');
  assert.equal((await f.callback(authorize.searchParams.get('state'))).status, 303);
  const row = f.db.prepare('SELECT account, provider_id, handle FROM account_connections').get();
  assert.match(row.account, /^tiktok-/);
  assert.equal(row.provider_id, 'stable-tiktok-id');
  assert.equal(row.handle, '@different_account');
});
