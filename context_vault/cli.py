"""
CLI for Context Vault.

  python -m context_vault.cli ingest
  python -m context_vault.cli query "What is our API version?"
  python -m context_vault.cli stats
  python -m context_vault.cli conflicts "What is our API version?"
  python -m context_vault.cli mark-stale api_version_jan
  python -m context_vault.cli flag-conflict "API is v2" "API is v3" --ask-llm
  python -m context_vault.cli review --diff fixtures/sample_pr.diff
  python -m context_vault.cli review --diff fixtures/sample_pr.diff --provider heuristic
"""

from __future__ import annotations

import argparse
import json
import sys

from context_vault import config
from context_vault.conflicts import detect_conflicts, flag_conflict, load_conflicts, mark_stale
from context_vault.get_context import get_context, hits_as_dicts
from context_vault.ingest import ingest_docs
from context_vault.review import load_diff, review_diff, review_github_pr
from context_vault.store import get_collection


def cmd_ingest(args: argparse.Namespace) -> int:
    docs_dir = args.docs or config.DEFAULT_DOCS_DIR
    print(f"Ingesting from {docs_dir} (CHUNK_STRATEGY={args.chunk_strategy or config.CHUNK_STRATEGY})")
    summary = ingest_docs(
        docs_dir,
        reset=not args.no_reset,
        chunk_strategy=args.chunk_strategy,
    )
    print(json.dumps(summary, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    hits = get_context(args.query, top_k=args.top_k, strategy=args.strategy)
    if not hits:
        print("No results (empty index?). Run: python -m context_vault.cli ingest")
        return 1

    print(f"\nQuery: {args.query!r}  (RETRIEVAL_STRATEGY={args.strategy or config.RETRIEVAL_STRATEGY})\n")
    for i, h in enumerate(hits, 1):
        preview = h.text.replace("\n", " ")[:120]
        dist = f"{h.distance:.4f}" if h.distance is not None else "n/a"
        print(f"--- hit {i} [{h.status}] age={h.age_days}d dist={dist} ---")
        print(f"doc_id={h.doc_id}  updated_at={h.updated_at}")
        print(f"{preview}...")
        print()

    if args.json:
        print(json.dumps(hits_as_dicts(hits), indent=2))
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    collection = get_collection()
    count = collection.count()
    print(f"collection={config.DEFAULT_COLLECTION}  chunks={count}")
    if count == 0:
        return 0

    data = collection.get(include=["metadatas"])
    by_doc: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for meta in data.get("metadatas") or []:
        meta = meta or {}
        doc_id = str(meta.get("doc_id") or "?")
        by_doc[doc_id] = by_doc.get(doc_id, 0) + 1
        st = str(meta.get("status") or "?")
        by_status[st] = by_status.get(st, 0) + 1

    print("per doc_id:")
    for doc_id, n in sorted(by_doc.items()):
        print(f"  {doc_id}: {n}")
    print("stored status:")
    for st, n in sorted(by_status.items()):
        print(f"  {st}: {n}")

    conflicts = load_conflicts()
    print(f"conflict records: {len(conflicts)} ({config.DEFAULT_CONFLICTS_PATH})")
    return 0


def cmd_conflicts(args: argparse.Namespace) -> int:
    judge = args.judge or config.CONFLICT_JUDGE
    print(f"Detecting conflicts for: {args.query!r}")
    print(f"(judge={judge}, model={config.GEMINI_MODEL})\n")
    summary = detect_conflicts(args.query, top_k=args.top_k, judge=args.judge)
    print(json.dumps(summary, indent=2))

    if summary["conflicts_found"]:
        print("\n-> Contested chunks stamped. Re-query to see [contested] status.")
    elif summary["pairs_checked"] == 0:
        print("\n-> No cross-doc pairs to compare (need >=2 different doc_ids in hits).")
    else:
        print("\n-> Judge found no contradictions in the pairs checked.")
    return 0


def cmd_mark_stale(args: argparse.Namespace) -> int:
    result = mark_stale(args.doc_id)
    print(json.dumps(result, indent=2))
    if result["chunks_updated"] == 0:
        print(f"No chunks for doc_id={args.doc_id!r}. Check: python -m context_vault.cli stats")
        return 1
    return 0


def cmd_flag_conflict(args: argparse.Namespace) -> int:
    record = flag_conflict(
        args.fact_a,
        args.fact_b,
        ask_llm=args.ask_llm,
        reason="" if args.ask_llm else (args.reason or "flagged via CLI"),
    )
    print(json.dumps(record.__dict__, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    provider = args.provider or config.REVIEW_LLM

    if args.pr:
        print(f"Fetching GitHub PR {args.pr!r} …")
        summary = review_github_pr(
            args.pr,
            provider=provider,
            post_review=bool(args.post_review),
            request_changes=not bool(args.comment_only),
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        if summary.get("fallback_reason"):
            print(f"\n-> Fell back to heuristic: {summary['fallback_reason']}")
        posted = (summary.get("github") or {}).get("posted_review")
        if posted:
            print(f"\n-> Posted GitHub review: {posted.get('html_url') or posted}")
        elif args.post_review:
            print("\n-> --post-review was set but no review was stored (check errors above).")
        if summary["findings_count"]:
            print(f"\n-> {summary['findings_count']} finding(s). Fix before merge.")
            return 2 if args.fail_on_findings else 0
        print("\n-> No findings.")
        return 0

    if not args.diff:
        print("Provide --diff PATH (or '-') or --pr https://github.com/owner/repo/pull/N")
        return 1

    if args.diff == "-":
        diff_text = sys.stdin.read()
        diff = load_diff(raw=diff_text)
    else:
        diff = load_diff(args.diff)

    print(f"Reviewing diff ({len(diff)} chars) with REVIEW_LLM={provider}")
    summary = review_diff(
        diff,
        title=args.title or "",
        body=args.body or "",
        provider=provider,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary.get("fallback_reason"):
        print(f"\n-> Fell back to heuristic: {summary['fallback_reason']}")
    if summary["findings_count"]:
        print(f"\n-> {summary['findings_count']} finding(s). Fix before merge.")
        return 2 if args.fail_on_findings else 0
    print("\n-> No findings.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="context_vault", description="Context Drift Detector")
    sub = p.add_subparsers(dest="command", required=True)

    ing = sub.add_parser("ingest", help="Index markdown/txt under data/docs")
    ing.add_argument("--docs", type=str, default=None, help="Docs folder (default: data/docs)")
    ing.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not wipe collection; replace per doc_id instead",
    )
    ing.add_argument(
        "--chunk-strategy",
        type=str,
        default=None,
        help="fixed | by_heading | by_paragraph (default: config.CHUNK_STRATEGY)",
    )
    ing.set_defaults(func=cmd_ingest)

    q = sub.add_parser("query", help="get_context(query) with recency / health")
    q.add_argument("query", type=str, help="Natural language question")
    q.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K)
    q.add_argument(
        "--strategy",
        type=str,
        default=None,
        help="similarity | recency_boosted | filter_stale (default: config.RETRIEVAL_STRATEGY)",
    )
    q.add_argument("--json", action="store_true", help="Also dump full JSON")
    q.set_defaults(func=cmd_query)

    st = sub.add_parser("stats", help="Show index counts + conflict file size")
    st.set_defaults(func=cmd_stats)

    cf = sub.add_parser("conflicts", help="Retrieve + contradiction check")
    cf.add_argument("query", type=str, help="Natural language question")
    cf.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K)
    cf.add_argument(
        "--judge",
        type=str,
        default=None,
        help="gemini | heuristic (default: config.CONFLICT_JUDGE)",
    )
    cf.set_defaults(func=cmd_conflicts)

    ms = sub.add_parser("mark-stale", help="Mark all chunks of a doc_id as stale")
    ms.add_argument("doc_id", type=str, help="e.g. api_version_jan")
    ms.set_defaults(func=cmd_mark_stale)

    fc = sub.add_parser("flag-conflict", help="Store a conflict record (optional LLM judge)")
    fc.add_argument("fact_a", type=str)
    fc.add_argument("fact_b", type=str)
    fc.add_argument("--ask-llm", action="store_true", help="Ask Gemini if they contradict")
    fc.add_argument("--reason", type=str, default="", help="Manual reason (ignored with --ask-llm)")
    fc.set_defaults(func=cmd_flag_conflict)

    rv = sub.add_parser("review", help="PR review against vault security policies")
    rv.add_argument(
        "--diff",
        type=str,
        default=None,
        help="Path to unified diff, or '-' for stdin (git diff …)",
    )
    rv.add_argument(
        "--pr",
        type=str,
        default=None,
        help="GitHub PR URL or owner/repo#123 (fetches diff via API)",
    )
    rv.add_argument(
        "--post-review",
        action="store_true",
        help="Post a summary review comment on the GitHub PR (needs GITHUB_TOKEN write)",
    )
    rv.add_argument(
        "--comment-only",
        action="store_true",
        help="With --post-review, always use COMMENT (never REQUEST_CHANGES)",
    )
    rv.add_argument(
        "--provider",
        type=str,
        default=None,
        help="qwen | gemini | heuristic (default: config.REVIEW_LLM)",
    )
    rv.add_argument("--title", type=str, default="", help="Optional PR title (local --diff only)")
    rv.add_argument("--body", type=str, default="", help="Optional PR body (local --diff only)")
    rv.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit code 2 when findings exist (handy in CI)",
    )
    rv.set_defaults(func=cmd_review)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
