# Context Vault — Handoff (open this repo and resume here)

**Student:** Achyuth  
**Repo:** `C:\Users\Achyut\context-vault`  
**Stack:** Python vault (strategies) + conflict health + **GitHub PR review guardrail** (fetch PR / optional post review). MCP + optional Next.js dashboard.

---

## Paste into a new chat

```
Resume Context Vault from HANDOFF.md.
Vault + PR review (local diff + GitHub --pr / --post-review) done.
Next: optional CI Action, or portfolio write-up — still no multi-tenant GitHub App.
Use this repo's .venv.
```

---

## Status

| Piece | Status |
|-------|--------|
| Phases 1–4 (ingest, conflicts, MCP, dashboard) | ✅ |
| Config + strategies | ✅ |
| PR review (diff / heuristic / qwen / gemini) | ✅ |
| GitHub: `--pr URL` fetch + optional `--post-review` | ✅ |

**Intentionally not built:** GitHub App, webhooks, auto-merge, hosted multi-tenant bot.  
**Interview framing:** personal prototype proving the loop before a company CI/App rollout.

---

## Resume story (what it solves)

> “Agents and reviewers miss when code drifts from security policy. Context Vault stores policies with freshness/conflict health, retrieves the right ones for a PR diff, judges violations, and can leave a GitHub review comment — as a personal PoC before productionizing at work.”

---

## GitHub PR demo

```powershell
.\.venv\Scripts\Activate.ps1
# .env needs GITHUB_TOKEN (read PRs; write if posting)

# Fetch + review only (prints JSON)
python -m context_vault.cli review --pr https://github.com/OWNER/REPO/pull/123 --provider heuristic

# Fetch + review + post summary comment on the PR
python -m context_vault.cli review --pr https://github.com/OWNER/REPO/pull/123 --provider heuristic --post-review

# Local offline (no GitHub)
python -m context_vault.cli review --diff fixtures/sample_pr.diff --provider heuristic
```

Token: classic/fine-grained PAT with access to that repo. Never commit `.env`.

---

## Interview one-liner

> “Most RAG retrieves similar chunks. Context Vault tracks trust (freshness/conflicts) and reuses the same vault as a PR policy guardrail — including fetching a real GitHub PR and posting a review — as a portfolio prototype.”
