# Context Vault

**Portfolio project:** a small “context drift detector” for AI agents.

Normal RAG answers: *find text that looks related.*  
Context Vault also answers: *is that text still trustworthy?*

## The problem in one story

You ask an agent: “What’s our API version?”

- Old wiki: **v2**
- New policy: **v3**

A plain vector search returns **both** (they’re about the same topic). The agent may confidently mix them.  
Context Vault labels age (**fresh / stale**) and can mark pairs **contested** when they contradict.

## What you get

| Layer | Purpose |
|-------|---------|
| **Ingest + Chroma** | Store docs as meaning-vectors with provenance (`doc_id`, `updated_at`) |
| **get_context** | Retrieve + health labels |
| **conflicts** | Gemini or heuristic judge → `contested` |
| **PR review** | Diff + vault SECURITY_* policies → findings (qwen/gemini/heuristic) |
| **MCP tools** | Cursor/agent can call the same functions |
| **Dashboard** | Humans see pulse / docs / conflicts |
| **Config + strategies** | Swap chunk / retrieve / judge without rewriting the app |

## Demo script (2 minutes)

```powershell
cd C:\Users\Achyut\context-vault
.\.venv\Scripts\Activate.ps1

python -m context_vault.cli ingest
python -m context_vault.cli query "What is our API version?"
python -m context_vault.cli conflicts "What is our API version?" --judge heuristic
python -m context_vault.cli query "What is starter plan pricing?"
python -m context_vault.cli conflicts "What is starter plan pricing?" --judge heuristic
python -m context_vault.cli stats

# PR review guardrail (offline)
python -m context_vault.cli review --diff fixtures/sample_pr.diff --provider heuristic
```

### PR review with Qwen (OpenRouter)

1. Create a key at https://openrouter.ai/keys  
2. Put `OPENROUTER_API_KEY=...` in `.env` (never commit it)  
3. Run:

```powershell
python -m context_vault.cli review --diff fixtures/sample_pr.diff --provider qwen
# or from git:
git diff main...HEAD | python -m context_vault.cli review --diff - --provider heuristic
```

Default `REVIEW_LLM` is `qwen`. If OpenRouter fails/rate-limits, the CLI falls back to `heuristic` and reports why.

### Review a real GitHub PR (resume demo)

1. Create a PAT: https://github.com/settings/tokens (repo PR read; write if posting)  
2. Set `GITHUB_TOKEN=...` in `.env`  
3. Run:

```powershell
python -m context_vault.cli review --pr https://github.com/OWNER/REPO/pull/123 --provider heuristic
# optional: leave a summary review on the PR
python -m context_vault.cli review --pr https://github.com/OWNER/REPO/pull/123 --provider heuristic --post-review
```

This is a **personal PoC** (token + CLI), not a GitHub App / webhook bot — the story for interviews.

Try more questions against the sample corpus:

- `"What database do we use for profiles?"` (Postgres vs legacy Mongo)
- `"What is our support email?"` (support@ vs retired helpdesk@)
- `"What are the rate limits for Starter?"`
- `"What is the Sev-1 response time?"`

Optional UI:

```powershell
uvicorn context_vault.api:app --reload --port 8000
# other terminal
cd dashboard
npm run dev
# http://localhost:3000
```

Optional agent: enable MCP from `.cursor/mcp.json`, then ask Cursor to call `get_context_tool`.

## Sample knowledge (intentional conflicts)

| Topic | Fresh / current | Stale / conflicting |
|-------|-----------------|---------------------|
| API version | `api_version_sep.md` (v3) | `api_version_jan.md` (v2) |
| Pricing | `pricing_sep.md` ($29) | `pricing_mar.md` ($9) |
| Database | `database.md` (Postgres) | `database_legacy.md` (Mongo) |
| Support email | `support_contacts.md` | `support_contacts_old.md` |

Plus auth, rate limits, SLA, feature flags, incident runbook, retention, oncall, deploy region.

## Architecture (engineer view)

- **Config** — [`context_vault/config.py`](context_vault/config.py) (all knobs)
- **Strategies** — chunking / retrieval / conflict judge under `context_vault/strategies/`
- **Utils** — dates, age, paths, 429 retry
- **Python core** is source of truth; Next.js + MCP are thin clients (no RAG logic in Node)

```text
CHUNK_STRATEGY=fixed|by_heading|by_paragraph
RETRIEVAL_STRATEGY=similarity|recency_boosted|filter_stale
CONFLICT_JUDGE=gemini|heuristic
REVIEW_LLM=qwen|gemini|heuristic
```

Change chunk strategy/size → **re-ingest**.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # GEMINI_API_KEY and/or OPENROUTER_API_KEY
cd dashboard && npm install
```

Never commit `.env`, `chroma_db/`, or `data/conflicts.json`.

## Interview one-liner

> Most RAG retrieves similar chunks. Context Vault tracks whether that context is still trustworthy — and reuses the same vault to review PR diffs against security policies with a swappable LLM (Qwen/Gemini/heuristic).
