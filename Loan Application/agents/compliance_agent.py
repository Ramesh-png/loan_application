"""Compliance & Action Orchestrator Agent — FastAPI service backed by NotificationSystem MCP.

Outputs:
  - Action Taken
  - Notification Sent
  - Case ID
  - Timestamp
  - Summary
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from pydantic import BaseModel

from agents.mcp_client import call_mcp_tool
from agents.llm import generate_text, llm_available
from config import MCP_NOTIFICATION_URL, AGENT_COMPLIANCE_PORT, HOST
from models.schemas import (
    ApplicantProfileOutput,
    ComplianceOutput,
    FinancialRiskOutput,
    LoanApplication,
    LoanDecisionOutput,
)

app = FastAPI(title="Compliance & Action Orchestrator Agent", version="1.0")


class ComplianceRequest(BaseModel):
    application: LoanApplication
    profile: ApplicantProfileOutput
    risk: FinancialRiskOutput
    decision: LoanDecisionOutput


def _action_for(classification: str) -> tuple[str, str]:
    """Map a classification to (action, channel)."""
    if classification == "Approved":
        return ("Loan offer issued; disbursement workflow triggered.", "email")
    if classification == "Rejected":
        return ("Application rejected; adverse action notice queued.", "email")
    return ("Application routed to manual underwriter queue.", "in_app")


@app.post("/finalize", response_model=ComplianceOutput)
def finalize(req: ComplianceRequest) -> ComplianceOutput:
    aid = req.application.applicant_id

    case_obj = call_mcp_tool(MCP_NOTIFICATION_URL, "create_case_id", {"applicant_id": aid})
    case_id = case_obj.get("case_id") if isinstance(case_obj, dict) else f"CASE-{aid}"

    action, channel = _action_for(req.decision.classification.value)

    summary_default = (
        f"{req.decision.classification.value} for {aid}. Risk score {req.decision.risk_score}. "
        f"Top factors: {', '.join(req.decision.key_decision_factors[:3])}."
    )
    summary = summary_default
    if llm_available():
        llm_summary = generate_text(
            system=(
                "You are a compliance officer. Write a one-sentence neutral case summary "
                "suitable for an audit log. No marketing language, no speculation."
            ),
            user=(
                f"Decision: {req.decision.model_dump()}\n"
                f"Risk: {req.risk.model_dump()}\n"
                f"Profile: {req.profile.model_dump()}\n"
                f"Application: {req.application.model_dump(mode='json')}\n"
                f"Case ID: {case_id}\n"
                f"Action: {action}"
            ),
            max_tokens=160,
        )
        if llm_summary:
            summary = llm_summary

    customer_message = (
        f"Dear applicant {aid}, your loan application (case {case_id}) has been processed. "
        f"Outcome: {req.decision.classification.value}. {req.decision.explanation}"
    )

    notif = call_mcp_tool(
        MCP_NOTIFICATION_URL,
        "send_notification",
        {"applicant_id": aid, "channel": channel, "message": customer_message},
    )
    notification_sent = bool(notif.get("status") == "SENT") if isinstance(notif, dict) else False

    call_mcp_tool(
        MCP_NOTIFICATION_URL,
        "log_compliance_action",
        {
            "applicant_id": aid,
            "classification": req.decision.classification.value,
            "action": action,
            "summary": summary,
            "case_id": case_id,
        },
    )

    return ComplianceOutput(
        applicant_id=aid,
        action_taken=action,
        notification_sent=notification_sent,
        case_id=case_id,
        timestamp=datetime.utcnow(),
        summary=summary,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "compliance", "mcp": MCP_NOTIFICATION_URL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=AGENT_COMPLIANCE_PORT)
