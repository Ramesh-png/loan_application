"""Central configuration for the Loan Approval Multi-Agent System."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

MCP_APPLICANT_DB_PORT = int(os.getenv("MCP_APPLICANT_DB_PORT", "8001"))
MCP_RISK_RULES_PORT = int(os.getenv("MCP_RISK_RULES_PORT", "8002"))
MCP_DECISION_SYNTH_PORT = int(os.getenv("MCP_DECISION_SYNTH_PORT", "8003"))
MCP_NOTIFICATION_PORT = int(os.getenv("MCP_NOTIFICATION_PORT", "8004"))

AGENT_PROFILE_PORT = int(os.getenv("AGENT_PROFILE_PORT", "9001"))
AGENT_RISK_PORT = int(os.getenv("AGENT_RISK_PORT", "9002"))
AGENT_DECISION_PORT = int(os.getenv("AGENT_DECISION_PORT", "9003"))
AGENT_COMPLIANCE_PORT = int(os.getenv("AGENT_COMPLIANCE_PORT", "9004"))

MICROSERVICE_PORT = int(os.getenv("MICROSERVICE_PORT", "8000"))
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

HOST = os.getenv("HOST", "127.0.0.1")

MCP_APPLICANT_DB_URL = f"http://{HOST}:{MCP_APPLICANT_DB_PORT}/mcp"
MCP_RISK_RULES_URL = f"http://{HOST}:{MCP_RISK_RULES_PORT}/mcp"
MCP_DECISION_SYNTH_URL = f"http://{HOST}:{MCP_DECISION_SYNTH_PORT}/mcp"
MCP_NOTIFICATION_URL = f"http://{HOST}:{MCP_NOTIFICATION_PORT}/mcp"

AGENT_PROFILE_URL = f"http://{HOST}:{AGENT_PROFILE_PORT}"
AGENT_RISK_URL = f"http://{HOST}:{AGENT_RISK_PORT}"
AGENT_DECISION_URL = f"http://{HOST}:{AGENT_DECISION_PORT}"
AGENT_COMPLIANCE_URL = f"http://{HOST}:{AGENT_COMPLIANCE_PORT}"

MICROSERVICE_URL = f"http://{HOST}:{MICROSERVICE_PORT}"

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
