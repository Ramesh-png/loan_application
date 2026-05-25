"""LangGraph-based orchestration engine for the Loan Approval pipeline.

Graph topology:

  START
    -> applicant_profile_node
    -> financial_risk_node
    -> loan_decision_node
    -> route_on_classification
         |-- approved      -> compliance_node -> END
         |-- rejected      -> compliance_node -> END
         |-- needs_review  -> compliance_node -> END

Decision routing uses a conditional edge so the graph topology is faithful to
the case study (decision drives downstream action) even though all branches
currently fan into the same compliance node — keeping the routing logic
explicit makes it trivial to extend (e.g., human-in-the-loop branch).

Each node calls the corresponding FastAPI agent over HTTP, so agents are
truly independent microservices.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

import httpx
from langgraph.graph import END, START, StateGraph

from config import (
    AGENT_COMPLIANCE_URL,
    AGENT_DECISION_URL,
    AGENT_PROFILE_URL,
    AGENT_RISK_URL,
)
from models.schemas import (
    ApplicantProfileOutput,
    ComplianceOutput,
    FinancialRiskOutput,
    LoanApplication,
    LoanDecisionOutput,
    LoanDecisionResponse,
)


class LoanState(TypedDict, total=False):
    application: Dict[str, Any]
    profile: Dict[str, Any]
    risk: Dict[str, Any]
    decision: Dict[str, Any]
    compliance: Dict[str, Any]
    audit_trail: List[Dict[str, Any]]


def _audit(state: LoanState, step: str, payload: Any) -> None:
    state.setdefault("audit_trail", []).append(
        {"step": step, "timestamp": datetime.utcnow().isoformat(), "payload": payload}
    )


def _post(url: str, json_body: Dict[str, Any], timeout: float = 90.0) -> Dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=json_body)
        r.raise_for_status()
        return r.json()


def applicant_profile_node(state: LoanState) -> LoanState:
    payload = _post(f"{AGENT_PROFILE_URL}/analyze", state["application"])
    _audit(state, "applicant_profile_agent", payload)
    state["profile"] = payload
    return state


def financial_risk_node(state: LoanState) -> LoanState:
    payload = _post(f"{AGENT_RISK_URL}/analyze", state["application"])
    _audit(state, "financial_risk_agent", payload)
    state["risk"] = payload
    return state


def loan_decision_node(state: LoanState) -> LoanState:
    body = {
        "application": state["application"],
        "profile": state["profile"],
        "risk": state["risk"],
    }
    payload = _post(f"{AGENT_DECISION_URL}/decide", body)
    _audit(state, "loan_decision_agent", payload)
    state["decision"] = payload
    return state


def compliance_node(state: LoanState) -> LoanState:
    body = {
        "application": state["application"],
        "profile": state["profile"],
        "risk": state["risk"],
        "decision": state["decision"],
    }
    payload = _post(f"{AGENT_COMPLIANCE_URL}/finalize", body)
    _audit(state, "compliance_agent", payload)
    state["compliance"] = payload
    return state


def route_on_classification(state: LoanState) -> str:
    """Conditional edge — routes based on the Loan Decision Agent's classification."""
    cls = state.get("decision", {}).get("classification", "Requires Manual Review")
    if cls == "Approved":
        return "approved_branch"
    if cls == "Rejected":
        return "rejected_branch"
    return "review_branch"


def build_graph():
    g = StateGraph(LoanState)
    g.add_node("applicant_profile", applicant_profile_node)
    g.add_node("financial_risk", financial_risk_node)
    g.add_node("loan_decision", loan_decision_node)
    g.add_node("compliance", compliance_node)

    g.add_edge(START, "applicant_profile")
    g.add_edge("applicant_profile", "financial_risk")
    g.add_edge("financial_risk", "loan_decision")

    g.add_conditional_edges(
        "loan_decision",
        route_on_classification,
        {
            "approved_branch": "compliance",
            "rejected_branch": "compliance",
            "review_branch": "compliance",
        },
    )
    g.add_edge("compliance", END)
    return g.compile()


_compiled = None


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def run_pipeline(application: LoanApplication) -> LoanDecisionResponse:
    graph = get_graph()
    initial: LoanState = {"application": application.model_dump(mode="json"), "audit_trail": []}
    final = graph.invoke(initial)

    return LoanDecisionResponse(
        applicant_id=application.applicant_id,
        application=application,
        profile=ApplicantProfileOutput(**final["profile"]),
        risk=FinancialRiskOutput(**final["risk"]),
        decision=LoanDecisionOutput(**final["decision"]),
        compliance=ComplianceOutput(**final["compliance"]),
        audit_trail=final.get("audit_trail", []),
    )
