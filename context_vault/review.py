"""PR review guardrail — retrieve vault policies, then judge the diff."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from context_vault import config
from context_vault.get_context import get_context
from context_vault.models import ContextHit
from context_vault.strategies.review.factory import get_review_judge
from context_vault.strategies.review.heuristic_review import HeuristicReviewJudge
from context_vault.utils.logging import get_logger

log = get_logger("context_vault.review")

_PATH_IN_DIFF = re.compile(r"(?m)^(?:\+\+\+|---) [ab]/(.+)$")
_POLICY_QUERIES = (
    "authentication JWT Bearer required RBAC",
    "SQL injection parameterized queries raw string concat",
    "secrets password api_key .env credentials not in source",
)


def load_diff(source: str | Path | None = None, *, raw: str | None = None) -> str:
    """Load diff from explicit text, a file path, or raise."""
    if raw is not None:
        text = raw
    elif source is not None:
        path = Path(source)
        if str(source) == "-" or source == Path("-"):
            raise ValueError("Pass stdin via CLI reader, not load_diff('-')")
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError("Provide diff text or a file path")
    text = text.strip()
    if not text:
        raise ValueError("Diff is empty")
    if len(text) > config.REVIEW_MAX_DIFF_CHARS:
        text = text[: config.REVIEW_MAX_DIFF_CHARS] + "\n\n...[diff truncated]..."
    return text


def paths_from_diff(diff: str) -> list[str]:
    paths: list[str] = []
    for m in _PATH_IN_DIFF.finditer(diff):
        p = m.group(1).strip()
        if p != "/dev/null" and p not in paths:
            paths.append(p)
    return paths


def _prefer_fresh(hits: list[ContextHit]) -> list[ContextHit]:
    """Prefer fresh over aging over stale; contested last among equals."""
    rank = {"fresh": 0, "aging": 1, "stale": 2, "contested": 3, "unknown": 4}

    def key(h: ContextHit) -> tuple[int, float]:
        status_rank = rank.get(h.status, 4)
        # contested status overrides age for warning, but for *policy grounding*
        # we still prefer non-contested fresh docs when available
        age = h.age_days if h.age_days is not None else 9999.0
        return (status_rank, age)

    return sorted(hits, key=key)


def retrieve_policies(
    diff: str,
    *,
    top_k: int | None = None,
    title: str = "",
) -> list[ContextHit]:
    top_k = top_k if top_k is not None else config.REVIEW_TOP_K
    paths = paths_from_diff(diff)
    path_hint = " ".join(paths[:8])
    queries = list(_POLICY_QUERIES)
    if title:
        queries.insert(0, title)
    if path_hint:
        queries.append(f"security policy for files {path_hint}")
    # Short slice of diff as semantic hint (added lines only)
    added = " ".join(
        line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    )[:500]
    if added:
        queries.append(added)

    by_id: dict[str, ContextHit] = {}
    for q in queries:
        for hit in get_context(q, top_k=min(5, top_k)):
            # Prefer security / ADR-ish docs but keep any useful hit
            key = f"{hit.doc_id}__{hit.chunk_index}"
            prev = by_id.get(key)
            if prev is None:
                by_id[key] = hit
            else:
                # keep fresher / better status
                chosen = _prefer_fresh([prev, hit])[0]
                by_id[key] = chosen

    ordered = _prefer_fresh(list(by_id.values()))
    # Drop contested policy chunks when a fresh sibling doc exists for same prefix
    return ordered[:top_k]


def _hits_as_policy_dicts(hits: list[ContextHit]) -> list[dict[str, Any]]:
    return [
        {
            "doc_id": h.doc_id,
            "status": h.status,
            "age_bucket": h.age_bucket,
            "age_days": h.age_days,
            "text": h.text,
        }
        for h in hits
    ]


def review_diff(
    diff: str,
    *,
    title: str = "",
    body: str = "",
    provider: str | None = None,
    top_k: int | None = None,
    allow_fallback: bool = True,
) -> dict[str, Any]:
    """
    Retrieve vault policies for this diff, then run the configured review judge.

    On LLM failure, falls back to heuristic and records why.
    """
    policies = retrieve_policies(diff, top_k=top_k, title=title)
    policy_dicts = _hits_as_policy_dicts(policies)
    requested = (provider or config.REVIEW_LLM).strip().lower()
    fallback_reason: str | None = None
    used = requested

    try:
        judge = get_review_judge(requested)
        findings = judge.review(
            diff=diff, policies=policy_dicts, title=title, body=body
        )
    except Exception as e:
        if not allow_fallback or requested == "heuristic":
            raise
        fallback_reason = f"{type(e).__name__}: {e}"
        log.warning("Review provider %s failed (%s); falling back to heuristic", requested, e)
        used = "heuristic"
        findings = HeuristicReviewJudge().review(
            diff=diff, policies=policy_dicts, title=title, body=body
        )

    return {
        "provider_requested": requested,
        "provider_used": used,
        "fallback_reason": fallback_reason,
        "paths": paths_from_diff(diff),
        "policies_used": [
            {
                "doc_id": h.doc_id,
                "status": h.status,
                "age_bucket": h.age_bucket,
                "preview": h.text.replace("\n", " ")[:120],
            }
            for h in policies
        ],
        "findings_count": len(findings),
        "findings": findings,
        "note": (
            "Findings are grounded in retrieved vault policies. "
            "Prefer fresh policies; contested/stale are shown for awareness."
        ),
    }


def review_diff_file(
    path: str | Path,
    *,
    title: str = "",
    body: str = "",
    provider: str | None = None,
) -> dict[str, Any]:
    return review_diff(
        load_diff(path),
        title=title,
        body=body,
        provider=provider,
    )


def review_github_pr(
    pr_ref: str,
    *,
    provider: str | None = None,
    post_review: bool = False,
    request_changes: bool = True,
) -> dict[str, Any]:
    """
    Fetch a GitHub PR by URL (or owner/repo#n), review against the vault,
    optionally post a summary review comment on the PR.
    """
    from context_vault.utils import github as gh

    owner, repo, number = gh.parse_pr_ref(pr_ref)
    meta = gh.fetch_pull_request(owner, repo, number)
    diff = gh.fetch_pull_diff(owner, repo, number)
    if len(diff) > config.REVIEW_MAX_DIFF_CHARS:
        diff = diff[: config.REVIEW_MAX_DIFF_CHARS] + "\n\n...[diff truncated]..."

    summary = review_diff(
        diff,
        title=meta["title"],
        body=meta["body"],
        provider=provider,
    )
    summary["github"] = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "html_url": meta["html_url"],
        "title": meta["title"],
        "state": meta["state"],
        "posted_review": None,
    }

    if post_review:
        event = (
            gh.review_event_for_findings(summary["findings_count"])
            if request_changes
            else "COMMENT"
        )
        # Some tokens / branch rules reject REQUEST_CHANGES from non-collaborators;
        # still try, caller sees error.
        body = gh.format_review_body(summary, pr_url=meta["html_url"])
        posted = gh.post_pull_review(
            owner, repo, number, body=body, event=event
        )
        summary["github"]["posted_review"] = posted

    return summary
