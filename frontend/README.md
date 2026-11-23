# QoreSentinel Frontend — Google Stitch implementation starter

A responsive Next.js / React / TypeScript frontend based on the eight Google Stitch screen exports and QoreSentinel's design system.  
## Run locally

Requires Node.js 20+ and the Phase 1 FastAPI backend.

```bash
cd frontend
npm install
cp .env.example .env.local # Windows CMD: copy .env.example .env.local
npm run dev
```

Open http://localhost:3000. Start the FastAPI backend on http://127.0.0.1:8000. If the backend is elsewhere, change `BACKEND_URL` in `.env.local` and restart the Next.js server.

`next.config.ts` proxies `/backend-proxy/*` to FastAPI to avoid local browser CORS issues. Never put an LLM key into any NEXT_PUBLIC_* setting.

## Backend functionality wired

- `GET /health` — live connectivity indicator
- `POST /api/v1/projects` — create a project
- `POST /api/v1/projects/{id}/source` — submit pasted Solidity
- `POST /api/v1/projects/{id}/files` — upload `.sol` files or a ZIP
- `POST /api/v1/projects/{id}/audits` — run the configured audit engine

The backend currently executes audits **synchronously**, so the progress screen is a pending state, not a real per-agent telemetry feed. Audit results show backend Markdown as delivered. The backend's `findings` array is empty until structured parsing is implemented; this frontend does not invent issues or scores.

## Not yet implemented

- Persistent user authentication, full projects list, and stored audit history
- Per-agent progress streaming and background audit jobs
- Parsed structured findings and source line drilldown
- Context-aware assistant API
- QoreScan / CBOM / QoreChain hybrid-signature integrations
- fUSD testnet payments and entitlements

These pages show honest feature-pending states and can be connected as APIs are delivered.

## Next engineering milestones

1. Implement async audit jobs, status endpoint, and structured findings schema in backend.
2. Replace pending status with backend polling or SSE and wire detailed results.
3. Implement persistent project/audit listing, auth, and authorization.
4. Hook remaining pages into genuine PQC / assistant / payment APIs.
