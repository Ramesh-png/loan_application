# Agentic AI Intelligent Loan Approval System

A Multi-Agent Agentic AI system that ingests loan applications and classifies them
as **Approved**, **Rejected**, or **Requires Manual Review** — with full explainability
and an auditable trail.

## Architecture

```
+----------------------+
|  Streamlit Chatbot   |  (Presentation)
+----------+-----------+
           | HTTP
+----------v-----------+
|  FastAPI Microservice|  POST /loan/apply
+----------+-----------+
           |
+----------v-----------+
|  LangGraph           |  applicant_profile -> financial_risk -> loan_decision
|  Orchestrator        |     -> route_on_classification -> compliance -> END
+----------+-----------+
           | HTTP (each node)
+----------v-----------+
|  4 FastAPI Agents    |  (Domain-Specific)
+----------+-----------+
           | FastMCP HTTP
+----------v-----------+
|  4 MCP Servers       |  ApplicantDB | RiskRulesDB | DecisionSynthesis | NotificationSystem
+----------------------+
```

| Layer | Component | Tech |
|---|---|---|
| Presentation | Chatbot UI | Streamlit |
| Microservice | REST entry point | FastAPI |
| Orchestration | Stateful workflow | LangGraph + LangChain |
| Agents | 4 domain agents | FastAPI + Anthropic Agent SDK + Claude Sonnet 4.6 |
| Communication | Standardized agent tools | FastMCP (MCP) |
| Data | Mock applicant/risk store | JSON files in `data/` |

## Agents and their MCP servers

| # | Agent | MCP Server | Output |
|---|---|---|---|
| 1 | Applicant Profile | ApplicantDB | Income stability, employment risk, credit history summary, completeness flags |
| 2 | Financial Risk Analysis | RiskRulesDB | DTI ratio, credit risk level, loan amount risk, anomalies, reasoning |
| 3 | Loan Decision | DecisionSynthesis | Classification, risk score, confidence, key factors, explanation |
| 4 | Compliance & Action Orchestrator | NotificationSystem | Action taken, notification sent, case ID, timestamp, summary |

## Project layout

```
.
├── config.py                            # Central config (ports, URLs, model)
├── models/schemas.py                    # Pydantic models shared across services
├── mcp_servers/
│   ├── applicant_db_server.py           # FastMCP server :8001
│   ├── risk_rules_server.py             # FastMCP server :8002
│   ├── decision_synthesis_server.py     # FastMCP server :8003
│   └── notification_system_server.py    # FastMCP server :8004
├── agents/
│   ├── mcp_client.py                    # Sync wrapper around FastMCP Client
│   ├── llm.py                           # Anthropic Claude wrapper
│   ├── applicant_profile_agent.py       # FastAPI :9001
│   ├── financial_risk_agent.py          # FastAPI :9002
│   ├── loan_decision_agent.py           # FastAPI :9003
│   └── compliance_agent.py              # FastAPI :9004
├── orchestrator/graph.py                # LangGraph state graph
├── microservice/main.py                 # FastAPI :8000 (entry point)
├── ui/streamlit_app.py                  # Streamlit chatbot :8501
├── data/
│   ├── applicants.json                  # Demo applicant DB
│   └── risk_rules.json                  # Demo underwriting rules
├── run_all.sh / stop_all.sh             # Start / stop every service
├── requirements.txt
└── .env.example
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# edit .env to add ANTHROPIC_API_KEY
```

> The system still produces deterministic decisions if `ANTHROPIC_API_KEY` is
> empty — Claude is used to enrich reasoning/explanations on top of the
> rule-based MCP signals, so the pipeline is resilient.

## Running everything

```bash
./run_all.sh
# Streamlit chatbot : http://127.0.0.1:8501
# Microservice docs : http://127.0.0.1:8000/docs
./stop_all.sh
```

## Running manually (in 9 terminals — useful for debugging)

```bash
# MCP servers
.venv/bin/python mcp_servers/applicant_db_server.py
.venv/bin/python mcp_servers/risk_rules_server.py
.venv/bin/python mcp_servers/decision_synthesis_server.py
.venv/bin/python mcp_servers/notification_system_server.py

# Agents
.venv/bin/python agents/applicant_profile_agent.py
.venv/bin/python agents/financial_risk_agent.py
.venv/bin/python agents/loan_decision_agent.py
.venv/bin/python agents/compliance_agent.py

# Microservice + UI
.venv/bin/python microservice/main.py
.venv/bin/streamlit run ui/streamlit_app.py
```

## Calling the API directly

```bash
curl -X POST http://127.0.0.1:8000/loan/apply \
  -H "Content-Type: application/json" \
  -d '{
    "applicant_id": "APP1001",
    "age": 32, "income": 1080000, "employment_type": "Salaried",
    "credit_score": 760, "loan_amount": 500000, "loan_tenure_months": 60,
    "existing_liabilities": 5000, "location": "Bengaluru"
  }'
```

The response includes the full audit trail of each agent invocation, the
risk score, classification, confidence, key decision factors, the customer
explanation, and the compliance case ID.

## Demo applicant IDs

| ID | Profile |
|---|---|
| APP1001 | Salaried, stable income, clean credit — happy path approve |
| APP1002 | Self-employed, volatile income, recent late payments — review case |
| APP1003 | Business owner, KYC incomplete, prior default — rejection path |
| APP1004 | New employee, no credit history, address unverified — review case |
| APP1005 | Unemployed — auto-reject |

## Evaluation checklist (mapped to the case study)

- [x] Streamlit chatbot UI for submission + status
- [x] FastAPI REST microservice with validation
- [x] LangGraph orchestration with state management and decision-driven routing
- [x] 4 domain agents with distinct responsibilities
- [x] FastMCP servers for standardized agent communication
- [x] Anthropic Claude Sonnet 4.6 for reasoning + explanations
- [x] Explainable outputs (every agent returns reasoning; final decision has explanation, factors, confidence)
- [x] Audit trail (LangGraph audit_trail + NotificationSystem MCP compliance log)
- [x] Loosely-coupled microservices architecture (every layer is independently runnable)
```
