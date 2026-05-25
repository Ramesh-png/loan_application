"""Modern banking-style Streamlit UI for the Loan Approval Multi-Agent System."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
import streamlit as st

from config import MICROSERVICE_URL

st.set_page_config(
    page_title="State Bank — Smart Loan Approval",
    page_icon=":bank:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

/* Hide default streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* Hero header */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #4338ca 100%);
    padding: 2.2rem 2.5rem;
    border-radius: 22px;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 25px 50px -12px rgba(30, 58, 138, 0.45);
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; right: -60px; top: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(255,255,255,0.12), transparent 70%);
    border-radius: 50%;
}
.hero h1 {
    font-size: 2.25rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.02em;
}
.hero p {
    margin: 0.4rem 0 0;
    opacity: 0.9;
    font-size: 1.02rem;
    font-weight: 400;
}
.hero .brand-tag {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
    backdrop-filter: blur(8px);
}

/* Section card */
.card {
    background: white;
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 8px 24px rgba(15, 23, 42, 0.06);
    border: 1px solid #e5e7eb;
    margin-bottom: 1.1rem;
}
.card-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: #4338ca;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.25rem;
}
.card-heading {
    font-size: 1.25rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 1rem;
}

/* Stat badges */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.9rem;
    margin: 1rem 0;
}
.stat {
    background: linear-gradient(135deg, #f8fafc, #ffffff);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1rem 1.2rem;
}
.stat .label {
    font-size: 0.72rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}
.stat .value {
    font-size: 1.55rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.1;
}
.stat .sub {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 2px;
}

/* Decision banner */
.decision-banner {
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    color: white;
    display: flex;
    align-items: center;
    gap: 1.2rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 18px 40px -10px rgba(0,0,0,0.18);
}
.decision-banner.approved   { background: linear-gradient(135deg, #047857, #10b981); }
.decision-banner.rejected   { background: linear-gradient(135deg, #991b1b, #ef4444); }
.decision-banner.review     { background: linear-gradient(135deg, #b45309, #f59e0b); }
.decision-icon {
    width: 60px; height: 60px;
    border-radius: 50%;
    background: rgba(255,255,255,0.22);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem;
    font-weight: 800;
    backdrop-filter: blur(6px);
    flex-shrink: 0;
}
.decision-title {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    opacity: 0.85;
    margin-bottom: 4px;
    font-weight: 600;
}
.decision-value {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.01em;
}
.decision-sub {
    font-size: 0.92rem;
    opacity: 0.9;
    margin-top: 4px;
}

/* Pipeline */
.pipeline {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    align-items: center;
    padding: 0.4rem 0 0.6rem;
}
.pipeline-step {
    flex: 1 1 200px;
    background: linear-gradient(135deg, #eef2ff, #ffffff);
    border: 1px solid #c7d2fe;
    padding: 0.85rem 1rem;
    border-radius: 12px;
    position: relative;
}
.pipeline-step .num {
    display: inline-block;
    width: 26px; height: 26px;
    border-radius: 50%;
    background: #4338ca;
    color: white;
    font-weight: 700;
    text-align: center;
    line-height: 26px;
    font-size: 0.82rem;
    margin-right: 8px;
}
.pipeline-step .name {
    font-weight: 700;
    color: #1e1b4b;
    font-size: 0.92rem;
}
.pipeline-step .mcp {
    font-size: 0.72rem;
    color: #6366f1;
    margin-top: 4px;
    font-weight: 500;
    letter-spacing: 0.02em;
}

/* Explanation box */
.explanation {
    background: linear-gradient(135deg, #fefce8, #ffffff);
    border-left: 4px solid #f59e0b;
    padding: 1.1rem 1.4rem;
    border-radius: 10px;
    color: #1f2937;
    line-height: 1.6;
    font-size: 0.97rem;
    white-space: pre-wrap;
}

/* Factor pills */
.factor-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 0.4rem; }
.factor {
    background: #eef2ff;
    color: #3730a3;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 500;
    border: 1px solid #c7d2fe;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4338ca, #6366f1);
    color: white;
    border: 0;
    padding: 0.7rem 1.4rem;
    border-radius: 10px;
    font-weight: 600;
    font-size: 1rem;
    letter-spacing: 0.01em;
    box-shadow: 0 10px 20px -8px rgba(67, 56, 202, 0.5);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 15px 25px -8px rgba(67, 56, 202, 0.6);
    background: linear-gradient(135deg, #3730a3, #4f46e5);
    color: white;
}
.stButton > button:focus:not(:active) {
    border-color: #4338ca;
    color: white;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: #f1f5f9;
    padding: 6px;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    color: #475569;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #4338ca !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}

/* Input fields */
.stTextInput input, .stNumberInput input, .stSelectbox > div > div {
    border-radius: 10px !important;
    border-color: #e2e8f0 !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}

/* Form section divider */
.form-section-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: #4338ca;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 1.2rem 0 0.4rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #eef2ff;
}

/* Customer-facing chat */
.bot-message {
    background: linear-gradient(135deg, #f8fafc, #ffffff);
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    color: #1f2937;
}

/* Status timeline */
.case-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.9rem 1rem;
    border-bottom: 1px solid #f1f5f9;
}
.case-row:last-child { border-bottom: 0; }
.case-id { font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: #4338ca; font-weight: 600; }
.case-badge {
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.case-badge.approved { background: #d1fae5; color: #065f46; }
.case-badge.rejected { background: #fee2e2; color: #991b1b; }
.case-badge.review   { background: #fef3c7; color: #92400e; }

/* Misc */
hr { margin: 1.5rem 0; border: 0; border-top: 1px solid #e5e7eb; }

/* Custom progress bars */
.metric-block { margin: 0.75rem 0 1.1rem; }
.metric-row {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 6px;
}
.metric-row .metric-name {
    font-size: 0.82rem; color: #475569; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em;
}
.metric-row .metric-val {
    font-size: 1rem; color: #0f172a; font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.metric-row .metric-val .sub {
    font-size: 0.78rem; color: #94a3b8; font-weight: 500; margin-left: 4px;
}
.bar {
    width: 100%; height: 10px;
    background: #f1f5f9;
    border-radius: 999px;
    overflow: hidden;
    position: relative;
}
.bar-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.5s ease;
}
.bar-fill.green   { background: linear-gradient(90deg, #10b981, #34d399); }
.bar-fill.yellow  { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.bar-fill.red     { background: linear-gradient(90deg, #ef4444, #f87171); }
.bar-fill.blue    { background: linear-gradient(90deg, #4338ca, #6366f1); }
.bar-fill.teal    { background: linear-gradient(90deg, #0891b2, #06b6d4); }

.metric-caption {
    font-size: 0.76rem; color: #94a3b8; margin-top: 4px;
}

/* Streamlit st.metric override */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8fafc, #ffffff);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 0.9rem 1.1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
div[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem !important;
}
div[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-weight: 700 !important;
}

/* Agent result card */
.agent-card {
    background: linear-gradient(135deg, #ffffff, #f8fafc);
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    height: 100%;
}
.agent-card .agent-num {
    display: inline-block;
    width: 28px; height: 28px; line-height: 28px;
    border-radius: 8px;
    background: linear-gradient(135deg, #4338ca, #6366f1);
    color: white; text-align: center;
    font-weight: 700; font-size: 0.85rem;
    margin-right: 10px;
}
.agent-card .agent-name {
    font-size: 1.02rem; font-weight: 700; color: #0f172a;
}
.agent-card .agent-mcp {
    font-size: 0.74rem; color: #6366f1; font-weight: 600;
    margin-top: 2px; margin-left: 38px;
    letter-spacing: 0.04em; text-transform: uppercase;
}
.agent-summary {
    color: #475569; font-size: 0.88rem; line-height: 1.5;
    margin: 0.7rem 0 0.4rem;
}

/* Status badges (inline) */
.status-chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.status-chip.green  { background: #d1fae5; color: #065f46; }
.status-chip.yellow { background: #fef3c7; color: #92400e; }
.status-chip.red    { background: #fee2e2; color: #991b1b; }
.status-chip.blue   { background: #dbeafe; color: #1e40af; }
.status-chip.gray   { background: #f1f5f9; color: #475569; }

/* Timeline */
.timeline { position: relative; padding-left: 28px; }
.timeline::before {
    content: ''; position: absolute; left: 11px; top: 8px; bottom: 8px;
    width: 2px; background: linear-gradient(to bottom, #4338ca, #06b6d4, #10b981);
    border-radius: 2px;
}
.timeline-item { position: relative; padding: 6px 0 18px; }
.timeline-item::before {
    content: ''; position: absolute; left: -22px; top: 10px;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: white;
    border: 3px solid #4338ca;
    box-shadow: 0 0 0 3px rgba(67, 56, 202, 0.15);
}
.timeline-item .ti-title { font-weight: 700; color: #0f172a; font-size: 0.92rem; }
.timeline-item .ti-time  { font-size: 0.76rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ────────────────────────────────────────────────────────────
if "last_decision" not in st.session_state:
    st.session_state.last_decision = None
if "submitted_count" not in st.session_state:
    st.session_state.submitted_count = 0


# ── Helpers ──────────────────────────────────────────────────────────────────
def fetch_existing_ids() -> List[str]:
    try:
        r = httpx.get(f"{MICROSERVICE_URL}/loan/applicants", timeout=8)
        return r.json().get("applicant_ids", []) if r.status_code == 200 else []
    except Exception:
        return []


def next_applicant_id(existing: List[str], session_count: int) -> str:
    """Auto-generate the next applicant ID based on the existing IDs.

    Finds the common alpha prefix + max numeric suffix and increments.
    Falls back to 'APP1001' if no IDs exist yet. Also advances past any
    IDs already submitted in this session so two new applicants in a row
    don't collide.
    """
    import re

    max_num = 1000
    prefix = "APP"
    for aid in existing:
        m = re.match(r"^([A-Za-z]+)(\d+)$", aid.strip())
        if not m:
            continue
        p, n = m.group(1), int(m.group(2))
        if n > max_num:
            max_num = n
            prefix = p
    return f"{prefix}{max_num + 1 + session_count}"


def submit_application(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = httpx.post(f"{MICROSERVICE_URL}/loan/apply", json=payload, timeout=180)
    r.raise_for_status()
    return r.json()


def fetch_cases(limit: int = 20) -> List[Dict[str, Any]]:
    try:
        r = httpx.get(f"{MICROSERVICE_URL}/loan/cases", params={"limit": limit}, timeout=8)
        return r.json().get("cases", []) if r.status_code == 200 else []
    except Exception:
        return []


def classification_class(cls: str) -> str:
    if cls == "Approved":
        return "approved"
    if cls == "Rejected":
        return "rejected"
    return "review"


def classification_icon(cls: str) -> str:
    return {"Approved": "OK", "Rejected": "NO", "Requires Manual Review": "REV"}.get(cls, "?")


def classification_sub(cls: str) -> str:
    return {
        "Approved": "Your loan has been approved and the offer is being prepared.",
        "Rejected": "Unfortunately we could not approve this application.",
        "Requires Manual Review": "An underwriter will review your application shortly.",
    }.get(cls, "")


def progress_bar(label: str, value_pct: float, color: str, value_label: str, caption: str = "") -> str:
    """Render a labeled progress bar as HTML."""
    value_pct = max(0.0, min(100.0, value_pct))
    cap = f'<div class="metric-caption">{caption}</div>' if caption else ""
    return (
        f'<div class="metric-block">'
        f'<div class="metric-row"><span class="metric-name">{label}</span>'
        f'<span class="metric-val">{value_label}</span></div>'
        f'<div class="bar"><div class="bar-fill {color}" style="width:{value_pct}%;"></div></div>'
        f'{cap}</div>'
    )


def risk_color(score: float) -> str:
    if score < 30: return "green"
    if score < 60: return "yellow"
    return "red"


def dti_color(dti: float) -> str:
    if dti <= 0.36: return "green"
    if dti <= 0.45: return "yellow"
    return "red"


def stability_color(s: float) -> str:
    if s >= 0.75: return "green"
    if s >= 0.5: return "yellow"
    return "red"


def employment_risk_chip(level: str) -> str:
    color = {"Low": "green", "Medium": "yellow", "High": "red", "Critical": "red"}.get(level, "gray")
    return f'<span class="status-chip {color}">{level}</span>'


def credit_band_chip(band: str) -> str:
    color = {
        "Excellent": "green", "Good": "green",
        "Fair": "yellow", "Poor": "red", "Very Poor": "red",
    }.get(band, "gray")
    return f'<span class="status-chip {color}">{band}</span>'


def loan_risk_chip(level: str) -> str:
    color = {"Low": "green", "Moderate": "yellow", "High": "red", "Critical": "red"}.get(level, "gray")
    return f'<span class="status-chip {color}">{level}</span>'


# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
    <span class="brand-tag">State Bank &nbsp;·&nbsp; Agentic AI Platform</span>
    <h1>Smart Loan Approval, in seconds.</h1>
    <p>Powered by a multi-agent AI system that evaluates your profile, risk, and compliance — instantly and transparently.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_apply, tab_status, tab_about = st.tabs(["Apply for a Loan", "Track Applications", "How it Works"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — APPLY
# ════════════════════════════════════════════════════════════════════════════
with tab_apply:
    left, right = st.columns([1.25, 1], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Loan Application</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-heading">Tell us about yourself</div>',
            unsafe_allow_html=True,
        )

        customer_type = st.radio(
            "Are you an existing State Bank customer?",
            ["Existing customer", "New applicant"],
            horizontal=True,
            index=0,
            help="New applicants will be flagged for additional KYC verification.",
        )

        existing_ids = fetch_existing_ids()

        with st.form("loan_form", clear_on_submit=False):
            st.markdown('<div class="form-section-title">Identity</div>', unsafe_allow_html=True)
            if customer_type == "Existing customer":
                col_id1, col_id2 = st.columns([1, 1])
                with col_id1:
                    applicant_id = st.selectbox(
                        "Customer ID",
                        options=existing_ids or ["APP1001"],
                        help="Your unique customer reference.",
                    )
                with col_id2:
                    full_name = st.text_input("Full name (optional)", value="")
            else:
                auto_id = next_applicant_id(existing_ids, st.session_state.submitted_count)
                col_id1, col_id2 = st.columns([1, 1])
                with col_id1:
                    st.text_input(
                        "Applicant ID (auto-generated)",
                        value=auto_id,
                        disabled=True,
                        help="We've assigned you this unique ID — no need to remember it. It will appear on your confirmation.",
                    )
                    applicant_id = auto_id
                with col_id2:
                    full_name = st.text_input("Full name", value="")
                st.caption(
                    f"This ID was generated based on {len(existing_ids)} existing customer(s). "
                    "Quote it when contacting support."
                )

            st.markdown('<div class="form-section-title">Personal Details</div>', unsafe_allow_html=True)
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                age = st.number_input("Age", min_value=18, max_value=100, value=32)
            with col_p2:
                location = st.text_input("City / Location", value="Bengaluru")
            with col_p3:
                employment_type = st.selectbox(
                    "Employment type",
                    ["Salaried", "Self-Employed", "Business", "Unemployed", "Retired", "Student"],
                )

            st.markdown('<div class="form-section-title">Financial Profile</div>', unsafe_allow_html=True)
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                income = st.number_input(
                    "Annual income (INR)",
                    min_value=0.0,
                    value=1_080_000.0,
                    step=10_000.0,
                    format="%.0f",
                )
            with col_f2:
                credit_score = st.number_input(
                    "Credit score (300–900)",
                    min_value=300,
                    max_value=900,
                    value=760,
                )
            with col_f3:
                liabilities = st.number_input(
                    "Monthly liabilities (INR)",
                    min_value=0.0,
                    value=5_000.0,
                    step=1_000.0,
                    format="%.0f",
                )

            st.markdown('<div class="form-section-title">Loan Requirements</div>', unsafe_allow_html=True)
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                loan_amount = st.number_input(
                    "Loan amount (INR)",
                    min_value=10_000.0,
                    value=500_000.0,
                    step=10_000.0,
                    format="%.0f",
                )
            with col_l2:
                tenure = st.number_input(
                    "Tenure (months)",
                    min_value=1,
                    max_value=480,
                    value=60,
                )

            st.markdown(" ")
            submitted = st.form_submit_button(
                "Submit Application",
                use_container_width=True,
                type="primary",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Why State?</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Instant. Transparent. Fair.</div>', unsafe_allow_html=True)
        st.markdown(
            """
- **Decisions in under a minute** — no waiting in branch queues.
- **Explainable AI** — see exactly why your application was approved, rejected, or sent for review.
- **Four specialist agents** evaluate your profile, financial risk, decision logic, and compliance independently.
- **Bank-grade audit trail** — every step is logged and traceable.
- **No credit-score penalty** — we do a soft check during evaluation.
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

      #  st.markdown('<div class="card">', unsafe_allow_html=True)
      #  st.markdown('<div class="card-title">Live System Status</div>', unsafe_allow_html=True)
      #  try:
       #     health = httpx.get(f"{MICROSERVICE_URL}/health", timeout=4).json()
      #      st.success(f"Loan engine online · `{health.get('service')}`")
      #  except Exception:
       #     st.error("Loan engine offline — please run ./run_all.sh")
      #  st.caption(f"Microservice: {MICROSERVICE_URL}")
      #  st.markdown("</div>", unsafe_allow_html=True)

    # ─── Handle submission ───────────────────────────────────────────────────
    if submitted:
        was_new_applicant = customer_type == "New applicant"
        payload = {
            "applicant_id": applicant_id.strip() or "UNKNOWN",
            "age": int(age),
            "income": float(income),
            "employment_type": employment_type,
            "credit_score": int(credit_score),
            "loan_amount": float(loan_amount),
            "loan_tenure_months": int(tenure),
            "existing_liabilities": float(liabilities),
            "location": location.strip() or "Unknown",
            "application_timestamp": datetime.utcnow().isoformat(),
            "full_name": full_name.strip() or None,
        }
        with st.spinner("Our AI agents are reviewing your application..."):
            try:
                result = submit_application(payload)
                st.session_state.last_decision = result
                st.session_state.submitted_count += 1
                if was_new_applicant:
                    st.toast(
                        f"Welcome to State Bank! Your customer ID {payload['applicant_id']} is now active.",
                        icon=":material/check_circle:",
                    )
                    # Force a fresh fetch of the applicant list on next render
                    st.rerun()
            except httpx.HTTPError as e:
                st.error(f"Pipeline error: {e}")

    # ─── Decision display ────────────────────────────────────────────────────
    if st.session_state.last_decision:
        result = st.session_state.last_decision
        decision = result["decision"]
        compliance = result["compliance"]
        profile = result["profile"]
        risk = result["risk"]

        cls = decision["classification"]
        cls_class = classification_class(cls)

        st.markdown(
            f"""
<div class="decision-banner {cls_class}">
    <div class="decision-icon">{classification_icon(cls)}</div>
    <div>
        <div class="decision-title">Decision</div>
        <div class="decision-value">{cls}</div>
        <div class="decision-sub">{classification_sub(cls)}</div>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # ── Key metrics (Streamlit native + custom) ──────────────────────
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                "Risk Score",
                f"{decision['risk_score']}",
                delta=f"{'Low' if decision['risk_score']<30 else 'High' if decision['risk_score']>60 else 'Moderate'} risk",
                delta_color=(
                    "normal" if decision['risk_score'] < 30
                    else "off" if decision['risk_score'] < 60
                    else "inverse"
                ),
                help="0 = safest, 100 = riskiest",
            )
        with m2:
            st.metric(
                "Confidence",
                f"{decision['confidence_level']*100:.0f}%",
                delta="AI underwriter",
                delta_color="off",
                help="How confident the AI is in this decision",
            )
        with m3:
            st.metric(
                "Case ID",
                compliance['case_id'].replace("CASE-", ""),
                delta="Compliance reference",
                delta_color="off",
            )
        with m4:
            st.metric(
                "AI Agents Run",
                f"{len(result.get('audit_trail', []))}",
                delta="of 4 specialists",
                delta_color="off",
            )

        # ── Headline progress bars (Risk + Confidence) ───────────────────
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Decision Confidence & Risk</div>', unsafe_allow_html=True)
        col_pb1, col_pb2 = st.columns(2)
        with col_pb1:
            st.markdown(
                progress_bar(
                    "Overall Risk Score",
                    decision['risk_score'],
                    risk_color(decision['risk_score']),
                    f"{decision['risk_score']} / 100",
                    "Lower is safer. <30 strong, 30-60 borderline, >60 high risk.",
                ),
                unsafe_allow_html=True,
            )
        with col_pb2:
            st.markdown(
                progress_bar(
                    "AI Confidence",
                    decision['confidence_level'] * 100,
                    "blue",
                    f"{decision['confidence_level']*100:.0f}%",
                    "Higher = stronger evidence for this classification.",
                ),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Customer-facing explanation ──────────────────────────────────
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">What this means for you</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="explanation">{decision["explanation"]}</div>',
            unsafe_allow_html=True,
        )
        if decision.get("key_decision_factors"):
            st.markdown(
                '<div style="margin-top:1rem;font-weight:600;color:#475569;font-size:0.88rem;">Key factors considered</div>',
                unsafe_allow_html=True,
            )
            pills = "".join(f'<span class="factor">{f}</span>' for f in decision["key_decision_factors"])
            st.markdown(f'<div class="factor-list">{pills}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Pipeline visualization ───────────────────────────────────────
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Multi-Agent Pipeline</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-heading">Each step is handled by a specialist AI agent</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
<div class="pipeline">
    <div class="pipeline-step"><span class="num">1</span><span class="name">Applicant Profile</span><div class="mcp">MCP · ApplicantDB</div></div>
    <div class="pipeline-step"><span class="num">2</span><span class="name">Financial Risk</span><div class="mcp">MCP · RiskRulesDB</div></div>
    <div class="pipeline-step"><span class="num">3</span><span class="name">Loan Decision</span><div class="mcp">MCP · DecisionSynthesis</div></div>
    <div class="pipeline-step"><span class="num">4</span><span class="name">Compliance &amp; Action</span><div class="mcp">MCP · NotificationSystem</div></div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Visual per-agent breakdown (2x2 grid) ────────────────────────
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Agent Outputs · Explainable AI</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-heading">What each AI specialist found</div>',
            unsafe_allow_html=True,
        )

        col_a, col_b = st.columns(2, gap="medium")

        # AGENT 1 — Applicant Profile
        with col_a:
            stability = profile.get("income_stability_score", 0.0)
            flags = profile.get("application_completeness_flags", []) or []
            flag_chips = (
                "".join(
                    f'<span class="status-chip red" style="margin-right:6px;">{f}</span>'
                    for f in flags
                )
                if flags
                else '<span class="status-chip green">All checks passed</span>'
            )
            st.markdown(
                f"""
<div class="agent-card">
    <div><span class="agent-num">1</span><span class="agent-name">Applicant Profile</span></div>
    <div class="agent-mcp">MCP · ApplicantDB</div>
    <div class="agent-summary">{profile.get('credit_history_summary','')}</div>
    {progress_bar(
        "Income Stability",
        stability * 100,
        stability_color(stability),
        f"{stability:.2f}",
        "How consistent the applicant's monthly income is."
    )}
    <div class="metric-row" style="margin-top:0.6rem;">
        <span class="metric-name">Employment Risk</span>
        <span class="metric-val">{employment_risk_chip(profile.get('employment_risk','Unknown'))}</span>
    </div>
    <div style="margin-top:0.6rem;font-size:0.8rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Completeness</div>
    <div style="margin-top:6px;">{flag_chips}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Full reasoning & raw payload", expanded=False):
                st.markdown(profile.get("reasoning", ""))
                st.json(profile)

        # AGENT 2 — Financial Risk
        with col_b:
            dti = risk.get("debt_to_income_ratio", 0.0)
            anomaly_chips = (
                "".join(
                    f'<span class="status-chip red" style="margin-right:6px;margin-bottom:4px;display:inline-block;">{a}</span>'
                    for a in risk.get("anomaly_reasons", [])
                )
                if risk.get("anomaly_detected")
                else '<span class="status-chip green">No anomalies</span>'
            )
            st.markdown(
                f"""
<div class="agent-card">
    <div><span class="agent-num">2</span><span class="agent-name">Financial Risk Analysis</span></div>
    <div class="agent-mcp">MCP · RiskRulesDB</div>
    <div class="agent-summary">Debt-to-income, credit band, and loan-amount sizing.</div>
    {progress_bar(
        "Debt-to-Income Ratio",
        min(dti * 100, 100),
        dti_color(dti),
        f"{dti*100:.1f}%",
        "Safe ≤ 36% · Moderate ≤ 45% · High ≤ 55% · Critical above."
    )}
    <div class="metric-row" style="margin-top:0.6rem;">
        <span class="metric-name">Credit Band</span>
        <span class="metric-val">{credit_band_chip(risk.get('credit_score_risk_level','Unknown'))}</span>
    </div>
    <div class="metric-row" style="margin-top:0.4rem;">
        <span class="metric-name">Loan Amount Risk</span>
        <span class="metric-val">{loan_risk_chip(risk.get('loan_amount_risk','Unknown'))}</span>
    </div>
    <div style="margin-top:0.6rem;font-size:0.8rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Anomalies</div>
    <div style="margin-top:6px;">{anomaly_chips}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Full reasoning & raw payload", expanded=False):
                st.markdown(risk.get("reasoning", ""))
                st.json(risk)

        col_c, col_d = st.columns(2, gap="medium")

        # AGENT 3 — Loan Decision
        with col_c:
            cls_chip_color = {"Approved": "green", "Rejected": "red", "Requires Manual Review": "yellow"}.get(cls, "gray")
            top_factors = decision.get("key_decision_factors", [])[:3]
            top_factors_html = "".join(f'<li style="margin-bottom:4px;">{f}</li>' for f in top_factors) or "<li>No specific factors</li>"
            st.markdown(
                f"""
<div class="agent-card">
    <div><span class="agent-num">3</span><span class="agent-name">Loan Decision</span></div>
    <div class="agent-mcp">MCP · DecisionSynthesis</div>
    <div class="agent-summary">Synthesizes profile + risk signals into a final classification.</div>
    {progress_bar(
        "Risk Score",
        decision['risk_score'],
        risk_color(decision['risk_score']),
        f"{decision['risk_score']} / 100"
    )}
    {progress_bar(
        "Confidence",
        decision['confidence_level']*100,
        "blue",
        f"{decision['confidence_level']*100:.0f}%"
    )}
    <div class="metric-row" style="margin-top:0.6rem;">
        <span class="metric-name">Classification</span>
        <span class="metric-val"><span class="status-chip {cls_chip_color}">{cls}</span></span>
    </div>
    <div style="margin-top:0.6rem;font-size:0.8rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Top factors</div>
    <ul style="margin:6px 0 0 1rem;color:#1f2937;font-size:0.88rem;">{top_factors_html}</ul>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Full explanation & raw payload", expanded=False):
                st.markdown(decision.get("explanation", ""))
                st.json(decision)

        # AGENT 4 — Compliance & Action Orchestrator
        with col_d:
            sent_chip = (
                '<span class="status-chip green">Notification sent</span>'
                if compliance.get("notification_sent")
                else '<span class="status-chip yellow">Notification pending</span>'
            )
            ts = compliance.get("timestamp", "")[:19].replace("T", " ")
            st.markdown(
                f"""
<div class="agent-card">
    <div><span class="agent-num">4</span><span class="agent-name">Compliance &amp; Action</span></div>
    <div class="agent-mcp">MCP · NotificationSystem</div>
    <div class="agent-summary">Persists the case to the audit log and notifies the applicant.</div>
    <div class="metric-row" style="margin-top:0.4rem;">
        <span class="metric-name">Action Taken</span>
    </div>
    <div style="color:#1f2937;font-size:0.92rem;margin-bottom:0.5rem;">{compliance.get('action_taken','')}</div>
    <div class="metric-row" style="margin-top:0.4rem;">
        <span class="metric-name">Case ID</span>
        <span class="metric-val" style="font-family:'JetBrains Mono',monospace;font-size:0.9rem;color:#4338ca;">{compliance.get('case_id','')}</span>
    </div>
    <div class="metric-row">
        <span class="metric-name">Logged At</span>
        <span class="metric-val" style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;">{ts}</span>
    </div>
    <div class="metric-row">
        <span class="metric-name">Status</span>
        <span class="metric-val">{sent_chip}</span>
    </div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Full summary & raw payload", expanded=False):
                st.markdown(compliance.get("summary", ""))
                st.json(compliance)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Audit timeline ───────────────────────────────────────────────
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">LangGraph Audit Trail</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-heading">Every step is traceable and timestamped</div>',
            unsafe_allow_html=True,
        )
        audit = result.get("audit_trail", [])
        if audit:
            timeline_html = '<div class="timeline">'
            for step in audit:
                timeline_html += (
                    f'<div class="timeline-item">'
                    f'<div class="ti-title">{step["step"].replace("_", " ").title()}</div>'
                    f'<div class="ti-time">{step["timestamp"]}</div>'
                    f'</div>'
                )
            timeline_html += "</div>"
            st.markdown(timeline_html, unsafe_allow_html=True)
            with st.expander("Show full JSON payloads for every step", expanded=False):
                for step in audit:
                    st.markdown(f"**{step['step']}** · `{step['timestamp']}`")
                    st.code(json.dumps(step["payload"], indent=2, default=str), language="json")
        st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRACK
# ════════════════════════════════════════════════════════════════════════════
with tab_status:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Recent Decisions</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-heading">Live feed from the compliance log</div>',
        unsafe_allow_html=True,
    )
    cases = fetch_cases(limit=25)
    if not cases:
        st.info("No applications processed yet. Submit one in the **Apply for a Loan** tab to see it here.")
    else:
        for c in reversed(cases):
            cls = c.get("classification", "Requires Manual Review")
            badge_class = classification_class(cls)
            st.markdown(
                f"""
<div class="case-row">
    <div>
        <span class="case-id">{c.get('case_id','')}</span>
        &nbsp;·&nbsp;
        <span style="color:#475569;font-weight:500;">{c.get('applicant_id','')}</span>
    </div>
    <div style="display:flex;gap:1rem;align-items:center;">
        <span style="color:#94a3b8;font-size:0.82rem;">{c.get('timestamp','')[:19].replace('T',' ')}</span>
        <span class="case-badge {badge_class}">{cls}</span>
    </div>
</div>
""",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — ABOUT
# ════════════════════════════════════════════════════════════════════════════
with tab_about:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Architecture</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Multi-agent Agentic AI system</div>', unsafe_allow_html=True)
        st.markdown(
            """
| Layer | Technology |
|---|---|
| Chatbot UI | Streamlit |
| Microservice | FastAPI |
| Orchestration | LangGraph + LangChain |
| Agents | FastAPI + Anthropic Agent SDK |
| Communication | FastMCP (MCP servers) |
| LLM | Claude Sonnet 4.6 |
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">The four agents</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Specialists, not generalists</div>', unsafe_allow_html=True)
        st.markdown(
            """
1. **Applicant Profile Agent** — income stability, employment risk, credit history summary (MCP: ApplicantDB)
2. **Financial Risk Analysis Agent** — DTI ratio, credit risk level, loan-amount risk, anomalies (MCP: RiskRulesDB)
3. **Loan Decision Agent** — classification, risk score, confidence, factors, explanation (MCP: DecisionSynthesis)
4. **Compliance & Action Orchestrator Agent** — case ID, notification, audit log, action taken (MCP: NotificationSystem)
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Pipeline flow</div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="pipeline">
    <div class="pipeline-step"><span class="num">1</span><span class="name">Applicant Profile</span><div class="mcp">MCP · ApplicantDB</div></div>
    <div class="pipeline-step"><span class="num">2</span><span class="name">Financial Risk</span><div class="mcp">MCP · RiskRulesDB</div></div>
    <div class="pipeline-step"><span class="num">3</span><span class="name">Loan Decision</span><div class="mcp">MCP · DecisionSynthesis</div></div>
    <div class="pipeline-step"><span class="num">4</span><span class="name">Compliance &amp; Action</span><div class="mcp">MCP · NotificationSystem</div></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption("Orchestrated by LangGraph with explicit state management and decision-driven routing.")
    st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    """
<hr/>
<div style="text-align:center;color:#94a3b8;font-size:0.82rem;padding:0.5rem 0 1rem;">
    State Bank · Agentic AI Loan Approval &nbsp;·&nbsp;
</div>
""",
    unsafe_allow_html=True,
)
