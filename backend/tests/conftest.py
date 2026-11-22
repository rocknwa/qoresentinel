import os
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import storage
    monkeypatch.setattr(storage,"DATA_DIR",tmp_path)
    monkeypatch.delenv("QORE_ENABLE_LLM_AUDIT",raising=False)
    from app.main import app
    return TestClient(app)

@pytest.fixture
def project_id(client):
    return client.post("/api/v1/projects",json={"name":"Test"}).json()["id"]
