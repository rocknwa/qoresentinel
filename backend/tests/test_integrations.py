"""No real keys, wallets or chain writes; all chain calls are mocked."""
import pytest
from fastapi import HTTPException

WALLET='0x'+'a'*40
TREASURY='0x'+'b'*40

def test_mocked_fusd_receipt_requires_exact_matching_transfer(monkeypatch):
    from app import chain
    expected=2_001_234
    def valid_rpc(method,params=None):
        if method=='eth_chainId':return hex(9800)
        if method=='eth_blockNumber':return hex(105)
        if method=='eth_getTransactionReceipt':
            return {'status':'0x1','blockNumber':hex(101),'logs':[
                {'address':chain.FUSD,'topics':[chain.TRANSFER_TOPIC,'0x'+'0'*24+WALLET[2:],'0x'+'0'*24+TREASURY[2:]],'data':hex(expected)}]}
        raise AssertionError(method)
    monkeypatch.setattr(chain,'rpc',valid_rpc)
    tx='0x'+'f'*64
    r=chain.verify_fusd_transfer(tx,WALLET,TREASURY,expected)
    assert r['confirmed'] and r['confirmations']==5
    with pytest.raises(HTTPException) as err:chain.verify_fusd_transfer(tx,WALLET,TREASURY,expected+1)
    assert err.value.status_code==422
    with pytest.raises(HTTPException) as err:chain.verify_fusd_transfer(tx,WALLET,'0x'+'c'*40,expected)
    assert err.value.status_code==422

def test_mocked_payment_intent_credit_is_idempotent(client,monkeypatch):
    from app import payments,storage
    monkeypatch.setattr(payments,'payment_ready',lambda:TREASURY)
    monkeypatch.setenv('QORE_TESTNET_PRO_FUSD','1.000000')
    def verified(*args,**kwargs):return {'confirmed':True,'tx_hash':'0x'+'1'*64,'confirmations':3}
    monkeypatch.setattr(payments.chain,'verify_fusd_transfer',verified)
    created=client.post('/api/v1/payments/intents',json={'plan':'pro'})
    assert created.status_code==201,created.text
    intent=created.json();assert intent['recipient']==TREASURY
    assert int(intent['amount_raw'])>=1_000_001
    tx='0x'+'1'*64
    r=client.post(f"/api/v1/payments/intents/{intent['id']}/verify",json={'tx_hash':tx})
    assert r.status_code==200 and r.json()['status']=='paid'
    assert client.get('/api/v1/subscriptions/me').json()['plan']=='pro'
    repeat=client.post(f"/api/v1/payments/intents/{intent['id']}/verify",json={'tx_hash':tx})
    assert repeat.status_code==200 and repeat.json()['status']=='paid'
    new_intent=client.post('/api/v1/payments/intents',json={'plan':'pro'}).json()
    repeated_tx=client.post(f"/api/v1/payments/intents/{new_intent['id']}/verify",json={'tx_hash':tx})
    assert repeated_tx.status_code==409

def test_wallet_challenge_nonce_is_one_time(client,monkeypatch):
    from app import auth,storage
    monkeypatch.setenv('QORE_SESSION_SECRET','unit-test-secret-at-least-thirty-two-characters')
    row=auth.challenge(WALLET,'localhost:3000')
    assert WALLET in row['message']
    assert storage.consume_challenge(row['challenge_id'],WALLET,10) is not None
    assert storage.consume_challenge(row['challenge_id'],WALLET,10) is None

def test_readonly_tx_evidence_parses_verification(monkeypatch):
    from app import chain
    class FakeResponse:
        status_code=200
        def raise_for_status(self):return None
        def json(self):return {'tx_response':{'code':0,'events':[{'type':'pqc_hybrid_verify','attributes':[{'key':'status','value':'verified'}]}]},'tx':{'body':{'extension_options':[{'@type':'/qorechain.pqc.v1.PQCHybridSignature'}]}}}
    monkeypatch.setattr(chain.requests,'get',lambda *a,**k:FakeResponse())
    data=chain.transaction_evidence('0x'+'2'*64)
    assert data['success'] and data['hybrid_layer_present'] and data['chain_reports_verified']
    assert data['verification_method'].startswith('chain-reported')
