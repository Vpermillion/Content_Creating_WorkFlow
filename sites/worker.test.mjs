import assert from 'node:assert/strict';
import { test } from 'node:test';
import worker from './worker.mjs';

const owner = { 'oai-authenticated-user-id': 'fixture', 'oai-authenticated-user-email': 'owner@example.test' };
const env = { IFVERSE_SITE_OWNER_EMAIL: 'owner@example.test', IFVERSE_BACKEND_URL: 'https://api.example.test',
  IFVERSE_BACKEND_TOKEN: 'fixture-token' };
const draft = 'a'.repeat(32);
const digest = 'b'.repeat(64);

async function rpc(method, params, identity = owner) {
  const response = await worker.fetch(new Request('https://site.example.test/mcp', {
    method: 'POST', headers: { ...identity, 'content-type': 'application/json', 'mcp-method': method },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
  }), env);
  return { status: response.status, ...await response.json() };
}

test('native Sites discovery exposes tools and gates calls to the authenticated owner', async (t) => {
  const requests = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    requests.push([String(url), options.headers.Authorization, JSON.parse(options.body)]);
    return Response.json({ draft_id: draft, snapshot_hash: digest });
  });
  const call = (name, args, identity) => rpc('tools/call', { name, arguments: args }, identity);
  const listed = await rpc('tools/list', {}, {});
  assert.equal(listed.result.tools.length, 10);
  assert.equal(listed.result.tools.find(t => t.name === 'ifverse_publish').annotations.destructiveHint, true);
  assert.equal((await call('ifverse_accounts', {}, {})).status, 403);
  assert.equal((await call('ifverse_accounts', {}, { ...owner, 'oai-authenticated-user-email': 'other@example.test' })).status, 403);
  assert.equal((await call('ifverse_accounts', {}, { 'oai-authenticated-user-email': 'owner@example.test' })).status, 403);
  const result = await call('ifverse_preview', { draft_id: draft });
  assert.equal(result.result.structuredContent.snapshot_hash, digest);
  const selection = { draft_id: draft, snapshot_hash: digest, destinations: ['anime-instagram'], approved: true };
  assert.equal((await call('ifverse_publish', { ...selection, approved: false })).error.code, -32602);
  assert.equal((await call('ifverse_publish', { ...selection, destinations: ['ig', 'ig'] })).error.code, -32602);
  await call('ifverse_publish', selection);
  assert.deepEqual(requests, [
    ['https://api.example.test/drafts/get', 'Bearer fixture-token', { draft_id: draft }],
    ['https://api.example.test/drafts/publish', 'Bearer fixture-token', selection],
  ]);
});
