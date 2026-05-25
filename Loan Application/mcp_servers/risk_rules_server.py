"""RiskRulesDB MCP Server — exposes underwriting rules and risk computations.

Tools:
  - get_credit_score_band(score): rule band + default probability
  - compute_dti(income_monthly, loan_amount, tenure_months, existing_liabilities)
  - get_loan_amount_cap(employment_type, monthly_income)
  - detect_anomalies(payload): rule-based anomaly detection
  - get_policy_notes(): plain-language policy hints for the LLM
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastmcp import FastMCP  # type: ignore
from config import MCP_RISK_RULES_PORT, HOST, DATA_DIR

mcp = FastMCP(name="RiskRulesDB")

_RULES_PATH = DATA_DIR / "risk_rules.json"


def _load_rules() -> Dict[str, Any]:
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@mcp.tool
def get_credit_score_band(credit_score: int) -> Dict[str, Any]:
    """Return the credit risk band for a given credit score."""
    rules = _load_rules()
    for band in rules["credit_score_bands"]:
        if band["min"] <= credit_score <= band["max"]:
            return {"credit_score": credit_score, **band}
    return {"credit_score": credit_score, "level": "Unknown", "default_probability": 1.0}


@mcp.tool
def compute_dti(
    monthly_income: float,
    loan_amount: float,
    tenure_months: int,
    existing_liabilities: float = 0.0,
    annual_interest_rate: float = 0.11,
) -> Dict[str, Any]:
    """Compute Debt-to-Income ratio and return its risk classification."""
    rules = _load_rules()
    if monthly_income <= 0 or tenure_months <= 0:
        return {
            "monthly_income": monthly_income,
            "monthly_emi": 0.0,
            "dti": 1.0,
            "classification": "Unfeasible",
            "reason": "Zero or invalid income / tenure.",
        }
    r = annual_interest_rate / 12
    n = tenure_months
    emi = (loan_amount * r * (1 + r) ** n) / (((1 + r) ** n) - 1) if r > 0 else loan_amount / n
    dti = (emi + existing_liabilities) / monthly_income
    thresholds = rules["dti_thresholds"]
    if dti <= thresholds["safe"]:
        classification = "Safe"
    elif dti <= thresholds["moderate"]:
        classification = "Moderate"
    elif dti <= thresholds["high"]:
        classification = "High"
    else:
        classification = "Critical"
    return {
        "monthly_income": monthly_income,
        "monthly_emi": round(emi, 2),
        "existing_liabilities": existing_liabilities,
        "dti": round(dti, 4),
        "classification": classification,
        "thresholds": thresholds,
    }


@mcp.tool
def get_loan_amount_cap(employment_type: str, monthly_income: float) -> Dict[str, Any]:
    """Return the maximum eligible loan amount based on employment-type multipliers."""
    rules = _load_rules()
    caps = rules["loan_amount_multiplier_caps"]
    mult = caps.get(employment_type, 0)
    cap = mult * monthly_income
    return {
        "employment_type": employment_type,
        "monthly_income": monthly_income,
        "multiplier": mult,
        "max_loan_amount": cap,
    }


@mcp.tool
def detect_anomalies(
    age: int,
    loan_amount: float,
    tenure_months: int,
    location: str,
    employment_type: str,
) -> Dict[str, Any]:
    """Rule-based anomaly detection on application fields."""
    rules = _load_rules()
    anomalies: List[str] = []
    ar = rules["anomaly_rules"]
    if age < ar["min_age"]:
        anomalies.append(f"Age {age} below minimum {ar['min_age']}.")
    if age > ar["max_age"]:
        anomalies.append(f"Age {age} above maximum {ar['max_age']}.")
    if tenure_months > ar["max_tenure_months"]:
        anomalies.append(f"Tenure {tenure_months} exceeds max {ar['max_tenure_months']}.")
    if loan_amount < ar["min_loan_amount"]:
        anomalies.append(f"Loan amount {loan_amount} below minimum {ar['min_loan_amount']}.")
    if location in rules["high_risk_locations"]:
        anomalies.append(f"Location '{location}' is flagged as high-risk.")
    if employment_type == "Unemployed":
        anomalies.append("Unemployed applicants are not eligible for unsecured loans.")
    return {
        "anomaly_detected": len(anomalies) > 0,
        "anomaly_reasons": anomalies,
    }


@mcp.tool
def get_policy_notes() -> Dict[str, Any]:
    """Plain-language policy notes that the LLM can quote when explaining decisions."""
    rules = _load_rules()
    return {"policy_notes": rules["policy_notes"]}


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=MCP_RISK_RULES_PORT)
