# QoreSentinel Workspace

**Wallet-connected Solidity security analysis, PQC inventory, audit history and QoreChain testnet billing.**

The QoreSentinel frontend is a Next.js 15 / React 19 workspace deployed on Vercel. It presents two different source-analysis products—VulnHunter audits and QoreScan cryptographic inventories—alongside native QoreX wallet interactions and blockchain evidence. State that affects ownership, payment credit, job execution or usage is checked by the FastAPI backend, not trusted from the browser.

**Live workspace:** https://qoresentinel.vercel.app  
**Network:** QoreChain Diana testnet (`qorechain-diana` / EVM chain ID `9800`)

## The workspace journey

### Wallet connection

The entry flow detects the QoreX extension and requests its native `qor1` account on Diana. Authentication uses a one-time backend challenge and a user-approved native 1 uqor self-transfer carrying the challenge memo. The backend confirms the transfer and hybrid-verification evidence before the workspace is authenticated.

The interface accounts for wallet-locked states, rejected requests, insufficient testnet QOR and network mismatches. Wallet access requests can invoke QoreX's unlock prompt when supported by the installed extension. A one-hour HTTP-only session cookie allows a page refresh without an additional sign-in transfer while the session remains valid.

Wallet secrets never enter QoreSentinel. Transaction approvals happen inside QoreX.

### New Audit → Progress → Results

The **New Audit** view accepts pasted Solidity, multiple `.sol` files or a ZIP of Solidity sources. Files are sent to a wallet-owned project and submitted to the configured VulnHunter audit engine. The progress page polls the persisted job and shows the completed-agent count from the twelve-specialist backend workflow.

When the final report is available, **Audit Results** renders the Markdown report, report-derived finding summaries and agent outputs. Generated severity labels are presented as unverified rather than as independently validated exploits.

**Audit History** lists saved jobs across the authenticated wallet. Each report has a permanent `/audits/{audit-id}` URL, with authorization enforced by the API; a copied link does not make the report public. The same audit's Q&A discussion is stored and can be reopened later. Pending audit jobs can also be revisited by their URL.

### PQC Readiness

**PQC Readiness** is a separate, non-audit workflow. Its three input choices are:

| Input | Behavior |
| --- | --- |
| **Saved project** | Reuses Solidity source already owned by the connected wallet. |
| **Paste Solidity** | Runs QoreScan on the pasted source without creating a project. |
| **Upload files / ZIP** | Runs QoreScan on uploaded `.sol` sources without creating a project. |

A scan surfaces discovered cryptographic assets, file/line evidence, QoreScan classifications and a CycloneDX 1.6 CBOM. The workspace can also export QoreScan's framework-mapped Markdown readiness report. **No PQC scan-history entries are created, and no paid audit entitlement is consumed.** Scans may be rerun against changed source. Results are not retained as a separate stored report after navigation or sign-out.

The adjoining **QoreChain hybrid-signature evidence** panel is intentionally distinct from the Solidity scan. Users can approve a native testnet proof in QoreX, inspect its transaction hash, and see whether the chain reports a hybrid-verification event. The proof concerns a transaction on Diana, not the quantum safety of the uploaded Solidity.

### Billing and Usage

**Billing & Usage** displays the active Free or Pro entitlement, a wallet-specific audit allowance and pending native fUSD payment intents. A Pro purchase uses the testnet quote returned by FastAPI, checks wallet balances and asks QoreX to approve the exact native transfer to the configured treasury.

The wallet's broadcast hash can be retained against an intent so an interrupted checkout can be resumed. The UI does not activate Pro merely because a hash exists: backend confirmation and settlement are required. **Transaction History** distinguishes verified authentication, proof and subscription activity recorded for the wallet.

## Navigation

| Route | Screen |
| --- | --- |
| `/overview` | Workspace status and recent activity. |
| `/new-audit` | Solidity project submission and audit launch. |
| `/audit-progress` | Agent-completion progress for an active job. |
| `/audit-results` | The currently selected report and its discussion. |
| `/audit-history` | Wallet-scoped saved audits and report navigation. |
| `/audits/{audit-id}` | Permanent, owner-restricted audit report or live job view. |
| `/ai-assistant` | Project-aware security questions using saved source. |
| `/pqc-readiness` | Stateless QoreScan, CBOM exports and hybrid chain proof. |
| `/transaction-history` | Verified wallet-linked QoreChain activity. |
| `/billing` | fUSD testnet checkout, subscriptions and usage. |
| `/settings` | Wallet identity, session status and service information. |

The sidebar uses browser-history-aware routes; back/forward navigation and direct audit URLs are supported.

## Frontend implementation

| Area | Implementation |
| --- | --- |
| **Application** | Next.js 15 App Router, React 19, TypeScript and Lucide icons. |
| **Workspace screen** | `src/app/page.tsx` contains session state, source submission, audit polling, QoreScan display, payment recovery and wallet interactions. |
| **Navigation** | `src/lib/routes.ts` maps sections to URLs and parses audit identifiers. `src/app/[section]/` and `src/app/audits/[auditId]/` provide route entry points. |
| **API client** | `src/lib/api.ts` calls FastAPI through the `/backend-proxy` rewrite, manages the in-memory Bearer token and works with the HTTP-only session cookie. |
| **QoreX integration** | `src/lib/wallet.ts` requests native wallet access, constructs MsgSend transfers, classifies wallet errors and delegates signing/broadcast to QoreX. |
| **Design** | `src/app/globals.css` defines the workspace, report presentation, wallet onboarding and scanner views. |
| **Deployment** | Vercel hosts the frontend. `next.config.ts` forwards `/backend-proxy/:path*` to the configured `BACKEND_URL`, the Render FastAPI service in the hosted environment. |

The browser does not directly hold the cloud LLM credentials, the signing key used for application sessions, or the testnet treasury's private keys. QoreX manages wallet signing; the backend performs authentication and settlement verification.

## What the interface reports—and what it does not

- A **completed VulnHunter audit** means the configured specialist-and-judge workflow returned a report, not that every finding has been exploited, reproduced or independently verified.
- A **QoreScan inventory** shows detected source-level cryptographic references and transition classifications. It is not a certification that the contract, application or connected chain is quantum-safe.
- A **verified hybrid proof** means the chain reported an appropriate transaction and verification event. It is not a local cryptographic re-verification by the web application.
- **Free versus Pro allowances** are visible in the UI but are enforced by FastAPI. The default rolling 24-hour audit allowance is 2 for Free and 10 for Pro; actual limits are server-configurable.
- **An audit permalink is private**, even if someone else knows the URL. A matching authenticated wallet is required to retrieve its contents.

The backend implementation and persistence model are documented in [`backend/README.md`](../backend/README.md). The complete product narrative and license are in the [repository README](../README.md).
