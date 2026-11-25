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


FUSD_DENOM='erc20:0x97143B771D34ddb9130b807b135Ae675A5a963CA'
FAUCET_URL='https://dashboard.qorechain.io/faucet'

def _tx_hash(value:str)->str:
    if not isinstance(value,str) or not re.fullmatch(r'(?:0x)?[a-fA-F0-9]{64}',value):
        raise HTTPException(422,'Invalid native transaction hash')
    return value.removeprefix('0x').lower()

def _rest_get(path:str,*,params:dict|None=None)->dict|None:
    try:
        response=requests.get(f'{REST}{path}',params=params,timeout=12)
        if response.status_code==404:return None
        response.raise_for_status()
        body=response.json()
        if not isinstance(body,dict):raise ValueError('Unexpected QoreChain REST response')
        return body
    except (requests.RequestException,ValueError) as exc:
        raise HTTPException(502,'QoreChain testnet REST unavailable') from exc

def native_balance(address:str,denom:str='uqor')->dict:
    if denom not in ('uqor',FUSD_DENOM):raise HTTPException(422,'Unsupported native asset')
    response=_rest_get(f'/cosmos/bank/v1beta1/balances/{address}/by_denom',params={'denom':denom})
    raw=(response or {}).get('balance') or {}
    try:
        amount=int(raw.get('amount') or 0)
        if amount<0 or (raw.get('denom') and raw['denom']!=denom):raise ValueError('Malformed bank balance')
    except (TypeError,ValueError) as exc:
        raise HTTPException(502,'Malformed balance from QoreChain') from exc
    return {'network':'qorechain-diana','address':address,'denom':denom,
        'amount_raw':str(amount),'decimals':6,'faucet_url':FAUCET_URL,
        'low_gas':denom=='uqor' and amount<500_000}

def _verified_hybrid(record:dict)->bool:
    tr=record.get('tx_response') or {}
    tx=record.get('tx') or {}
    body=tx.get('body') or {}
    extensions=(body.get('extension_options') or [])+(body.get('non_critical_extension_options') or [])
    if not any('PQCHybridSignature' in str(ext.get('@type','')) for ext in extensions):
        return False
    for event in tr.get('events') or []:
        if event.get('type')!='pqc_hybrid_verify':continue
        attrs={}
        for attr in event.get('attributes') or []:
            def decode(value):
                if value in ('status','verified'):return value
                try:return base64.b64decode(value,validate=True).decode('utf-8')
                except (ValueError,UnicodeDecodeError,TypeError):return value
            attrs[decode(attr.get('key',''))]=decode(attr.get('value',''))
        if attrs.get('status')=='verified':return True
    return False

def verify_native_send(tx_hash:str,sender:str,recipient:str,denom:str,
                       amount_raw:int,memo:str,*,confirmations:int=1,
                       require_hybrid:bool=True)->dict:
    """Validate a native bank transfer before granting any authenticated access."""
    hash_value=_tx_hash(tx_hash)
    record=_rest_get(f'/cosmos/tx/v1beta1/txs/{hash_value}')
    if record is None:return {'confirmed':False,'reason':'transaction-not-indexed'}
    tr=record.get('tx_response') or {}
    tx=record.get('tx') or {}
    body=tx.get('body') or {}
    try:code=int(tr.get('code',-1))
    except (ValueError,TypeError) as exc:
        raise HTTPException(502,'Malformed QoreChain transaction status') from exc
    if code!=0:raise HTTPException(422,'Native transaction was not successful')
    if body.get('memo')!=memo:
        raise HTTPException(422,'Transaction memo does not match the challenge or payment intent')
    messages=body.get('messages') or []
    if not isinstance(messages,list) or len(messages)!=1:
        raise HTTPException(422,'Expected exactly one native bank transfer')
    msg=messages[0]
    if msg.get('@type')!='/cosmos.bank.v1beta1.MsgSend':
        raise HTTPException(422,'Unexpected native transaction message')
    if msg.get('from_address')!=sender or msg.get('to_address')!=recipient:
        raise HTTPException(422,'Native transfer account mismatch')
    coins=msg.get('amount') or []
    if (not isinstance(coins,list) or len(coins)!=1 or
        coins[0].get('denom')!=denom or str(coins[0].get('amount'))!=str(amount_raw)):
        raise HTTPException(422,'Native transfer denomination or amount mismatch')
    if require_hybrid and not _verified_hybrid(record):
        raise HTTPException(422,'Hybrid-signature verification was not confirmed on-chain')
    try:tx_height=int(tr.get('height') or 0)
    except (ValueError,TypeError) as exc:
        raise HTTPException(502,'Malformed transaction block height') from exc
    if tx_height<=0:return {'confirmed':False,'reason':'transaction-unconfirmed'}
    latest=_rest_get('/cosmos/base/tendermint/v1beta1/blocks/latest')
    if not latest:raise HTTPException(502,'Could not read testnet block height')
    try:latest_height=int(latest['block']['header']['height'])
    except (KeyError,TypeError,ValueError) as exc:
        raise HTTPException(502,'Malformed latest block height') from exc
    depth=latest_height-tx_height+1
    if depth<max(1,confirmations):
        return {'confirmed':False,'reason':'insufficient-confirmations',
                'confirmations':depth,'required':confirmations}
    return {'confirmed':True,'tx_hash':'0x'+hash_value,'confirmations':depth,
            'hybrid_verified':True if require_hybrid else _verified_hybrid(record),
            'height':tx_height}
