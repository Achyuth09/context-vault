"""Heuristic contradiction judge (no API) — version / price markers."""

from __future__ import annotations

import re
from typing import Any


_VERSION = re.compile(r"\bv(\d+)\b", re.IGNORECASE)
_PRICE = re.compile(r"\$(\d+(?:\.\d+)?)")


def _versions(text: str) -> set[str]:
    return {m.group(1) for m in _VERSION.finditer(text)}


def _prices(text: str) -> set[str]:
    return {m.group(1) for m in _PRICE.finditer(text)}


class HeuristicConflictJudge:
    name = "heuristic"

    def judge(self, fact_a: str, fact_b: str) -> dict[str, Any]:
        """
        Conservative offline judge:
        - both sides name version markers (vN) and sets differ, or
        - both sides name $prices and sets differ.
        """
        va, vb = _versions(fact_a), _versions(fact_b)
        if va and vb and va != vb:
            return {
                "contradict": True,
                "reason": (
                    f"Heuristic: different version markers "
                    f"{sorted(va)} vs {sorted(vb)}."
                ),
            }

        pa, pb = _prices(fact_a), _prices(fact_b)
        if pa and pb and pa != pb:
            return {
                "contradict": True,
                "reason": (
                    f"Heuristic: different price markers "
                    f"{sorted(pa)} vs {sorted(pb)}."
                ),
            }

        return {
            "contradict": False,
            "reason": "Heuristic: no clear conflicting version/price markers.",
        }
