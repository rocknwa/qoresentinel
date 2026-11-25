import pytest
from fastapi.testclient import TestClient

TEST_WALLET='qor178nscfyp0cq2ac5x7un4u98xrj4ayp6pt0kw08'
@pytest.fixture
def client(tmp_path,monkeypatch):
    from app import storage,auth
    monkeypatch.setattr(storage,'DATA_DIR',tmp_path)
    monkeypatch.delenv('DATABASE_URL',raising=False)
    monkeypatch.delenv('QORE_ENABLE_LLM_AUDIT',raising=False)
    monkeypatch.delenv('QORE_ENABLE_TESTNET_PAYMENTS',raising=False)
    from app.main import app
    app.dependency_overrides[auth.require_wallet]=lambda: TEST_WALLET
    with TestClient(app) as cli:yield cli
    app.dependency_overrides.clear()
@pytest.fixture
def project_id(client):
    res=client.post('/api/v1/projects',json={'name':'Test'})
    assert res.status_code==201,res.text
    return res.json()['id']
