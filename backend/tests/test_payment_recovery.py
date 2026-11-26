"""Payment intents survive browser refresh without trusting a broadcast ID as settlement."""
import time
from app import payments, storage
from tests.conftest import TEST_WALLET

TREASURY='qor1pppppppppppppppppppppppppppppppp3pcmkz'

def prepare(monkeypatch):
    monkeypatch.setattr(payments,'payment_ready',lambda:TREASURY)
    monkeypatch.setenv('QORE_TESTNET_PRO_FUSD','1.500000')

def test_pending_checkout_can_be_recovered(client,monkeypatch):
    prepare(monkeypatch)
    created=client.post('/api/v1/payments/intents',json={'plan':'pro'})
    assert created.status_code==201,created.text
    intent=created.json()
    pending=client.get('/api/v1/payments/intents')
    assert pending.status_code==200,pending.text
    first=next(x for x in pending.json()['intents'] if x['id']==intent['id'])
    assert first['amount_raw']=='1500000'
    assert first['amount_fusd']=='1.500000'
    assert first['memo']==intent['memo']
    assert first['tx_hash'] is None
    assert storage.subscription(TEST_WALLET) is None

def test_broadcast_hash_records_without_activating_subscription(client,monkeypatch):
    prepare(monkeypatch)
    intent=client.post('/api/v1/payments/intents',json={'plan':'pro'}).json()
    tx='A1'*32
    endpoint=f"/api/v1/payments/intents/{intent['id']}/broadcast"
    saved=client.post(endpoint,json={'tx_hash':tx})
    assert saved.status_code==200,saved.text
    assert saved.json()['verified'] is False
    assert saved.json()['tx_hash']=='0x'+tx.lower()
    assert storage.subscription(TEST_WALLET) is None
    restored=client.get('/api/v1/payments/intents').json()['intents']
    assert next(x for x in restored if x['id']==intent['id'])['tx_hash']=='0x'+tx.lower()
    assert client.post(endpoint,json={'tx_hash':'0x'+tx.lower()}).status_code==200
    assert client.post(endpoint,json={'tx_hash':'b'*64}).status_code==409

def test_broadcast_rejects_other_wallet_and_invalid_hash(client,monkeypatch):
    prepare(monkeypatch)
    intent=client.post('/api/v1/payments/intents',json={'plan':'pro'}).json()
    endpoint=f"/api/v1/payments/intents/{intent['id']}/broadcast"
    assert client.post(endpoint,json={'tx_hash':'bad'}).status_code==422
    assert storage.pending_intents('qor1other',int(time.time()))==[]
    assert client.post('/api/v1/payments/intents/missing/broadcast',json={'tx_hash':'f'*64}).status_code==404

def test_expired_payment_intents_are_not_recoverable(client,monkeypatch):
    prepare(monkeypatch)
    intent=client.post('/api/v1/payments/intents',json={'plan':'pro'}).json()
    with storage.engine().begin() as conn:
        from sqlalchemy import update
        conn.execute(update(storage.intents).where(storage.intents.c.id==intent['id']).values(expires_at=1))
    assert not any(x['id']==intent['id'] for x in client.get('/api/v1/payments/intents').json()['intents'])
    assert client.post(f"/api/v1/payments/intents/{intent['id']}/broadcast",json={'tx_hash':'1'*64}).status_code==409
