"""QoreChain native fUSD bank transfers, settled only after chain verification."""
import os
import time
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException
from . import storage,chain,auth

PLANS={'pro':'QORE_TESTNET_PRO_FUSD'}

def payment_ready():
    if os.getenv('QORE_ENABLE_TESTNET_PAYMENTS','false').lower()!='true':
        raise HTTPException(503,'Testnet checkout is not enabled')
    if not os.getenv('DATABASE_URL','').startswith(('postgres://','postgresql://','postgresql+psycopg://')):
        raise HTTPException(503,'PostgreSQL is required for the payment ledger')
    treasury=os.getenv('QORE_TREASURY_NATIVE_ADDRESS','').strip()
    if not auth.is_native(treasury):
        raise HTTPException(503,'Native qor1 treasury address is not configured')
    return treasury

def payment_memo(intent_id:str)->str:
    return f'QoreSentinel testnet subscription {intent_id}'

def create(wallet:str,plan:str):
    treasury=payment_ready()
    if not auth.is_native(wallet):
        raise HTTPException(422,'QoreX native authentication is required for testnet checkout')
    if wallet==treasury:
        raise HTTPException(422,'The treasury wallet cannot purchase its own subscription')
    if plan not in PLANS:raise HTTPException(422,'Unknown testnet plan')
    try:
        price=Decimal(os.getenv(PLANS[plan],''))
        raw=price*1_000_000
        if not price.is_finite() or price<=0 or price>100 or raw!=raw.to_integral_value():
            raise ValueError()
    except (ValueError,InvalidOperation):
        raise HTTPException(503,'Testnet plan amount not configured')
    row=storage.create_intent(wallet,plan,int(raw),chain.FUSD_DENOM,treasury,int(time.time())+1800)
    return {'id':row['id'],'network':'qorechain-diana','chain_id':9800,
        'currency':'fUSD','decimals':6,'denom':chain.FUSD_DENOM,
        'recipient':row['treasury'],'amount_raw':row['amount_raw'],
        'amount_fusd':f'{price:.6f}','memo':payment_memo(row['id']),
        'expires_at':row['expires_at'],'status':'pending',
        'notice':'Testnet tokens only. A QoreX-approved native transfer is required.'}

def verify(intent_id:str,wallet:str,tx_hash:str):
    treasury=payment_ready()
    row=storage.get_intent(intent_id,wallet)
    if not row:raise HTTPException(404,'Payment intent not found')
    hash_normalized='0x'+chain._tx_hash(tx_hash)
    if row['status']=='paid':
        if row['tx_hash']==hash_normalized:return {'status':'paid','tx_hash':row['tx_hash']}
        raise HTTPException(409,'Intent already paid with a different transaction')
    if int(time.time())>row['expires_at']:
        raise HTTPException(410,'Payment intent expired; contact support for late-payment handling')
    if row['treasury']!=treasury or row['token']!=chain.FUSD_DENOM:
        raise HTTPException(409,'Testnet payment configuration changed')
    required=max(1,min(12,int(os.getenv('QORE_PAYMENT_CONFIRMATIONS','3'))))
    evidence=chain.verify_native_send(hash_normalized,wallet,row['treasury'],row['token'],
        int(row['amount_raw']),payment_memo(intent_id),confirmations=required,require_hybrid=True)
    if not evidence['confirmed']:return {'status':'pending',**evidence}
    existing=storage.subscription(wallet)
    now=int(time.time())
    new_expiry=max(now,existing['expires_at'] if existing else now)+30*24*3600
    state=storage.mark_intent_paid(intent_id,wallet,hash_normalized,new_expiry)
    if state not in ('paid','already-paid'):
        raise HTTPException(409,'Payment was already credited or intent is unavailable')
    return {'status':'paid','tx_hash':hash_normalized,'plan':row['plan'],'expires_at':new_expiry,**evidence}

def entitlement(wallet:str):
    row=storage.subscription(wallet);now=int(time.time())
    if not row or row['expires_at']<=now:return {'plan':'free','active':True,'expires_at':None}
    return {'plan':row['plan'],'active':True,'expires_at':row['expires_at']}
