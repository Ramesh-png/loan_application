"""ApplicantDB MCP Server — exposes applicant profile data and credit history.

Tools:
  - get_applicant_profile(applicant_id): full record
  - get_credit_history(applicant_id): credit history block
  - get_income_history(applicant_id): last 12 months income
  - check_kyc(applicant_id): KYC + address verification status
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is on path when executed directly
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastmcp import FastMCP  # type: ignore
from config import MCP_APPLICANT_DB_PORT, HOST, DATA_DIR

mcp = FastMCP(name="ApplicantDB")

_DB_PATH = DATA_DIR / "applicants.json"


def _load_db() -> Dict[str, Any]:
    with open(_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_db(db: Dict[str, Any]) -> None:
    with open(_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


@mcp.tool
def get_applicant_profile(applicant_id: str) -> Dict[str, Any]:
    """Return the full applicant record for the given applicant_id."""
    db = _load_db()
    record = db.get(applicant_id)
    if not record:
        return {"error": "applicant_not_found", "applicant_id": applicant_id}
    return record


@mcp.tool
def get_credit_history(applicant_id: str) -> Dict[str, Any]:
    """Return only the credit history block for an applicant."""
    db = _load_db()
    record = db.get(applicant_id)
    if not record:
        return {"error": "applicant_not_found", "applicant_id": applicant_id}
    return {"applicant_id": applicant_id, "credit_history": record["credit_history"]}


@mcp.tool
def get_income_history(applicant_id: str) -> Dict[str, Any]:
    """Return the last 12 months of income for an applicant."""
    db = _load_db()
    record = db.get(applicant_id)
    if not record:
        return {"error": "applicant_not_found", "applicant_id": applicant_id}
    income: List[float] = record["income_history_12mo"]
    avg = sum(income) / len(income) if income else 0
    variance = (sum((x - avg) ** 2 for x in income) / len(income)) if income else 0
    return {
        "applicant_id": applicant_id,
        "income_history_12mo": income,
        "average_monthly_income": avg,
        "monthly_variance": variance,
    }


@mcp.tool
def check_kyc(applicant_id: str) -> Dict[str, Any]:
    """Return KYC and address verification status."""
    db = _load_db()
    record = db.get(applicant_id)
    if not record:
        return {"error": "applicant_not_found", "applicant_id": applicant_id}
    return {
        "applicant_id": applicant_id,
        "kyc_complete": record.get("kyc_complete", False),
        "address_verified": record.get("address_verified", False),
    }


@mcp.tool
def list_applicants() -> Dict[str, Any]:
    """List all known applicant IDs (helper for demo / debugging)."""
    db = _load_db()
    return {"applicant_ids": list(db.keys()), "count": len(db)}


@mcp.tool
def register_applicant(
    applicant_id: str,
    full_name: str = "",
    age: int = 0,
    employment_type: str = "Unknown",
    employer: str = "",
    annual_income: float = 0.0,
    location: str = "",
) -> Dict[str, Any]:
    """Idempotently create an applicant record if one doesn't exist.

    Used when a brand-new applicant submits a loan application — they get added
    to ApplicantDB so future lookups (and the existing-customer dropdown) see them.
    Returns {"created": bool, "applicant_id": str, "record": <record>}.
    """
    db = _load_db()
    if applicant_id in db:
        return {"created": False, "applicant_id": applicant_id, "record": db[applicant_id]}

    monthly = float(annual_income) / 12.0 if annual_income else 0.0
    record = {
        "applicant_id": applicant_id,
        "name": full_name or applicant_id,
        "age": age,
        "employment_type": employment_type,
        "employer": employer or None,
        "employment_tenure_years": 0,
        "credit_history": {
            "loans_taken": 0,
            "loans_closed": 0,
            "defaults": 0,
            "late_payments_12mo": 0,
        },
        "income_history_12mo": [round(monthly, 2)] * 12,
        "address_verified": False,
        "kyc_complete": False,
        "location": location,
        "is_new_applicant": True,
    }
    db[applicant_id] = record
    _save_db(db)
    return {"created": True, "applicant_id": applicant_id, "record": record}


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=MCP_APPLICANT_DB_PORT)
