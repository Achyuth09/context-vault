"""Unit tests for GitHub PR helpers (no network)."""

import pytest

from context_vault.utils.github import (
    GitHubError,
    format_review_body,
    parse_pr_ref,
    review_event_for_findings,
)


def test_parse_pr_url():
    o, r, n = parse_pr_ref("https://github.com/acme/widgets/pull/42")
    assert (o, r, n) == ("acme", "widgets", 42)


def test_parse_pr_shorthand():
    o, r, n = parse_pr_ref("acme/widgets#7")
    assert (o, r, n) == ("acme", "widgets", 7)


def test_parse_pr_bad():
    with pytest.raises(GitHubError):
        parse_pr_ref("not-a-pr")


def test_format_review_body_with_findings():
    body = format_review_body(
        {
            "provider_used": "heuristic",
            "findings": [
                {
                    "severity": "high",
                    "rule": "RAW_SQL_CONCAT",
                    "evidence": "f-string SQL",
                    "suggestion": "use binds",
                    "policy_doc_id": "SECURITY_SQL",
                }
            ],
            "policies_used": [{"doc_id": "SECURITY_SQL", "status": "fresh", "age_bucket": "fresh"}],
        },
        pr_url="https://github.com/acme/widgets/pull/1",
    )
    assert "RAW_SQL_CONCAT" in body
    assert "Context Vault" in body


def test_review_event():
    assert review_event_for_findings(0) == "COMMENT"
    assert review_event_for_findings(2) == "REQUEST_CHANGES"
