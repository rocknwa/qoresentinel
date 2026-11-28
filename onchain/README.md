# QoreSentinel on-chain audit attestations

This standalone Hardhat 3 module adds an optional, publisher-controlled, read-only-verifiable **SHA-256 audit report anchor** to QoreSentinel, with no changes to native `qor1` treasury payments. It does not prove an AI audit is correct, nor does it replace human review. The contract publishes **only** the 32-byte SHA-256 digest of the exact Markdown report bytes and a timestamp. Wallet identity, report ownership, and entitlement remain enforced by FastAPI.

**Status: Deployed and exercised on QoreChain Diana testnet.** The Solidity publisher contract is `0x457962c68d6F3BeaAdAF47456402F57Fb40Fc6BF` (EVM chain ID `9800`); a live UI-requested report attestation was confirmed on **28 November 2026**. Before any testnet EVM transaction, a coin-60 (Ethereum-derived) account needs a registered ML-DSA-87 key and a hybrid-signed EVM window. A standard coin-118-only `qor1` treasury account is not interchangeable with an EVM signing account.

## Official scaffolder / build provenance

The QoreChain official scaffold is `create-qorechain-dapp@0.14.0` with the Hardhat template:
```sh
npx create-qorechain-dapp@0.14.0 qs-scaffold --template hardhat --network testnet --package-manager pnpm
```
Compare generated files to this `onchain/` workspace and retain its official `window.ts` window flow. This project's Hardhat wiring follows the published Workshop 1 template; the window helper is adapted from the upstream Apache-2.0 example (see [UPSTREAM_LICENSE](UPSTREAM_LICENSE)). **Merely recording the command is not proof the official scaffolder was executed**. Successful deployment alone does not establish this hackathon requirement; execute the scaffold command and preserve the generated project, CLI output or other reproducible evidence for the jury.

## Local verification

Requires Node 22.13+, npm and internet to install dependencies and download the Solidity compiler:
```sh
cd onchain
npm install
npm run test
npm run build
npm run typecheck
```

## Diana deployment (operator action; uses a fresh disposable testnet-only key)

1. `cp .env.example .env` and set a **new testnet-only** EVM/coin-60 `PRIVATE_KEY`. Never commit private keys, PQC recovery codes, or mnemonics, and don't share them in chat.
2. Generate a PQC code: `npm run window -- recovery-code`. Store it as `QORE_PQC_RECOVERY_CODE`; keep it and the private key separate. Or use a purpose-built `QORE_MNEMONIC` for the same coin-60 account.
3. `npm run window -- status`. Fund the returned **qor1** address from the [Diana faucet](https://dashboard.qorechain.io/faucet).
4. `npm run window -- register` once, then `npm run window -- open` to send the required *hybrid-signed* message. Preserve this **native** hash and register the associated qor1 address on the hackathon project page.
5. After the window is live, `npm run deploy:testnet` (chain 9800). A scoped window with `allowed_targets` cannot admit contract creation; deploy using a window that admits creation and use a scoped window for later calls.
6. Copy the deployed EVM `0x...` contract address into `onchain/.env` as `QORE_ATTESTATION_CONTRACT`. Set the same public address in Render for contract reads. For **automatic** publishing, the Render backend additionally requires a *dedicated disposable testnet-only* publisher private key and PQC recovery code in Render's secret environment configuration. Never commit or expose these secrets in the frontend, logs or screenshots; they enable signing and are not risk-free even on testnet.
7. **Manual operator path (optional):** Export the exact completed report Markdown (preserve its bytes), then run `npm run attest -- ./report.md` with a live EVM window. `npm run attest -- ./report.md --read` verifies the digest without broadcasting. **Automatic product path:** Log in with QoreX, open a completed, wallet-owned audit and click **Request on-chain attestation**; the protected Render worker opens a scoped hybrid window and publishes for the user. Neither path changes native fUSD subscriptions.
8. `npm run verify:hybrid -- <native-window-hash>` verifies the registered hybrid proof, where the REST response must contain a `PQCHybridSignature` extension and `pqc_hybrid_verify` with status `verified`.
9. Add only independently established deployment and publication evidence to the hackathon project page; do not infer an EVM deployment transaction hash from the deployed contract address. Switch [explore.qore.network](https://explore.qore.network) to Testnet when inspecting evidence.

## Automated publishing and verification

The wallet-protected `GET /api/v1/audits/{id}/attestation` returns the exact saved report SHA-256 and Diana contract status (`not_configured`, `not_attested` or `attested`). The authenticated user can request publication with `POST /api/v1/audits/{id}/attestation/request` and check job status using `GET /api/v1/audits/{id}/attestation/request`.

The Render backend signs **only** the attestation transaction using the contract's authorized publisher account (`0x28ae5289681319a1b0c05b3ffbbb658d15ad33e9`) and a hybrid-authorized, target-scoped EVM window. It never deploys a new contract per report. The transaction hash is persisted before broadcast for recovery, and the UI displays `confirmed` only after receipt and matching on-chain digest verification. A wallet can request at most three distinct attestations per rolling 24 hours; retries are bounded and ambiguous transactions are not automatically resent.

**Required Render variables:** `QORE_NETWORK=testnet`, `QORE_ATTESTATION_ENABLED=true`, `QORE_ATTESTATION_CONTRACT=0x457962c68d6F3BeaAdAF47456402F57Fb40Fc6BF`, plus secret `QORE_ATTESTATION_PRIVATE_KEY` and `QORE_ATTESTATION_PQC_RECOVERY_CODE` for the **same** registered testnet publisher. No secret values belong in the repository. See [backend documentation](../backend/README.md#automated-report-attestations-diana-only) for recovery and limitations.

## Recorded Diana testnet evidence

| Item | Value |
| --- | --- |
| Contract | `0x457962c68d6F3BeaAdAF47456402F57Fb40Fc6BF` |
| Authorized EVM publisher | `0x28ae5289681319a1b0c05b3ffbbb658d15ad33e9` |
| Live user-initiated attestation tx | `0x4ba2f6d45ce7afe5a0eef16c34f820d4528a29149890633860e38e79e9f2a958` |
| Exact report SHA-256 | `0x5dad307f63853af2af9590c2ac3656895e1e64385603c60937264d11d653039f` |
| Contract-recorded UTC timestamp | **2026-11-28 09:06:22** |
| Previously verified *deployment-era* hybrid window tx | `B8F95A264E7B9CAA9F4B2D8CE60ECBEDAB238AF6315580CB93813FE0DCC17B42` |

The successful UI run showed `confirmed` and `Verified on Diana`; the on-chain timestamp and hashes above are from that observed testnet run. The deployment-era hybrid-window hash is **not** the reported window hash for the automated transaction. No deployment EVM transaction hash is asserted here because it was not captured in this documentation.


## Threat model and limitations

* A digest commit is evidence a publisher recorded these report bytes at a time; it does **not** establish a vulnerability was real or source code was audited correctly.
* Only the deployment publisher can publish digests, so attestation authority is deliberately centralised.
* Public digests can link otherwise private reports when their content is already known; do not publish sensitive source or report material.
* Contract reads via `eth_call` are free and need no EVM window. Contract deployments and writes require a live window opened with a hybrid native transaction.
* Hashing uses SHA-256 of raw report UTF-8 bytes. Export without normalisation to reproduce the digest.
* Testnet contracts and QOR have no real-world financial value. No mainnet deployment is intended.
