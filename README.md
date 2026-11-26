# QoreSentinel

**Smart-contract auditing meets post-quantum readiness.**

Every smart contract raises two security questions: *What can go wrong in its logic?* And *which cryptographic systems does it depend on?* QoreSentinel brings both answers into one wallet-connected workspace on QoreChain.

With **12 specialist security agents and a final judge**, QoreSentinel analyzes Solidity contracts and delivers detailed findings with source evidence. Alongside the audit, **QoreScan-powered PQC Readiness** identifies cryptographic dependencies, highlights quantum-vulnerable algorithms, and generates a CycloneDX 1.6 Cryptographic Bill of Materials (CBOM). **QoreX and QoreChain Diana** complete the experience with wallet-based access, hybrid-signature transaction evidence, and testnet fUSD subscriptions.

From source submission to security reporting, cryptographic inventory, and on-chain verification, QoreSentinel gives builders a connected view of their contracts.

**Application:** https://qoresentinel.vercel.app  
**Network:** QoreChain Diana testnet (`qorechain-diana`, EVM chain ID `9800`)

## What QoreSentinel delivers

| Workspace capability | What happens | What the user receives |
| --- | --- | --- |
| **Smart-contract audit** | Twelve specialist security agents examine Solidity source and a final judge consolidates the findings. | Job progress, a Markdown security report, agent output, and report-derived finding summaries. |
| **PQC Readiness** | QoreScan inventories cryptographic references from a saved project, pasted Solidity, or uploaded source files/ZIP. | Algorithm classifications, source-line evidence, a CycloneDX 1.6 CBOM, and a readiness report. |
| **Hybrid-signature proof** | QoreX authorizes a small Diana-native self-transfer; QoreSentinel inspects the chain response for the hybrid-signature extension and successful verification event. | A transaction hash and chain-reported hybrid-verification evidence. |
| **Audit history** | Completed reports, running jobs, and per-audit discussions are retained against the authenticated wallet. | Private audit URLs and the ability to reopen a report without running it again. |
| **Billing and usage** | The API applies wallet-scoped Free and Pro limits. Native fUSD payments become subscriptions only after the transaction is verified on-chain. | Current plan, remaining audit allowance, pending checkout state, and verified transaction activity. |

## The experience

### Audit a smart contract

A QoreX wallet establishes the workspace identity. A Solidity project is created from pasted source, individual `.sol` files, or a ZIP containing Solidity contracts. The submitted files become part of that wallet's saved project.

Starting an audit creates a persistent job ID. The API reserves one of the wallet's available audit slots, queues execution, and reports progress as the twelve specialist analyses complete. The final synthesis is saved as Markdown alongside the individual agent results. The results page presents report-derived findings and their evidence alongside the complete security analysis.

A report remains accessible through its private `/audits/{audit-id}` URL. The same wallet can reopen saved reports and discussion threads at any time. Server-side ownership checks keep audit history and report access private to the authenticated wallet.

### Map post-quantum exposure

PQC Readiness is a separate workflow. It accepts a previously saved project, newly pasted Solidity, or uploaded Solidity files/ZIPs. QoreScan examines the source and inventories algorithms such as ECDSA, Keccak-256, and SHA-256, including the file and line associated with each detection.

The output includes a **CycloneDX 1.6 CBOM**, QoreScan classification and transition metadata, and a downloadable framework-mapped Markdown report when available. The dashboard distinguishes quantum-vulnerable public-key cryptography from hashes and other cryptographic primitives.

**Unlimited, on-demand PQC analysis is independent of paid auditing.** Saved projects can be rescanned, while pasted and uploaded sources run as temporary, history-free scans. Each run produces downloadable CBOM and readiness-report outputs for further analysis and sharing.

### Verify hybrid-signature activity

QoreSentinel uses QoreX's native `qor1` wallet interface on Diana. Native authentication begins with a short-lived challenge and a wallet-approved 1 uqor self-transfer containing the challenge memo. The backend checks the sender, recipient, amount, memo, confirmation, and chain-reported hybrid verification before issuing a one-hour session.

The separate hybrid-proof action uses another wallet-approved 1 uqor self-transfer and inspects the transaction record for the PQC hybrid extension and verification event. The dashboard presents the resulting **QoreChain-reported hybrid-signature evidence**, linked to the transaction hash.

An authenticated browser session can be restored after refresh through a secure, HTTP-only cookie. Locked-wallet and network-mismatch states are surfaced in the interface; compatible QoreX versions may display their own unlock prompt when wallet access is requested.

### Access Free and Pro plans

The billing screen retrieves the server-defined testnet fUSD amount and treasury destination before requesting a QoreX-approved transfer. The resulting transaction hash is associated with a pending payment intent, enabling seamless checkout recovery after a page refresh.

On-chain settlement verification matches the sender, treasury, denomination, exact amount, memo, hybrid-signature verification, and confirmation depth. Once verified, the payment activates 30 days of Pro access on the Diana testnet.

## Architecture

```text
Next.js 15 / React 19 interface (Vercel)
    |
    | /backend-proxy/* (same-origin rewrite)
    v
FastAPI service (Render)
    |-- QoreX wallet challenge and session verification
    |-- Solidity ingestion, source validation, project ownership
    |-- Audit job tracking -> 12-specialist audit + final judge -> cloud LLM provider
    |-- QoreScan CLI -> cryptographic inventory / CycloneDX CBOM
    |-- Native QOR and fUSD verification -> QoreChain Diana REST API
    |-- Wallet-scoped billing, usage, audit history and discussions
    |
    v
PostgreSQL (Supabase in the hosted environment)
```

The frontend owns presentation, routing, file selection, transaction approval, and report exports. **Authentication, ownership, usage limits, payment confirmation, and audit persistence are enforced in FastAPI.** QoreX handles transaction signing and wallet secrets within the extension, while QoreSentinel verifies authenticated sessions and on-chain outcomes.

| Repository area | Role |
| --- | --- |
| [`frontend/`](frontend/README.md) | Workspace routes, QoreX interaction, QoreScan presentation, audit progress and billing UI. |
| [`backend/`](backend/README.md) | API, persistent state, twelve-specialist audit orchestration, QoreScan execution, QoreChain evidence and payment verification. |
| `backend/audit/` | Specialist-agent orchestration, report synthesis, prompts and cloud-provider adapters. |
| `backend/tests/` | Authentication, billing, job history, direct API authorization, PQC, wallet session and scanner regression tests. |

## Security and access

QoreSentinel keeps contract security workflows tied to a verified wallet identity. Its API performs source validation, project ownership checks, audit quota reservation, report authorization, and on-chain payment verification before committing protected operations.

**Free and Pro audit allowances are enforced server-side:** the default rolling 24-hour limits are two audits for Free and ten for Pro, with separate security-assistant allowances. PQC inventory scanning remains available to authenticated users independently of paid audit usage.

Saved audit history, detailed results, report conversations, subscription activity, and transaction history are organized by wallet. QoreX handles native transaction approvals, and FastAPI validates the corresponding QoreChain Diana evidence.

## License

QoreSentinel is released under the [MIT License](LICENSE).
