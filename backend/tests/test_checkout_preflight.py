"""Checkout pricing and balance preflight regression tests."""
import pytest
from fastapi import HTTPException

def test_quote_matches_created_native_payment_intent(client,monkeypatch):
    from app import payments,chain
    treasury='qor1pppppppppppppppppppppppppppppppp3pcmkz'
    monkeypatch.setattr(payments,'payment_ready',lambda:treasury)
    monkeypatch.setenv('QORE_TESTNET_PRO_FUSD','2.500000')
    quoted=client.get('/api/v1/payments/plans/pro')
    assert quoted.status_code==200,quoted.text
    info=quoted.json()
    assert info['amount_raw']=='2500000'
    assert info['amount_fusd']=='2.500000'
    assert info['denom']==chain.FUSD_DENOM
    created=client.post('/api/v1/payments/intents',json={'plan':'pro'})
    assert created.status_code==201,created.text
    assert created.json()['amount_raw']==info['amount_raw']
    assert created.json()['denom']==info['denom']

@pytest.mark.parametrize('price', ['0','-1','101','0.0000001','not-a-number','NaN','Infinity'])
def test_quote_rejects_invalid_plan_price(client,monkeypatch,price):
    from app import payments
    monkeypatch.setattr(payments,'payment_ready',lambda:'qor1pppppppppppppppppppppppppppppppp3pcmkz')
    monkeypatch.setenv('QORE_TESTNET_PRO_FUSD',price)
    response=client.get('/api/v1/payments/plans/pro')
    assert response.status_code==503,response.text

def test_plan_quote_rejects_unknown_plan(client,monkeypatch):
    from app import payments
    monkeypatch.setattr(payments,'payment_ready',lambda:'qor1pppppppppppppppppppppppppppppppp3pcmkz')
    assert client.get('/api/v1/payments/plans/enterprise').status_code==422

def test_quote_does_not_create_payment_intent(client,monkeypatch):
    from app import payments,storage
    from tests.conftest import TEST_WALLET
    monkeypatch.setattr(payments,'payment_ready',lambda:'qor1pppppppppppppppppppppppppppppppp3pcmkz')
    monkeypatch.setenv('QORE_TESTNET_PRO_FUSD','1.00')
    assert client.get('/api/v1/payments/plans/pro').status_code==200
    with storage.engine().connect() as connection:
        from sqlalchemy import select
        rows=connection.execute(select(storage.intents.c.id).where(storage.intents.c.wallet==TEST_WALLET)).all()
    assert rows==[]
