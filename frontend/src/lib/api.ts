export type Project={id:string;name:string;files?:string[]};
export type AuditSummary={id:string;project_id:string;project_name:string;status:string;completed_agents:number;total_agents:number;created_at:string};
export type AuditMessage={id:string;role:'user'|'assistant';body:string;created_at:string};
export type ChainTx={tx_hash:string;kind:string;denom:string;amount_raw:string;status:string;created_at:string};
export type ReportFinding={severity:string;title:string;evidence:string;source:string;verified:boolean};
export type AttestationStatus={
 status:'not_configured'|'not_attested'|'attested'; report_sha256:string;
 contract_address:string|null; chain_id:number; network:string; attested_at:string|null;
};
export type Audit={id:string;project_id:string;created_at?:string;status:'queued'|'running'|'completed'|'failed';report_markdown:string;agents:unknown[];findings:ReportFinding[];findings_status:string;completed_agents:number;total_agents:number;error?:string};
export type PqcScan={status:string;method:string;components:number;evidence:Array<{file:string;line:number;algorithm:string;classification:string;excerpt:string;confidence:string;standard?:string;transition?:string}>;risk_summary?:Record<string,number>;report_markdown?:string;cbom:Record<string,unknown>;limitations:string};
export type TxEvidence={found:boolean;tx_hash:string;network:string;success?:boolean;hybrid_layer_present?:boolean;chain_reports_verified?:boolean;height?:string;verification_method?:string};
export type UsageWindow={plan:string;expires_at:number|null;window:string;audits:{used:number;limit:number;remaining:number};assistant:{used:number;limit:number;remaining:number};pqc:{used:number;limit:number|null;remaining:number|null;history_enabled?:boolean}};
export type PlanQuote={plan:string;network:string;chain_id:number;currency:string;denom:string;decimals:number;amount_raw:string;amount_fusd:string};
export type PendingPaymentIntent={id:string;plan:string;network:string;chain_id:number;currency:string;decimals:number;denom:string;recipient:string;amount_raw:string;amount_fusd:string;memo:string;expires_at:number;status:string;tx_hash:string|null};
export type PaymentIntent={id:string;network:string;chain_id:number;currency:string;decimals:number;denom:string;recipient:string;amount_raw:string;amount_fusd:string;memo:string;expires_at:number;status:string;notice:string};
const BASE='/backend-proxy';
let ACCESS_TOKEN='';
export function setAccessToken(token:string){ACCESS_TOKEN=token;}
async function request<T>(path:string,init?:RequestInit):Promise<T>{
 const headers=new Headers(init?.headers);
 if(ACCESS_TOKEN)headers.set('Authorization',`Bearer ${ACCESS_TOKEN}`);
 let response:Response;
 try{response=await fetch(`${BASE}${path}`,{...init,headers,cache:'no-store'});}catch{throw new Error('The security service is temporarily unreachable.');}
 if(!response.ok){let reason=`Request failed (${response.status})`;try{const data=await response.json();if(typeof data.detail==='string')reason=data.detail;}catch{}throw new Error(reason);}
 return response.json() as Promise<T>;
}
const json=(body:unknown)=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} as RequestInit);
export const api={
 health:()=>request<{status:string}>('/health'),
 session:()=>request<{wallet:string;authenticated:boolean}>('/api/v1/auth/session'),
 logout:()=>request<{ok:boolean}>('/api/v1/auth/logout',{method:'POST'}),
 audits:(offset=0)=>request<{audits:AuditSummary[];has_more:boolean}>(`/api/v1/audits?limit=50&offset=${offset}`),
 attestation:(id:string)=>request<AttestationStatus>(`/api/v1/audits/${encodeURIComponent(id)}/attestation`),
 auditMessages:(id:string)=>request<{messages:AuditMessage[]}>(`/api/v1/audits/${encodeURIComponent(id)}/messages`),
 auditQuestion:(id:string,question:string)=>request<{answer:string}>(`/api/v1/audits/${encodeURIComponent(id)}/messages`,json({question})),
 transactions:(offset=0)=>request<{transactions:ChainTx[];has_more:boolean}>(`/api/v1/transactions?limit=50&offset=${offset}`),
 registerHybrid:(tx_hash:string)=>request<{confirmed:boolean}>('/api/v1/transactions/hybrid-proof',json({tx_hash})),
 nativeBalance:(address:string,denom?:string)=>request<{address:string;denom:string;amount_raw:string;decimals:number;low_gas:boolean;faucet_url:string}>(`/api/v1/qorechain/native/balance/${encodeURIComponent(address)}${denom?'?denom='+encodeURIComponent(denom):''}`),
 nativeChallenge:(address:string)=>request<{challenge_id:string;memo:string;amount:string;denom:string;expires_at:number}>('/api/v1/auth/native/challenge',json({address})),
 nativeVerify:(address:string,challenge_id:string,tx_hash:string)=>request<{access_token:string;wallet:string}>('/api/v1/auth/native/verify',json({address,challenge_id,tx_hash})),
 challenge:(address:string)=>request<{challenge_id:string;message:string}>('/api/v1/auth/challenge',json({address})),
 verifyLogin:(address:string,challenge_id:string,signature:string)=>request<{access_token:string;wallet:string}>('/api/v1/auth/verify',json({address,challenge_id,signature})),
 listProjects:()=>request<{projects:Project[]}>('/api/v1/projects'),
 createProject:(name:string)=>request<Project>('/api/v1/projects',json({name})),
 getProject:(id:string)=>request<Project>(`/api/v1/projects/${encodeURIComponent(id)}`),
 pasteSource:(id:string,source:string)=>request<{files:string[]}>(`/api/v1/projects/${encodeURIComponent(id)}/source`,json({source})),
 upload:(id:string,files:File[])=>{const data=new FormData();files.forEach(file=>data.append('files',file));return request<{files:string[]}>(`/api/v1/projects/${encodeURIComponent(id)}/files`,{method:'POST',body:data});},
 runAudit:(id:string)=>request<Audit>(`/api/v1/projects/${encodeURIComponent(id)}/audits`,{method:'POST'}),
 audit:(id:string)=>request<Audit>(`/api/v1/audits/${encodeURIComponent(id)}`),
 pqc:(id:string)=>request<PqcScan>(`/api/v1/projects/${encodeURIComponent(id)}/pqc/scan`,{method:'POST'}),
 pqcPaste:(source:string)=>request<PqcScan>('/api/v1/pqc/scan',json({source})),
 pqcFiles:(files:File[])=>{const data=new FormData();files.forEach(file=>data.append('files',file));return request<PqcScan>('/api/v1/pqc/scan/files',{method:'POST',body:data});},
 inspectTx:(hash:string)=>request<TxEvidence>(`/api/v1/qorechain/transactions/${encodeURIComponent(hash)}`),
 subscription:()=>request<{plan:string;expires_at:number|null;active:boolean}>('/api/v1/subscriptions/me'),
 usage:()=>request<UsageWindow>('/api/v1/subscriptions/usage'),
 planQuote:(plan:string)=>request<PlanQuote>(`/api/v1/payments/plans/${encodeURIComponent(plan)}`),
 pendingIntents:()=>request<{intents:PendingPaymentIntent[]}>('/api/v1/payments/intents'),
 broadcastPayment:(id:string,tx_hash:string)=>request<{status:string;tx_hash:string;verified:boolean}>(`/api/v1/payments/intents/${encodeURIComponent(id)}/broadcast`,json({tx_hash})),
 intent:(plan:string)=>request<PaymentIntent>('/api/v1/payments/intents',json({plan})),
 verifyPayment:(id:string,tx_hash:string)=>request<{status:string;tx_hash?:string;reason?:string;confirmations?:number;required?:number}> (`/api/v1/payments/intents/${encodeURIComponent(id)}/verify`,json({tx_hash})),
 ask:(project_id:string,question:string)=>request<{answer:string;validation:string}>(`/api/v1/projects/${encodeURIComponent(project_id)}/assistant`,json({question})),
};
