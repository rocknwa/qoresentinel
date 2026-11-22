"""
audit/static_rules.py — Zero-cost, zero-LLM static pattern scan.

No API calls, no local model, runs instantly. This is NOT a substitute for
the specialist-agent audit — it can't reason about logic, it can only flag
known-risky patterns via regex, the same way spotblocks' bytecode/source
rules work. Use it as a free first-pass triage: if it comes back clean,
that does NOT mean the contract is safe, only that it doesn't contain
these specific textbook smells. Real bugs live in logic these patterns
can't see.
"""

import re

RULES = [
    (
        "reentrancy-risk",
        r"\.call\{[^}]*value\s*:",
        "Low-level `.call{value: ...}` found — verify checks-effects-interactions "
        "ordering (state updated BEFORE the external call) and that a reentrancy "
        "guard is present if this contract holds user funds.",
        "high",
    ),
    (
        "tx-origin-auth",
        r"\btx\.origin\b",
        "`tx.origin` used — if used for authentication/authorization, it's phishable "
        "via a malicious intermediary contract. Should be `msg.sender`.",
        "high",
    ),
    (
        "delegatecall",
        r"\.delegatecall\(",
        "`delegatecall` found — the target contract executes in this contract's "
        "storage context. If the target address is user-controlled or upgradeable "
        "without access control, this is a full storage-takeover vector.",
        "high",
    ),
    (
        "selfdestruct",
        r"\bselfdestruct\s*\(|\bsuicide\s*\(",
        "`selfdestruct` present — confirm it's access-controlled; unguarded, it's a "
        "full contract + fund destruction vector.",
        "high",
    ),
    (
        "unchecked-external-call",
        r"\.call\([^)]*\)\s*;",
        "Low-level `.call(...)` with return value not obviously checked — a silently "
        "failing external call can leave state inconsistent.",
        "medium",
    ),
    (
        "unprotected-initializer",
        r"function\s+initialize\s*\([^)]*\)\s*(external|public)",
        "`initialize()` function found — confirm it has an `initializer` modifier "
        "(OZ Initializable) and can't be called twice or front-run on deployment.",
        "high",
    ),
    (
        "floating-pragma",
        r"pragma\s+solidity\s*\^",
        "Floating pragma (`^`) — locks to a range, not a specific compiler version. "
        "Fine for libraries, risky for a deployed contract (different bytecode than "
        "what was reviewed if recompiled).",
        "low",
    ),
    (
        "block-timestamp-dependence",
        r"\bblock\.timestamp\b",
        "`block.timestamp` used — miners/validators have limited but nonzero control "
        "over this. Flag if used for anything precise (randomness, tight deadlines, "
        "price windows).",
        "low",
    ),
    (
        "weak-randomness",
        r"keccak256\([^)]*block\.(timestamp|number|difficulty|prevrandao)",
        "On-chain pseudo-randomness derived from block data — predictable/manipulable "
        "by miners or via a lookahead contract.",
        "high",
    ),
    (
        "arbitrary-call-target",
        r"function\s+\w+\([^)]*address\s+\w+[^)]*\)\s*(external|public)[^{]*\{[^}]*\.call\(",
        "Function accepts a user-supplied `address` and calls it — if that target "
        "isn't validated/allowlisted, this can be used to drain approvals or proxy "
        "arbitrary calls through this contract's identity.",
        "high",
    ),
    (
        "ecrecover-no-zero-check",
        r"ecrecover\(",
        "`ecrecover` used — confirm the recovered address is checked against "
        "`address(0)` (a malformed signature returns the zero address, which can "
        "pass an unguarded `== signer` check if `signer` is also unset).",
        "medium",
    ),
    (
        "unbounded-loop-over-array",
        r"for\s*\([^)]*;\s*\w+\s*<\s*\w+\.length\s*;",
        "Loop bounded by an array's `.length` — if that array can grow without limit "
        "(e.g. via a public `push`), this is a gas-DoS vector that can eventually "
        "make the function uncallable.",
        "medium",
    ),
    (
        "missing-access-control-hint",
        r"function\s+(mint|burn|withdraw|withdrawAll|setOwner|upgradeTo|pause|unpause|"
        r"rescue\w*|recoverFunds|blacklist)\s*\([^)]*\)\s*(external|public)(?![^{]*"
        r"(onlyOwner|onlyRole|onlyAdmin|require\s*\(\s*msg\.sender))",
        "Sensitive-sounding function ({match}) with no obvious access-control modifier "
        "or `require(msg.sender == ...)` guard on the same line — verify it's actually "
        "protected (guard may be in the function body, this regex can't see that).",
        "high",
    ),
]


def scan_source(source_code: str) -> list:
    """Returns a list of {id, label, severity, matches} for every rule that hits."""
    findings = []
    for rule_id, pattern, label, severity in RULES:
        matches = list(re.finditer(pattern, source_code, re.IGNORECASE))
        if matches:
            sample = matches[0].group(0)[:80].replace("\n", " ")
            findings.append(
                {
                    "id": rule_id,
                    "label": label.replace("{match}", sample),
                    "severity": severity,
                    "count": len(matches),
                    "sample": sample,
                }
            )
    return findings


def format_report(address: str, chain: str, contract_name: str, findings: list) -> str:
    lines = [
        f"# Static Pattern Scan — {contract_name or address}",
        "",
        f"**Address:** `{address}` on `{chain}`",
        "**Mode:** static regex/pattern scan — NO LLM, NO reasoning, free & instant.",
        "",
        "> ⚠️ This mode only flags textbook risky patterns by string/regex match. "
        "It cannot trace logic, cannot confirm exploitability, and cannot see bugs "
        "that don't match a known pattern (which is most real bugs). A clean scan "
        "does **not** mean the contract is safe — it means it doesn't contain these "
        "specific smells. Use the hosted cloud LLM providers or full Claude "
        "agent panel for anything you intend to actually submit to a bug bounty.",
        "",
        "---",
        "",
    ]

    if not findings:
        lines.append("No textbook risk patterns matched.")
        return "\n".join(lines)

    sev_order = {"high": 0, "medium": 1, "low": 2}
    findings_sorted = sorted(findings, key=lambda f: sev_order.get(f["severity"], 3))

    for f in findings_sorted:
        lines.append(f"### [{f['severity'].upper()}] {f['id']}")
        lines.append(f"{f['label']}")
        lines.append(f"- Matches: {f['count']}")
        lines.append(f"- Sample: `{f['sample']}`")
        lines.append("")

    return "\n".join(lines)
