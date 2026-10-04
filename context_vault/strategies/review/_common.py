"""Shared review prompt / JSON parsing helpers."""

from __future__ import annotations

import json
import re
from typing import Any

REVIEW_SYSTEM = """You are a strict PR security/policy reviewer for Context Vault.
You MUST ground findings in the POLICY snippets provided.
Prefer FRESH policies over STALE/CONTESTED when they disagree.
Only report real issues visible in the DIFF. Do not invent files.
Reply with ONLY a JSON object (no markdown fences):
{"findings":[{"severity":"high|medium|low","rule":"SHORT_ID","evidence":"short quote from diff","suggestion":"what to do","policy_doc_id":"optional doc id"}]}
If nothing is wrong, return {"findings":[]}.
"""


def build_user_prompt(
    *,
    diff: str,
    policies: list[dict[str, Any]],
    title: str = "",
    body: str = "",
) -> str:
    policy_blocks: list[str] = []
    for i, p in enumerate(policies, 1):
        policy_blocks.append(
            f"[{i}] doc_id={p.get('doc_id')} status={p.get('status')} "
            f"age_bucket={p.get('age_bucket')}\n{p.get('text', '')}"
        )
    policies_text = "\n\n---\n\n".join(policy_blocks) or "(no policies retrieved)"
    return (
        f"PR_TITLE: {title or '(none)'}\n"
        f"PR_BODY: {body or '(none)'}\n\n"
        f"POLICIES:\n{policies_text}\n\n"
        f"DIFF:\n{diff}\n"
    )


def parse_findings_json(raw: str) -> list[dict[str, Any]]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError(f"Review reply was not JSON: {raw[:240]!r}")
        data = json.loads(m.group(0))

    findings = data.get("findings") if isinstance(data, dict) else data
    if not isinstance(findings, list):
        raise ValueError("Review JSON missing findings list")

    cleaned: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        sev = str(item.get("severity") or "medium").lower()
        if sev not in ("high", "medium", "low"):
            sev = "medium"
        rule = str(item.get("rule") or "POLICY").strip() or "POLICY"
        evidence = str(item.get("evidence") or "").strip()
        suggestion = str(item.get("suggestion") or "").strip()
        if not evidence and not suggestion:
            continue
        cleaned.append(
            {
                "severity": sev,
                "rule": rule,
                "evidence": evidence or "(see diff)",
                "suggestion": suggestion or "Align with vault policy.",
                "policy_doc_id": str(item.get("policy_doc_id") or "") or None,
            }
        )
    return cleaned
