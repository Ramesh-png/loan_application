"""Public-facing FastAPI microservice.

Endpoints:
  POST /loan/apply           -> submit a loan application, runs full pipeline
  GET  /loan/cases           -> recent compliance cases (audit display)
  GET  /loan/applicants      -> known applicant IDs (demo helper)
  GET  /health               -> liveness probe
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.mcp_client import call_mcp_tool
from config import (
    HOST,
    MCP_APPLICANT_DB_URL,
    MCP_NOTIFICATION_URL,
    MICROSERVICE_PORT,
)
from models.schemas import LoanApplication, LoanDecisionResponse
from orchestrator.graph import run_pipeline

app = FastAPI(
    title="Loan Approval Microservice",
    description="Front door for the Multi-Agent Agentic AI Loan Approval System.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/loan/apply", response_model=LoanDecisionResponse)
def apply_for_loan(application: LoanApplication) -> LoanDecisionResponse:
    """Submit a loan application and receive a final decision + audit trail.

    New applicants are upserted into the ApplicantDB so they appear in the
    existing-customer dropdown on subsequent visits. The upsert is idempotent —
    existing applicants are left untouched.
    """
    try:
        call_mcp_tool(
            MCP_APPLICANT_DB_URL,
            "register_applicant",
            {
                "applicant_id": application.applicant_id,
                "full_name": application.full_name or "",
                "age": application.age,
                "employment_type": application.employment_type.value,
                "employer": "",
                "annual_income": application.income,
                "location": application.location,
            },
        )
        return run_pipeline(application)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failure: {e}")


@app.get("/loan/cases")
def list_recent_cases(limit: int = 20) -> Dict[str, Any]:
    """Recent compliance/audit cases from the NotificationSystem MCP."""
    return call_mcp_tool(MCP_NOTIFICATION_URL, "list_recent_cases", {"limit": limit})


@app.get("/loan/applicants")
def list_applicants() -> Dict[str, Any]:
    """Known applicant IDs (demo helper from ApplicantDB MCP)."""
    return call_mcp_tool(MCP_APPLICANT_DB_URL, "list_applicants", {})


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "loan_microservice"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=MICROSERVICE_PORT)
