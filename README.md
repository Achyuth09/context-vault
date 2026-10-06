# Context Vault

Context Vault is a retrieval system that attaches provenance and trust labels to every chunk it returns. Similarity search still finds related text. Age and conflict labels indicate whether that text is current and consistent with other documents.

## Retrieval

Source documents are Markdown files in `data/docs`. Ingest chunks each file, embeds the chunks with `all-MiniLM-L6-v2`, and writes them to a local Chroma collection. Each chunk stores:

- `doc_id` — document identifier, normally the filename stem
- `updated_at` — source file modification time
- `ingested_at` — time the chunk was indexed

`get_context` embeds the query and returns the nearest chunks with a health label.

| Label | Meaning |
|-------|---------|
| `fresh` | Source modified within 30 days |
| `aging` | Source modified within 30–90 days |
| `stale` | Source older than 90 days, or explicitly marked stale |
| `contested` | A conflict check recorded a contradiction with another document |

A query returns evidence and labels. It does not select a winning document. The `contested` label is written only when a conflict check stamps the chunk.

## Conflict detection

Conflict detection retrieves the top hits, pairs chunks from different documents, and submits each pair to a judge.

| Judge | Behavior |
|-------|----------|
| `gemini` (default) | `gemini-3.5-flash`, with retry on HTTP 429 |
| `heuristic` | Flags mismatched version identifiers (`v2` / `v3`) and mismatched prices only |

Confirmed contradictions are appended to `data/conflicts.json`. The affected chunks are updated to `contested` in Chroma.

## Pull request review

Review loads the security policies `SECURITY_AUTH.md`, `SECURITY_SQL.md`, and `SECURITY_SECRETS.md`, prefers fresh chunks, and asks a judge to compare those policies with a diff.

| Judge | Behavior |
|-------|----------|
| `qwen` (default) | Qwen via OpenRouter (`qwen/qwen3.8-27b:free`) |
| `gemini` | Gemini |
| `heuristic` | Pattern checks, used automatically when the selected model call fails |

The result is a JSON list of findings: severity, rule, evidence, suggestion, and policy document. The command does not merge the pull request.

```powershell
python -m context_vault.cli review --diff fixtures/sample_pr.diff --provider qwen
python -m context_vault.cli review --pr https://github.com/OWNER/REPO/pull/123 --provider qwen --post-review
```

`--pr` fetches the diff from the GitHub API. `--post-review` submits one summary review. `GITHUB_TOKEN` requires pull request read access, and write access when posting. GitHub rejects `REQUEST_CHANGES` when the authenticated user opened the pull request; that review is submitted as a comment.

## Interfaces

**CLI.** Ingest, query, conflict detection, stale marking, and review.

**MCP.** `get_context_tool`, `mark_stale_tool`, `flag_conflict_tool`, `detect_conflicts_tool`, and `review_pr_tool`. Cursor launches the server from `.cursor/mcp.json`. `PYTHONPATH` must be the repository root.

**Dashboard.** A Next.js application on port 3000. It reads the FastAPI service on port 8000 and displays chunk counts, documents, and recorded conflicts. **Mark stale** sets `stale` on every chunk of a document.

Run the API from the project virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn context_vault.api:app --reload --port 8000
```

```powershell
cd dashboard
npm run dev
```

The dashboard is at http://localhost:3000. Port 8000 must be free for the API process.

## Sample corpus

The sample documents contain deliberate contradictions.

| Topic | Current | Superseded |
|-------|---------|------------|
| API version | `api_version_sep.md` (v3) | `api_version_jan.md` (v2) |
| Pricing | `pricing_sep.md` ($29) | `pricing_mar.md` ($9) |
| Database | `database.md` (Postgres) | `database_legacy.md` (Mongo) |
| Support email | `support_contacts.md` | `support_contacts_old.md` |

Additional documents cover authentication, rate limits, SLA, feature flags, incident response, retention, on-call, and deploy region.

```powershell
python -m context_vault.cli ingest
python -m context_vault.cli query "What is our API version?"
python -m context_vault.cli conflicts "What is our API version?" --judge heuristic
python -m context_vault.cli query "What is starter plan pricing?"
python -m context_vault.cli conflicts "What is starter plan pricing?" --judge heuristic
python -m context_vault.cli stats
```

## Configuration

Settings are defined in `context_vault/config.py`. A change to chunk size or chunk strategy requires a new ingest.

```text
CHUNK_STRATEGY=fixed|by_heading|by_paragraph
RETRIEVAL_STRATEGY=similarity|recency_boosted|filter_stale
CONFLICT_JUDGE=gemini|heuristic
REVIEW_LLM=qwen|gemini|heuristic
```

Chunking, retrieval, conflict judging, and review are strategy modules under `context_vault/strategies/`. Shared utilities live under `context_vault/utils/`. The Python package owns retrieval and judging. The dashboard and the MCP server call that package.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
cd dashboard
npm install
```

Set `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, and `GITHUB_TOKEN` in `.env`. Do not commit `.env`, `chroma_db/`, or `data/conflicts.json`.
