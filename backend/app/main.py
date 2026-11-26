"""QoreSentinel v0.2 API: protected projects, audit jobs, PQC, wallet and testnet billing."""
import json
import os
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI,HTTPException,UploadFile,File,Depends,Request,Query
from pydantic import BaseModel,Field
from .auth import require_wallet,ChallengeRequest,VerifyRequest,challenge,verify
from . import storage,auth,pqc,chain,payments
from .ingestion import BadSource,ingest_files,ingest_paste,ingest_zip,as_http_error
from .audit_service import analyze,EngineNotConfigured
from .findings import extract_findings

app=FastAPI(title='QoreSentinel API',version='0.2.0')
EXECUTOR=ThreadPoolExecutor(max_workers=1,thread_name_prefix='qs-audit')

class ProjectCreate(BaseModel):name:str=Field(min_length=1,max_length=120)
class PasteInput(BaseModel):source:str=Field(min_length=1)
class PlanInput(BaseModel):plan:str
class VerifyTransfer(BaseModel):tx_hash:str
class TxRegistration(BaseModel):tx_hash:str

@app.get('/api/v1/qorechain/native/balance/{address}')
def native_balance(address:str,denom:str='uqor'):
    if not auth.is_native(address):raise HTTPException(422,'Invalid QoreChain native address')
    return chain.native_balance(address,denom)

@app.post('/api/v1/auth/native/challenge')
def create_native_challenge(payload:auth.ChallengeRequest):
    return auth.native_challenge(payload.address)

@app.post('/api/v1/auth/native/verify')
def complete_native_challenge(payload:auth.NativeVerifyRequest):
    return auth.verify_native(payload)

@app.get('/health')
def health():return {'status':'ok','service':'qoresentinel-backend'}

@app.post('/api/v1/auth/challenge')
def new_challenge(payload:ChallengeRequest,request:Request):
    auth.auth_secret()
    # Host is a presentational part of the challenge; signed nonce is verified server-side.
    return challenge(payload.address,request.headers.get('host','qoresentinel'))

@app.post('/api/v1/auth/verify')
def verify_challenge(payload:VerifyRequest):return verify(payload)

@app.get('/api/v1/audits')
def audit_history(owner:str=Depends(require_wallet),
                  limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):
    return storage.list_all_audits(owner,limit,offset)

@app.get('/api/v1/transactions')
def transaction_history(owner:str=Depends(require_wallet),
                        limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):
    return storage.list_chain_transactions(owner,limit,offset)

@app.post('/api/v1/transactions/hybrid-proof')
def register_hybrid_proof(payload:TxRegistration,owner:str=Depends(require_wallet)):
    if not auth.is_native(owner):raise HTTPException(422,'QoreX native authentication required')
    result=chain.verify_native_send(
        payload.tx_hash,owner,owner,'uqor',1,
        'QoreSentinel hybrid-signature testnet proof',
        confirmations=1,require_hybrid=True)
    if not result['confirmed']:
        raise HTTPException(409,'Hybrid proof transaction is awaiting confirmation')
    storage.record_chain_transaction(owner,result['tx_hash'],'hybrid-proof','uqor','1')
    return result

@app.get('/api/v1/projects')
def list_projects(owner:str=Depends(require_wallet)):return {'projects':storage.list_projects(owner)}

@app.post('/api/v1/projects',status_code=201)
def new_project(payload:ProjectCreate,owner:str=Depends(require_wallet)):
    return storage.create_project(payload.name,owner)

@app.get('/api/v1/projects/{project_id}')
def project(project_id:str,owner:str=Depends(require_wallet)):
    row=storage.get_project(project_id,owner)
    if row is None:raise HTTPException(404,'Project not found')
    return {'id':row['id'],'name':row['name'],'files':sorted(json.loads(row['files']))}

@app.post('/api/v1/projects/{project_id}/source')
def paste(project_id:str,payload:PasteInput,owner:str=Depends(require_wallet)):
    if not storage.get_project(project_id,owner):raise HTTPException(404,'Project not found')
    try:files=ingest_paste(payload.source)
    except BadSource as exc:raise as_http_error(exc) from exc
    return {'files':storage.save_files(project_id,owner,files)}

@app.post('/api/v1/projects/{project_id}/files')
async def upload(project_id:str,files:list[UploadFile]=File(...),owner:str=Depends(require_wallet)):
    if not storage.get_project(project_id,owner):raise HTTPException(404,'Project not found')
    if len(files)!=1 and any((f.filename or '').lower().endswith('.zip') for f in files):raise HTTPException(422,'Submit ZIP by itself')
    if len(files)>80:raise HTTPException(422,'Too many files')
    try:
        items=[]
        for f in files:
            data=await f.read(4_000_001)
            if len(data)>4_000_000:raise BadSource('Upload exceeds size limit')
            items.append((f.filename or '',data))
        sources=ingest_zip(items[0][1]) if len(items)==1 and items[0][0].lower().endswith('.zip') else ingest_files(items)
    except BadSource as exc:raise as_http_error(exc) from exc
    return {'files':storage.save_files(project_id,owner,sources)}

def _audit_task(job_id:str,files:dict[str,str]):
    storage.set_job(job_id,status='running')
    try:
        def notify(_result):
            row=storage._one(storage.audit_jobs,'id',job_id)
            storage.set_job(job_id,completed_agents=min(12,(row or {}).get('completed_agents',0)+1))
        result=analyze(files,on_agent_done=notify)
        storage.set_job(job_id,status='completed',completed_agents=12,report=result.report,agent_results=json.dumps(result.agent_results))
    except Exception:
        # Secrets and source must not enter public job error messages.
        storage.set_job(job_id,status='failed',error='Audit failed. Review Render service logs.')

@app.post('/api/v1/projects/{project_id}/audits',status_code=202)
def start_audit(project_id:str,owner:str=Depends(require_wallet)):
    row=storage.get_project(project_id,owner)
    if not row:raise HTTPException(404,'Project not found')
    files=json.loads(row['files'])
    if not files:raise HTTPException(422,'Project contains no source files')
    if os.getenv('QORE_ENABLE_LLM_AUDIT','false').lower()!='true':raise HTTPException(503,'Audit disabled or temporarily unavailable')
    if not any(os.getenv(k) for k in ('ANTHROPIC_API_KEY','OPENROUTER_API_KEY','GROQ_API_KEY','AGENTROUTER_API_KEY')):
        raise HTTPException(503,'No cloud audit provider is available')
    quota=payments.audit_quota(owner)
    if quota==0:raise HTTPException(402,'An active Pro subscription is required')
    since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    reservation=storage.reserve_audit(owner,project_id,quota,since)
    if reservation.get('error')=='pending':raise HTTPException(429,'You already have a pending audit')
    if reservation.get('error')=='limit':raise HTTPException(429,'Daily audit quota reached')
    if reservation.get('error'):raise HTTPException(404,'Project not found')
    job=reservation['id']
    EXECUTOR.submit(_audit_task,job,files)
    return {'id':job,'status':'queued','completed_agents':0,'total_agents':12}

@app.get('/api/v1/audits/{job_id}')
def get_audit(job_id:str,owner:str=Depends(require_wallet)):
    row=storage.get_job(job_id,owner)
    if not row:raise HTTPException(404,'Audit not found')
    return {'id':row['id'],'project_id':row['project_id'],'status':row['status'],'created_at':row['created_at'],
      'completed_agents':row['completed_agents'],'total_agents':row['total_agents'],
      'report_markdown':row['report'] if row['status']=='completed' else '',
      'agents':json.loads(row['agent_results']) if row['status']=='completed' else [],
      'findings':extract_findings(row['report']) if row['status']=='completed' else [],
      'findings_status':'report_extracted_unverified',
      'error':row['error']}

@app.get('/api/v1/audits/{job_id}/messages')
def audit_conversation(job_id:str,owner:str=Depends(require_wallet)):
    messages=storage.audit_message_history(job_id,owner)
    if messages is None:raise HTTPException(404,'Audit not found')
    return {'messages':messages}

class AuditQuestion(BaseModel):
    question:str=Field(min_length=1,max_length=2000)

@app.post('/api/v1/audits/{job_id}/messages')
def audit_conversation_question(job_id:str,payload:AuditQuestion,owner:str=Depends(require_wallet)):
    row=storage.get_job(job_id,owner)
    if not row:raise HTTPException(404,'Audit not found')
    if row['status']!='completed':raise HTTPException(409,'Audit must finish before discussion')
    since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    if not storage.reserve_usage(owner,'assistant',payments.assistant_quota(owner),since):
        raise HTTPException(429,'Daily assistant usage limit reached')
    from .assistant import answer
    result=answer(row['project_id'],owner,payload.question,audit_id=job_id)
    if not storage.append_audit_exchange(job_id,owner,payload.question,result['answer']):
        raise HTTPException(409,'Could not append audit discussion')
    return result

@app.post('/api/v1/projects/{project_id}/pqc/scan')
def scan_pqc(project_id:str,owner:str=Depends(require_wallet)):
    row=storage.get_project(project_id,owner)
    if not row:raise HTTPException(404,'Project not found')
    files=json.loads(row['files'])
    if not files:raise HTTPException(422,'Project has no source files')
    since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    if not storage.reserve_usage(owner,'pqc',15,since):
        raise HTTPException(429,'Daily PQC scan limit reached')
    try:return pqc.scan(files)
    except (RuntimeError,ValueError) as exc:raise HTTPException(502,'PQC scanner failed; check server logs') from exc

@app.get('/api/v1/qorechain/transactions/{tx_hash}')
def qore_tx(tx_hash:str):return chain.transaction_evidence(tx_hash)

@app.get('/api/v1/payments/plans/{plan}')
def payment_plan_quote(plan:str,owner:str=Depends(require_wallet)):
    return payments.plan_quote(plan)

@app.get('/api/v1/payments/intents')
def pending_payment_intents(owner:str=Depends(require_wallet)):
    return payments.list_pending(owner)

@app.post('/api/v1/payments/intents/{intent_id}/broadcast')
def broadcast_payment_intent(intent_id:str,payload:VerifyTransfer,owner:str=Depends(require_wallet)):
    return payments.register_broadcast(intent_id,owner,payload.tx_hash)

@app.post('/api/v1/payments/intents',status_code=201)
def new_intent(payload:PlanInput,owner:str=Depends(require_wallet)):return payments.create(owner,payload.plan)

@app.get('/api/v1/payments/intents/{intent_id}')
def intent(intent_id:str,owner:str=Depends(require_wallet)):
    row=storage.get_intent(intent_id,owner)
    if not row:raise HTTPException(404,'Payment intent not found')
    return {'id':row['id'],'status':row['status'],'tx_hash':row['tx_hash'],'expires_at':row['expires_at'],'amount_raw':row['amount_raw']}

@app.post('/api/v1/payments/intents/{intent_id}/verify')
def verify_intent(intent_id:str,payload:VerifyTransfer,owner:str=Depends(require_wallet)):
    return payments.verify(intent_id,owner,payload.tx_hash)

@app.get('/api/v1/subscriptions/me')
def my_subscription(owner:str=Depends(require_wallet)):return payments.entitlement(owner)

@app.get('/api/v1/subscriptions/usage')
def subscription_usage(owner:str=Depends(require_wallet)):
    return payments.usage(owner)


class AssistantQuestion(BaseModel):question:str=Field(min_length=1,max_length=2000)
@app.post('/api/v1/projects/{project_id}/assistant')
def assistant_message(project_id:str,payload:AssistantQuestion,owner:str=Depends(require_wallet)):
    if not storage.get_project(project_id,owner):raise HTTPException(404,'Project not found')
    since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    if not storage.reserve_usage(owner,'assistant',payments.assistant_quota(owner),since):
        raise HTTPException(429,'Daily assistant usage limit reached')
    from .assistant import answer
    return answer(project_id,owner,payload.question)

@app.get('/api/v1/projects/{project_id}/audits')
def project_audits(project_id:str,owner:str=Depends(require_wallet)):
    if not storage.get_project(project_id,owner):raise HTTPException(404,'Project not found')
    return {'audits':storage.recent_jobs(project_id,owner)}
