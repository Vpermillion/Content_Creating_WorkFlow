// Owner-only Sites server runtime. Never ship IFVERSE_API_TOKEN to browser code.
import express from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';

const app = express();
app.use(express.json({limit: '250kb'}));
const destination = z.object({account:z.string(),format:z.string(),title:z.string(),caption:z.string(),
  media_sha256:z.string(),manifest:z.record(z.string(),z.unknown())});
const tools = [
 ['ifverse_media_prepare','/jobs/prepare',{request_id:z.string()},false,
  'Run one existing checked-in review request through the established media renderer. Owner topic/script choice is required. '
  +'Does not publish. Poll media status; never submit a different job to retry an uncertain job.'],
 ['ifverse_media_status','/jobs/get',{request_id:z.string()},true,'Retrieve durable media job status and its prepared media hash.'],
 ['ifverse_media_import','/jobs/import',{brand:z.string(),episode:z.string(),export:z.enum(['master','facebook_reel','jpeg']).optional()},false,'Stage a pinned private Ifverse render or separate Facebook Reel or image export. This does not publish.'],
 ['ifverse_accounts','/accounts',{},true,'List intended destinations and supported formats; entries are not proof of consent.'],
 ['ifverse_connect','/connect',{account:z.string(),method:z.enum(['studio','oauth']).optional()},false,'Start browser consent or Studio account confirmation. Return the link to the owner.'],
 ['ifverse_verify','/verify',{account:z.string()},true,'Read-only check of the authorized provider ID and handle or Page.'],
 ['ifverse_prepare','/drafts/create',{brand:z.string(),destinations:z.array(destination)},false,
  'Save a durable immutable draft from already prepared and reviewed media jobs. Does not publish.'],
 ['ifverse_preview','/drafts/get',{draft_id:z.string()},true,
  'Retrieve a draft across chats. Show every destination, caption, media preview, hash and current delivery status.'],
 ['ifverse_status','/drafts/status',{draft_id:z.string()},true,
  'Refresh actual publication status using read-only provider checks. Does not upload, resume, or publish.'],
 ['ifverse_publish','/drafts/publish',{draft_id:z.string(),snapshot_hash:z.string(),destinations:z.array(z.string()),approved:z.boolean()},false,
  'Public write. Only after explicit owner approval of this exact preview. Post it is approval only when the draft and destinations are clear. '
  +'Select exactly the requested subset. Instagram only means only its alias. Never infer approval while preparing. '
  +'Retry only requested failed destinations. TikTok returns action required; it does not auto-publish.'],
 ['ifverse_verify_tiktok','/tiktok/verify',{draft_id:z.string(),snapshot_hash:z.string(),account:z.string(),video_id:z.string()},false,
  'Read-only provider ownership verification after the owner completes the reviewed Studio handoff. Updates the receipt only on proof.']
];
app.post('/mcp', async (req,res) => {
  // Sites owner-only visibility is required. Remote deployment additionally needs
  // authenticated MCP ingress; never expose this wrapper as an anonymous remote server.
  const ingress = process.env.IFVERSE_MCP_TOKEN;
  if (!ingress || req.headers.authorization !== `Bearer ${ingress}`) return res.sendStatus(401);
  const backend = process.env.IFVERSE_BACKEND_URL;
  if (!backend?.startsWith('https://') || !process.env.IFVERSE_API_TOKEN) return res.sendStatus(503);
  const server = new McpServer({name:'Ifverse',version:'1.0.0'});
  for (const [name,path,inputSchema,readOnlyHint,description] of tools) {
    server.registerTool(name,{description,inputSchema,annotations:{readOnlyHint,destructiveHint:name==='ifverse_publish',
      idempotentHint:name==='ifverse_publish',openWorldHint:true}},async args => {
      try {
        const response = await fetch(new URL(path,backend),{method:'POST',redirect:'error',
          headers:{Authorization:`Bearer ${process.env.IFVERSE_API_TOKEN}`,'Content-Type':'application/json'},
          body:JSON.stringify(args),signal:AbortSignal.timeout(180000)});
        if (!response.ok) throw new Error('backend');
        return {content:[{type:'text',text:JSON.stringify(await response.json())}]};
      } catch {
        return {isError:true,content:[{type:'text',text:'Request incomplete. Retrieve the draft before retrying. Never assume an uncertain write failed.'}]};
      }
    });
  }
  const transport = new StreamableHTTPServerTransport({sessionIdGenerator:undefined});
  res.on('close',()=>{transport.close();server.close();});
  await server.connect(transport);
  await transport.handleRequest(req,res,req.body);
});
app.listen(Number(process.env.PORT || 3000),'0.0.0.0');
