"""Bridge to the original 12-specialist + final-judge VulnHunter engine."""
import os
from dataclasses import dataclass

class EngineNotConfigured(RuntimeError):
    pass

@dataclass
class AuditResult:
    report: str
    agent_results: list[dict]
    status: str

def analyze(files: dict[str, str], on_agent_done=None) -> AuditResult:
    if os.getenv("QORE_ENABLE_LLM_AUDIT", "false").lower() != "true":
        raise EngineNotConfigured("Real LLM audit disabled. Set QORE_ENABLE_LLM_AUDIT=true and configure your LLM provider.")
    # Keep source files separated, with path evidence visible to the agents.
    source = "\n\n".join(f"=== FILE: {name} ===\n{body}" for name, body in sorted(files.items()))
    from audit.orchestrator import run_audit
    result = run_audit(source, max_workers=max(1,min(12,int(os.getenv("QORE_AUDIT_WORKERS", "3")))), on_agent_done=on_agent_done)
    if not isinstance(result.get("report"),str) or not result["report"].strip():
        raise RuntimeError("Judge returned no report")
    return AuditResult(report=result["report"],agent_results=result["raw_results"],status="completed")
