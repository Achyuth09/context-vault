"""Gemini LLM contradiction judge."""

from __future__ import annotations

import json
import re
from typing import Any

from google import genai
from google.genai import types

from context_vault import config
from context_vault.utils.retry import with_backoff

JUDGE_PROMPT = """You are a careful fact-checker for a knowledge base.
Decide whether FACT A and FACT B contradict each other about the same topic.

Rules:
- Contradict = they cannot both be true at the same time (e.g. API is v2 vs API is v3).
- Do NOT treat "similar topic" as a contradiction.
- Do NOT treat updates that clearly supersede older wording as "no conflict" —
  if one says X and the other says not-X / a different value for the same attribute, that IS a contradiction.
- Reply with ONLY a JSON object, no markdown fences:
  {{"contradict": true or false, "reason": "one short sentence"}}

FACT A:
{fact_a}

FACT B:
{fact_b}
"""


def parse_judge_json(raw: str) -> dict[str, Any]:
    """Extract {contradict, reason} from model text (tolerate fences)."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError(f"Judge reply was not JSON: {raw[:200]!r}")
        data = json.loads(m.group(0))

    contradict = data.get("contradict")
    if isinstance(contradict, str):
        contradict = contradict.strip().lower() in ("true", "yes", "1")
    else:
        contradict = bool(contradict)

    reason = str(data.get("reason") or "").strip() or "(no reason)"
    return {"contradict": contradict, "reason": reason}


class GeminiConflictJudge:
    name = "gemini"

    def judge(self, fact_a: str, fact_b: str) -> dict[str, Any]:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY missing. Copy .env.example → .env and set your key."
            )
        prompt = JUDGE_PROMPT.format(fact_a=fact_a.strip(), fact_b=fact_b.strip())
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        model = config.GEMINI_MODEL

        def _call() -> str:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned empty text")
            return text

        raw = with_backoff(_call, label="gemini-judge")
        parsed = parse_judge_json(raw)
        parsed["raw"] = raw
        return parsed
