"""Phase 3: MCP tool registration (no live Cursor client required)."""

import asyncio
import json

from context_vault.mcp_server import mcp


def test_mcp_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = sorted(t.name for t in tools)
    assert names == [
        "detect_conflicts_tool",
        "flag_conflict_tool",
        "get_context_tool",
        "mark_stale_tool",
        "review_pr_tool",
    ]


def test_get_context_tool_returns_json():
    """Needs an ingested index; skips gracefully if empty."""
    result = asyncio.run(mcp.call_tool("get_context_tool", {"query": "API version", "top_k": 3}))
    assert result.is_error is False
    text = result.content[0].text
    data = json.loads(text)
    assert "hits" in data
    assert data["query"] == "API version"
