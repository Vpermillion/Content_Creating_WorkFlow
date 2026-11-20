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
