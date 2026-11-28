"""Automated attestation controls: wallet ownership, idempotency, quotas and signer guards."""
import hashlib
from unittest.mock import Mock
from fastapi import HTTPException

from tests.conftest import TEST_WALLET

def _job(client, project_id, text="# Analyzed report\n"):
    from app import storage
    job_id=storage.create_job(project_id,TEST_WALLET)
    storage.set_job(job_id,status="completed",report=text,completed_agents=12)
    return job_id

def test_request_rejects_missing_incomplete_and_disabled(client, project_id, monkeypatch):
    from app import storage
    monkeypatch.setenv("QORE_ATTESTATION_ENABLED","true")
    monkeypatch.delenv("QORE_ATTESTATION_CONTRACT",raising=False)
    assert client.post("/api/v1/audits/missing/attestation/request").status_code==404
    pending=storage.create_job(project_id,TEST_WALLET)
    assert client.post(f"/api/v1/audits/{pending}/attestation/request").status_code==409
    completed=_job(client, project_id)
    monkeypatch.setenv("QORE_ATTESTATION_ENABLED","false")
    assert client.post(f"/api/v1/audits/{completed}/attestation/request").status_code==503
    monkeypatch.setenv("QORE_ATTESTATION_ENABLED","true")
    assert client.post(f"/api/v1/audits/{completed}/attestation/request").status_code==503

def test_request_idempotent_and_wallet_scoped(client,project_id,monkeypatch):
    from app import storage, attestation_worker, attestation, auth
    monkeypatch.setenv("QORE_ATTESTATION_ENABLED","true")
    monkeypatch.setenv("QORE_ATTESTATION_CONTRACT",attestation_worker.CONTRACT)
    monkeypatch.setattr(attestation,"report_status",lambda report:{"status":"not_attested","report_sha256":"0x"+hashlib.sha256(report.encode()).hexdigest()})
    calls=[]
    monkeypatch.setattr(attestation_worker,"process",lambda job_id:calls.append(job_id))
    job=_job(client,project_id)
    url=f"/api/v1/audits/{job}/attestation/request"
    first=client.post(url)
    assert first.status_code==202,first.text
    assert first.json()["status"]=="queued"
    assert first.json()["tx_hash"] is None
    second=client.post(url)
    assert second.status_code==202,second.text
    assert storage.get_attestation_request(job,TEST_WALLET)["status"]=="queued"
    assert calls==[job,job]
    client.app.dependency_overrides[auth.require_wallet]=lambda:"qor1someoneelse"
    assert client.post(url).status_code==404
    assert client.get(f"/api/v1/audits/{job}/attestation/request").status_code==404

def test_request_quota_three_audits_per_day(client,project_id,monkeypatch):
    from app import attestation_worker, attestation
    monkeypatch.setenv("QORE_ATTESTATION_ENABLED","true")
    monkeypatch.setenv("QORE_ATTESTATION_CONTRACT",attestation_worker.CONTRACT)
    monkeypatch.setattr(attestation,"report_status",lambda report:{"status":"not_attested"})
    monkeypatch.setattr(attestation_worker,"process",lambda job_id:None)
    for i in range(3):
        job=_job(client,project_id,f"# Report {i}\n")
        assert client.post(f"/api/v1/audits/{job}/attestation/request").status_code==202
    job=_job(client,project_id,"# Report four\n")
    assert client.post(f"/api/v1/audits/{job}/attestation/request").status_code==429

def test_worker_credential_and_destination_guards(monkeypatch):
    from app import attestation_worker as worker
    monkeypatch.setenv("QORE_NETWORK","mainnet")
    with __import__("pytest").raises(worker.PublishError):
        worker.publisher()
    monkeypatch.setenv("QORE_NETWORK","testnet")
    monkeypatch.delenv("QORE_ATTESTATION_PRIVATE_KEY",raising=False)
    with __import__("pytest").raises(worker.PublishError):
        worker.publisher()
    monkeypatch.setenv("QORE_ATTESTATION_CONTRACT","0x"+"1"*40)
    with __import__("pytest").raises(worker.PublishError):
        worker.contract_address()

def test_submitted_tx_does_not_retry_blindly(client,project_id,monkeypatch):
    from app import storage,attestation_worker
    job=_job(client,project_id)
    digest="0x"+hashlib.sha256("# Analyzed report\n".encode()).hexdigest()
    storage.reserve_attestation_request(job,TEST_WALLET,digest)
    storage.update_attestation_request(job,status="submitted",tx_hash="0x"+"a"*64)
    called=[]
    monkeypatch.setattr(attestation_worker,"publisher",lambda:called.append("signed"))
    monkeypatch.setattr(attestation_worker.chain,"rpc",lambda method,params=None:None)
    attestation_worker.process(job)
    assert called==[]
    assert storage.get_attestation_request(job,TEST_WALLET)["status"]=="submitted"

def test_transaction_signing_checksums_destination(client,project_id,monkeypatch):
    """Regression: eth-account rejects a non-checksummed mixed-letter destination."""
    from types import SimpleNamespace
    from eth_account import Account
    from eth_utils import to_checksum_address
    from app import attestation_worker as worker,storage
    job=_job(client,project_id)
    digest="0x"+hashlib.sha256("# Analyzed report\\n".encode()).hexdigest()
    storage.reserve_attestation_request(job,TEST_WALLET,digest)
    key="0x"+"23"*32
    signer=SimpleNamespace(evm=Account.from_key(key).address,private_key_hex=key)
    sent=[]
    def rpc(method,params=None):
        if method=="eth_gasPrice":return hex(1_000_000_000)
        if method=="eth_estimateGas":return hex(55000)
        if method=="eth_getTransactionCount":return "0x3"
        if method=="eth_sendRawTransaction":
            sent.append(params[0])
            return "0x"+"a"*64
        raise AssertionError(method)
    monkeypatch.setattr(worker.chain,"rpc",rpc)
    original=Account.sign_transaction
    def signed_with_expected_address(tx,private_key):
        assert tx["to"] == to_checksum_address(worker.CONTRACT)
        return original(tx,private_key)
    monkeypatch.setattr(worker.Account,"sign_transaction",signed_with_expected_address)
    hash_value=worker._send_attestation(job,digest,signer,worker.CONTRACT)
    saved=storage.get_attestation_request(job,TEST_WALLET)
    assert len(sent)==1
    assert saved["tx_hash"]==hash_value
    assert hash_value.startswith("0x") and len(hash_value)==66
    assert sent[0].startswith("0x") and len(sent[0])>200
    assert saved["status"]=="submitted"
    assert Account.recover_transaction(sent[0]).lower()==signer.evm.lower()


def test_prebroadcast_failed_request_can_retry_after_two_attempts(client,project_id):
    from app import storage
    job=_job(client,project_id)
    digest="0x"+hashlib.sha256("# Analyzed report\\n".encode()).hexdigest()
    storage.reserve_attestation_request(job,TEST_WALLET,digest)
    for attempt in range(2):
        assert storage.claim_attestation_request(job)
        storage.update_attestation_request(job,status="failed")
        row=storage.reserve_attestation_request(job,TEST_WALLET,digest)
        assert row["status"]=="queued"
    assert storage.get_attestation_request(job,TEST_WALLET)["attempts"]==2


def test_legacy_unprefixed_hash_is_normalized_during_receipt_lookup(client,project_id,monkeypatch):
    from app import storage,attestation_worker as worker
    job=_job(client,project_id)
    report="# Analyzed report\\n"
    digest="0x"+hashlib.sha256(report.encode()).hexdigest()
    storage.reserve_attestation_request(job,TEST_WALLET,digest)
    storage.update_attestation_request(job,status="submitted",tx_hash="a"*64)
    requested=[]
    def mock_rpc(method,params=None):
        if method=="eth_getTransactionReceipt":
            requested.append(params[0])
            return None
        raise AssertionError(method)
    monkeypatch.setattr(worker.chain,"rpc",mock_rpc)
    row=worker.reconcile(job,TEST_WALLET)
    assert row["status"]=="submitted"
    assert requested==["0x"+"a"*64]

def test_legacy_hash_is_prefixed_in_user_response(client,project_id,monkeypatch):
    from app import storage,attestation_worker as worker
    job=_job(client,project_id)
    digest="0x"+hashlib.sha256("# Analyzed report\\n".encode()).hexdigest()
    storage.reserve_attestation_request(job,TEST_WALLET,digest)
    storage.update_attestation_request(job,status="submitted",tx_hash="b"*64)
    monkeypatch.setattr(worker,"reconcile",lambda job_id,owner:storage.get_attestation_request(job_id,owner))
    r=client.get(f"/api/v1/audits/{job}/attestation/request")
    assert r.status_code==200
    assert r.json()["tx_hash"]=="0x"+"b"*64
