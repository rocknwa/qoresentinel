import io
import zipfile

def make_zip(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w") as z:
        for name,data in entries.items(): z.writestr(name,data)
    return stream.getvalue()

def test_health(client):
    assert client.get("/health").json()["status"]=="ok"

def test_paste(client, project_id):
    r=client.post(f"/api/v1/projects/{project_id}/source",json={"source":"pragma solidity ^0.8.20; contract C {}"})
    assert r.status_code==200
    assert "Contract.sol" in r.json()["files"]

def test_sol_upload(client,project_id):
    r=client.post(f"/api/v1/projects/{project_id}/files",files=[("files",("src/C.sol",b"contract C {}","text/plain"))])
    assert r.status_code==200
    assert r.json()["files"]==["src/C.sol"]

def test_wrong_extension(client,project_id):
    r=client.post(f"/api/v1/projects/{project_id}/files",files=[("files",("evil.py",b"print(1)","text/plain"))])
    assert r.status_code==422

def test_traversal(client,project_id):
    zipdata=make_zip({"../malicious.sol":"contract E {}"})
    r=client.post(f"/api/v1/projects/{project_id}/files",files=[("files",("files.zip",zipdata,"application/zip"))])
    assert r.status_code==422

def test_oversize_zip(client,project_id, monkeypatch):
    from app import settings
    monkeypatch.setattr(settings,"MAX_TOTAL_BYTES",10)
    zipdata=make_zip({"a.sol":"contract Example {}"})
    r=client.post(f"/api/v1/projects/{project_id}/files",files=[("files",("files.zip",zipdata,"application/zip"))])
    assert r.status_code==422

def test_empty_project(client,project_id):
    assert client.post(f"/api/v1/projects/{project_id}/audits").status_code==422

def test_unconfigured_audit_is_honest(client,project_id):
    client.post(f"/api/v1/projects/{project_id}/source",json={"source":"contract C {}"})
    r=client.post(f"/api/v1/projects/{project_id}/audits")
    assert r.status_code==503 and "disabled" in r.json()["detail"]

def test_zip_files(client,project_id):
    data=make_zip({"src/A.sol":"contract A {}", "package.json":"{}"})
    r=client.post(f"/api/v1/projects/{project_id}/files",files=[("files",("project.zip",data,"application/zip"))])
    assert r.status_code==200 and r.json()["files"]==["src/A.sol"]

def test_reject_binary(client,project_id):
    r=client.post(f"/api/v1/projects/{project_id}/source",json={"source":"hello\u0000world"})
    assert r.status_code==422
