# QoreSentinel API

**From contract source to security intelligence, cryptographic visibility, and verified QoreChain activity.**

The QoreSentinel API connects the 12-specialist audit workflow, QoreScan cryptographic inventory, wallet authentication, saved reports, and Diana testnet payments. A single FastAPI service processes Solidity submissions, coordinates analyses, maintains wallet-specific records, and verifies the network events that underpin wallet access and subscriptions.

The hosted application uses **FastAPI + SQLAlchemy + PostgreSQL** (Supabase), with the service deployed on Render. SQLite remains the local/test storage backend. The audit orchestration and QoreScan executable run server-side; cloud provider credentials and billing configuration never belong in the browser.

## Request and data flow

```mermaid
flowchart TB
    UI["QoreSentinel frontend"] --> API["FastAPI<br/>app/main.py"]
    API --> AUTH["app/auth.py<br/>Wallet challenges · JWT"]
    API --> SRC["app/ingestion.py<br/>Solidity source validation"]
    API --> STORE["app/storage.py<br/>Wallet-scoped records"]
    API --> AUD["app/audit_service.py + audit/<br/>12 specialists · final judge"]
    API --> SCAN["app/pqc.py<br/>QoreScan · CBOM"]
    API --> CHAIN["app/chain.py<br/>Diana chain verification"]
    API --> BILL["app/payments.py<br/>fUSD · subscriptions"]
    API --> ASST["app/assistant.py<br/>Project / audit Q&A"]
    AUD --> LLM["Configured cloud LLM"]
    STORE --> DB[("PostgreSQL")]
    CHAIN --> NET["QoreChain Diana REST"]
    BILL --> CHAIN
    AUTH --> CHAIN
```

Wallet authentication, source ingestion, audit orchestration, scanner execution, and native payment settlement are connected through the FastAPI service. Persistent project, audit, and subscription records are managed through SQLAlchemy.

### Wallet identity and sessions

```mermaid
sequenceDiagram
    actor User
    participant Browser as QoreSentinel
    participant QoreX
    participant API as FastAPI
    participant Diana as QoreChain Diana
    User->>Browser: Connect wallet
    Browser->>QoreX: Request native qor1 address
    QoreX-->>Browser: Selected address
    Browser->>API: Request one-time challenge
    API-->>Browser: Challenge memo and expiry
    Browser->>QoreX: Request 1 uqor self-transfer
    User->>QoreX: Approve transaction
    QoreX->>Diana: Sign and broadcast
    QoreX-->>Browser: Transaction hash
    Browser->>API: Verify challenge and transaction
    API->>Diana: Inspect transfer and hybrid verification
    Diana-->>API: Confirmed on-chain evidence
    API-->>Browser: Wallet session
```


For the native `qor1` path, the backend generates a five-minute, single-use challenge tied to the wallet address. QoreX signs and broadcasts a 1 uqor self-transfer with the exact challenge memo. The API validates the message, sender, recipient, amount, chain-reported hybrid verification and transaction confirmation before consuming the challenge.

A successful verification issues a one-hour JWT session, delivered as a Bearer token and an HTTP-only, SameSite=Lax cookie (Secure by default). The same session governs project ownership, audit history, report discussions, usage and payment records. A legacy EVM message-signature challenge is also present in the API, although the primary product flow uses QoreX native authentication.

**Authorization is enforced by the API:** project IDs, audit IDs, report URLs, discussions, and billing records are resolved against the authenticated wallet. This protection also applies to direct API requests.

### Source ingestion and saved projects

Project ingestion accepts pasted Solidity, individual `.sol` files or a ZIP containing Solidity source. Archive paths and file types are validated before any data is stored. Binary files, traversal paths, symlinks and oversized uploads are rejected. Non-Solidity ZIP members are ignored.

Solidity ingestion applies a controlled source-text processing pipeline with file and archive validation. It supports up to 80 source files, checks expanded archive sizes, and processes Solidity references without running uploaded scripts or project commands.

Saved project source is associated with the authenticated wallet in the `projects` table. Temporary source submitted through the standalone PQC endpoints is not created as a project.

### 12-specialist security analysis

Audit creation requires a saved project with Solidity source, the configured Python audit pipeline and at least one configured cloud LLM provider. The reservation is performed server-side before a worker is scheduled. PostgreSQL advisory transaction locks protect each wallet's quota and pending-job reservation against concurrent requests.

The job begins at `queued`, moves to `running` and finishes as `completed` or `failed`. The Python audit modules in `audit/` coordinate twelve specialist analyses, track completed-agent counts, and pass the results to the final judge. The persisted output comprises the Markdown report and raw per-agent results. `app/findings.py` extracts report-derived finding summaries and associates them with their evidence status for the user interface.

Audit IDs persist independently of the browser. The report endpoint, job history and per-audit assistant conversations are all constrained to the wallet that owns the job.

Audit execution is coordinated by a dedicated `ThreadPoolExecutor`. Job state, agent progress, completed reports, and related conversations are recorded in PostgreSQL, allowing the workspace to retrieve them by audit ID.

### QoreScan and cryptographic readiness

`app/pqc.py` invokes QoreScan Community 0.1.0 against a temporary source directory. Its official output is a CycloneDX 1.6 CBOM of cryptographic assets, classifications, file/line occurrences, transition metadata and dependencies. QoreSentinel also exposes QoreScan's framework-mapped Markdown report when the CLI produces one.

Three authenticated routes serve the same stateless inventory:

| Source | API endpoint | Storage behavior |
| --- | --- | --- |
| Existing saved project | `POST /api/v1/projects/{project_id}/pqc/scan` | Reuses wallet-owned source; does not create a new report or history entry. |
| Pasted Solidity | `POST /api/v1/pqc/scan` | Scans request source; does not create or change a project. |
| `.sol` files or ZIP | `POST /api/v1/pqc/scan/files` | Validates and scans the upload without storing a project or scan history. |

**PQC analysis is stateless and independent of audit entitlements.** Authenticated users can scan saved or newly submitted source, receive the cryptographic inventory immediately, export the results, and rerun the analysis as needed. The endpoints maintain a distinct, history-free flow from the twelve-specialist audit.

The standard QoreScan invocation analyzes Solidity source. The `QORE_QORESCAN_NETWORK=testnet` configuration extends the scan with read-only Diana network context. Both modes return structured algorithm evidence, classifications, and transition metadata.

### QoreChain evidence and fUSD entitlements

`app/chain.py` reads the Diana native REST API to check balances, native transactions and hybrid-signature evidence. The recorded verification is derived from successful transaction status, the `PQCHybridSignature` extension and a `pqc_hybrid_verify` event. Transaction hashes, hybrid extensions, and verification events are captured as evidence from the network.

The Pro checkout is a QoreX-approved **native fUSD bank transfer on Diana**. The backend creates a time-limited payment intent with its own memo, expected denomination, exact raw amount and treasury recipient. A recorded broadcast hash supports checkout recovery while chain settlement is verified.

An entitlement is credited only after the server verifies a matching sender, recipient, amount, memo, required hybrid verification and confirmation depth, then marks the intent paid and records the transaction. Verified Pro access lasts 30 days, with renewal extending the existing expiry. QoreSentinel records the verified native fUSD payment as a Diana testnet transaction.

### Audit and assistant usage policy

| Capability | Free | Pro |
| --- | --- | --- |
| Audits | 2 per rolling 24 hours by default | 10 per rolling 24 hours by default |
| Assistant requests | 10 per rolling 24 hours by default | 50 per rolling 24 hours by default |
| PQC inventory | Unmetered by plan; authenticated | Unmetered by plan; authenticated |
| Saved audit reports | Wallet-owner access | Wallet-owner access |

**Usage is enforced centrally by FastAPI.** PostgreSQL-backed reservations account for concurrent requests, while wallet-scoped entitlements and rolling-window usage statistics are available to the workspace through the subscription API.

## API surface

All paths are relative to the FastAPI service; protected endpoints require the wallet session.

| Area | Principal routes | Result |
| --- | --- | --- |
| Health | `GET /health` | Service status. |
| Native authentication | `POST /api/v1/auth/native/challenge`, `POST /api/v1/auth/native/verify` | One-time challenge and verified wallet session. |
| Session | `GET /api/v1/auth/session`, `POST /api/v1/auth/logout` | Session restoration and cookie invalidation. |
| Projects | `GET/POST /api/v1/projects`, `GET /api/v1/projects/{id}` | Wallet-owned project index and metadata. |
| Source | `POST /api/v1/projects/{id}/source`, `POST /api/v1/projects/{id}/files` | Validated Solidity stored against a project. |
| Audits | `POST /api/v1/projects/{id}/audits`, `GET /api/v1/audits/{id}`, `GET /api/v1/audits` | Job submission, status/report retrieval and history. |
| Audit discussion | `GET/POST /api/v1/audits/{id}/messages` | Saved exchange associated with an owned completed audit. |
| PQC inventory | `POST /api/v1/projects/{id}/pqc/scan`, `POST /api/v1/pqc/scan`, `POST /api/v1/pqc/scan/files` | Stateless cryptographic inventory and export data. |
| QoreChain | `GET /api/v1/qorechain/native/balance/{address}`, `GET /api/v1/qorechain/transactions/{hash}` | Read-only public network evidence. |
| Checkout | `GET /api/v1/payments/plans/{plan}`, `POST /api/v1/payments/intents`, `POST /api/v1/payments/intents/{id}/broadcast`, `POST /api/v1/payments/intents/{id}/verify` | Server-priced payment intent and verified entitlement. |
| Subscriptions | `GET /api/v1/subscriptions/me`, `GET /api/v1/subscriptions/usage` | Plan and rolling-window usage. |
| Transactions | `GET /api/v1/transactions`, `POST /api/v1/transactions/hybrid-proof` | Wallet activity index and confirmed proof registration. |
| Assistant | `POST /api/v1/projects/{id}/assistant` | Source-grounded project analysis. |

## Persistence and service design

SQLAlchemy manages QoreSentinel's wallet-linked data model through the `projects`, `challenges`, `audit_jobs`, `audit_messages`, `subscriptions`, `payment_intents`, `payment_broadcasts`, `usage_events`, `chain_transactions` and `attestation_requests` tables.

The service brings together three evidence streams: **specialist audit reports and findings**, **QoreScan source-level cryptographic inventories**, and **QoreChain transaction and hybrid-signature records**. Each is preserved and presented in its own context, giving users a connected view of contract behavior, cryptographic dependencies, and network verification.

For the user experience and navigation model, see the [QoreSentinel frontend](../frontend/README.md) and the [project overview](../README.md).


## Automated report attestations (Diana only)

The authenticated audit results page includes **Request on-chain attestation**.
The API verifies that the requested audit belongs to the session's wallet, is
completed, and has an immutable persisted Markdown report. It creates one
idempotent request per audit, enforcing a maximum of three distinct requests
per wallet per rolling 24 hours. Request status is stored in PostgreSQL.

An isolated publish worker, running as a FastAPI background task, holds a
PostgreSQL advisory lock on the publisher account. It verifies contract
bytecode, contract publisher, chain 9800, and the account's registered PQC key.
It signs a hybrid Native transaction to open a **one-transaction, target-scoped
EVM window** for the deployed attestation contract, then signs only
`attest(bytes32)` with the SHA-256 of the persisted report.

**Render environment variables** (never commit or log secret values):

- `QORE_ATTESTATION_ENABLED=true`
- `QORE_ATTESTATION_CONTRACT=0x457962c68d6F3BeaAdAF47456402F57Fb40Fc6BF`
- `QORE_ATTESTATION_PRIVATE_KEY=` the **same disposable testnet EVM key** that deployed the contract
- `QORE_ATTESTATION_PQC_RECOVERY_CODE=` the **same QRC1 recovery code** that registered the key
- `QORE_NETWORK=testnet`

The publisher is **pinned** to `0x28ae5289681319a1b0c05b3ffbbb658d15ad33e9`;
the contract destination is also pinned. Both guards fail closed if a key or
destination is misconfigured. This is a hackathon-only signing design, not a
production-grade key-management replacement.

The API exposes `POST /api/v1/audits/{id}/attestation/request` (202) and
`GET /api/v1/audits/{id}/attestation/request` for request and recovery status,
in addition to the existing `GET /api/v1/audits/{id}/attestation` chain read.

### Live verification (28 November 2026)

A completed wallet-owned report was successfully attested **from the web UI**, using the hosted FastAPI publisher and the existing Diana contract, without manually invoking the terminal publisher. The application displayed `confirmed`, `Verified on Diana`, and the UTC publication timestamp **2026-11-28 09:06:22**.

- **Report SHA-256:** `0x5dad307f63853af2af9590c2ac3656895e1e64385603c60937264d11d653039f`
- **Attestation EVM tx:** `0x4ba2f6d45ce7afe5a0eef16c34f820d4528a29149890633860e38e79e9f2a958`
- **Contract:** `0x457962c68d6F3BeaAdAF47456402F57Fb40Fc6BF` (Diana chain `9800`)

The earlier deployment-window native hybrid transaction `B8F95A264E7B9CAA9F4B2D8CE60ECBEDAB238AF6315580CB93813FE0DCC17B42` was separately confirmed by chain-reported signature evidence. It is **not** claimed to be the distinct window-opening transaction used in the automatic UI request. The first end-to-end run validates this workflow on testnet; it does not establish high availability, production key custody, or report-finding correctness.

### Confirmation and recovery

The EVM transaction hash is stored **before** broadcast to support recovery. Signed raw transactions and hashes are `0x`-prefixed for Ethereum JSON-RPC; legacy hashes without a prefix are normalised during receipt lookups.
A confirmed receipt and matching on-chain report digest are required before
status becomes `confirmed`. If an EVM hash exists and the outcome is
uncertain, the worker will **not** blindly resend a transaction. A signed
transaction without confirmation remains `submitted` until checked again.
Native-window transactions must confirm with a chain-reported hybrid signature.

For the demo, the user can refresh the audit page to reconcile an existing
transaction or resubmit a still-queued request. Failed pre-broadcast requests without a stored transaction hash may be retried within a bounded four-attempt cap. Requests with a recorded hash are not blindly resent: establish their outcome using `eth_getTransactionReceipt`, `eth_getTransactionByHash` and the publisher nonce first. FastAPI background tasks are
not a durable job queue; unusual interruptions may need operator inspection.
Do not operate more than one independent publisher service against the same
wallet without sharing its PostgreSQL database and lock.

### Security boundaries

* Users can request publication only for their own completed audit reports;
  neither private keys nor report bodies are returned from status endpoints.
* Gas is testnet-only and capped on the signing path. The EVM window is
  restricted to the attestation contract.
* Contract publication proves publisher timestamping, **not verified AI findings**.
* The subscription treasury and native fUSD checkout are unchanged.

