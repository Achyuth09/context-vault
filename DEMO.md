# Demo cheat sheet

## 30-second pitch

> Agents break when old docs contradict new ones. Context Vault retrieves with freshness labels, detects conflicts, and reviews PR diffs against the same policy vault.

## Commands

```powershell
.\.venv\Scripts\Activate.ps1
python -m context_vault.cli ingest
python -m context_vault.cli query "What is our API version?"
python -m context_vault.cli conflicts "What is our API version?" --judge heuristic
python -m context_vault.cli query "What is starter plan pricing?"
python -m context_vault.cli conflicts "What is starter plan pricing?" --judge heuristic

# PR review (offline)
python -m context_vault.cli review --diff fixtures/sample_pr.diff --provider heuristic

# PR review (Qwen via OpenRouter — needs OPENROUTER_API_KEY)
python -m context_vault.cli review --diff fixtures/sample_pr.diff --provider qwen

# Real GitHub PR (needs GITHUB_TOKEN)
python -m context_vault.cli review --pr https://github.com/OWNER/REPO/pull/123 --provider heuristic
python -m context_vault.cli review --pr https://github.com/OWNER/REPO/pull/123 --provider heuristic --post-review
```

## What “good” looks like

- Query API version → sep **fresh/contested**, jan **stale/contested**
- Query pricing → $29 fresh vs $9 stale, conflict stamped
- `review` on `fixtures/sample_pr.diff` → findings for secrets, SQL concat, missing JWT / RBAC-from-body
- Unrelated noise (oncall, region) ranks lower or doesn’t “win”

## Dashboard

```powershell
uvicorn context_vault.api:app --port 8000
cd dashboard && npm run dev
```

Open http://localhost:3000 — Pulse should show contested counts after conflict runs.
