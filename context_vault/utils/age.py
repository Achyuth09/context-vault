"""Age buckets from updated_at (uses central config thresholds)."""

from __future__ import annotations

from datetime import datetime, timezone

from context_vault import config
from context_vault.utils.timeutil import parse_iso


def age_bucket(
    updated_at: str | None,
    now: datetime | None = None,
    *,
    fresh_days: int | None = None,
    aging_days: int | None = None,
) -> tuple[float | None, str]:
    """Map updated_at → (age_days, fresh|aging|stale|unknown)."""
    now = now or datetime.now(timezone.utc)
    fresh_days = config.FRESH_DAYS if fresh_days is None else fresh_days
    aging_days = config.AGING_DAYS if aging_days is None else aging_days
    dt = parse_iso(updated_at)
    if dt is None:
        return None, "unknown"
    age_days = (now - dt).total_seconds() / 86400.0
    if age_days <= fresh_days:
        bucket = "fresh"
    elif age_days <= aging_days:
        bucket = "aging"
    else:
        bucket = "stale"
    return age_days, bucket
