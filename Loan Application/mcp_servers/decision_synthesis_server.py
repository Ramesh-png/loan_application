"""DecisionSynthesis MCP Server — combines profile + risk signals into a recommendation.

Tools:
  - synthesize_decision(...): bundled recommendation used as LLM grounding
  - compute_risk_score(...): numeric 0..100 risk score
  - recommend_classification(...): heuristic mapping of score+flags to label
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastmcp import FastMCP  # type: ignore
from config import MCP_DECISION_SYNTH_PORT, HOST

mcp = FastMCP(name="DecisionSynthesis")


def _risk_score(
    credit_default_probability: float,
    dti: float,
    income_stability: float,
    anomaly_count: int,
    employment_risk_level: str,
) -> float:
    employment_weight = {
        "Low": 0.0,
        "Medium": 0.5,
        "High": 1.0,
        "Critical": 1.0,
    }.get(employment_risk_level, 0.5)
    score = (
        45 * max(0.0, min(1.0, credit_default_probability))
        + 25 * max(0.0, min(1.0, dti))
        + 15 * max(0.0, min(1.0, 1.0 - income_stability))
        + 10 * employment_weight
        + 5 * min(1.0, anomaly_count / 3.0)
    )
    return round(max(0.0, min(100.0, score)), 2)


def _classify(risk_score: float, anomalies: List[str], hard_policy_violations: List[str]) -> Dict[str, Any]:
    if hard_policy_violations:
        return {
            "classification": "Rejected",
            "confidence": 0.95,
            "rationale": "Hard policy violations: " + "; ".join(hard_policy_violations),
        }
    if risk_score < 30 and not anomalies:
        return {
            "classification": "Approved",
            "confidence": 0.9,
            "rationale": "Low risk score and no anomalies.",
        }
    if risk_score > 70:
        return {
            "classification": "Rejected",
            "confidence": 0.85,
            "rationale": f"High risk score ({risk_score}).",
        }
    return {
        "classification": "Requires Manual Review",
        "confidence": 0.6,
        "rationale": (
            f"Borderline risk score ({risk_score})"
            + (f" with anomalies: {anomalies}" if anomalies else "")
            + " — requires human underwriter."
        ),
    }


@mcp.tool
def compute_risk_score(
    credit_default_probability: float,
    dti: float,
    income_stability: float,
    anomaly_count: int,
    employment_risk_level: str,
) -> Dict[str, Any]:
    """Combine signals into a 0..100 risk score (higher = riskier)."""
    return {
        "risk_score": _risk_score(
            credit_default_probability,
            dti,
            income_stability,
            anomaly_count,
            employment_risk_level,
        )
    }


@mcp.tool
def recommend_classification(
    risk_score: float,
    anomalies: List[str],
    hard_policy_violations: List[str],
) -> Dict[str, Any]:
    """Map a risk score and policy signals to Approve / Reject / Review."""
    return _classify(risk_score, anomalies, hard_policy_violations)


@mcp.tool
def synthesize_decision(
    applicant_id: str,
    income_stability_score: float,
    employment_risk: str,
    credit_default_probability: float,
    dti: float,
    anomalies: List[str],
    hard_policy_violations: List[str],
) -> Dict[str, Any]:
    """One-shot helper that bundles risk score + classification + key factors."""
    score = _risk_score(
        credit_default_probability=credit_default_probability,
        dti=dti,
        income_stability=income_stability_score,
        anomaly_count=len(anomalies),
        employment_risk_level=employment_risk,
    )
    cls_obj = _classify(score, anomalies, hard_policy_violations)
    key_factors: List[str] = []
    if credit_default_probability >= 0.2:
        key_factors.append("Elevated credit default probability")
    if dti >= 0.45:
        key_factors.append("High debt-to-income ratio")
    if income_stability_score < 0.5:
        key_factors.append("Unstable income pattern")
    if employment_risk in ("High", "Critical"):
        key_factors.append(f"Employment risk: {employment_risk}")
    if anomalies:
        key_factors.append(f"{len(anomalies)} anomaly signal(s) detected")
    if hard_policy_violations:
        key_factors.append("Hard policy violation(s)")
    if not key_factors:
        key_factors.append("All risk signals within acceptable thresholds")
    return {
        "applicant_id": applicant_id,
        "risk_score": score,
        "classification": cls_obj["classification"],
        "confidence": cls_obj["confidence"],
        "rationale": cls_obj["rationale"],
        "key_decision_factors": key_factors,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=MCP_DECISION_SYNTH_PORT)
