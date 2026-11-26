# QoreSentinel Workspace

**Wallet-connected Solidity security analysis, PQC inventory, audit history and QoreChain testnet billing.**

The QoreSentinel frontend is a Next.js 15 / React 19 workspace deployed on Vercel. It presents QoreSentinel's twelve-specialist contract audits and QoreScan cryptographic inventories alongside native QoreX wallet interactions and blockchain evidence. FastAPI provides the authenticated backend for ownership, audit execution, payment confirmation, and subscription usage, while the Next.js interface coordinates the complete user experience.

**Live workspace:** https://qoresentinel.vercel.app  
**Network:** QoreChain Diana testnet (`qorechain-diana` / EVM chain ID `9800`)

## The workspace journey

### Wallet connection

The entry flow detects the QoreX extension and requests its native `qor1` account on Diana. Authentication uses a one-time backend challenge and a user-approved native 1 uqor self-transfer carrying the challenge memo. The backend confirms the transfer and hybrid-verification evidence before the workspace is authenticated.

The interface accounts for wallet-locked states, rejected requests, insufficient testnet QOR and network mismatches. Wallet access requests can invoke QoreX's unlock prompt when supported by the installed extension. A one-hour HTTP-only session cookie allows a page refresh without an additional sign-in transfer while the session remains valid.

QoreX manages wallet secrets and transaction approvals inside its extension, while QoreSentinel uses verified wallet sessions to connect the workspace to its owner's projects and reports.

### New Audit → Progress → Results

The **New Audit** view accepts pasted Solidity, multiple `.sol` files or a ZIP of Solidity sources. Files are sent to a wallet-owned project and submitted to QoreSentinel's configured audit workflow. The progress page polls the persisted job and shows the completed-agent count from the twelve-specialist backend workflow.

When the final report is available, **Audit Results** renders the Markdown report, report-derived finding summaries and agent outputs. Reports bring together findings, severity indicators, source evidence, agent outputs, and the final analysis in a single results view.

**Audit History** lists saved jobs across the authenticated wallet. Each report has a permanent `/audits/{audit-id}` URL protected by backend wallet-ownership checks. The same audit's Q&A discussion is stored and can be reopened later. Pending audit jobs can also be revisited by their URL.

### PQC Readiness

**PQC Readiness** is a separate, non-audit workflow. Its three input choices are:

| Input | Behavior |
| --- | --- |
| **Saved project** | Reuses Solidity source already owned by the connected wallet. |
| **Paste Solidity** | Runs QoreScan on the pasted source without creating a project. |
| **Upload files / ZIP** | Runs QoreScan on uploaded `.sol` sources without creating a project. |

A scan surfaces discovered cryptographic assets, file/line evidence, QoreScan classifications and a CycloneDX 1.6 CBOM. The workspace can also export QoreScan's framework-mapped Markdown readiness report. **PQC scanning runs on demand with no audit-credit cost or stored scan history.** Users can rerun source analysis whenever a contract changes and export their CBOMs and readiness reports.

The adjoining **QoreChain hybrid-signature evidence** panel is intentionally distinct from the Solidity scan. Users can approve a native testnet proof in QoreX, inspect its transaction hash, and see whether the chain reports a hybrid-verification event. This pairs cryptographic source visibility with transaction-level hybrid-signature evidence from Diana.

### Billing and Usage

**Billing & Usage** displays the active Free or Pro entitlement, a wallet-specific audit allowance and pending native fUSD payment intents. A Pro purchase uses the testnet quote returned by FastAPI, checks wallet balances and asks QoreX to approve the exact native transfer to the configured treasury.

The wallet's broadcast hash can be retained against an intent so an interrupted checkout can be resumed. The backend verifies the on-chain settlement before activating Pro. **Transaction History** distinguishes verified authentication, proof and subscription activity recorded for the wallet.

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

The security boundary separates browser presentation from backend-controlled cloud-provider credentials, session signing, treasury configuration, wallet authorization, and on-chain settlement checks. QoreX remains responsible for native signing.

## Connected security experience

QoreSentinel unifies **wallet authentication**, **twelve-specialist security analysis**, **source-based cryptographic inventory**, **chain-reported hybrid verification**, and **testnet subscription management** in one navigable workspace.

Every audit report and discussion is associated with its authenticated wallet. Protected report URLs open the saved analysis directly for the owner, and backend-issued sessions support continuity across browser refreshes.

The frontend surfaces Free and Pro usage with the backend's rolling 24-hour allowances, while PQC Readiness offers on-demand source analysis independently of audit-credit usage.

The backend implementation and persistence model are documented in [`backend/README.md`](../backend/README.md). The complete product narrative and license are in the [repository README](../README.md).
