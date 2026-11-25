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

def test_native_payment_intent_credit_is_idempotent(client,monkeypatch):
    from app import payments,chain
    from tests.conftest import TEST_WALLET
    treasury='qor1pppppppppppppppppppppppppppppppp3pcmkz'
    assert payments.auth.is_native(TEST_WALLET) and payments.auth.is_native(treasury)
    monkeypatch.setattr(payments,'payment_ready',lambda:treasury)
    monkeypatch.setenv('QORE_TESTNET_PRO_FUSD','1.000000')
    monkeypatch.setattr(chain,'verify_native_send',lambda *args,**kw:{'confirmed':True,'tx_hash':'0x'+'1'*64,'confirmations':3})
    created=client.post('/api/v1/payments/intents',json={'plan':'pro'})
    assert created.status_code==201,created.text
    intent=created.json()
    assert intent['recipient']==treasury and intent['denom']==chain.FUSD_DENOM
    assert intent['memo'].endswith(intent['id']) and int(intent['amount_raw'])==1_000_000
    tx='0x'+'1'*64
    response=client.post(f"/api/v1/payments/intents/{intent['id']}/verify",json={'tx_hash':tx})
    assert response.status_code==200 and response.json()['status']=='paid'
    assert client.get('/api/v1/subscriptions/me').json()['plan']=='pro'
    assert client.post(f"/api/v1/payments/intents/{intent['id']}/verify",json={'tx_hash':tx}).status_code==200
    newer=client.post('/api/v1/payments/intents',json={'plan':'pro'}).json()
    assert client.post(f"/api/v1/payments/intents/{newer['id']}/verify",json={'tx_hash':tx}).status_code==409

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


def test_native_login_accepts_verified_hybrid_once(client,monkeypatch):
    from app import chain
    from tests.conftest import TEST_WALLET
    monkeypatch.setenv('QORE_SESSION_SECRET','native-tests-secret-keep-private-32-characters')
    response=client.post('/api/v1/auth/native/challenge',json={'address':TEST_WALLET})
    assert response.status_code==200,response.text
    challenge=response.json()
    assert challenge['denom']=='uqor' and challenge['amount']=='1'
    def fake_send(tx_hash,sender,recipient,denom,amount,memo,**kwargs):
        assert sender==recipient==TEST_WALLET
        assert denom=='uqor' and amount==1 and memo==challenge['memo']
        assert kwargs['require_hybrid']
        return {'confirmed':True,'hybrid_verified':True}
    monkeypatch.setattr(chain,'verify_native_send',fake_send)
    proof={'address':TEST_WALLET,'challenge_id':challenge['challenge_id'],'tx_hash':'0x'+'f'*64}
    accepted=client.post('/api/v1/auth/native/verify',json=proof)
    assert accepted.status_code==200 and accepted.json()['wallet']==TEST_WALLET
    assert client.post('/api/v1/auth/native/verify',json=proof).status_code==401

def test_native_login_can_retry_unconfirmed_transaction(client,monkeypatch):
    from app import chain
    from tests.conftest import TEST_WALLET
    monkeypatch.setenv('QORE_SESSION_SECRET','native-tests-secret-keep-private-32-characters')
    challenge=client.post('/api/v1/auth/native/challenge',json={'address':TEST_WALLET}).json()
    monkeypatch.setattr(chain,'verify_native_send',lambda *a,**k:{'confirmed':False})
    proof={'address':TEST_WALLET,'challenge_id':challenge['challenge_id'],'tx_hash':'0x'+'a'*64}
    assert client.post('/api/v1/auth/native/verify',json=proof).status_code==409
    monkeypatch.setattr(chain,'verify_native_send',lambda *a,**k:{'confirmed':True})
    assert client.post('/api/v1/auth/native/verify',json=proof).status_code==200

def test_native_balance_and_faucet(client,monkeypatch):
    from app import chain
    from tests.conftest import TEST_WALLET
    monkeypatch.setattr(chain,'_rest_get',lambda *a,**kw:{'balance':{'denom':'uqor','amount':'100000'}})
    result=client.get(f'/api/v1/qorechain/native/balance/{TEST_WALLET}')
    assert result.status_code==200,result.text
    balance=result.json()
    assert balance['low_gas'] and balance['amount_raw']=='100000'
    assert balance['faucet_url']=='https://dashboard.qorechain.io/faucet'
    assert client.get('/api/v1/qorechain/native/balance/qor1bad').status_code==422
    assert client.get(f'/api/v1/qorechain/native/balance/{TEST_WALLET}?denom=bogus').status_code==422

def test_native_send_verifier_checks_memo_amount_and_pqc(monkeypatch):
    from app import chain
    from tests.conftest import TEST_WALLET
    memo='QoreSentinel testnet subscription intent-id'
    record={'tx_response':{'code':0,'height':'100','events':[{'type':'pqc_hybrid_verify','attributes':[{'key':'status','value':'verified'}]}]},
            'tx':{'body':{'memo':memo,'messages':[{'@type':'/cosmos.bank.v1beta1.MsgSend',
                'from_address':TEST_WALLET,'to_address':TEST_WALLET,
                'amount':[{'denom':chain.FUSD_DENOM,'amount':'1000000'}]}],
                'extension_options':[{'@type':'/qorechain.pqc.v1.PQCHybridSignature'}]}}}
    monkeypatch.setattr(chain,'_rest_get',lambda path,**kw: {'block':{'header':{'height':'105'}}} if path.endswith('/latest') else record)
    tx='0x'+'f'*64
    result=chain.verify_native_send(tx,TEST_WALLET,TEST_WALLET,chain.FUSD_DENOM,1_000_000,memo,confirmations=3)
    assert result['confirmed'] and result['hybrid_verified'] and result['confirmations']==6
    with pytest.raises(HTTPException) as e:chain.verify_native_send(tx,TEST_WALLET,TEST_WALLET,chain.FUSD_DENOM,999_999,memo)
    assert e.value.status_code==422
    with pytest.raises(HTTPException) as e:chain.verify_native_send(tx,TEST_WALLET,TEST_WALLET,chain.FUSD_DENOM,1_000_000,'wrong memo')
    assert e.value.status_code==422
    record['tx']['body']['extension_options']=[]
    with pytest.raises(HTTPException) as e:chain.verify_native_send(tx,TEST_WALLET,TEST_WALLET,chain.FUSD_DENOM,1_000_000,memo)
    assert e.value.status_code==422

def test_native_address_checksum_validation():
    from app.auth import is_native
    from tests.conftest import TEST_WALLET
    assert is_native(TEST_WALLET)
    assert not is_native(TEST_WALLET[:-1]+'x')
    assert not is_native('qor1'+'a'*38)
    assert not is_native('0x'+'a'*40)


def test_native_inspector_accepts_qorex_hash_without_prefix(monkeypatch):
    from app import chain
    canonical='A1B2'*16
    called=[]
    class FakeResponse:
        status_code=200
        def raise_for_status(self):pass
        def json(self):
            return {'tx_response':{'code':0,'height':'300',
                'events':[{'type':'pqc_hybrid_verify',
                           'attributes':[{'key':'status','value':'verified'}]}]},
                'tx':{'body':{'extension_options':[{'@type':'/qorechain.pqc.v1.PQCHybridSignature'}]}}}
    def fake_get(url,**kw):
        called.append(url)
        return FakeResponse()
    monkeypatch.setattr(chain.requests,'get',fake_get)
    for candidate in (canonical,canonical.lower(),'0x'+canonical.lower(),'0X'+canonical):
        evidence=chain.transaction_evidence(candidate)
        assert evidence['found'] and evidence['chain_reports_verified']
        assert evidence['tx_hash']==canonical
        assert called[-1].endswith('/cosmos/tx/v1beta1/txs/'+canonical)

def test_native_inspector_rejects_bad_hash_without_rpc(monkeypatch):
    from app import chain
    called=[]
    monkeypatch.setattr(chain.requests,'get',lambda *a,**k:called.append(a))
    for candidate in ('abc','0x123','0x'+'g'*64,'0x'+'a'*63):
        with pytest.raises(HTTPException) as err:chain.transaction_evidence(candidate)
        assert err.value.status_code==422
    assert called==[]

def test_native_inspector_not_indexed_is_not_a_failed_broadcast(monkeypatch):
    from app import chain
    class Missing:
        status_code=404
    monkeypatch.setattr(chain.requests,'get',lambda *a,**k:Missing())
    evidence=chain.transaction_evidence('f'*64)
    assert evidence['found'] is False
    assert evidence['tx_hash']=='F'*64
