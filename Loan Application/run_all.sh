#!/usr/bin/env bash
# Launch the entire Loan Approval multi-agent system locally.
#
# Order:
#   1. 4 MCP servers (FastMCP/HTTP)
#   2. 4 FastAPI agent services
#   3. Main FastAPI microservice (LangGraph orchestrator inside)
#   4. Streamlit chatbot UI

set -euo pipefail

cd "$(dirname "$0")"

PY="${PY:-./.venv/bin/python}"
STREAMLIT="${STREAMLIT:-./.venv/bin/streamlit}"

mkdir -p logs

start() {
  local name="$1"; shift
  echo "[start] $name -> logs/${name}.log"
  nohup "$@" > "logs/${name}.log" 2>&1 &
  echo $! > "logs/${name}.pid"
}

# --- MCP Servers ---
start mcp_applicant_db   "$PY" mcp_servers/applicant_db_server.py
start mcp_risk_rules     "$PY" mcp_servers/risk_rules_server.py
start mcp_decision_synth "$PY" mcp_servers/decision_synthesis_server.py
start mcp_notification   "$PY" mcp_servers/notification_system_server.py

sleep 2

# --- Agents ---
start agent_profile    "$PY" agents/applicant_profile_agent.py
start agent_risk       "$PY" agents/financial_risk_agent.py
start agent_decision   "$PY" agents/loan_decision_agent.py
start agent_compliance "$PY" agents/compliance_agent.py

sleep 2

# --- Microservice ---
start microservice "$PY" microservice/main.py

sleep 1

# --- UI ---
start streamlit_ui "$STREAMLIT" run ui/streamlit_app.py --server.port "${STREAMLIT_PORT:-8501}" --server.headless true

echo
echo "All services launched."
echo "  Microservice docs : http://127.0.0.1:${MICROSERVICE_PORT:-8000}/docs"
echo "  Streamlit chatbot : http://127.0.0.1:${STREAMLIT_PORT:-8501}"
echo "Run ./stop_all.sh to stop everything."
