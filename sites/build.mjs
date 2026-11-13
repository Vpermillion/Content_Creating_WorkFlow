import { copyFile, mkdir, readFile } from 'node:fs/promises';

const root = new URL('./', import.meta.url);
const hosting = new URL('.openai/hosting.json', root);
const manifest = JSON.parse(await readFile(hosting, 'utf8'));
if (!manifest.capabilities?.includes('mcp') || manifest.static) {
  throw new Error('The hosting manifest must declare the MCP Worker capability.');
}

await mkdir(new URL('dist/.openai/', root), { recursive: true });
await mkdir(new URL('dist/server/', root), { recursive: true });
await copyFile(hosting, new URL('dist/.openai/hosting.json', root));
await copyFile(new URL('worker.mjs', root), new URL('dist/server/index.js', root));
await copyFile(new URL('accounts.mjs', root), new URL('dist/server/accounts.mjs', root));

