"""GitHub REST helpers for PR review (personal token — not a GitHub App)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from context_vault import config
from context_vault.utils.logging import get_logger

log = get_logger("context_vault.github")

_PR_URL = re.compile(
    r"https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)
_PR_SHORTHAND = re.compile(
    r"^(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)#(?P<number>\d+)$"
)


class GitHubError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def parse_pr_ref(ref: str) -> tuple[str, str, int]:
    """
    Accept:
      https://github.com/owner/repo/pull/123
      owner/repo#123
    """
    text = ref.strip()
    m = _PR_URL.search(text) or _PR_SHORTHAND.match(text)
    if not m:
        raise GitHubError(
            "Could not parse PR. Use https://github.com/owner/repo/pull/123 "
            "or owner/repo#123"
        )
    return m.group("owner"), m.group("repo"), int(m.group("number"))


def _headers() -> dict[str, str]:
    if not config.GITHUB_TOKEN:
        raise GitHubError(
            "GITHUB_TOKEN missing. Create a fine-scoped PAT "
            "(pull_requests: read, and contents/PRs write if posting reviews) "
            "and set GITHUB_TOKEN in .env"
        )
    return {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "context-vault-pr-review",
    }


def _api(path: str, *, accept: str | None = None) -> httpx.Response:
    url = f"{config.GITHUB_API_URL.rstrip('/')}{path}"
    headers = _headers()
    if accept:
        headers["Accept"] = accept
    with httpx.Client(timeout=config.GITHUB_API_TIMEOUT) as client:
        resp = client.get(url, headers=headers)
    if resp.status_code == 401:
        raise GitHubError("GitHub auth failed (401). Check GITHUB_TOKEN.", status_code=401)
    if resp.status_code == 403:
        raise GitHubError(
            f"GitHub forbidden (403): {resp.text[:240]}", status_code=403
        )
    if resp.status_code == 404:
        raise GitHubError(
            "PR not found (404). Check URL, repo visibility, and token access.",
            status_code=404,
        )
    if resp.status_code >= 400:
        raise GitHubError(
            f"GitHub HTTP {resp.status_code}: {resp.text[:300]}",
            status_code=resp.status_code,
        )
    return resp


def fetch_pull_request(owner: str, repo: str, number: int) -> dict[str, Any]:
    data = _api(f"/repos/{owner}/{repo}/pulls/{number}").json()
    return {
        "owner": owner,
        "repo": repo,
        "number": number,
        "title": str(data.get("title") or ""),
        "body": str(data.get("body") or ""),
        "html_url": str(data.get("html_url") or ""),
        "state": str(data.get("state") or ""),
        "head_sha": str((data.get("head") or {}).get("sha") or ""),
        "base_ref": str((data.get("base") or {}).get("ref") or ""),
        "head_ref": str((data.get("head") or {}).get("ref") or ""),
    }


def fetch_pull_diff(owner: str, repo: str, number: int) -> str:
    resp = _api(
        f"/repos/{owner}/{repo}/pulls/{number}",
        accept="application/vnd.github.v3.diff",
    )
    text = (resp.text or "").strip()
    if not text:
        raise GitHubError("GitHub returned an empty PR diff")
    return text


def format_review_body(summary: dict[str, Any], *, pr_url: str = "") -> str:
    findings = summary.get("findings") or []
    provider = summary.get("provider_used") or "?"
    lines = [
        "## Context Vault — policy review",
        "",
        f"_Personal portfolio guardrail_ · judge=`{provider}`",
    ]
    if pr_url:
        lines.append(f"_PR:_ {pr_url}")
    lines.append("")

    if not findings:
        lines.extend(
            [
                "No policy findings from the vault-backed review.",
                "",
                "Policies consulted:",
            ]
        )
    else:
        lines.append(f"**{len(findings)} finding(s)** — please address before merge.")
        lines.append("")
        for i, f in enumerate(findings, 1):
            sev = str(f.get("severity") or "medium").upper()
            rule = f.get("rule") or "POLICY"
            evidence = (f.get("evidence") or "").replace("\n", " ")[:200]
            suggestion = (f.get("suggestion") or "").replace("\n", " ")[:200]
            policy = f.get("policy_doc_id") or "—"
            lines.append(f"### {i}. [{sev}] `{rule}`")
            lines.append(f"- **Evidence:** {evidence}")
            lines.append(f"- **Suggestion:** {suggestion}")
            lines.append(f"- **Policy:** `{policy}`")
            lines.append("")

    policies = summary.get("policies_used") or []
    if policies:
        lines.append("<details><summary>Policies retrieved from vault</summary>")
        lines.append("")
        for p in policies[:12]:
            lines.append(
                f"- `{p.get('doc_id')}` [{p.get('status')}/{p.get('age_bucket')}]"
            )
        lines.append("")
        lines.append("</details>")

    if summary.get("fallback_reason"):
        lines.append("")
        lines.append(f"_Fallback:_ `{summary['fallback_reason']}`")

    lines.extend(
        [
            "",
            "---",
            "_Generated by Context Vault. Not a substitute for human review._",
        ]
    )
    return "\n".join(lines)


def post_pull_review(
    owner: str,
    repo: str,
    number: int,
    *,
    body: str,
    event: str = "COMMENT",
) -> dict[str, Any]:
    """
    Create a PR review (summary comment). event: COMMENT | REQUEST_CHANGES | APPROVE
    """
    if event not in ("COMMENT", "REQUEST_CHANGES", "APPROVE"):
        raise GitHubError(f"Invalid review event: {event}")

    url = f"{config.GITHUB_API_URL.rstrip('/')}/repos/{owner}/{repo}/pulls/{number}/reviews"
    payload = {"body": body, "event": event}
    with httpx.Client(timeout=config.GITHUB_API_TIMEOUT) as client:
        resp = client.post(url, headers=_headers(), json=payload)
    if resp.status_code >= 400:
        raise GitHubError(
            f"Failed to post review ({resp.status_code}): {resp.text[:300]}",
            status_code=resp.status_code,
        )
    data = resp.json()
    log.info("Posted GitHub review id=%s on %s/%s#%s", data.get("id"), owner, repo, number)
    return {
        "id": data.get("id"),
        "html_url": data.get("html_url"),
        "state": data.get("state"),
        "event": event,
    }


def review_event_for_findings(findings_count: int) -> str:
    return "REQUEST_CHANGES" if findings_count > 0 else "COMMENT"
