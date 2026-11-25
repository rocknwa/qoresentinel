"""Read-only QoreChain Diana REST and EVM RPC evidence checks."""
import os
import re
import base64
import requests
from fastapi import HTTPException

REST='https://api-testnet.qore.host'
RPC='https://evm-testnet.qore.host'
TESTNET_CHAIN_ID=9800
FUSD='0x97143b771d34ddb9130b807b135ae675a5a963ca'
TRANSFER_TOPIC='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

def rpc(method,params=None):
    url=os.getenv('QORE_EVM_RPC',RPC)
    try:
        response=requests.post(url,json={'jsonrpc':'2.0','id':1,'method':method,'params':params or []},timeout=12)
        response.raise_for_status();result=response.json()
        if result.get('error'):raise ValueError('RPC request refused')
        return result.get('result')
    except (requests.RequestException,ValueError) as exc:
        raise HTTPException(502,'QoreChain testnet RPC unavailable') from exc

def transaction_evidence(tx_hash:str):
    if not re.fullmatch(r'0x[a-fA-F0-9]{64}',tx_hash):raise HTTPException(422,'Invalid transaction hash')
    try:
        resp=requests.get(f'{REST}/cosmos/tx/v1beta1/txs/{tx_hash.removeprefix("0x")}',timeout=12)
        if resp.status_code==404:return {'found':False,'network':'qorechain-diana','tx_hash':tx_hash}
        resp.raise_for_status();body=resp.json()
        tr=body.get('tx_response') or {};tx=body.get('tx') or {}
        txbody=tx.get('body') or {}
        opts=(txbody.get('extension_options') or [])+(txbody.get('non_critical_extension_options') or [])
        has_layer=any('PQCHybridSignature' in x.get('@type','') for x in opts)
        verified_event=False
        for event in tr.get('events',[]):
            if event.get('type')=='pqc_hybrid_verify':
                for attr in event.get('attributes',[]):
                    key=attr.get('key','');value=attr.get('value','')
                    if key!='status':
                        try:key=base64.b64decode(key,validate=True).decode('utf-8')
                        except (ValueError,UnicodeDecodeError):pass
                    if value!='verified':
                        try:value=base64.b64decode(value,validate=True).decode('utf-8')
                        except (ValueError,UnicodeDecodeError):pass
                    if key=='status' and value=='verified':verified_event=True
        success=str(tr.get('code',''))=='0'
        return {'found':True,'network':'qorechain-diana','tx_hash':tx_hash,'success':success,
           'hybrid_layer_present':has_layer,'chain_reports_verified':success and has_layer and verified_event,'height':tr.get('height'),
           'verification_method':'chain-reported evidence (not independent local ML-DSA verification)'}
    except (requests.RequestException,ValueError) as exc:raise HTTPException(502,'Could not retrieve QoreChain transaction evidence') from exc

def verify_fusd_transfer(tx_hash:str,from_wallet:str,treasury:str,expected_raw:int,token:str=FUSD,confirmations:int=3):
    if not re.fullmatch(r'0x[a-fA-F0-9]{64}',tx_hash):raise HTTPException(422,'Invalid transaction hash')
    if int(rpc('eth_chainId'),16)!=TESTNET_CHAIN_ID:raise HTTPException(502,'RPC chain mismatch: expected Diana testnet')
    receipt=rpc('eth_getTransactionReceipt',[tx_hash])
    if not receipt:return {'confirmed':False,'reason':'transaction-pending'}
    if int(receipt.get('status','0x0'),16)!=1:raise HTTPException(422,'Transaction failed on-chain')
    if not receipt.get('blockNumber'):return {'confirmed':False,'reason':'transaction-unconfirmed'}
    height=int(rpc('eth_blockNumber'),16)
    depth=height-int(receipt['blockNumber'],16)+1
    if depth < confirmations:return {'confirmed':False,'reason':'insufficient-confirmations','confirmations':depth,'required':confirmations}
    sender=from_wallet.lower();to=treasury.lower();token=token.lower();events=[]
    for log in receipt.get('logs',[]):
        topics=log.get('topics',[])
        if log.get('address','').lower()!=token or len(topics)<3 or topics[0].lower()!=TRANSFER_TOPIC:continue
        try:
            log_sender='0x'+topics[1][-40:].lower();recipient='0x'+topics[2][-40:].lower();amount=int(log['data'],16)
        except (ValueError,TypeError,KeyError):continue
        if log_sender==sender and recipient==to and amount==expected_raw:events.append(log)
    if not events:raise HTTPException(422,'No matching fUSD Transfer event for this wallet, token, destination and exact amount')
    return {'confirmed':True,'confirmations':depth,'tx_hash':tx_hash.lower(),'block_number':int(receipt['blockNumber'],16)}
