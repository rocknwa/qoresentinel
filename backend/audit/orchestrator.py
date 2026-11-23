"""
audit/orchestrator.py — Runs the specialist agents in parallel, then runs a
final judge pass that dedups, gates, and formats the report. Provider fallback (Anthropic, OpenRouter, Groq, AgentRouter) is provided by
audit/llm_client.py.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from audit.llm_client import generate
from audit.prompts_loader import (
    available_agent_names,
    build_agent_bundle,
    build_judge_prompt,
    load_shared_texts,
)

MAX_TOKENS_AGENT = 8000
MAX_TOKENS_JUDGE = 8000


def _run_agent(agent_name: str, source_blob: str, shared: dict) -> dict:
    prompt = build_agent_bundle(agent_name, source_blob, shared)
    start = time.time()
    try:
        text = generate(prompt, max_tokens=MAX_TOKENS_AGENT, role="agent")
        # Some backends may (rarely) return None or a non-string; coerce to
        # an empty string so downstream code can safely call string methods.
        if text is None:
            text = ""
        elif not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                text = ""
        return {
            "agent": agent_name,
            "ok": True,
            "text": text,
            "elapsed_s": round(time.time() - start, 1),
        }
    except Exception as e:
        return {
            "agent": agent_name,
            "ok": False,
            "text": "",
            "error": str(e),
            "elapsed_s": round(time.time() - start, 1),
        }


def run_audit(
    source_blob: str,
    agents: list = None,
    max_workers: int = 6,
    on_agent_done=None,
) -> dict:
    """
    Run the full multi-agent audit pipeline against `source_blob`.

    Returns:
      {
        "raw_results": [ {agent, ok, text, elapsed_s, error?}, ... ],
        "report": str,   # final formatted markdown report from the judge pass
      }
    """
    agents = agents or available_agent_names()
    shared = load_shared_texts()

    raw_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_run_agent, name, source_blob, shared): name
            for name in agents
        }
        for fut in as_completed(futures):
            result = fut.result()
            raw_results.append(result)
            if on_agent_done:
                on_agent_done(result)

    ok_results = [r for r in raw_results if r["ok"] and r["text"].strip()]
    if not ok_results:
        # Try to give a more actionable error message: prefer an explicit
        # backend error if present, otherwise note that agents returned
        # empty/whitespace responses (common when a free-tier model returns
        # an empty string). Include a sample agent status for debugging.
        if raw_results:
            first_err = next((r.get("error") for r in raw_results if not r.get("ok") and r.get("error")), None)
            if first_err:
                raise RuntimeError("All specialist agents failed. First error: " + first_err)
            sample = raw_results[0]
            sample_text = sample.get("text") or ""
            raise RuntimeError(
                "All specialist agents returned empty or whitespace responses. "
                f"Sample: agent={sample.get('agent')}, ok={sample.get('ok')}, text_len={len(sample_text)}"
            )
        else:
            raise RuntimeError("All specialist agents failed: no agents ran")

    combined_findings = "\n\n".join(
        f"=== Agent: {r['agent']} ===\n{r['text']}" for r in ok_results
    )

    judge_prompt = build_judge_prompt(
        source_blob=source_blob,
        raw_findings=combined_findings,
        shared=shared,
        meta={"num_agents": len(ok_results)},
    )

    report = generate(judge_prompt, max_tokens=MAX_TOKENS_JUDGE, role="judge")

    return {"raw_results": raw_results, "report": report}
