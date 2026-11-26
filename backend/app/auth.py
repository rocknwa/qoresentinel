"""Wallet challenge authentication for native QoreChain and legacy EVM accounts."""
import os
import re
import secrets
import time
from fastapi import Depends,Header,Cookie,HTTPException
from pydantic import BaseModel
from . import storage

ETH_ADDR=re.compile(r'^0x[a-fA-F0-9]{40}$')

# QoreChain native accounts are bech32-encoded 20-byte addresses.
_NATIVE_CHARS = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
_NATIVE_MAP = {c: i for i, c in enumerate(_NATIVE_CHARS)}

def is_native(address: str) -> bool:
    if not isinstance(address,str) or not address.startswith('qor1') or len(address)!=42:
        return False
    try: data=[_NATIVE_MAP[c] for c in address[4:]]
    except KeyError: return False
    chk=1
    values=[ord(c)>>5 for c in 'qor']+[0]+[ord(c)&31 for c in 'qor']+data
    for value in values:
        top=chk>>25
        chk=((chk&0x1ffffff)<<5)^value
        for i,poly in enumerate((0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3)):
            if (top>>i)&1:chk^=poly
    return chk==1 and len(data[:-6])==32

class NativeVerifyRequest(BaseModel):
    address:str
    challenge_id:str
    tx_hash:str

def native_challenge(address:str):
    auth_secret()
    if not is_native(address):raise HTTPException(422,'Invalid QoreChain native address')
    now=int(time.time())
    nonce=secrets.token_hex(16)
    memo=f'QoreSentinel login qorechain-diana {address} {nonce} {now+300}'
    id=storage.store_challenge(address,memo,now+300)
    return {'challenge_id':id,'memo':memo,'expires_at':now+300,'denom':'uqor','amount':'1',
            'faucet_url':'https://dashboard.qorechain.io/faucet'}

def verify_native(payload:NativeVerifyRequest):
    auth_secret()
    if not is_native(payload.address):raise HTTPException(422,'Invalid QoreChain native address')
    memo=storage.peek_challenge(payload.challenge_id,payload.address,int(time.time()))
    if not memo:raise HTTPException(401,'Login challenge expired or already used')
    from . import chain
    proof=chain.verify_native_send(payload.tx_hash,payload.address,payload.address,'uqor',1,memo,
                                   confirmations=1,require_hybrid=True)
    if not proof['confirmed']:
        raise HTTPException(409,'Login transaction is not confirmed yet; retry verification shortly')
    if storage.consume_challenge(payload.challenge_id,payload.address,int(time.time()))!=memo:
        raise HTTPException(401,'Login challenge expired or already used')
    storage.record_chain_transaction(payload.address,payload.tx_hash,'login','uqor','1')
    import jwt
    now=int(time.time())
    token=jwt.encode({'sub':payload.address,'iat':now,'exp':now+3600,'iss':'qoresentinel'},
                     auth_secret(),algorithm='HS256')
    return {'access_token':token,'token_type':'bearer','expires_in':3600,'wallet':payload.address}

class ChallengeRequest(BaseModel): address:str
class VerifyRequest(BaseModel): address:str; challenge_id:str; signature:str

def auth_secret():
    key=os.getenv('QORE_SESSION_SECRET','')
    if len(key)<32: raise HTTPException(503,'Wallet authentication is not configured')
    return key

def challenge(address:str,host:str):
    if not ETH_ADDR.fullmatch(address):raise HTTPException(422,'Invalid EVM wallet address')
    if not host or len(host)>200:raise HTTPException(400,'Invalid application origin')
    host=re.sub(r'[^a-zA-Z0-9.:-]','',host)
    now=int(time.time());nonce=secrets.token_hex(16)
    message=f'QoreSentinel sign-in\nDomain: {host}\nWallet: {address.lower()}\nChain: qorechain-diana (9800)\nNonce: {nonce}\nIssued: {now}\nExpires: {now+300}\nPurpose: Authenticate to manage audits and testnet subscriptions. No blockchain transaction.'
    id=storage.store_challenge(address,message,now+300)
    return {'challenge_id':id,'message':message,'expires_at':now+300}

def verify(payload:VerifyRequest):
    auth_secret()
    message=storage.consume_challenge(payload.challenge_id,payload.address,int(time.time()))
    if not message:raise HTTPException(401,'Challenge invalid, expired or already used')
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        signer=Account.recover_message(encode_defunct(text=message),signature=payload.signature)
    except Exception as exc:
        raise HTTPException(401,'Invalid wallet signature') from exc
    if signer.lower()!=payload.address.lower():raise HTTPException(401,'Signature does not match wallet')
    import jwt
    token=jwt.encode({'sub':signer.lower(),'iat':int(time.time()),'exp':int(time.time())+3600,'iss':'qoresentinel'},auth_secret(),algorithm='HS256')
    return {'access_token':token,'token_type':'bearer','expires_in':3600,'wallet':signer.lower()}

def require_wallet(authorization:str|None=Header(None),qs_session:str|None=Cookie(None)):
    import jwt
    secret=auth_secret()
    token=authorization[7:] if authorization and authorization.startswith('Bearer ') else qs_session
    if not token:raise HTTPException(401,'QoreX wallet authentication required')
    try:data=jwt.decode(token,secret,algorithms=['HS256'],issuer='qoresentinel')
    except jwt.PyJWTError as exc:raise HTTPException(401,'Invalid or expired wallet session') from exc
    wallet=data.get('sub','')
    if not (ETH_ADDR.fullmatch(wallet) or is_native(wallet)):raise HTTPException(401,'Invalid wallet session')
    return wallet.lower()
