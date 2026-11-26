# QoreSentinel

**Smart-contract security analysis and post-quantum cryptographic inventory on QoreChain.**

QoreSentinel brings two distinct security workflows into one wallet-connected workspace: a twelve-specialist Solidity audit led by the VulnHunter engine, and a cryptographic inventory produced by the QoreScan engine. The former examines contract behavior and reports potential vulnerabilities; the latter identifies cryptographic dependencies, classifies quantum-migration exposure, and produces a machine-readable Cryptographic Bill of Materials (CBOM).

QoreSentinel also connects those source-level findings with **chain-reported hybrid-signature evidence on the QoreChain Diana testnet**. It is a working demonstration of how contract review, cryptographic visibility, and verifiable network activity can coexist without representing an inventory scan as a security certification.

**Application:** https://qoresentinel.vercel.app  
**Network:** QoreChain Diana testnet (`qorechain-diana`, EVM chain ID `9800`)

## The product

| Workspace capability | What happens | What the user receives |
| --- | --- | --- |
| **Smart-contract audit** | Saved Solidity source runs through twelve VulnHunter specialist agents and a final report synthesis. | Job progress, a Markdown security report, agent output, and report-derived finding summaries. |
| **PQC Readiness** | QoreScan inventories cryptographic references from a saved project, pasted Solidity, or uploaded source files/ZIP. | Algorithm classifications, source-line evidence, a CycloneDX 1.6 CBOM, and a readiness report. |
| **Hybrid-signature proof** | QoreX authorizes a small Diana-native self-transfer; QoreSentinel inspects the chain response for the hybrid-signature extension and successful verification event. | A transaction hash and chain-reported hybrid-verification evidence. |
| **Audit history** | Completed reports, running jobs, and per-audit discussions are retained against the authenticated wallet. | Private audit URLs and the ability to reopen a report without running it again. |
| **Billing and usage** | The API applies wallet-scoped Free and Pro limits. Native fUSD payments become subscriptions only after the transaction is verified on-chain. | Current plan, remaining audit allowance, pending checkout state, and verified transaction activity. |

## How the workflows connect

### 1. From Solidity source to an audit report

A QoreX wallet establishes the workspace identity. A Solidity project is created from pasted source, individual `.sol` files, or a ZIP containing Solidity contracts. The submitted files become part of that wallet's saved project.

Starting an audit creates a persistent job ID. The API reserves one of the wallet's available audit slots, queues execution, and reports progress as the twelve specialist analyses complete. The final synthesis is saved as Markdown alongside the individual agent results. The results page extracts finding summaries from the generated report, with those summaries explicitly marked **unverified**.

A report remains accessible through its private `/audits/{audit-id}` URL. The same wallet can return to the report and its saved discussion thread without purchasing another run. Knowing the URL is not sufficient to read another wallet's report.

### 2. From cryptographic source references to a CBOM

PQC Readiness is a separate workflow. It accepts a previously saved project, newly pasted Solidity, or uploaded Solidity files/ZIPs. QoreScan examines the source and inventories algorithms such as ECDSA, Keccak-256, and SHA-256, including the file and line associated with each detection.

The output includes a **CycloneDX 1.6 CBOM**, QoreScan classification and transition metadata, and a downloadable framework-mapped Markdown report when available. The dashboard distinguishes quantum-vulnerable public-key cryptography from hashes and other cryptographic primitives.

PQC scans **do not create projects, audit jobs, scan history, or paid audit charges**. Pasted and uploaded PQC-only source is processed for the request rather than stored as a project. A user may rerun a scan whenever the source changes. The user retains a result by exporting the CBOM or report.

### 3. From QoreX approval to chain evidence

QoreSentinel uses QoreX's native `qor1` wallet interface on Diana. Native authentication begins with a short-lived challenge and a wallet-approved 1 uqor self-transfer containing the challenge memo. The backend checks the sender, recipient, amount, memo, confirmation, and chain-reported hybrid verification before issuing a one-hour session.

The separate hybrid-proof action uses another wallet-approved 1 uqor self-transfer and checks its transaction record for the PQC hybrid extension and verification event. It is **evidence reported by QoreChain**, not an independent local ML-DSA signature verification by QoreSentinel.

An authenticated browser session can be restored after refresh through a secure, HTTP-only cookie. Locked-wallet and network-mismatch states are surfaced in the interface; compatible QoreX versions may display their own unlock prompt when wallet access is requested.

### 4. From a native fUSD transfer to Pro access

The billing screen retrieves the server-defined testnet fUSD amount and treasury destination before requesting a QoreX-approved transfer. The resulting transaction hash can be saved against a pending intent, including after a page refresh. **A broadcast hash alone never activates Pro.**

Only an on-chain transfer that matches the intended sender, treasury, denomination, exact amount, memo, hybrid-verification requirement, and confirmation depth can credit the subscription. A verified payment extends Pro access by 30 days. These are **testnet assets**, not a production payment system.

## Architecture

```text
Next.js 15 / React 19 interface (Vercel)
    |
    | /backend-proxy/* (same-origin rewrite)
    v
FastAPI service (Render)
    |-- QoreX wallet challenge and session verification
    |-- Solidity ingestion, source validation, project ownership
    |-- Audit job tracking -> VulnHunter 12-agent workflow -> cloud LLM provider
    |-- QoreScan CLI -> cryptographic inventory / CycloneDX CBOM
    |-- Native QOR and fUSD verification -> QoreChain Diana REST API
    |-- Wallet-scoped billing, usage, audit history and discussions
    |
    v
PostgreSQL (Supabase in the hosted environment)
```

The frontend owns presentation, routing, file selection, transaction approval, and report exports. **Authentication, ownership, usage limits, payment confirmation, and audit persistence are enforced in FastAPI.** The wallet extension signs transactions; QoreSentinel does not handle recovery phrases or private keys.

| Repository area | Role |
| --- | --- |
| [`frontend/`](frontend/README.md) | Workspace routes, QoreX interaction, QoreScan presentation, audit progress and billing UI. |
| [`backend/`](backend/README.md) | API, persistent state, VulnHunter bridge, QoreScan execution, QoreChain evidence and payment verification. |
| `backend/audit/` | Specialist-agent orchestration, report synthesis, prompts and cloud-provider adapters. |
| `backend/tests/` | Authentication, billing, job history, direct API authorization, PQC, wallet session and scanner regression tests. |

## Product boundaries

- **Audits and PQC inventories answer different questions.** A detected algorithm is evidence of a source reference, not proof that the entire contract is quantum-safe or insecure. QoreScan does not certify compliance.
- **The audit findings are generated claims.** Report-derived severities and evidence require independent review before security decisions.
- **Free and Pro are enforced at the API boundary.** The default rolling 24-hour audit allowances are 2 for Free and 10 for Pro, with configurable limits; project-level assistant requests have separate usage limits. PQC scans have no paid-audit quota.
- **Source access is wallet-scoped.** Direct access to API endpoints is possible, but project records, private reports, audit discussions, and payment records require the owning wallet's authenticated session.
- **Audit processing is an MVP worker.** Jobs are stored durably, but execution uses an in-process worker rather than a restart-safe distributed queue. A service restart during an active job may require operational intervention.
- **Wallet and payment interactions are on Diana testnet.** Hybrid verification refers to evidence returned by chain endpoints; it does not replace cryptographic verification or a production settlement audit.

## License

QoreSentinel's original project code is offered under the [MIT License](LICENSE). External dependencies, including QoreScan and the QoreX integration packages, retain their own licenses and attribution requirements.
