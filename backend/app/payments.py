"""Exact-amount fUSD testnet ERC-20 payment intents. No private keys or custody."""
import os
import re
import secrets
import time
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException
from . import storage,chain

VALID_ADDR=re.compile(r'^0x[a-fA-F0-9]{40}$')
PLANS={'pro':'QORE_TESTNET_PRO_FUSD'}

def payment_ready():
    # Persist ledger before enabling credits: Render free ephemeral disk is unsafe.
    if os.getenv('QORE_ENABLE_TESTNET_PAYMENTS','false').lower()!='true':raise HTTPException(503,'Testnet checkout is not enabled')
    if not os.getenv('DATABASE_URL','').startswith(('postgres://','postgresql://','postgresql+psycopg://')):
        raise HTTPException(503,'PostgreSQL is required for testnet payment ledger')
    treasury=os.getenv('QORE_TREASURY_ADDRESS','')
    if not VALID_ADDR.fullmatch(treasury):raise HTTPException(503,'Dedicated testnet receiving address is not configured')
    return treasury.lower()

def create(wallet:str,plan:str):
    treasury=payment_ready()
    if plan not in PLANS:raise HTTPException(422,'Unknown testnet plan')
    try:
        price=Decimal(os.getenv(PLANS[plan],''))
        raw=price*1_000_000
        if price<=0 or price>100 or raw!=raw.to_integral_value():raise ValueError()
    except (ValueError,InvalidOperation):raise HTTPException(503,'Testnet plan amount not configured')
    # Per intent value is unique and attributable by sender+receipt; rounding never occurs.
    amount=int(raw)+secrets.randbelow(9_999)+1
    row=storage.create_intent(wallet,plan,amount,chain.FUSD,treasury,int(time.time())+1800)
    return {'id':row['id'],'network':'qorechain-diana','chain_id':9800,'currency':'fUSD','decimals':6,
            'token':row['token'],'recipient':row['treasury'],'amount_raw':row['amount_raw'],
            'amount_fusd':f'{Decimal(amount)/Decimal(1_000_000):.6f}','expires_at':row['expires_at'],'status':'pending',
            'notice':'Testnet tokens only; no real monetary value. Every purchase requires a wallet-approved transfer.'}

def verify(intent_id:str,wallet:str,tx_hash:str):
    treasury=payment_ready()
    row=storage.get_intent(intent_id,wallet)
    if not row:raise HTTPException(404,'Payment intent not found')
    if row['status']=='paid':
        if row['tx_hash']==tx_hash.lower():return {'status':'paid','tx_hash':row['tx_hash']}
        raise HTTPException(409,'Intent already paid with a different transaction')
    if int(time.time())>row['expires_at']:raise HTTPException(410,'Payment intent expired; contact support for late-payment handling')
    if row['treasury']!=treasury:raise HTTPException(409,'Receiving address changed since intent creation')
    evidence=chain.verify_fusd_transfer(tx_hash,wallet,row['treasury'],int(row['amount_raw']),row['token'],confirmations=max(1,int(os.getenv('QORE_PAYMENT_CONFIRMATIONS','3'))))
    if not evidence['confirmed']:return {'status':'pending',**evidence}
    existing=storage.subscription(wallet)
    now=int(time.time());new_exp=max(now,existing['expires_at'] if existing else now)+30*24*3600
    state=storage.mark_intent_paid(intent_id,wallet,tx_hash.lower(),new_exp)
    if state not in ('paid','already-paid'):raise HTTPException(409,'Payment has already been credited or intent is unavailable')
    return {'status':'paid','tx_hash':tx_hash.lower(),'plan':row['plan'],'expires_at':new_exp,**evidence}

def entitlement(wallet:str):
    row=storage.subscription(wallet);now=int(time.time())
    if not row or row['expires_at']<=now:return {'plan':'free','active':True,'expires_at':None}
    return {'plan':row['plan'],'active':True,'expires_at':row['expires_at']}
