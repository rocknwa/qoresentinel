"""Regression checks for wallet-scoped history, audit discussions and verified activity."""
from fastapi import HTTPException
from tests.conftest import TEST_WALLET


def test_audit_history_and_saved_report(client, project_id):
    from app import storage
    job = storage.create_job(project_id, TEST_WALLET)
    storage.set_job(job, status='completed', completed_agents=12,
                    report='# Finding\nPersisted report', agent_results='[]')
    listing = client.get('/api/v1/audits')
    assert listing.status_code == 200
    audits = listing.json()['audits']
    assert any(x['id'] == job and x['project_name'] == 'Test' for x in audits)
    report = client.get(f'/api/v1/audits/{job}')
    assert report.status_code == 200
    assert '# Finding' in report.json()['report_markdown']
    assert storage.get_job(job, 'qor1someone-else') is None
    assert storage.list_all_audits('qor1someone-else')['audits'] == []


def test_audit_thread_persists_questions_by_job(client, project_id, monkeypatch):
    from app import storage, assistant
    job = storage.create_job(project_id, TEST_WALLET)
    storage.set_job(job, status='completed', report='# Original analysis')
    monkeypatch.setattr(assistant, 'answer', lambda project_id, owner, question, audit_id=None:
                        {'answer': 'Inspect the access control at line 4.', 'project_id': project_id})
    response = client.post(f'/api/v1/audits/{job}/messages',
                           json={'question': 'What is the priority finding?'})
    assert response.status_code == 200, response.text
    messages = client.get(f'/api/v1/audits/{job}/messages').json()['messages']
    assert [m['role'] for m in messages] == ['user', 'assistant']
    assert 'priority finding' in messages[0]['body']
    assert 'access control' in messages[1]['body']
    assert len(storage.audit_message_history(job, TEST_WALLET)) == 2
    assert storage.audit_message_history(job, 'qor1someone-else') is None
    assert client.get('/api/v1/audits/missing/messages').status_code == 404


def test_incomplete_audit_cannot_have_discussion(client, project_id):
    from app import storage
    job = storage.create_job(project_id, TEST_WALLET)
    assert client.post(f'/api/v1/audits/{job}/messages',
                       json={'question': 'Review this now'}).status_code == 409


def test_verified_transaction_ledger_is_idempotent_and_private(client):
    from app import storage
    tx = '0x' + 'a' * 64
    assert storage.record_chain_transaction(TEST_WALLET, tx, 'login', 'uqor', '1')
    assert not storage.record_chain_transaction(TEST_WALLET, tx, 'login', 'uqor', '1')
    result = client.get('/api/v1/transactions')
    assert result.status_code == 200
    assert len(result.json()['transactions']) == 1
    assert result.json()['transactions'][0]['kind'] == 'login'
    assert storage.list_chain_transactions('qor1someone-else')['transactions'] == []


def test_hybrid_proof_is_verified_before_logging(client, monkeypatch):
    from app import chain, storage
    captured = {}
    def verify(*args, **kwargs):
        captured['args'] = args
        captured['kwargs'] = kwargs
        return {'confirmed': True, 'tx_hash': '0x' + 'b' * 64}
    monkeypatch.setattr(chain, 'verify_native_send', verify)
    result = client.post('/api/v1/transactions/hybrid-proof',
                         json={'tx_hash': '0x' + 'b' * 64})
    assert result.status_code == 200, result.text
    assert captured['args'][1] == captured['args'][2] == TEST_WALLET
    assert captured['args'][3:5] == ('uqor', 1)
    assert captured['kwargs']['require_hybrid'] is True
    assert storage.list_chain_transactions(TEST_WALLET)['transactions'][0]['kind'] == 'hybrid-proof'


def test_native_faucet_threshold_is_ten_qor(client, monkeypatch):
    from app import chain
    values = iter([9_999_999, 10_000_000, 49_850_003])
    monkeypatch.setattr(chain, '_rest_get',
                        lambda *a, **k: {'balance': {'denom': 'uqor', 'amount': str(next(values))}})
    url = f'/api/v1/qorechain/native/balance/{TEST_WALLET}'
    assert client.get(url).json()['low_gas'] is True
    assert client.get(url).json()['low_gas'] is False
    assert client.get(url).json()['low_gas'] is False
