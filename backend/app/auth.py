"""EVM wallet challenge login. QoreX native wallet connects separately; it cannot personal_sign yet."""
import os
import re
import secrets
import time
from fastapi import Depends,Header,HTTPException
from pydantic import BaseModel
from . import storage

ETH_ADDR=re.compile(r'^0x[a-fA-F0-9]{40}$')
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

def require_wallet(authorization:str|None=Header(None)):
    import jwt
    secret=auth_secret()
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Sign in with an EVM wallet')
    try:data=jwt.decode(authorization[7:],secret,algorithms=['HS256'],issuer='qoresentinel')
    except jwt.PyJWTError as exc:raise HTTPException(401,'Invalid or expired wallet session') from exc
    wallet=data.get('sub','')
    if not ETH_ADDR.fullmatch(wallet):raise HTTPException(401,'Invalid wallet session')
    return wallet.lower()
