"""Applicant Profile Agent — FastAPI service backed by ApplicantDB MCP.

Outputs:
  - Income Stability Score
  - Employment Risk
  - Credit History Summary
  - Application Completeness Flags
"""
from __future__ import annotations

import sys
import statistics
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI

from agents.mcp_client import call_mcp_tool
from agents.llm import generate_text, llm_available
from config import MCP_APPLICANT_DB_URL, AGENT_PROFILE_PORT, HOST
from models.schemas import ApplicantProfileOutput, LoanApplication

app = FastAPI(title="Applicant Profile Agent", version="1.0")


def _employment_risk(employment_type: str, tenure_years: float) -> str:
    if employment_type == "Unemployed":
        return "Critical"
    if employment_type == "Student":
        return "High"
    if employment_type == "Salaried" and tenure_years >= 2:
        return "Low"
    if employment_type == "Salaried":
        return "Medium"
    if employment_type == "Self-Employed" and tenure_years >= 3:
        return "Low"
    if employment_type == "Self-Employed":
        return "Medium"
    if employment_type == "Business" and tenure_years >= 5:
        return "Low"
    if employment_type == "Business":
        return "Medium"
    if employment_type == "Retired":
        return "Medium"
    return "High"


def _income_stability(income_history: List[float]) -> float:
    if not income_history or sum(income_history) == 0:
        return 0.0
    avg = statistics.mean(income_history)
    if avg == 0:
        return 0.0
    stdev = statistics.pstdev(income_history)
    cv = stdev / avg  # coefficient of variation
    # Map cv in [0, 1.0+] -> stability in [1, 0]
    stability = max(0.0, min(1.0, 1.0 - cv))
    return round(stability, 3)


def _credit_history_summary(ch: dict) -> str:
    taken = ch.get("loans_taken", 0)
    closed = ch.get("loans_closed", 0)
    defaults = ch.get("defaults", 0)
    late = ch.get("late_payments_12mo", 0)
    if taken == 0:
        return "No prior credit history."
    parts = [f"{taken} loans taken, {closed} closed"]
    if defaults:
        parts.append(f"{defaults} default(s)")
    if late:
        parts.append(f"{late} late payment(s) in last 12 months")
    return "; ".join(parts) + "."


@app.post("/analyze", response_model=ApplicantProfileOutput)
def analyze(application: LoanApplication) -> ApplicantProfileOutput:
    aid = application.applicant_id

    profile = call_mcp_tool(MCP_APPLICANT_DB_URL, "get_applicant_profile", {"applicant_id": aid})
    income_obj = call_mcp_tool(MCP_APPLICANT_DB_URL, "get_income_history", {"applicant_id": aid})
    kyc = call_mcp_tool(MCP_APPLICANT_DB_URL, "check_kyc", {"applicant_id": aid})

    completeness_flags: list[str] = []
    is_new_applicant = False
    if isinstance(profile, dict) and profile.get("error") == "applicant_not_found":
        completeness_flags.append("applicant_record_missing")
        employment_type = application.employment_type.value
        tenure_years = 0.0
        income_history: List[float] = []
        credit_history = {}
    else:
        is_new_applicant = bool(profile.get("is_new_applicant", False))
        employment_type = profile.get("employment_type", application.employment_type.value)
        tenure_years = float(profile.get("employment_tenure_years", 0))
        income_history = list(income_obj.get("income_history_12mo", [])) if isinstance(income_obj, dict) else []
        credit_history = profile.get("credit_history", {})
        if not kyc.get("kyc_complete"):
            # Distinguish first-time customers (KYC pending by definition) from
            # existing customers whose KYC has gone stale — different policy paths.
            completeness_flags.append(
                "new_applicant_kyc_pending" if is_new_applicant else "kyc_incomplete"
            )
        if not kyc.get("address_verified"):
            completeness_flags.append("address_unverified")

    if not income_history:
        completeness_flags.append("income_history_missing")

    stability = _income_stability(income_history)
    emp_risk = _employment_risk(employment_type, tenure_years)
    ch_summary = _credit_history_summary(credit_history)

    reasoning_default = (
        f"Employment '{employment_type}' with {tenure_years} years tenure -> {emp_risk} risk. "
        f"Income stability {stability:.2f} computed from 12-month history. {ch_summary}"
    )
    reasoning = reasoning_default
    if llm_available():
        llm_reason = generate_text(
            system=(
                "You are an applicant profile analyst. Write a concise, factual two-sentence "
                "explanation grounded only in the provided data."
            ),
            user=(
                f"Employment: {employment_type} ({tenure_years}y tenure)\n"
                f"Income history (12mo): {income_history}\n"
                f"Stability score: {stability}\n"
                f"Credit history: {credit_history}\n"
                f"KYC: {kyc}\n"
                f"Completeness flags: {completeness_flags}\n"
                f"Application: {application.model_dump(mode='json')}"
            ),
            max_tokens=200,
        )
        if llm_reason:
            reasoning = llm_reason

    return ApplicantProfileOutput(
        applicant_id=aid,
        income_stability_score=stability,
        employment_risk=emp_risk,
        credit_history_summary=ch_summary,
        application_completeness_flags=completeness_flags,
        reasoning=reasoning,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "applicant_profile", "mcp": MCP_APPLICANT_DB_URL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=AGENT_PROFILE_PORT)
