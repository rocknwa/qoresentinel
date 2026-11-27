"""Persistent project, challenge, audit-job and billing records.

Render requires DATABASE_URL pointing at PostgreSQL for durable production data.
SQLite is intended only for local development and tests.
"""
import json
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Integer, select, update, insert, delete, UniqueConstraint, func, text
from sqlalchemy.pool import NullPool
from .settings import DATA_DIR

_lock = Lock()
_engine = None
_engine_url = None
metadata = MetaData()
projects = Table('projects', metadata,
    Column('id', String(40), primary_key=True), Column('name', String(120), nullable=False),
    Column('files', Text, nullable=False, default='{}'), Column('owner', String(42), nullable=False),
    Column('created_at', String(35), nullable=False))
challenges = Table('challenges', metadata,
    Column('id', String(40), primary_key=True), Column('wallet', String(42), nullable=False),
    Column('message', Text, nullable=False), Column('expires_at', Integer, nullable=False),
    Column('used', Integer, nullable=False, default=0))
audit_jobs = Table('audit_jobs', metadata,
    Column('id', String(40), primary_key=True), Column('project_id', String(40), nullable=False),
    Column('owner', String(42), nullable=False), Column('status', String(20), nullable=False),
    Column('completed_agents', Integer, nullable=False, default=0), Column('total_agents', Integer, nullable=False, default=12),
    Column('report', Text, nullable=False, default=''), Column('agent_results', Text, nullable=False, default='[]'),
    Column('error', Text, nullable=False, default=''), Column('created_at', String(35), nullable=False))
intents = Table('payment_intents', metadata,
    Column('id', String(40), primary_key=True), Column('wallet', String(42), nullable=False),
    Column('plan', String(30), nullable=False), Column('amount_raw', String(40), nullable=False),
    Column('token', String(96), nullable=False), Column('treasury', String(42), nullable=False),
    Column('status', String(20), nullable=False), Column('tx_hash', String(70), nullable=True),
    Column('expires_at', Integer, nullable=False), Column('created_at', String(35), nullable=False),
    UniqueConstraint('tx_hash', name='uq_payment_tx_hash'))
subscriptions = Table('subscriptions', metadata,
    Column('wallet', String(42), primary_key=True), Column('plan', String(30), nullable=False),
    Column('expires_at', Integer, nullable=False), Column('credited_intent', String(40), nullable=False))

payment_broadcasts = Table('payment_broadcasts', metadata,
    Column('intent_id', String(40), primary_key=True),
    Column('owner', String(42), nullable=False),
    Column('tx_hash', String(70), nullable=False),
    Column('created_at', String(35), nullable=False))

audit_messages = Table('audit_messages', metadata,
    Column('id', String(40), primary_key=True),
    Column('job_id', String(40), nullable=False),
    Column('owner', String(42), nullable=False),
    Column('role', String(16), nullable=False),
    Column('body', Text, nullable=False),
    Column('created_at', String(35), nullable=False))
usage_events = Table('usage_events', metadata,
    Column('id',String(40),primary_key=True),Column('owner',String(42),nullable=False),
    Column('kind',String(24),nullable=False),Column('created_at',String(35),nullable=False))

chain_transactions = Table('chain_transactions', metadata,
    Column('id', String(40), primary_key=True),
    Column('tx_hash', String(70), nullable=False),
    Column('owner', String(42), nullable=False),
    Column('kind', String(32), nullable=False),
    Column('denom', String(96), nullable=False),
    Column('amount_raw', String(64), nullable=False),
    Column('status', String(20), nullable=False),
    Column('created_at', String(35), nullable=False),
    UniqueConstraint('tx_hash','kind',name='uq_chain_transaction_kind'))


# One immutable report hash per audited job. The request and settlement state
# remain durable across Render restarts; only public transaction hashes are stored.
attestation_requests = Table('attestation_requests', metadata,
    Column('job_id', String(40), primary_key=True),
    Column('owner', String(42), nullable=False),
    Column('report_digest', String(66), nullable=False),
    Column('status', String(20), nullable=False),
    Column('tx_hash', String(70), nullable=True),
    Column('created_at', String(35), nullable=False),
    Column('updated_at', String(35), nullable=False),
    Column('attempts', Integer, nullable=False, default=0))

def get_attestation_request(job_id: str, owner: str):
    return _one(attestation_requests, 'job_id', job_id, attestation_requests.c.owner == owner.lower())

def reserve_attestation_request(job_id: str, owner: str, digest: str, max_daily: int = 3):
    """Idempotently reserve one on-chain publication per completed audit.

    A failed request without a prepared on-chain tx may be attempted twice.
    Quota is counted per distinct audit job; retries do not evade the cap.
    """
    owner = owner.lower()
    now = iso_now()
    since = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp()-86400,timezone.utc).isoformat()
    with engine().begin() as conn:
        job = conn.execute(select(audit_jobs.c.status, audit_jobs.c.report)
            .where((audit_jobs.c.id == job_id) & (audit_jobs.c.owner == owner))).first()
        if not job:
            return {'error': 'not_found'}
        if job.status != 'completed' or not job.report:
            return {'error': 'not_completed'}
        row = conn.execute(select(attestation_requests).where(attestation_requests.c.job_id == job_id)).mappings().first()
        if row:
            old = dict(row)
            if old['owner'] != owner or old['report_digest'] != digest:
                return {'error': 'conflict'}
            if old['status'] == 'failed' and not old['tx_hash'] and old['attempts'] < 2:
                conn.execute(update(attestation_requests).where(
                    (attestation_requests.c.job_id == job_id) &
                    (attestation_requests.c.status == 'failed') &
                    (attestation_requests.c.tx_hash.is_(None))
                ).values(status='queued', updated_at=now))
                old['status'] = 'queued'
            elif old['status'] == 'processing' and not old['tx_hash']:
                try:
                    last = datetime.fromisoformat(old['updated_at'])
                    if (datetime.now(timezone.utc) - last).total_seconds() > 600 and old['attempts'] < 2:
                        conn.execute(update(attestation_requests).where(
                            (attestation_requests.c.job_id == job_id) &
                            (attestation_requests.c.status == 'processing') &
                            (attestation_requests.c.tx_hash.is_(None))
                        ).values(status='queued', updated_at=now))
                        old['status'] = 'queued'
                except (ValueError,TypeError):
                    pass
            return old
        count = conn.scalar(select(func.count()).select_from(attestation_requests).where(
            (attestation_requests.c.owner == owner) & (attestation_requests.c.created_at >= since))) or 0
        if count >= max_daily:
            return {'error': 'limit'}
        data = {'job_id': job_id, 'owner': owner, 'report_digest': digest,
                'status': 'queued', 'tx_hash': None, 'created_at': now,
                'updated_at': now, 'attempts': 0}
        conn.execute(insert(attestation_requests).values(**data))
        return data

def claim_attestation_request(job_id: str):
    now = iso_now()
    with engine().begin() as conn:
        result = conn.execute(update(attestation_requests).where(
            (attestation_requests.c.job_id == job_id) & (attestation_requests.c.status == 'queued')
        ).values(status='processing', updated_at=now, attempts=attestation_requests.c.attempts + 1))
        return result.rowcount == 1

def update_attestation_request(job_id: str, *, status: str, tx_hash: str | None = None):
    now = iso_now()
    with engine().begin() as conn:
        values = {'status': status, 'updated_at': now}
        if tx_hash is not None:
            values['tx_hash'] = tx_hash
        conn.execute(update(attestation_requests).where(attestation_requests.c.job_id == job_id).values(**values))



def iso_now(): return datetime.now(timezone.utc).isoformat()

def engine():
    global _engine,_engine_url
    url = os.getenv('DATABASE_URL', '').strip()
    if url.startswith('postgres://'): url='postgresql+psycopg://' + url[len('postgres://'):]
    elif url.startswith('postgresql://'): url='postgresql+psycopg://' + url[len('postgresql://'):]
    if not url:
        DATA_DIR.mkdir(parents=True,exist_ok=True)
        url='sqlite:///'+str(DATA_DIR/'qoresentinel-v2.sqlite')
    with _lock:
        if _engine is None or _engine_url!=url:
            if _engine is not None:_engine.dispose()
            kw={'pool_pre_ping':True}
            if url.startswith('sqlite:'):kw['poolclass']=NullPool
            _engine=create_engine(url,**kw)
            metadata.create_all(_engine)
            _engine_url=url
        return _engine

def _one(table,key,value,where=None):
    with engine().connect() as c:
        cond=(table.c[key]==value)
        if where is not None:cond=cond & where
        row=c.execute(select(table).where(cond)).mappings().first()
        return dict(row) if row else None

def create_project(name:str,owner:str):
    row={'id':str(uuid.uuid4()),'name':name,'owner':owner.lower(),'files':'{}','created_at':iso_now()}
    with engine().begin() as c:c.execute(insert(projects).values(**row))
    return {'id':row['id'],'name':name,'file_count':0}

def get_project(project_id:str,owner:str):
    row=_one(projects,'id',project_id,projects.c.owner==owner.lower())
    if not row:return None
    return row

def save_files(project_id:str,owner:str,files:dict[str,str]):
    with engine().begin() as c:
        row=c.execute(select(projects.c.files).where((projects.c.id==project_id)&(projects.c.owner==owner.lower()))).first()
        if not row:return None
        current=json.loads(row[0]);current.update(files)
        c.execute(update(projects).where((projects.c.id==project_id)&(projects.c.owner==owner.lower())).values(files=json.dumps(current)))
        return sorted(current)

def list_projects(owner:str):
    with engine().connect() as c:
        rows=c.execute(select(projects.c.id,projects.c.name,projects.c.created_at).where(projects.c.owner==owner.lower()).order_by(projects.c.created_at.desc()).limit(50)).mappings().all()
    return [dict(r) for r in rows]

def store_challenge(wallet:str,message:str,expiry:int):
    id=str(uuid.uuid4());with_values={'id':id,'wallet':wallet.lower(),'message':message,'expires_at':expiry,'used':0}
    with engine().begin() as c:c.execute(insert(challenges).values(**with_values))
    return id

def peek_challenge(id:str,wallet:str,now:int):
    row=_one(challenges,'id',id,challenges.c.wallet==wallet.lower())
    if not row or row['used'] or row['expires_at']<now:return None
    return row['message']

def consume_challenge(id:str,wallet:str,now:int):
    with engine().begin() as c:
        row=c.execute(select(challenges).where(challenges.c.id==id)).mappings().first()
        if not row or row['wallet']!=wallet.lower() or row['used'] or row['expires_at']<now:return None
        updated=c.execute(update(challenges).where((challenges.c.id==id)&(challenges.c.used==0)&(challenges.c.expires_at>=now)).values(used=1))
        return row['message'] if updated.rowcount==1 else None

def create_job(project_id:str,owner:str):
    data={'id':str(uuid.uuid4()),'project_id':project_id,'owner':owner.lower(),'status':'queued','completed_agents':0,'total_agents':12,'report':'','agent_results':'[]','error':'','created_at':iso_now()}
    with engine().begin() as c:c.execute(insert(audit_jobs).values(**data))
    return data['id']

def reserve_audit(owner:str,project_id:str,limit:int,since_iso:str):
    """Atomically reserve a wallet's audit slot before starting a costly worker."""
    owner=owner.lower()
    eng=engine()
    # Lock the wallet's quota scope across Render workers on PostgreSQL.
    with _audit_reservation_lock:
        with eng.begin() as conn:
            if eng.dialect.name=='postgresql':
                lock_key=int.from_bytes(hashlib.sha256(owner.encode()).digest()[:8],'big',signed=True)
                conn.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock_key})
            active=conn.scalar(select(func.count()).select_from(audit_jobs).where(
                (audit_jobs.c.owner==owner)&(audit_jobs.c.status.in_(['queued','running']))))
            if active:return {'error':'pending'}
            used=conn.scalar(select(func.count()).select_from(audit_jobs).where(
                (audit_jobs.c.owner==owner)&(audit_jobs.c.created_at>=since_iso))) or 0
            if used>=limit:return {'error':'limit','used_today':used,'daily_limit':limit}
            project=conn.execute(select(projects.c.id).where(
                (projects.c.id==project_id)&(projects.c.owner==owner))).first()
            if not project:return {'error':'not-found'}
            data={'id':str(uuid.uuid4()),'project_id':project_id,'owner':owner,'status':'queued',
                  'completed_agents':0,'total_agents':12,'report':'','agent_results':'[]',
                  'error':'','created_at':iso_now()}
            conn.execute(insert(audit_jobs).values(**data))
            return {'id':data['id'],'used_today':used+1,'daily_limit':limit}

_audit_reservation_lock = Lock()

def get_job(job_id:str,owner:str):return _one(audit_jobs,'id',job_id,audit_jobs.c.owner==owner.lower())

def set_job(job_id:str,**values):
    with engine().begin() as c:c.execute(update(audit_jobs).where(audit_jobs.c.id==job_id).values(**values))

def create_intent(wallet:str,plan:str,amount_raw:int,token:str,treasury:str,expires:int):
    data={'id':str(uuid.uuid4()),'wallet':wallet.lower(),'plan':plan,'amount_raw':str(amount_raw),'token':token,'treasury':treasury.lower(),'status':'pending','tx_hash':None,'expires_at':expires,'created_at':iso_now()}
    with engine().begin() as c:c.execute(insert(intents).values(**data))
    return data

def get_intent(intent_id:str,wallet:str):return _one(intents,'id',intent_id,intents.c.wallet==wallet.lower())

def pending_intents(wallet:str,now:int,limit:int=20):
    """Recover open payment intents and known broadcast IDs for one wallet."""
    stmt=(select(intents.c.id,intents.c.plan,intents.c.amount_raw,intents.c.token,
                 intents.c.treasury,intents.c.expires_at,intents.c.status,
                 payment_broadcasts.c.tx_hash.label('broadcast_hash'))
          .select_from(intents.outerjoin(payment_broadcasts,
                                        payment_broadcasts.c.intent_id==intents.c.id))
          .where((intents.c.wallet==wallet.lower())&
                 (intents.c.status=='pending')&
                 (intents.c.expires_at>now))
          .order_by(intents.c.created_at.desc(),intents.c.id.desc()).limit(limit))
    with engine().connect() as conn:
        rows=conn.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


def save_payment_broadcast(intent_id:str,owner:str,tx_hash:str,now:int):
    """Store an unverified broadcast ID; never grant entitlement here."""
    from sqlalchemy.exc import IntegrityError
    with engine().begin() as conn:
        row=conn.execute(select(intents.c.id,intents.c.status,intents.c.expires_at).where(
            (intents.c.id==intent_id)&(intents.c.wallet==owner.lower()))).mappings().first()
        if not row:return 'not-found'
        if row['status']!='pending':return 'not-pending'
        if row['expires_at']<=now:return 'expired'
        existing=conn.execute(select(payment_broadcasts.c.tx_hash).where(
            (payment_broadcasts.c.intent_id==intent_id)&
            (payment_broadcasts.c.owner==owner.lower()))).first()
        if existing:
            return 'recorded' if existing[0]==tx_hash else 'conflict'
        try:
            with conn.begin_nested():
                conn.execute(insert(payment_broadcasts).values(
                    intent_id=intent_id,owner=owner.lower(),
                    tx_hash=tx_hash,created_at=iso_now()))
        except IntegrityError:return 'conflict'
    return 'recorded'


def mark_intent_paid(intent_id:str,owner:str,tx_hash:str,new_expiry:int):
    """Atomic idempotent crediting. Caller must have verified receipt from chain."""
    with engine().begin() as c:
        row=c.execute(select(intents).where((intents.c.id==intent_id)&(intents.c.wallet==owner.lower()))).mappings().first()
        if not row:return 'not-found'
        if row['status']=='paid':return 'already-paid' if row['tx_hash']==tx_hash else 'conflict'
        if row['status']!='pending':return 'conflict'
        duplicate=c.execute(select(intents.c.id).where(intents.c.tx_hash==tx_hash)).first()
        if duplicate:return 'duplicate-tx'
        result=c.execute(update(intents).where((intents.c.id==intent_id)&(intents.c.status=='pending')).values(status='paid',tx_hash=tx_hash))
        if result.rowcount!=1:return 'conflict'
        c.execute(delete(subscriptions).where(subscriptions.c.wallet==owner.lower()))
        c.execute(insert(subscriptions).values(wallet=owner.lower(),plan=row['plan'],expires_at=new_expiry,credited_intent=intent_id))
    return 'paid'

def subscription(wallet:str):return _one(subscriptions,'wallet',wallet.lower())

def latest_completed_job(project_id:str,owner:str):
    with engine().connect() as c:
        row=c.execute(select(audit_jobs).where((audit_jobs.c.project_id==project_id)&(audit_jobs.c.owner==owner.lower())&(audit_jobs.c.status=='completed')).order_by(audit_jobs.c.created_at.desc()).limit(1)).mappings().first()
        return dict(row) if row else None


def owner_recent_audit_count(owner:str,since_iso:str):
    with engine().connect() as c:
        rows=c.execute(select(audit_jobs.c.id).where((audit_jobs.c.owner==owner.lower())&(audit_jobs.c.created_at>=since_iso))).all()
    return len(rows)

def owner_pending_audits(owner:str):
    with engine().connect() as c:
        rows=c.execute(select(audit_jobs.c.id).where((audit_jobs.c.owner==owner.lower())&(audit_jobs.c.status.in_(['queued','running'])))).all()
    return len(rows)

def recent_jobs(project_id:str,owner:str):
    with engine().connect() as c:
        rows=c.execute(select(audit_jobs.c.id,audit_jobs.c.status,audit_jobs.c.created_at).where((audit_jobs.c.project_id==project_id)&(audit_jobs.c.owner==owner.lower())).order_by(audit_jobs.c.created_at.desc()).limit(10)).mappings().all()
    return [dict(r) for r in rows]


def list_all_audits(owner:str,limit:int=50,offset:int=0):
    """Wallet-scoped audit index; completed report bodies are retrieved separately."""
    stmt=(select(audit_jobs.c.id,audit_jobs.c.project_id,projects.c.name.label('project_name'),
                 audit_jobs.c.status,audit_jobs.c.completed_agents,audit_jobs.c.total_agents,
                 audit_jobs.c.created_at)
          .join(projects,projects.c.id==audit_jobs.c.project_id)
          .where((audit_jobs.c.owner==owner.lower())&(projects.c.owner==owner.lower()))
          .order_by(audit_jobs.c.created_at.desc(),audit_jobs.c.id.desc())
          .limit(limit+1).offset(offset))
    with engine().connect() as conn:
        rows=[dict(row) for row in conn.execute(stmt).mappings().all()]
    return {'audits':rows[:limit],'has_more':len(rows)>limit}


def audit_message_history(job_id:str,owner:str,limit:int=100):
    """Return messages only when the audit belongs to the requesting wallet."""
    if not get_job(job_id,owner):return None
    stmt=(select(audit_messages.c.id,audit_messages.c.role,audit_messages.c.body,audit_messages.c.created_at)
          .where((audit_messages.c.job_id==job_id)&(audit_messages.c.owner==owner.lower()))
          .order_by(audit_messages.c.created_at.desc(),audit_messages.c.id.desc()).limit(limit))
    with engine().connect() as conn:rows=[dict(row) for row in conn.execute(stmt).mappings().all()]
    return list(reversed(rows))


def append_audit_exchange(job_id:str,owner:str,question:str,response:str):
    """Persist a complete Q&A pair against one completed, wallet-owned audit."""
    now=datetime.now(timezone.utc)
    with engine().begin() as conn:
        job=conn.execute(select(audit_jobs.c.status).where(
            (audit_jobs.c.id==job_id)&(audit_jobs.c.owner==owner.lower()))).first()
        if not job or job[0]!='completed':return False
        for i,(role,body) in enumerate((('user',question),('assistant',response))):
            from datetime import timedelta
            conn.execute(insert(audit_messages).values(
                id=str(uuid.uuid4()),job_id=job_id,owner=owner.lower(),role=role,body=body,
                created_at=(now+timedelta(microseconds=i)).isoformat()))
    return True


def record_chain_transaction(owner:str,tx_hash:str,kind:str,denom:str,amount_raw:str):
    """Idempotent ledger for on-chain verified QoreSentinel transactions."""
    from sqlalchemy.exc import IntegrityError
    tx_hash='0x'+tx_hash.lower().removeprefix('0x')
    with engine().begin() as conn:
        if conn.execute(select(chain_transactions.c.id).where(
            (chain_transactions.c.tx_hash==tx_hash)&(chain_transactions.c.kind==kind))).first():
            return False
        try:
            with conn.begin_nested():
                conn.execute(insert(chain_transactions).values(
                    id=str(uuid.uuid4()),owner=owner.lower(),tx_hash=tx_hash,kind=kind,
                    denom=denom,amount_raw=str(amount_raw),status='confirmed',created_at=iso_now()))
        except IntegrityError:return False
    return True


def list_chain_transactions(owner:str,limit:int=50,offset:int=0):
    stmt=(select(chain_transactions.c.tx_hash,chain_transactions.c.kind,chain_transactions.c.denom,
                 chain_transactions.c.amount_raw,chain_transactions.c.status,chain_transactions.c.created_at)
          .where(chain_transactions.c.owner==owner.lower())
          .order_by(chain_transactions.c.created_at.desc(),chain_transactions.c.id.desc())
          .limit(limit+1).offset(offset))
    with engine().connect() as conn:rows=[dict(row) for row in conn.execute(stmt).mappings().all()]
    return {'transactions':rows[:limit],'has_more':len(rows)>limit}

def usage_count(owner:str,kind:str,since_iso:str):
    with engine().connect() as conn:
        return conn.scalar(select(func.count()).select_from(usage_events).where(
            (usage_events.c.owner==owner.lower())&
            (usage_events.c.kind==kind)&(usage_events.c.created_at>=since_iso))) or 0

def reserve_usage(owner:str,kind:str,limit:int,since_iso:str):
    """Reserve a costly request under a per-wallet advisory transaction lock."""
    if kind not in ('assistant','pqc'):raise ValueError('Invalid usage type')
    if limit<=0:return False
    eng=engine()
    with _audit_reservation_lock:
        with eng.begin() as conn:
            if eng.dialect.name=='postgresql':
                key=int.from_bytes(hashlib.sha256((owner.lower()+'-'+kind).encode()).digest()[:8],'big',signed=True)
                conn.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':key})
            count=conn.scalar(select(func.count()).select_from(usage_events).where(
                (usage_events.c.owner==owner.lower())&(usage_events.c.kind==kind)&
                (usage_events.c.created_at>=since_iso))) or 0
            if count>=limit:return False
            conn.execute(insert(usage_events).values(
                id=str(uuid.uuid4()),owner=owner.lower(),kind=kind,created_at=iso_now()))
            return True

