"""Testnet-only, wallet-requested attestation publisher.

Signs only the bytes32 digest of a persisted completed audit. The deployed
publisher address and contract are independently verified before sending.
A PostgreSQL advisory session lock serializes the shared publisher across
Render instances; no secret is returned to the client or stored in the DB.
"""
import logging
import os
import re
import time
from contextlib import contextmanager

from eth_account import Account
from eth_utils import keccak
from sqlalchemy import text

from . import attestation, chain, storage

LOG = logging.getLogger(__name__)
EXPECTED_PUBLISHER = "0x28ae5289681319a1b0c05b3ffbbb658d15ad33e9"
CONTRACT = "0x457962c68d6f3beaad af47456402f57fb40fc6bf".replace(" ", "")
# Constant wallet/contract guards avoid accidentally signing for another dApp.
LOCK_ID = 789342109
HEX64 = re.compile(r"^0x[a-fA-F0-9]{64}$")
PUBLISHER_SELECTOR = "0x" + keccak(text="publisher()")[:4].hex()
ATTEST_SELECTOR = "0x" + keccak(text="attest(bytes32)")[:4].hex()
REST = "https://api-testnet.qore.host"


class PublishError(Exception):
    pass


def enabled():
    return os.getenv("QORE_ATTESTATION_ENABLED", "").lower() == "true"


def publisher():
    if os.getenv("QORE_NETWORK", "testnet") != "testnet":
        raise PublishError("Testnet-only publisher refuses a non-testnet network")
    key = os.getenv("QORE_ATTESTATION_PRIVATE_KEY", "").strip()
    recovery = os.getenv("QORE_ATTESTATION_PQC_RECOVERY_CODE", "").strip()
    if not HEX64.fullmatch(key) or not recovery.startswith("QRC1-"):
        raise PublishError("Testnet attestation publisher credentials are unavailable")
    from qorsdk import unified_account_from_seed
    account = unified_account_from_seed(bytes.fromhex(key[2:]), recovery_code=recovery)
    if account.evm.lower() != EXPECTED_PUBLISHER:
        raise PublishError("Configured publisher is not the deployed contract publisher")
    return account


def contract_address():
    addr = os.getenv("QORE_ATTESTATION_CONTRACT", "").lower().strip()
    if addr != CONTRACT:
        raise PublishError("Unexpected attestation contract; publisher refuses to sign")
    return addr


def check_chain(contract: str, account):
    if int(chain.rpc("eth_chainId"), 16) != 9800:
        raise PublishError("Refusing to publish outside Diana testnet")
    if chain.rpc("eth_getCode", [contract, "latest"]) in (None, "", "0x"):
        raise PublishError("Attestation contract is not deployed")
    raw = chain.rpc("eth_call", [{"to":contract, "data":PUBLISHER_SELECTOR}, "latest"])
    if not isinstance(raw, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", raw):
        raise PublishError("Cannot verify contract publisher")
    observed = "0x" + raw[-40:].lower()
    if observed != account.evm.lower():
        raise PublishError("The publisher key does not control this contract")


@contextmanager
def publisher_lock():
    """Lock the shared key across processes; SQLite uses a process-local lock."""
    eng = storage.engine()
    if eng.dialect.name == "postgresql":
        conn = eng.connect()
        try:
            locked = conn.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": LOCK_ID})
            yield bool(locked)
        finally:
            if locked:
                conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
            conn.close()
    else:
        with storage._audit_reservation_lock:
            yield True


def _account_sequence(native: str):
    rec = chain._rest_get("/cosmos/auth/v1beta1/accounts/" + native)
    if not isinstance(rec, dict) or not rec.get("account"):
        raise PublishError("Publisher account not found on Diana")
    acct = rec["account"]
    for _ in range(5):
        if isinstance(acct, dict) and isinstance(acct.get("base_account"), dict):
            acct = acct["base_account"]
        else:
            break
    return int(acct.get("account_number", 0)), int(acct.get("sequence", 0))


def _native_confirmed(hash_value: str):
    result = chain.transaction_evidence(hash_value)
    return bool(result.get("found") and result.get("success") and result.get("chain_reports_verified"))


def _open_scoped_window(account, contract):
    """Each request gets one tightly scoped EVM transaction authorization."""
    from qorsdk import (RestClient, broadcast, fetch_pqc_status, get_evm_window,
                        is_registered_pqc_key, msg, resolve_sign_bytes_version, sign_hybrid_eth)

    key_info = fetch_pqc_status(REST, account.cosmos)
    if not key_info.get("registered") or is_registered_pqc_key(key_info, account.pqc.public_key) is not True:
        raise PublishError("PQC registration is missing or does not match the configured recovery code")
    with RestClient(REST) as rest:
        window = get_evm_window(rest, account.cosmos)
    if (window.live and not window.native_only and
        tuple(t.lower() for t in window.allowed_targets) == (contract,) and
        window.remaining_txs >= 1 and window.remaining_blocks >= 20 and
        window.remaining_value >= 200000):
        return None

    account_number, sequence = _account_sequence(account.cosmos)
    message = msg.pqc.open_evm_window(
        sender=account.cosmos, blocks=300, max_txs=1, max_value="500000",
        allowed_targets=[contract],
    )
    version = resolve_sign_bytes_version("qorechain-diana", rest_url=REST)
    built = sign_hybrid_eth(
        account=account, chain_id="qorechain-diana",
        account_number=account_number, sequence=sequence, messages=[message],
        fee={"amount":[{"denom":"uqor", "amount":"100000"}], "gas":"800000"},
        sign_bytes_version=version,
    )
    response = broadcast(REST, built.tx_raw_bytes)
    tx = response.get("tx_response") or {}
    if int(tx.get("code", 1)) != 0:
        raise PublishError("QoreChain rejected the hybrid EVM authorization")
    tx_hash = tx.get("txhash", "")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", tx_hash):
        raise PublishError("No transaction hash returned for hybrid authorization")
    for _ in range(12):
        if _native_confirmed(tx_hash):
            return tx_hash
        time.sleep(2)
    raise PublishError("Hybrid authorization was broadcast but could not be confirmed")


def _send_attestation(job_id, digest, account, contract):
    """Persist raw EVM hash BEFORE broadcasting, so crashed work is reconcilable."""
    calldata = ATTEST_SELECTOR + digest[2:]
    gas_price = int(chain.rpc("eth_gasPrice"), 16)
    if not 0 < gas_price <= 250_000_000_000:
        raise PublishError("Unexpected Diana fee quote")
    gas_price = min(gas_price * 12 // 10, 250_000_000_000)
    gas_estimate = int(chain.rpc("eth_estimateGas", [{
        "from": account.evm, "to":contract, "data":calldata, "value":"0x0",
    }]), 16)
    gas_limit = min(200_000, gas_estimate * 13 // 10 + 3000)
    if gas_estimate < 21000 or gas_estimate > 150000:
        raise PublishError("Unusual attestation gas estimate")
    if (gas_limit * gas_price + 10**12-1)//10**12 > 200000:
        raise PublishError("Transaction exceeds authorized gas budget")
    nonce = int(chain.rpc("eth_getTransactionCount", [account.evm, "pending"]), 16)
    transaction = {
        "to": contract, "value":0, "data":calldata,
        "gas":gas_limit, "gasPrice":gas_price, "nonce":nonce, "chainId":9800,
    }
    signed = Account.sign_transaction(transaction, account.private_key_hex)
    tx_hash = signed.hash.hex()
    storage.update_attestation_request(job_id, status="submitted", tx_hash=tx_hash)
    chain.rpc("eth_sendRawTransaction", [signed.raw_transaction.hex()])
    return tx_hash


def reconcile(job_id, owner):
    row = storage.get_attestation_request(job_id, owner)
    if not row:
        return None
    if row["status"] == "confirmed":
        return row
    digest = row["report_digest"]
    if row["tx_hash"]:
        try:
            receipt = chain.rpc("eth_getTransactionReceipt", [row["tx_hash"]])
            if receipt and receipt.get("status") == "0x0":
                storage.update_attestation_request(job_id, status="failed")
            elif receipt and receipt.get("status") == "0x1":
                proof = attestation.report_status(storage.get_job(job_id, owner)["report"])
                if proof["status"] == "attested" and proof["report_sha256"] == digest:
                    storage.update_attestation_request(job_id, status="confirmed")
        except Exception:
            LOG.warning("Attestation reconciliation unavailable", exc_info=False)
    elif row["status"] in ("processing", "submitted"):
        # Processing without an EVM hash may have been interrupted while opening
        # a hybrid window; never claim success from an unconfirmed attempt.
        try:
            proof = attestation.report_status(storage.get_job(job_id, owner)["report"])
            if proof["status"] == "attested":
                storage.update_attestation_request(job_id, status="confirmed")
        except Exception:
            pass
    return storage.get_attestation_request(job_id, owner)


def process(job_id: str):
    row = storage._one(storage.attestation_requests, "job_id", job_id)
    if not row or row["status"] != "queued":
        return
    try:
        with publisher_lock() as locked:
            if not locked:
                return  # Remain queued; a later authenticated request can retry.
            if not storage.claim_attestation_request(job_id):
                return
            row = storage._one(storage.attestation_requests, "job_id", job_id)
            job = storage.get_job(job_id, row["owner"])
            if not job or job["status"] != "completed":
                raise PublishError("Audit is no longer complete")
            digest = "0x" + __import__("hashlib").sha256(job["report"].encode("utf-8")).hexdigest()
            if digest != row["report_digest"]:
                raise PublishError("Report changed after attestation request")
            contract = contract_address()
            acct = publisher()
            check_chain(contract, acct)
            proof = attestation.report_status(job["report"])
            if proof["status"] == "attested":
                storage.update_attestation_request(job_id, status="confirmed")
                return
            _open_scoped_window(acct, contract)
            # Opening a QoreChain window advances the EVM nonce; nonce is read only here.
            _send_attestation(job_id, digest, acct, contract)
            reconcile(job_id, row["owner"])
    except Exception as exc:
        LOG.warning("Attestation worker could not finish (%s)", type(exc).__name__)
        row = storage._one(storage.attestation_requests, "job_id", job_id)
        if row and not row["tx_hash"]:
            storage.update_attestation_request(job_id, status="failed")
        # With a prepared tx hash, leave it submitted until on-chain reconciliation.
