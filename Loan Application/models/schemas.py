"""Pydantic schemas shared across microservice, orchestrator, agents, and MCP servers."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EmploymentType(str, Enum):
    SALARIED = "Salaried"
    SELF_EMPLOYED = "Self-Employed"
    BUSINESS = "Business"
    UNEMPLOYED = "Unemployed"
    RETIRED = "Retired"
    STUDENT = "Student"


class LoanApplication(BaseModel):
    applicant_id: str = Field(..., description="Unique applicant identifier")
    age: int = Field(..., ge=18, le=100)
    income: float = Field(..., ge=0, description="Annual income in INR")
    employment_type: EmploymentType
    credit_score: int = Field(..., ge=300, le=900)
    loan_amount: float = Field(..., ge=0)
    loan_tenure_months: int = Field(..., ge=1, le=480)
    existing_liabilities: float = Field(0.0, ge=0)
    location: str
    application_timestamp: datetime = Field(default_factory=datetime.utcnow)
    full_name: Optional[str] = Field(None, description="Applicant's full name (optional)")


class ApplicantProfileOutput(BaseModel):
    applicant_id: str
    income_stability_score: float = Field(..., ge=0, le=1)
    employment_risk: str
    credit_history_summary: str
    application_completeness_flags: List[str]
    reasoning: str


class FinancialRiskOutput(BaseModel):
    applicant_id: str
    debt_to_income_ratio: float
    credit_score_risk_level: str
    loan_amount_risk: str
    anomaly_detected: bool
    anomaly_reasons: List[str]
    reasoning: str


class Classification(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    REVIEW = "Requires Manual Review"


class LoanDecisionOutput(BaseModel):
    applicant_id: str
    classification: Classification
    risk_score: float = Field(..., ge=0, le=100)
    confidence_level: float = Field(..., ge=0, le=1)
    key_decision_factors: List[str]
    explanation: str


class ComplianceOutput(BaseModel):
    applicant_id: str
    action_taken: str
    notification_sent: bool
    case_id: str
    timestamp: datetime
    summary: str


class LoanDecisionResponse(BaseModel):
    """Full pipeline response returned to the UI."""
    applicant_id: str
    application: LoanApplication
    profile: ApplicantProfileOutput
    risk: FinancialRiskOutput
    decision: LoanDecisionOutput
    compliance: ComplianceOutput
    audit_trail: List[Dict[str, Any]]
