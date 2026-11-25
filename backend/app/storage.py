"""Persistent project, challenge, audit-job and billing records.

Render requires DATABASE_URL pointing at PostgreSQL for durable production data.
SQLite is intended only for local development and tests.
"""
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Integer, select, update, insert, delete, UniqueConstraint
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

def get_job(job_id:str,owner:str):return _one(audit_jobs,'id',job_id,audit_jobs.c.owner==owner.lower())

def set_job(job_id:str,**values):
    with engine().begin() as c:c.execute(update(audit_jobs).where(audit_jobs.c.id==job_id).values(**values))

def create_intent(wallet:str,plan:str,amount_raw:int,token:str,treasury:str,expires:int):
    data={'id':str(uuid.uuid4()),'wallet':wallet.lower(),'plan':plan,'amount_raw':str(amount_raw),'token':token,'treasury':treasury.lower(),'status':'pending','tx_hash':None,'expires_at':expires,'created_at':iso_now()}
    with engine().begin() as c:c.execute(insert(intents).values(**data))
    return data

def get_intent(intent_id:str,wallet:str):return _one(intents,'id',intent_id,intents.c.wallet==wallet.lower())

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
