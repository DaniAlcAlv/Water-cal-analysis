# services.filters.py
from __future__ import annotations

from typing import Iterable
from datetime import datetime, timezone, timedelta


def _is_recent(rec, days: int) -> bool:
    """Return True if record date is within the last `days` (handles tz-aware and naive)."""
    dt = getattr(rec, "date", None)
    if not dt:
        return False
    now_utc = datetime.now(timezone.utc)
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now_utc - dt) <= timedelta(days=days)


def apply_filters(records: Iterable, rig_filter: str, recent_days: int) -> list:
    """
    Apply rig and recency filters to records. Never mutates input.
    - rig_filter: 'All' = no rig filtering
    - recent_days: 0 = no recency filtering
    """
    out = list(records)

    if rig_filter and rig_filter != "All":
        out = [r for r in out if getattr(r, "rig_name", None) == rig_filter]

    rd = int(recent_days)   # <-- respect 0 = all; do not coalesce to default
    if rd > 0:
        out = [r for r in out if _is_recent(r, rd)]

    return out