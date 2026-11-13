import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import net from 'node:net';

test('MCP denies anonymous access and exposes callable publishing tools', async () => {
  const listener=net.createServer(); listener.listen(0,'127.0.0.1'); await once(listener,'listening');
  const port=listener.address().port; await new Promise(r=>listener.close(r));
  const child=spawn(process.execPath,['server.mjs'],{env:{...process.env,PORT:String(port),
    IFVERSE_MCP_TOKEN:'fictional-test-token',IFVERSE_API_TOKEN:'fictional-backend-token',
    IFVERSE_BACKEND_URL:'https://example.invalid'},stdio:'ignore'});
  const url=`http://127.0.0.1:${port}/mcp`;
  try {
    let response;
    for(let i=0;i<60;i++) {
      try { response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}); break; }
      catch { await new Promise(r=>setTimeout(r,50)); }
    }
    assert.equal(response.status,401);
    const rpc=async (method,params={})=>{
      const r=await fetch(url,{method:'POST',headers:{Authorization:'Bearer fictional-test-token',
        'Content-Type':'application/json',Accept:'application/json, text/event-stream'},
        body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})});
      assert.equal(r.status,200);
      const body=await r.text();
      return JSON.parse(body.split('\n').find(line=>line.startsWith('data: ')).slice(6));
    };
    const init=await rpc('initialize',{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'test',version:'1'}});
    assert.equal(init.result.serverInfo.name,'Ifverse');
    const result=await rpc('tools/list');
    const publish=result.result.tools.find(t=>t.name==='ifverse_publish');
    assert.equal(publish.annotations.readOnlyHint,false);
    assert.ok(publish.inputSchema.required.includes('snapshot_hash'));
    assert.ok(publish.inputSchema.required.includes('destinations'));
    assert.equal(result.result.tools.length,10);
  } finally { child.kill(); await once(child,'exit'); }
});
