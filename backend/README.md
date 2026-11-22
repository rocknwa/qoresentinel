# Backend Phase 1

Python 3.11+ recommended.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest -q
```

Open http://127.0.0.1:8000/docs for interactive API docs.

Endpoints: `GET /health`; `POST /api/v1/projects` (`{"name":"Example"}`); `GET /api/v1/projects/{id}`; `POST /api/v1/projects/{id}/source` (`{"source":"contract A {}"}`); `POST /api/v1/projects/{id}/files` (multipart field `files`, `.sol` or one ZIP); `POST /api/v1/projects/{id}/audits`.

Audit execution is **off by default**; enabling requires credentials for at least one RiskSearcher cloud LLM provider (Anthropic, OpenRouter, Groq, or AgentRouter). Original VulnHunter's 12 specialist agents and judge are included; their output remains Markdown plus raw agent results, NOT validated structured findings. Calls are synchronous and may be slow/expensive. The result explicitly marks structured parsing as unavailable. No fake findings.

Limits: 2 MB per `.sol`, 8 MB total expanded archive/source, 80 Solidity files, 4 MB ZIP compressed. ZIP non-Solidity entries are ignored; no project commands, scripts, package installation, or compilation runs. This MVP ingests source text only and does not resolve imports. Metadata and source text are stored in local SQLite under `.local-data/`; protect it and do not expose this service publicly without authentication, per-user isolation and retention controls.

**Next:** add auth, proper durable jobs/queue, sandbox and job cancellation, structured finding extraction with validation, and source retention controls before exposing an audit API to the internet.
 