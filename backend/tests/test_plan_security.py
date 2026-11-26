"""Server-side plan limits and direct API boundary tests."""
import pytest
from datetime import datetime,timedelta,timezone
from tests.conftest import TEST_WALLET

def test_audit_quota_applies_without_frontend(client,project_id,monkeypatch):
    from app import payments,storage
    monkeypatch.setenv('QORE_ENABLE_LLM_AUDIT','true')
    monkeypatch.setenv('OPENROUTER_API_KEY','dummy-not-used')
    monkeypatch.setenv('QORE_DAILY_AUDIT_LIMIT','1')
    monkeypatch.setattr(payments,'entitlement',lambda wallet:{'plan':'free','expires_at':None})
    monkeypatch.setattr('app.main.EXECUTOR.submit',lambda *args,**kw:None)
    client.post(f'/api/v1/projects/{project_id}/source',json={'source':'pragma solidity ^0.8.20; contract A {}'})
    first=client.post(f'/api/v1/projects/{project_id}/audits')
    assert first.status_code==202,first.text
    # A second direct API call cannot start another paid LLM job.
    assert client.post(f'/api/v1/projects/{project_id}/audits').status_code==429
    usage=client.get('/api/v1/subscriptions/usage')
    assert usage.status_code==200
    assert usage.json()['audits']=={'used':1,'limit':1,'remaining':0}

def test_quota_reservation_atomic_and_recovers_expiration(client,project_id):
    from app import storage
    since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    first=storage.reserve_audit(TEST_WALLET,project_id,1,since)
    assert first['id']
    assert storage.reserve_audit(TEST_WALLET,project_id,1,since)['error']=='pending'
    storage.set_job(first['id'],status='completed')
    assert storage.reserve_audit(TEST_WALLET,project_id,1,since)['error']=='limit'
    assert storage.reserve_audit(TEST_WALLET,project_id,2,since)['id']

def test_plan_quotas_and_expired_subscription(client,monkeypatch):
    from app import payments
    monkeypatch.setenv('QORE_DAILY_AUDIT_LIMIT','2')
    monkeypatch.setenv('QORE_PRO_DAILY_AUDIT_LIMIT','7')
    monkeypatch.setattr(payments,'entitlement',lambda _: {'plan':'pro','expires_at':9999999999})
    assert payments.audit_quota(TEST_WALLET)==7
    monkeypatch.setattr(payments,'entitlement',lambda _: {'plan':'free','expires_at':None})
    assert payments.audit_quota(TEST_WALLET)==2
    monkeypatch.setenv('QORE_REQUIRE_ACTIVE_PLAN','true')
    assert payments.audit_quota(TEST_WALLET)==0

def test_usage_buckets_enforced_without_ui(client):
    from app import storage
    since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    assert storage.reserve_usage(TEST_WALLET,'assistant',1,since)
    assert not storage.reserve_usage(TEST_WALLET,'assistant',1,since)
    assert storage.usage_count(TEST_WALLET,'assistant',since)==1
    assert storage.reserve_usage(TEST_WALLET,'pqc',1,since)
    with pytest.raises(ValueError):storage.reserve_usage(TEST_WALLET,'other',1,since)

def test_direct_api_cannot_read_private_wallet_data_without_auth(client,monkeypatch):
    from app import auth
    from app.main import app
    monkeypatch.setenv('QORE_SESSION_SECRET','direct-api-auth-regression-secret-32-chars')
    app.dependency_overrides.pop(auth.require_wallet,None)
    for method,path in [
        ('get','/api/v1/projects'),('post','/api/v1/projects'),
        ('get','/api/v1/audits'),('get','/api/v1/audits/missing'),
        ('get','/api/v1/transactions'),('get','/api/v1/subscriptions/me'),
        ('get','/api/v1/subscriptions/usage'),('get','/api/v1/payments/intents')
    ]:
        res=client.request(method,path,json={'name':'No auth'} if method=='post' else None)
        assert res.status_code==401,(path,res.status_code,res.text)
    assert client.get('/health').status_code==200
