"""Central knobs for Context Vault — change here, applies everywhere."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Repo root = parent of context_vault package
ROOT = Path(__file__).resolve().parent.parent

# --- Paths ---
DEFAULT_DOCS_DIR = ROOT / "data" / "docs"
DEFAULT_CHROMA_DIR = ROOT / "chroma_db"
DEFAULT_COLLECTION = "context_vault"
DEFAULT_CONFLICTS_PATH = ROOT / "data" / "conflicts.json"

# --- Embeddings ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Chunking strategy: fixed | by_heading | by_paragraph ---
CHUNK_STRATEGY = os.getenv("CHUNK_STRATEGY", "fixed")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# --- Retrieval strategy: similarity | recency_boosted | filter_stale ---
RETRIEVAL_STRATEGY = os.getenv("RETRIEVAL_STRATEGY", "similarity")
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
# Higher = prefer newer docs more when re-ranking (recency_boosted)
RECENCY_WEIGHT = float(os.getenv("RECENCY_WEIGHT", "0.01"))

# --- Age buckets (days) ---
FRESH_DAYS = int(os.getenv("FRESH_DAYS", "30"))
AGING_DAYS = int(os.getenv("AGING_DAYS", "90"))

# --- Conflict judge: gemini | heuristic ---
CONFLICT_JUDGE = os.getenv("CONFLICT_JUDGE", "gemini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MAX_API_RETRIES = int(os.getenv("MAX_API_RETRIES", "4"))
API_BASE_DELAY = float(os.getenv("API_BASE_DELAY", "2"))
MAX_CONFLICT_PAIRS = int(os.getenv("MAX_CONFLICT_PAIRS", "3"))

# --- PR review judge: qwen | gemini | heuristic ---
REVIEW_LLM = os.getenv("REVIEW_LLM", "qwen")
REVIEW_TOP_K = int(os.getenv("REVIEW_TOP_K", "8"))
REVIEW_MAX_DIFF_CHARS = int(os.getenv("REVIEW_MAX_DIFF_CHARS", "24000"))

# OpenRouter (OpenAI-compatible) — default PR review provider
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "https://github.com/local/context-vault")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "context-vault")
# Optional OpenRouter routing / reasoning (matches OpenAI SDK extra_body)
# e.g. OPENROUTER_PROVIDER_ONLY=modelrun/fp4
OPENROUTER_PROVIDER_ONLY = os.getenv("OPENROUTER_PROVIDER_ONLY", "").strip()
OPENROUTER_ALLOW_FALLBACKS = os.getenv("OPENROUTER_ALLOW_FALLBACKS", "true").lower() in (
    "1",
    "true",
    "yes",
)
OPENROUTER_REASONING = os.getenv("OPENROUTER_REASONING", "false").lower() in (
    "1",
    "true",
    "yes",
)

# --- GitHub PR integration (portfolio / personal token) ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "") or os.getenv("GH_TOKEN", "")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_API_TIMEOUT = float(os.getenv("GITHUB_API_TIMEOUT", "60"))

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
