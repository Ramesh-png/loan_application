"""Financial Risk Analysis Agent — FastAPI service backed by RiskRulesDB MCP.

Outputs:
  - Debt-to-Income Ratio
  - Credit Score Risk Level
  - Loan Amount Risk
  - Anomaly Detection
  - Reasoning
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI

from agents.mcp_client import call_mcp_tool
from agents.llm import generate_text, llm_available
from config import MCP_RISK_RULES_URL, AGENT_RISK_PORT, HOST
from models.schemas import FinancialRiskOutput, LoanApplication

app = FastAPI(title="Financial Risk Analysis Agent", version="1.0")


@app.post("/analyze", response_model=FinancialRiskOutput)
def analyze(application: LoanApplication) -> FinancialRiskOutput:
    monthly_income = application.income / 12.0

    band = call_mcp_tool(MCP_RISK_RULES_URL, "get_credit_score_band", {"credit_score": application.credit_score})
    dti = call_mcp_tool(
        MCP_RISK_RULES_URL,
        "compute_dti",
        {
            "monthly_income": monthly_income,
            "loan_amount": application.loan_amount,
            "tenure_months": application.loan_tenure_months,
            "existing_liabilities": application.existing_liabilities,
        },
    )
    cap = call_mcp_tool(
        MCP_RISK_RULES_URL,
        "get_loan_amount_cap",
        {"employment_type": application.employment_type.value, "monthly_income": monthly_income},
    )
    anomalies = call_mcp_tool(
        MCP_RISK_RULES_URL,
        "detect_anomalies",
        {
            "age": application.age,
            "loan_amount": application.loan_amount,
            "tenure_months": application.loan_tenure_months,
            "location": application.location,
            "employment_type": application.employment_type.value,
        },
    )

    max_loan = cap.get("max_loan_amount", 0) if isinstance(cap, dict) else 0
    if max_loan <= 0:
        loan_amount_risk = "Critical"
    elif application.loan_amount > max_loan:
        loan_amount_risk = "High"
    elif application.loan_amount > 0.75 * max_loan:
        loan_amount_risk = "Moderate"
    else:
        loan_amount_risk = "Low"

    anomaly_reasons: List[str] = list(anomalies.get("anomaly_reasons", [])) if isinstance(anomalies, dict) else []
    anomaly_detected = bool(anomalies.get("anomaly_detected", False)) if isinstance(anomalies, dict) else False

    reasoning_default = (
        f"Credit score {application.credit_score} -> {band.get('level')} (default p={band.get('default_probability')}). "
        f"DTI {dti.get('dti')} -> {dti.get('classification')}. "
        f"Loan amount risk: {loan_amount_risk} (cap {max_loan})."
    )
    reasoning = reasoning_default
    if llm_available():
        llm_reason = generate_text(
            system=(
                "You are a financial risk analyst. Provide a concise three-sentence narrative "
                "grounded ONLY in the supplied risk signals."
            ),
            user=(
                f"Credit band: {band}\nDTI calc: {dti}\nLoan cap: {cap}\nAnomalies: {anomalies}\n"
                f"Application: {application.model_dump(mode='json')}"
            ),
            max_tokens=220,
        )
        if llm_reason:
            reasoning = llm_reason

    return FinancialRiskOutput(
        applicant_id=application.applicant_id,
        debt_to_income_ratio=float(dti.get("dti", 0.0)),
        credit_score_risk_level=str(band.get("level", "Unknown")),
        loan_amount_risk=loan_amount_risk,
        anomaly_detected=anomaly_detected,
        anomaly_reasons=anomaly_reasons,
        reasoning=reasoning,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "financial_risk", "mcp": MCP_RISK_RULES_URL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=AGENT_RISK_PORT)
