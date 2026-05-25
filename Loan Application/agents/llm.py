"""Anthropic Claude wrapper used by agents for reasoning + explanation.

Falls back gracefully when no API key is configured so the rest of the
pipeline (deterministic MCP signals) still produces a meaningful decision.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client: Optional[Anthropic] = None


def get_client() -> Optional[Anthropic]:
    global _client
    if not ANTHROPIC_API_KEY:
        return None
    if _client is None:
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def llm_available() -> bool:
    return bool(ANTHROPIC_API_KEY)


def generate_json(
    system: str,
    user: str,
    max_tokens: int = 800,
    temperature: float = 0.2,
) -> Optional[Dict[str, Any]]:
    """Ask Claude for a JSON object and parse it. Returns None on failure."""
    client = get_client()
    if client is None:
        return None
    try:
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            system=(
                system
                + "\n\nReturn ONLY a single JSON object. Do not wrap it in code fences."
            ),
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text"
        ).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:  # pragma: no cover - resilient fallback
        print(f"[llm] generate_json failed: {e}")
        return None


def generate_text(system: str, user: str, max_tokens: int = 400, temperature: float = 0.4) -> Optional[str]:
    client = get_client()
    if client is None:
        return None
    try:
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text"
        ).strip()
    except Exception as e:  # pragma: no cover
        print(f"[llm] generate_text failed: {e}")
        return None
