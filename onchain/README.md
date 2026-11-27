# QoreSentinel on-chain audit attestations

This standalone Hardhat 3 module adds an optional, publisher-controlled, read-only-verifiable **SHA-256 audit report anchor** to QoreSentinel, with no changes to native `qor1` treasury payments. It does not prove an AI audit is correct, nor does it replace human review. The contract publishes **only** the 32-byte SHA-256 digest of the exact Markdown report bytes and a timestamp. Wallet identity, report ownership, and entitlement remain enforced by FastAPI.

**Status: code under development; no contract address or successful deployment is claimed.** Before any testnet EVM transaction, a coin-60 (Ethereum-derived) account needs a registered ML-DSA-87 key and a hybrid-signed EVM window. A standard coin-118-only `qor1` treasury account is not interchangeable with an EVM signing account.

## Official scaffolder / build provenance

The QoreChain official scaffold is `create-qorechain-dapp@0.14.0` with the Hardhat template:
```sh
npx create-qorechain-dapp@0.14.0 qs-scaffold --template hardhat --network testnet --package-manager pnpm
```
Compare generated files to this `onchain/` workspace and retain its official `window.ts` window flow. This project's Hardhat wiring follows the published Workshop 1 template; the window helper is adapted from the upstream Apache-2.0 example (see [UPSTREAM_LICENSE](UPSTREAM_LICENSE)). **Merely recording the command is not proof the official scaffolder was executed**; execute it and preserve evidence for the jury.

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
6. Copy the deployed EVM `0x...` contract address into `onchain/.env` as `QORE_ATTESTATION_CONTRACT`. Set the same **public address only** in the Render backend environment under that key. Do not send keys or recovery codes to Render.
7. Export the exact completed report Markdown (no editing of whitespace), then `npm run attest -- ./report.md`. An additional EVM transaction is consumed; reopen a properly scoped window if needed. `npm run attest -- ./report.md --read` is a read-only verification. This step is optional for subscription payments but necessary to demonstrate report anchoring.
8. `npm run verify:hybrid -- <native-window-hash>` verifies the registered hybrid proof, where the REST response must contain a `PQCHybridSignature` extension and `pqc_hybrid_verify` with status `verified`.
9. Add the verified deployment address, deployment hash, hybrid-window hash, and testnet **qor1** address to the README/project page **only once verified**. Switch [explore.qore.network](https://explore.qore.network) to Testnet when inspecting evidence.

## Public read-only API

After deployment, the existing wallet-protected endpoint `GET /api/v1/audits/{id}/attestation` returns the exact report's SHA-256 plus on-chain timestamp/verification status. If `QORE_ATTESTATION_CONTRACT` is absent, status is explicitly `not_configured`. The backend never signs deployment or attestation transactions.

## Threat model and limitations

* A digest commit is evidence a publisher recorded these report bytes at a time; it does **not** establish a vulnerability was real or source code was audited correctly.
* Only the deployment publisher can publish digests, so attestation authority is deliberately centralised.
* Public digests can link otherwise private reports when their content is already known; do not publish sensitive source or report material.
* Contract reads via `eth_call` are free and need no EVM window. Contract deployments and writes require a live window opened with a hybrid native transaction.
* Hashing uses SHA-256 of raw report UTF-8 bytes. Export without normalisation to reproduce the digest.
* Testnet contracts and QOR have no real-world financial value. No mainnet deployment is intended.
