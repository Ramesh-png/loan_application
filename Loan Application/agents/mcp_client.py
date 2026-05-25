"""Lightweight synchronous wrapper around the FastMCP async client.

Agents call MCP servers via plain function calls; this helper hides the
asyncio boilerplate and lets agents stay simple.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastmcp import Client  # type: ignore


def call_mcp_tool(server_url: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Invoke a single MCP tool synchronously and return the structured result."""

    async def _run() -> Any:
        async with Client(server_url) as client:
            result = await client.call_tool(tool_name, arguments)
            # FastMCP returns a CallToolResult with .data (parsed) and .content blocks
            data = getattr(result, "data", None)
            if data is not None:
                return data
            structured = getattr(result, "structured_content", None)
            if structured is not None:
                return structured
            return getattr(result, "content", result)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Nested event loop (e.g. FastAPI). Use a new loop in a thread.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(asyncio.run, _run())
                return fut.result()
    except RuntimeError:
        pass
    return asyncio.run(_run())


def list_mcp_tools(server_url: str) -> Any:
    """List the tools exposed by an MCP server (handy for debugging)."""

    async def _run() -> Any:
        async with Client(server_url) as client:
            return await client.list_tools()

    return asyncio.run(_run())
