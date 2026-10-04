"""Offline regex / path PR review (no LLM)."""

from __future__ import annotations

import re
from typing import Any


_SECRET_ASSIGN = re.compile(
    r"(?i)(password|passwd|api[_-]?key|secret|token|aws_secret)\s*=\s*['\"][^'\"]{4,}['\"]"
)
_SK_LIKE = re.compile(r"(?i)\b(sk-[a-z0-9_-]{8,}|sk_live_[a-z0-9]+)\b")
_ENV_FILE = re.compile(r"(?m)^\+\+\+ b/.*\.env(?:\.\w+)?$|^\+\+\+ b/.*credentials", re.I)
_PEM = re.compile(r"(?m)^\+\+\+ b/.*\.(pem|p12|pfx)$", re.I)
_SQL_FSTRING = re.compile(
    r"""(?i)f["'].*\b(select|insert|update|delete|from|where)\b.*\{"""
)
_SQL_CONCAT = re.compile(
    r"""(?i)(["'].*\b(select|insert|update|delete)\b.*["']\s*\+)|"""
    r"""(\+\s*["'].*\b(select|where)\b)"""
)
_NO_AUTH_HINT = re.compile(
    r"(?i)(no jwt|without auth|skip auth|intentionally no jwt|TODO: add auth)"
)
_ROLE_FROM_BODY = re.compile(
    r"(?i)(request\.(json|args|form)|body\.get)\([^\)]*(role|is_admin)"
)


def _policy_id(policies: list[dict[str, Any]], needle: str) -> str | None:
    for p in policies:
        doc = str(p.get("doc_id") or "")
        if needle.lower() in doc.lower():
            return doc
    return None


class HeuristicReviewJudge:
    name = "heuristic"

    def review(
        self,
        *,
        diff: str,
        policies: list[dict[str, Any]],
        title: str = "",
        body: str = "",
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        added = "\n".join(
            line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
        )

        if _ENV_FILE.search(diff) or _PEM.search(diff):
            findings.append(
                {
                    "severity": "high",
                    "rule": "NO_SECRETS_IN_REPO",
                    "evidence": "Diff adds .env / credentials / key material file",
                    "suggestion": "Remove the file from the PR; use env vars / secret manager.",
                    "policy_doc_id": _policy_id(policies, "SECRET") or "SECURITY_SECRETS",
                }
            )

        for m in _SECRET_ASSIGN.finditer(added):
            findings.append(
                {
                    "severity": "high",
                    "rule": "HARDCODED_SECRET",
                    "evidence": m.group(0)[:120],
                    "suggestion": "Move secret to environment variable; never commit credentials.",
                    "policy_doc_id": _policy_id(policies, "SECRET") or "SECURITY_SECRETS",
                }
            )
            break

        if _SK_LIKE.search(added):
            findings.append(
                {
                    "severity": "high",
                    "rule": "API_KEY_IN_SOURCE",
                    "evidence": "Possible API key literal (sk-...) in added lines",
                    "suggestion": "Use env-based configuration; rotate any exposed key.",
                    "policy_doc_id": _policy_id(policies, "SECRET") or "SECURITY_SECRETS",
                }
            )

        if _SQL_FSTRING.search(added) or _SQL_CONCAT.search(added):
            findings.append(
                {
                    "severity": "high",
                    "rule": "RAW_SQL_CONCAT",
                    "evidence": "SQL built via f-string or string concatenation",
                    "suggestion": "Use parameterized queries / ORM binds.",
                    "policy_doc_id": _policy_id(policies, "SQL") or "SECURITY_SQL",
                }
            )

        if _NO_AUTH_HINT.search(added) or (
            re.search(r"(?i)@app\.(get|post|put|delete|patch)", added)
            and not re.search(r"(?i)(jwt|bearer|require_auth|login_required|Authorization)", added)
            and re.search(r"(?i)(users|admin|delete|profile)", added)
        ):
            findings.append(
                {
                    "severity": "high",
                    "rule": "AUTH_JWT_REQUIRED",
                    "evidence": "Sensitive route appears without JWT/auth check",
                    "suggestion": "Require Bearer JWT verification before handler logic.",
                    "policy_doc_id": _policy_id(policies, "AUTH") or "SECURITY_AUTH",
                }
            )

        if _ROLE_FROM_BODY.search(added):
            findings.append(
                {
                    "severity": "high",
                    "rule": "RBAC_FROM_CLIENT",
                    "evidence": "Role/admin flag taken from request body/args",
                    "suggestion": "Authorize from verified JWT claims, not client-supplied role.",
                    "policy_doc_id": _policy_id(policies, "AUTH") or "SECURITY_AUTH",
                }
            )

        return findings
