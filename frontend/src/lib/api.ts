export type Project = {id:string;name:string;files?:string[]};
export type Audit = {status:string;report_markdown:string;agents:unknown;findings:unknown[];findings_status:string};
const API_URL = '/backend-proxy';
async function request<T>(path:string, init?:RequestInit):Promise<T> {
  let response:Response;
  try {response = await fetch(`${API_URL}${path}`,{...init,cache:'no-store'});} catch {throw new Error('Backend unavailable. Start FastAPI and check NEXT_PUBLIC_API_URL.');}
  if(!response.ok){let message = `Request failed (${response.status})`;try{const data = await response.json();message = typeof data.detail === 'string' ? data.detail : message;}catch{}throw new Error(message);}
  return response.json() as Promise<T>;
}
export const api = {
  health:()=>request<{status:string}>('/health'),
  createProject:(name:string)=>request<Project>('/api/v1/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}),
  getProject:(id:string)=>request<Project>(`/api/v1/projects/${encodeURIComponent(id)}`),
  pasteSource:(id:string,source:string)=>request<{files:string[]}>(`/api/v1/projects/${encodeURIComponent(id)}/source`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source})}),
  upload:(id:string,files:File[])=>{const data = new FormData();files.forEach(file=>data.append('files',file));return request<{files:string[]}>(`/api/v1/projects/${encodeURIComponent(id)}/files`,{method:'POST',body:data});},
  runAudit:(id:string)=>request<Audit>(`/api/v1/projects/${encodeURIComponent(id)}/audits`,{method:'POST'})
};
