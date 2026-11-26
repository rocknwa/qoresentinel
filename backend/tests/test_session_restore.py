"""Cookie-based session restoration and owner-scoped audit deep links."""
from app import auth,chain
from tests.conftest import TEST_WALLET

def test_wallet_cookie_session_survives_new_requests_and_logout(client,monkeypatch):
    from app.main import app
    monkeypatch.setenv('QORE_SESSION_SECRET','test-only-signing-secret-of-adequate-length')
    monkeypatch.setenv('QORE_COOKIE_SECURE','false')
    monkeypatch.setattr(chain,'verify_native_send',lambda *args,**kwargs:{'confirmed':True})
    challenge=client.post('/api/v1/auth/native/challenge',json={'address':TEST_WALLET}).json()
    tx='A'*64
    verified=client.post('/api/v1/auth/native/verify',json={
        'address':TEST_WALLET,'challenge_id':challenge['challenge_id'],'tx_hash':tx})
    assert verified.status_code==200,verified.text
    cookie=verified.headers.get('set-cookie','')
    assert 'qs_session=' in cookie and 'httponly' in cookie.lower() and 'samesite=lax' in cookie.lower()
    app.dependency_overrides.pop(auth.require_wallet,None)
    session=client.get('/api/v1/auth/session')
    assert session.status_code==200 and session.json()['wallet']==TEST_WALLET
    assert client.get('/api/v1/projects').status_code==200
    assert client.post('/api/v1/auth/logout').status_code==200
    assert client.get('/api/v1/auth/session').status_code==401

def test_unknown_or_foreign_audit_id_is_not_exposed(client,project_id):
    from app import storage
    job=storage.create_job(project_id,TEST_WALLET)
    assert client.get(f'/api/v1/audits/{job}').status_code==200
    assert storage.get_job(job,'qor1differentwallet') is None
    assert client.get('/api/v1/audits/00000000-0000-0000-0000-000000000000').status_code==404
