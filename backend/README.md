# QoreSentinel API

**FastAPI service for wallet-owned Solidity projects, VulnHunter audit jobs, QoreScan inventories and Diana testnet settlement.**

The backend is the trust boundary of QoreSentinel. The Next.js client can initiate an audit or submit a payment hash, but the API determines who owns the source, whether an audit is permitted, what the chain actually confirmed, and which records the requesting wallet may read.

The hosted application uses **FastAPI + SQLAlchemy + PostgreSQL** (Supabase), with the service deployed on Render. SQLite remains the local/test storage backend. The audit orchestration and QoreScan executable run server-side; cloud provider credentials and billing configuration never belong in the browser.

## Request and data flow

```text
QoreX wallet / Next.js workspace
    |
    | Browser request, authenticated session
    v
FastAPI (app/main.py)
    |-- app/auth.py       wallet challenges, native transaction verification, JWT sessions
    |-- app/ingestion.py  .sol / ZIP validation and source extraction
    |-- app/storage.py    projects, audit jobs, exchanges, transactions, usage, subscriptions
    |-- app/audit_service.py -> audit/ -> specialist agents and final judge
    |-- app/pqc.py        QoreScan subprocess / temporary Solidity source tree
    |-- app/chain.py      Diana native REST and transaction evidence
    |-- app/payments.py   fUSD intent, settlement checks, expiry and entitlement
    |-- app/assistant.py  answers grounded in the wallet's source and saved audit
    v
PostgreSQL / QoreChain Diana / configured cloud LLM provider
```

### Wallet identity and sessions

For the native `qor1` path, the backend generates a five-minute, single-use challenge tied to the wallet address. QoreX signs and broadcasts a 1 uqor self-transfer with the exact challenge memo. The API validates the message, sender, recipient, amount, chain-reported hybrid verification and transaction confirmation before consuming the challenge.

A successful verification issues a one-hour JWT session, delivered as a Bearer token and an HTTP-only, SameSite=Lax cookie (Secure by default). The same session governs project ownership, audit history, report discussions, usage and payment records. A legacy EVM message-signature challenge is also present in the API, although the primary product flow uses QoreX native authentication.

The API remains publicly reachable over HTTP as an addressable service. **Protected resources are authorized server-side**: holding another user's project ID, audit ID or report URL does not confer access.

### Source ingestion and saved projects

Project ingestion accepts pasted Solidity, individual `.sol` files or a ZIP containing Solidity source. Archive paths and file types are validated before any data is stored. Binary files, traversal paths, symlinks and oversized uploads are rejected. Non-Solidity ZIP members are ignored.

The current limits are 2 MB per Solidity file, 8 MB total uncompressed source, up to 80 files and a 4 MB compressed ZIP. Source is treated as text: QoreSentinel does **not** execute uploaded build scripts, install their packages or compile their contracts. Imports may be unresolved.

Saved project source is associated with the authenticated wallet in the `projects` table. Temporary source submitted through the standalone PQC endpoints is not created as a project.

### The twelve-specialist audit

Audit creation requires a saved project with Solidity source, the enabled VulnHunter bridge and at least one configured cloud LLM provider. The reservation is performed server-side before a worker is scheduled. PostgreSQL advisory transaction locks protect each wallet's quota and pending-job reservation against concurrent requests.

The job begins at `queued`, moves to `running` and finishes as `completed` or `failed`. The `audit/` engine runs twelve specialist analyses, reports completed-agent counts and hands results to the final judge. The persisted output comprises the Markdown report and raw per-agent results. `app/findings.py` extracts report-derived finding summaries, which remain labeled **unverified**.

Audit IDs persist independently of the browser. The report endpoint, job history and per-audit assistant conversations are all constrained to the wallet that owns the job.

The worker is a **single in-process ThreadPoolExecutor**, not a restart-safe distributed queue. Running and queued job records survive in PostgreSQL, but their execution cannot automatically resume after a service restart.

### QoreScan and cryptographic readiness

`app/pqc.py` invokes QoreScan Community 0.1.0 against a temporary source directory. Its official output is a CycloneDX 1.6 CBOM of cryptographic assets, classifications, file/line occurrences, transition metadata and dependencies. QoreSentinel also exposes QoreScan's framework-mapped Markdown report when the CLI produces one.

Three authenticated routes serve the same stateless inventory:

| Source | API endpoint | Storage behavior |
| --- | --- | --- |
| Existing saved project | `POST /api/v1/projects/{project_id}/pqc/scan` | Reuses wallet-owned source; does not create a new report or history entry. |
| Pasted Solidity | `POST /api/v1/pqc/scan` | Scans request source; does not create or change a project. |
| `.sol` files or ZIP | `POST /api/v1/pqc/scan/files` | Validates and scans the upload without storing a project or scan history. |

PQC scans do **not** reserve an AI-audit job, consume an audit entitlement or create a PQC scan-history record. The API does require an authenticated wallet session. When the QoreScan CLI is unavailable, the implementation returns an explicitly labeled **source-heuristic** inventory instead of claiming that the scanner ran.

`QORE_QORESCAN_NETWORK=testnet` includes read-only Diana network information in the QoreScan invocation; the default path analyzes Solidity sources alone. An inventory is evidence of observed cryptographic references, **not** a smart-contract vulnerability audit, quantum-safety certification or proof of compliance.

### QoreChain evidence and fUSD entitlements

`app/chain.py` reads the Diana native REST API to check balances, native transactions and hybrid-signature evidence. The recorded verification is derived from successful transaction status, the `PQCHybridSignature` extension and a `pqc_hybrid_verify` event. QoreSentinel does not independently reconstruct and validate ML-DSA signatures.

The Pro checkout is a QoreX-approved **native fUSD bank transfer on Diana**. The backend creates a time-limited payment intent with its own memo, expected denomination, exact raw amount and treasury recipient. Recording a broadcast transaction hash is not the same as confirming payment.

An entitlement is credited only after the server verifies a matching sender, recipient, amount, memo, required hybrid verification and confirmation depth, then marks the intent paid and records the transaction. Verified Pro access lasts 30 days, with renewal extending the existing expiry. Testnet fUSD and QOR are not live production payments.

### Audit and assistant usage policy

| Capability | Free | Pro |
| --- | --- | --- |
| Audits | 2 per rolling 24 hours by default | 10 per rolling 24 hours by default |
| Assistant requests | 10 per rolling 24 hours by default | 50 per rolling 24 hours by default |
| PQC inventory | Unmetered by plan; authenticated | Unmetered by plan; authenticated |
| Saved audit reports | Wallet-owner access | Wallet-owner access |

Limits are controlled by server configuration, not by UI affordances. `QORE_REQUIRE_ACTIVE_PLAN` can disable Free auditing entirely. API requests that exceed the server's quota return an error even if submitted without the frontend.

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

## Persistence and implementation boundaries

SQLAlchemy defines the `projects`, `challenges`, `audit_jobs`, `audit_messages`, `subscriptions`, `payment_intents`, `payment_broadcasts`, `usage_events` and `chain_transactions` records. Metadata initialization creates absent tables but does not perform versioned migrations to alter an existing PostgreSQL schema.

The current implementation deliberately separates **scanner observations**, **model-generated audit findings**, and **chain-reported verification**. None of those outputs alone guarantees safety. The competition build also does not have a restart-safe audit queue or broad IP-level request-rate limiting.

For the product experience and navigation model, see the [QoreSentinel frontend](../frontend/README.md) and the [project overview](../README.md).
