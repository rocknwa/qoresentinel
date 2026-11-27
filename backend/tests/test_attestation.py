import hashlib
from fastapi import HTTPException

def test_attestation_private_nonexistent_and_incomplete(client, project_id):
    assert client.get('/api/v1/audits/does-not-exist/attestation').status_code == 404
    from app import storage
    from tests.conftest import TEST_WALLET
    job = storage.create_job(project_id, TEST_WALLET)
    assert client.get(f'/api/v1/audits/{job}/attestation').status_code == 409

def test_attestation_without_contract_and_verified(client, project_id, monkeypatch):
    from app import storage, chain, auth
    from tests.conftest import TEST_WALLET
    # Store completed report directly to exercise the independent read-only path.
    job = storage.create_job(project_id,TEST_WALLET)
    report = "# Security report\nLow: demo\n"
    storage.set_job(job, status='completed', completed_agents=12, report=report)
    monkeypatch.delenv('QORE_ATTESTATION_CONTRACT', raising=False)
    r = client.get(f'/api/v1/audits/{job}/attestation')
    assert r.status_code == 200, r.text
    expected = '0x'+hashlib.sha256(report.encode('utf-8')).hexdigest()
    assert r.json()['status'] == 'not_configured'
    assert r.json()['report_sha256'] == expected

    contract = '0x'+'1'*40
    monkeypatch.setenv('QORE_ATTESTATION_CONTRACT',contract)
    called = []
    def mocked_rpc(method, params=None):
        called.append((method,params))
        return {'eth_chainId':'0x2648', 'eth_getCode':'0x6001',
                'eth_call':'0x'+format(1732809600,'064x')}[method]
    monkeypatch.setattr(chain,'rpc',mocked_rpc)
    r = client.get(f'/api/v1/audits/{job}/attestation')
    assert r.status_code == 200,r.text
    assert r.json()['status']=='attested'
    assert r.json()['attested_at']=='2024-11-28T16:00:00+00:00'
    assert called[-1][0]=='eth_call'
    assert called[-1][1][0]['data'].endswith(expected[2:])
    monkeypatch.setattr(chain,'rpc',lambda method,params=None: '0x' if method=='eth_getCode' else {'eth_chainId':'0x2648'}[method])
    assert client.get(f'/api/v1/audits/{job}/attestation').status_code == 502

def test_attestation_does_not_expose_other_wallet_report(client, project_id, monkeypatch):
    from app import storage, auth
    from tests.conftest import TEST_WALLET
    job = storage.create_job(project_id,TEST_WALLET)
    storage.set_job(job,status='completed',report='secret')
    client.app.dependency_overrides[auth.require_wallet]=lambda:'qor1notowned'
    assert client.get(f'/api/v1/audits/{job}/attestation').status_code==404
