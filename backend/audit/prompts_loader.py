"""
audit/prompts_loader.py — Assembles the prompt bundles used to drive each
specialist "attacker" agent. This is a straight port of the pashov/skills
`solidity-auditor` Claude Code skill methodology
(https://github.com/pashov/skills), adapted to run as direct Anthropic API
calls instead of Claude Code's Agent/Task tool.
"""

import os

_HERE = os.path.dirname(__file__)
_PROMPTS = os.path.join(_HERE, "prompts")
_AGENTS_DIR = os.path.join(_PROMPTS, "agents")

# Ordered specialty roster. Each maps to references/hacking-agents/<file>.
# The three "gap-hunter" agents (flow/numerical/trust) look for bugs at the
# seams BETWEEN other lenses, so they're most valuable once the base set has
# run — keep them last so users trimming --agents keep the core lenses.
AGENT_ROSTER = [
    ("access-control", "access-control-agent.md"),
    ("economic-security", "economic-security-agent.md"),
    ("math-precision", "math-precision-agent.md"),
    ("execution-trace", "execution-trace-agent.md"),
    ("invariant", "invariant-agent.md"),
    ("first-principles", "first-principles-agent.md"),
    ("asymmetry", "asymmetry-agent.md"),
    ("boundary", "boundary-agent.md"),
    ("periphery", "periphery-agent.md"),
    ("numerical-gap", "numerical-gap-agent.md"),
    ("trust-gap", "trust-gap-agent.md"),
    ("flow-gap", "flow-gap-agent.md"),
]


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_shared_texts() -> dict:
    return {
        "sop": _read(os.path.join(_PROMPTS, "senior_auditor_sop.md")),
        "shared_rules": _read(os.path.join(_PROMPTS, "shared_rules.md")),
        "judging": _read(os.path.join(_PROMPTS, "judging.md")),
    }


def available_agent_names() -> list:
    return [name for name, _ in AGENT_ROSTER]


def build_agent_bundle(agent_name: str, source_blob: str, shared: dict) -> str:
    """
    Build the full system prompt for one specialist agent: its specialty
    file + the senior-auditor SOP (how to think) + shared output rules,
    followed by the in-scope source code.
    """
    filename = dict(AGENT_ROSTER).get(agent_name)
    if not filename:
        raise ValueError(f"Unknown agent '{agent_name}'. Options: {available_agent_names()}")

    specialty = _read(os.path.join(_AGENTS_DIR, filename))

    return (
        "You are an attacker auditing a smart contract for exploitable "
        "vulnerabilities, working a bug-bounty / responsible-disclosure "
        "engagement. Your goal is to find real, exploitable bugs so they "
        "can be reported through a legitimate bug bounty program "
        "(Immunefi, Code4rena, Sherlock, Cantina, or direct to the "
        "project) — never to exploit anything yourself.\n\n"
        f"{specialty}\n\n---\n\n{shared['sop']}\n\n---\n\n{shared['shared_rules']}\n\n"
        f"---\n\n# In-scope source\n\n{source_blob}"
    )


def build_judge_prompt(source_blob: str, raw_findings: str, shared: dict, meta: dict) -> str:
    """
    Build the prompt for the final dedup + gate + report pass. This mirrors
    Turn 4 of the solidity-auditor skill: dedup, run judging.md's 4 gates,
    then emit a bug-bounty-oriented report.
    """
    return f"""You are the lead auditor reviewing raw findings submitted by {meta.get('num_agents')} \
specialist attacker agents who each independently reviewed the same contract(s) for a bug-bounty \
engagement. Your job: deduplicate, validate, and produce the final report.

## Step 1 — Deduplicate
Group findings by (contract, function, bug class). Merge duplicates reported by multiple agents \
(note how many agents independently flagged it — convergence is a confidence signal). Keep every \
distinct mechanism even within the same function; never silently drop a unique (contract, function) \
pair that appears in the raw findings.

## Step 2 — Gate every finding
Run each deduplicated finding through these four gates, in order, no skipping:

{shared['judging']}

## Step 3 — Produce the final report
Use this exact structure:

```
# Vulnerability Report — <contract name(s)>

## Summary
<2-3 sentences: overall risk posture, most severe finding, how many confirmed vs leads>

## Confirmed Findings
(sorted by confidence, highest first — only findings that cleared all 4 gates)

### [severity] <Title>
`Contract.function` · Confidence: <0-100> · Agents flagging: <N>

**Attack path:** caller → function → state change → impact
**Proof:** concrete values/trace from the actual code
**Impact:** who loses what, and how much
**Suggested fix:**
```diff
- vulnerable line(s)
+ fixed line(s)
```
**Bug bounty notes:** likely severity bucket (Critical/High/Medium/Low per Immunefi-style \
classification) and what a PoC would need to demonstrate.

---

## Leads (unverified, worth manual follow-up)
- **<Title>** — `Contract.function` — <code smell> — <what's unverified>

## Rejected / Not exploitable
(brief list — findings that did not clear the gates, and which gate stopped them — keeps the \
report honest about what was considered and ruled out)

---
> AI-assisted analysis. This does not replace a professional audit or guarantee completeness. \
Before reporting anything to a bug bounty program, verify the finding against the program's \
current scope and rules, and never test exploits against a live/mainnet deployment — use a fork \
or testnet.
```

## Contract source (for your own verification during gating)

{source_blob}

## Raw findings from the {meta.get('num_agents')} specialist agents

{raw_findings}
"""
