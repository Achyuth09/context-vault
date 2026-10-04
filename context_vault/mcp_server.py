"""
MCP server for Context Vault (Phase 3).

Thin adapter: agent requests a tool → we call existing Phase 1/2 functions.

  python -m context_vault.mcp_server

Cursor: see .cursor/mcp.json in this repo.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from context_vault.conflicts import detect_conflicts, flag_conflict, mark_stale
from context_vault.get_context import get_context, hits_as_dicts
from context_vault.review import review_diff, review_github_pr

mcp = MCPServer(
    name="context-vault",
    instructions=(
        "Context Vault: retrieve knowledge with freshness/conflict health. "
        "Use get_context before answering from docs. "
        "If hits are contested or stale, warn the user — do not treat both sides as true. "
        "Use detect_conflicts to check whether top hits contradict. "
        "Use mark_stale when a document is known to be outdated. "
        "Use review_pr_tool to check a PR unified diff against vault security policies."
    ),
)


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def get_context_tool(query: str, top_k: int = 5) -> str:
    """
    Semantic search over the vault with provenance and health labels.

    Returns chunks with status: fresh | aging | stale | contested.
    Contested/stale hits must not be treated as equally trustworthy.
    """
    hits = get_context(query, top_k=top_k)
    return _json(
        {
            "query": query,
            "count": len(hits),
            "hits": hits_as_dicts(hits),
            "note": "Prefer fresh over stale/contested. Contested = known contradiction.",
        }
    )


@mcp.tool()
def mark_stale_tool(doc_id: str) -> str:
    """
    Explicitly mark every chunk of a document as stale (untrustworthy).

    doc_id examples: api_version_jan, api_version_sep, deploy_region, oncall
    """
    result = mark_stale(doc_id)
    if result["chunks_updated"] == 0:
        return _json({**result, "error": f"No chunks found for doc_id={doc_id!r}"})
    return _json(result)


@mcp.tool()
def flag_conflict_tool(
    fact_a: str,
    fact_b: str,
    ask_llm: bool = True,
    reason: str = "",
) -> str:
    """
    Record a conflict between two claims. If ask_llm=True (default), Gemini
    decides whether they contradict and why; otherwise stores with your reason.
    """
    record = flag_conflict(
        fact_a,
        fact_b,
        ask_llm=ask_llm,
        reason=reason or ("flagged via MCP" if not ask_llm else ""),
    )
    return _json(record.__dict__)


@mcp.tool()
def detect_conflicts_tool(query: str, top_k: int = 5) -> str:
    """
    Retrieve top hits for a query, pair different docs, ask Gemini if they
    contradict, save conflict records, and stamp contested chunks.
    """
    summary = detect_conflicts(query, top_k=top_k)
    return _json(summary)


@mcp.tool()
def review_pr_tool(
    diff: str = "",
    pr_url: str = "",
    title: str = "",
    body: str = "",
    provider: str = "",
    post_review: bool = False,
) -> str:
    """
    Review a PR against Context Vault security policies.

    Provide either:
    - diff: unified git diff text, OR
    - pr_url: https://github.com/owner/repo/pull/N (needs GITHUB_TOKEN)

    If post_review=true with pr_url, posts a summary GitHub PR review comment.
    provider: qwen | gemini | heuristic (empty = config default).
    """
    if pr_url.strip():
        summary = review_github_pr(
            pr_url.strip(),
            provider=provider or None,
            post_review=post_review,
        )
        return _json(summary)
    if not diff.strip():
        return _json({"error": "Provide diff text or pr_url"})
    summary = review_diff(
        diff,
        title=title,
        body=body,
        provider=provider or None,
    )
    return _json(summary)


def main() -> None:
    # stdio = Cursor / Claude Desktop talk to this process over stdin/stdout
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
