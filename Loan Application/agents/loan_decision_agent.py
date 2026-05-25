"""Loan Decision Agent — FastAPI service backed by DecisionSynthesis MCP + Claude LLM.

Outputs:
  - Classification (Approve / Reject / Review)
  - Risk Score
  - Confidence Level
  - Key Decision Factors
  - Explanation
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from pydantic import BaseModel

from agents.mcp_client import call_mcp_tool
from agents.llm import generate_json, generate_text, llm_available
from config import MCP_DECISION_SYNTH_URL, MCP_RISK_RULES_URL, AGENT_DECISION_PORT, HOST
from models.schemas import (
    ApplicantProfileOutput,
    Classification,
    FinancialRiskOutput,
    LoanApplication,
    LoanDecisionOutput,
)

app = FastAPI(title="Loan Decision Agent", version="1.0")


class DecideRequest(BaseModel):
    application: LoanApplication
    profile: ApplicantProfileOutput
    risk: FinancialRiskOutput


def _hard_policy_violations(req: DecideRequest) -> List[str]:
    violations: List[str] = []
    if req.application.employment_type.value == "Unemployed":
        violations.append("Unemployed applicants are not eligible for unsecured loans.")
    if req.risk.debt_to_income_ratio > 0.55 and req.application.credit_score < 800:
        violations.append("DTI exceeds 0.55 and credit score below 800 — auto-reject per policy.")
    if "kyc_incomplete" in req.profile.application_completeness_flags:
        violations.append("KYC incomplete — cannot approve without completing KYC.")
    # Note: "new_applicant_kyc_pending" is NOT a hard violation — first-time
    # customers are expected to complete KYC during onboarding, so they're routed
    # to manual review rather than auto-rejected.
    return violations


def _soft_review_signals(req: DecideRequest) -> List[str]:
    """Conditions that should nudge a borderline case toward manual review."""
    signals: List[str] = []
    flags = req.profile.application_completeness_flags
    if "new_applicant_kyc_pending" in flags:
        signals.append("New customer — KYC verification pending.")
    if "address_unverified" in flags:
        signals.append("Address verification pending.")
    if "applicant_record_missing" in flags:
        signals.append("No prior banking history on file.")
    return signals


def _default_probability_from_band(band_name: str) -> float:
    return {
        "Excellent": 0.02,
        "Good": 0.06,
        "Fair": 0.15,
        "Poor": 0.28,
        "Very Poor": 0.55,
    }.get(band_name, 0.5)


@app.post("/decide", response_model=LoanDecisionOutput)
def decide(req: DecideRequest) -> LoanDecisionOutput:
    hard = _hard_policy_violations(req)
    onboarding_notes = _soft_review_signals(req)
    policy_notes = call_mcp_tool(MCP_RISK_RULES_URL, "get_policy_notes", {})

    # Classification is driven purely by real financial-risk signals.
    # Onboarding flags (new-applicant KYC pending, address unverified) are NOT
    # treated as risk anomalies — a strong-profile new applicant should still
    # be eligible for approval, with KYC handled as a downstream contingency.
    synth = call_mcp_tool(
        MCP_DECISION_SYNTH_URL,
        "synthesize_decision",
        {
            "applicant_id": req.application.applicant_id,
            "income_stability_score": req.profile.income_stability_score,
            "employment_risk": req.profile.employment_risk,
            "credit_default_probability": _default_probability_from_band(req.risk.credit_score_risk_level),
            "dti": req.risk.debt_to_income_ratio,
            "anomalies": req.risk.anomaly_reasons,
            "hard_policy_violations": hard,
        },
    )

    classification_str = synth.get("classification", "Requires Manual Review")
    risk_score = float(synth.get("risk_score", 50.0))
    confidence = float(synth.get("confidence", 0.6))
    key_factors: List[str] = list(synth.get("key_decision_factors", []))

    explanation = synth.get("rationale", "")
    if llm_available():
        llm_out = generate_json(
            system=(
                "You are a senior loan underwriter producing an explainable decision. "
                "You receive deterministic risk signals and a recommended classification. "
                "Your job is to either AGREE with the recommendation or escalate to manual review "
                "if the financial signals are contradictory, and to write a clear customer-facing explanation. "
                "IMPORTANT: Onboarding flags such as 'new applicant — KYC verification pending' or "
                "'address verification pending' must NOT cause a downgrade by themselves. New customers "
                "with strong financial profiles should be APPROVED, with KYC handled as a downstream "
                "contingency — mention this contingency in your explanation but do not change the "
                "classification because of it. Only true financial risk anomalies or hard policy violations "
                "should affect the classification. "
                "Never invent facts not present in the inputs. Respond with a JSON object with keys: "
                "classification (one of 'Approved','Rejected','Requires Manual Review'), "
                "confidence (0..1 float), key_decision_factors (string array), explanation (string)."
            ),
            user=(
                f"Application: {req.application.model_dump(mode='json')}\n"
                f"Profile signals: {req.profile.model_dump()}\n"
                f"Risk signals: {req.risk.model_dump()}\n"
                f"Hard policy violations: {hard}\n"
                f"Onboarding notes (informational, do not downgrade): {onboarding_notes}\n"
                f"Policy notes: {policy_notes}\n"
                f"Deterministic synthesis: {synth}"
            ),
            max_tokens=700,
        )
        if isinstance(llm_out, dict) and "classification" in llm_out:
            cls_candidate = str(llm_out.get("classification", classification_str))
            if cls_candidate in {"Approved", "Rejected", "Requires Manual Review"}:
                classification_str = cls_candidate
            try:
                confidence = float(llm_out.get("confidence", confidence))
            except (TypeError, ValueError):
                pass
            kf = llm_out.get("key_decision_factors")
            if isinstance(kf, list) and kf:
                key_factors = [str(x) for x in kf]
            exp = llm_out.get("explanation")
            if isinstance(exp, str) and exp.strip():
                explanation = exp.strip()

    if not explanation:
        explanation = generate_text(
            system="Write a one-paragraph explainable rationale for a loan decision.",
            user=str(synth),
        ) or synth.get("rationale", "Decision based on standard underwriting signals.")

    # For new-customer approvals, surface the KYC contingency in the explanation
    # so the customer knows their offer is real but conditional on onboarding.
    if classification_str == "Approved" and onboarding_notes:
        explanation = (
            f"{explanation}\n\nNote: As a new State Bank customer, final disbursement is "
            "subject to completing KYC verification and address proof — our team will reach "
            "out to guide you through this quick onboarding step."
        )
        if "Pending KYC verification (new customer)" not in key_factors:
            key_factors = list(key_factors) + ["Approval contingent on KYC completion"]

    return LoanDecisionOutput(
        applicant_id=req.application.applicant_id,
        classification=Classification(classification_str),
        risk_score=risk_score,
        confidence_level=max(0.0, min(1.0, confidence)),
        key_decision_factors=key_factors,
        explanation=explanation,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "loan_decision", "mcp": MCP_DECISION_SYNTH_URL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=AGENT_DECISION_PORT)
