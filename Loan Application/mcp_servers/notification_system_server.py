"""NotificationSystem MCP Server — handles compliance actions and notifications.

Tools:
  - create_case_id(applicant_id): generate a unique case ID
  - send_notification(applicant_id, channel, message)
  - log_compliance_action(applicant_id, classification, action, summary)
  - list_recent_cases(limit): for demo / audit display
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastmcp import FastMCP  # type: ignore
from config import MCP_NOTIFICATION_PORT, HOST, LOGS_DIR

mcp = FastMCP(name="NotificationSystem")

_LOG_PATH = LOGS_DIR / "compliance_log.jsonl"
_NOTIF_PATH = LOGS_DIR / "notifications.jsonl"


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


@mcp.tool
def create_case_id(applicant_id: str) -> Dict[str, Any]:
    """Generate a unique compliance case ID."""
    case_id = f"CASE-{uuid.uuid4().hex[:10].upper()}"
    return {"applicant_id": applicant_id, "case_id": case_id}


@mcp.tool
def send_notification(applicant_id: str, channel: str, message: str) -> Dict[str, Any]:
    """Simulate sending a notification (email/sms/in-app) to the applicant."""
    record = {
        "applicant_id": applicant_id,
        "channel": channel,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "SENT",
    }
    _append_jsonl(_NOTIF_PATH, record)
    return record


@mcp.tool
def log_compliance_action(
    applicant_id: str,
    classification: str,
    action: str,
    summary: str,
    case_id: str,
) -> Dict[str, Any]:
    """Persist a compliance action to an append-only audit log."""
    record = {
        "applicant_id": applicant_id,
        "classification": classification,
        "action": action,
        "summary": summary,
        "case_id": case_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    _append_jsonl(_LOG_PATH, record)
    return record


@mcp.tool
def list_recent_cases(limit: int = 10) -> Dict[str, Any]:
    """Return the most recent compliance entries from the audit log."""
    if not _LOG_PATH.exists():
        return {"cases": [], "count": 0}
    lines = _LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    records: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"cases": records, "count": len(records)}


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=MCP_NOTIFICATION_PORT)
