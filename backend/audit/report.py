"""audit/report.py — Saves the final markdown report to output/."""

import os
import re
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def save_report(address: str, chain: str, contract_name: str, report_md: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", contract_name or address)
    filename = f"{safe_name}-{chain}-{timestamp}.md"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report_md)
    return path
