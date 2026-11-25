"""Extract report headings into navigable finding summaries; do not infer exploit validity."""
import re

SEVERITY=re.compile(r'^###\s+\[(Critical|High|Medium|Low|Informational|Info)\]\s+(.+?)\s*$',re.I)
SECTION=re.compile(r'^##\s+(.+)$')
MAX_ITEMS=100

def extract_findings(report:str)->list[dict]:
    if not isinstance(report,str) or not report:
        return []
    found=[]
    in_confirmed=False
    current=None
    details=[]
    def finish():
        if current is not None:
            current['evidence']='\n'.join(details).strip()[:2500]
            found.append(current)
    for raw in report.splitlines():
        heading=SECTION.match(raw.strip())
        if heading:
            if in_confirmed:
                finish()
                break
            in_confirmed=heading.group(1).lower().startswith('confirmed findings')
            continue
        if not in_confirmed:
            continue
        match=SEVERITY.match(raw.strip())
        if match:
            finish()
            if len(found)>=MAX_ITEMS:break
            current={'severity':match.group(1).capitalize(),'title':match.group(2)[:220],
                     'source':'audit-report','verified':False}
            details=[]
        elif current is not None:
            details.append(raw)
    else:
        if in_confirmed:finish()
    return found[:MAX_ITEMS]
