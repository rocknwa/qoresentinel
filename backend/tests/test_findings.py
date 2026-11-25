"""Report heading extraction only; reported issues are not independently verified."""
from app.findings import extract_findings


def test_reported_findings_are_browsable_without_rerunning_audit():
    report = '''# Vulnerability Report — POAPDapp

## Summary
This is untrusted AI-generated analysis.

## Confirmed Findings
### [High] `updateCode` — code disclosed in event
**Attack path:** event exposes the string.

### [Medium] Mint authorization bypass
**Proof:** example source.

## Leads (unverified)
### [High] This is not a confirmed finding
'''
    findings = extract_findings(report)
    assert len(findings) == 2
    assert [f['severity'] for f in findings] == ['High', 'Medium']
    assert all(not f['verified'] and f['source'] == 'audit-report' for f in findings)
    assert 'Attack path' in findings[0]['evidence']


def test_report_without_confirmed_findings():
    report = '''# Vulnerability Report — POAPNFT
## Confirmed Findings
**None.**
## Leads (unverified)
- Soulbound override might be incorrect.
'''
    assert extract_findings(report) == []


def test_unrelated_markdown_does_not_count_as_findings():
    assert extract_findings('## Leads\n### [High] Unconfirmed issue') == []
    assert extract_findings('') == []
