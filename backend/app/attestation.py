"""Read-only, wallet-scoped audit-report digest anchoring for Diana EVM 9800.

Public blockchain proof says the designated publisher recorded this digest;
it is not a claim that the report's vulnerabilities were confirmed.
"""
import hashlib
import os
import re
from datetime import datetime,timezone
from fastapi import HTTPException
from eth_utils import keccak
from . import chain

ADDRESS = re.compile(r'^0x[a-fA-F0-9]{40}$')
SELECTOR = keccak(text='attestedAt(bytes32)')[:4].hex()

def report_status(report: str) -> dict:
    digest = '0x' + hashlib.sha256(report.encode('utf-8')).hexdigest()
    contract = os.getenv('QORE_ATTESTATION_CONTRACT', '').strip()
    base = {
        'report_sha256': digest, 'network': 'qorechain-diana',
        'chain_id': 9800, 'contract_address': contract or None,
        'attested_at': None,
    }
    if not contract:
        return {**base, 'status': 'not_configured'}
    if not ADDRESS.fullmatch(contract):
        raise HTTPException(503, 'Attestation contract is misconfigured')
    if int(chain.rpc('eth_chainId'), 16) != 9800:
        raise HTTPException(502, 'Attestation RPC is not on Diana testnet')
    code = chain.rpc('eth_getCode', [contract, 'latest'])
    if not code or code == '0x':
        raise HTTPException(502, 'Attestation contract not found on Diana')
    result = chain.rpc('eth_call', [{'to':contract, 'data':'0x'+SELECTOR+digest[2:]}, 'latest'])
    if not isinstance(result, str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}', result):
        raise HTTPException(502, 'Invalid attestation contract response')
    timestamp = int(result, 16)
    if timestamp == 0:
        return {**base, 'status': 'not_attested'}
    # Guard implausible response from a misconfigured contract.
    if timestamp > 253402300799:
        raise HTTPException(502, 'Invalid on-chain attestation timestamp')
    return {**base, 'status': 'attested',
            'attested_at': datetime.fromtimestamp(timestamp, timezone.utc).isoformat()}
