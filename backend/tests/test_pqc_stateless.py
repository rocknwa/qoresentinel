"""PQC scans are free, stateless and separate from the paid audit pipeline."""
import io
import zipfile
from app import pqc,storage
from tests.conftest import TEST_WALLET

def _fake_scanner(monkeypatch):
    seen=[]
    def fake(files):
        seen.append(files)
        return {'status':'completed','method':'test-qorescan','components':0,
                'evidence':[],'cbom':{'bomFormat':'CycloneDX','specVersion':'1.6'},
                'limitations':'Unit-test fixture'}
    monkeypatch.setattr(pqc,'scan',fake)
    return seen

def _upload_zip(items):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        for name,text in items.items():archive.writestr(name,text)
    return stream.getvalue()

def test_saved_project_pqc_scan_does_not_consume_audit_or_record_history(client,project_id,monkeypatch):
    files=_fake_scanner(monkeypatch)
    client.post(f'/api/v1/projects/{project_id}/source',
                json={'source':'pragma solidity ^0.8.20; contract Example {}'})
    for _ in range(3):
        response=client.post(f'/api/v1/projects/{project_id}/pqc/scan')
        assert response.status_code==200,response.text
    assert len(files)==3 and 'Contract.sol' in files[0]
    assert client.get('/api/v1/audits').json()['audits']==[]
    assert client.get('/api/v1/subscriptions/usage').json()['pqc']['history_enabled'] is False

def test_pasted_pqc_source_is_ephemeral_and_repeatable(client,monkeypatch):
    seen=_fake_scanner(monkeypatch)
    before=client.get('/api/v1/projects').json()['projects']
    source='pragma solidity ^0.8.20; contract P {}'
    for _ in range(3):
        response=client.post('/api/v1/pqc/scan',json={'source':source})
        assert response.status_code==200,response.text
    assert seen==[{'Contract.sol':source}]*3
    assert client.get('/api/v1/projects').json()['projects']==before
    assert client.get('/api/v1/audits').json()['audits']==[]

def test_upload_files_and_zip_do_not_create_project(client,monkeypatch):
    seen=_fake_scanner(monkeypatch)
    source=b'pragma solidity ^0.8.20; contract ZipP {}'
    r=client.post('/api/v1/pqc/scan/files',
                  files=[('files',('contracts/Example.sol',source,'text/plain'))])
    assert r.status_code==200,r.text
    assert seen[-1]=={'contracts/Example.sol':source.decode()}
    archive=_upload_zip({'contracts/Example.sol':source.decode(),'package.json':'{}'})
    r=client.post('/api/v1/pqc/scan/files',
                  files=[('files',('sources.zip',archive,'application/zip'))])
    assert r.status_code==200,r.text
    assert seen[-1]=={'contracts/Example.sol':source.decode()}
    assert client.get('/api/v1/projects').json()['projects']==[]

def test_ephemeral_pqc_upload_rejects_unsafe_sources(client,monkeypatch):
    seen=_fake_scanner(monkeypatch)
    mixed=client.post('/api/v1/pqc/scan/files',files=[
      ('files',('one.zip',_upload_zip({'A.sol':'contract A {}'}),'application/zip')),
      ('files',('B.sol',b'contract B {}','text/plain'))])
    assert mixed.status_code==422
    traversal=client.post('/api/v1/pqc/scan/files',
      files=[('files',('evil.zip',_upload_zip({'../secret.sol':'contract S {}'}),'application/zip'))])
    assert traversal.status_code==422
    binary=client.post('/api/v1/pqc/scan/files',
      files=[('files',('bad.sol',b'\x00','text/plain'))])
    assert binary.status_code==422
    empty=client.post('/api/v1/pqc/scan',json={'source':'  '})
    assert empty.status_code==422
    assert seen==[]

def test_ephemeral_pqc_requires_wallet_authentication(client,monkeypatch):
    from app import auth
    from app.main import app
    monkeypatch.setenv('QORE_SESSION_SECRET','integration-only-secret-at-least-32-characters')
    app.dependency_overrides.pop(auth.require_wallet,None)
    assert client.post('/api/v1/pqc/scan',json={'source':'contract C {}'}).status_code==401
    assert client.post('/api/v1/pqc/scan/files',files=[
      ('files',('A.sol',b'contract A {}','text/plain'))]).status_code==401
