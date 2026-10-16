"""Weekly popularity chart, refreshed once a week (Monday, KST).

Each ISO week's chart is the weekly-trending list of that week's first
edition (normally Monday's). Movement is computed against the previous
chart: rank change, NEW / re-entry, weeks on chart, peak position and
consecutive weeks at #1.
"""

from __future__ import annotations

import datetime as dt

CHART_SIZE = 20


def _week(date: str) -> tuple[int, int]:
    y, w, _ = dt.date.fromisoformat(date).isocalendar()
    return y, w


def build_charts(editions: list[dict]) -> list[dict]:
    """All weekly charts, oldest first. `editions` may be in any order."""
    first_of_week = {}
    for ed in sorted(editions, key=lambda e: e["date"]):
        weekly = ed.get("trending", {}).get("weekly") or []
        if weekly:
            first_of_week.setdefault(_week(ed["date"]), ed)

    charts, history = [], {}  # history: name -> {"weeks": n, "peak": best rank}
    prev_ranks, no1 = {}, (None, 0)
    for _, ed in sorted(first_of_week.items()):
        entries = []
        for rank, repo in enumerate(ed["trending"]["weekly"][:CHART_SIZE], start=1):
            name = repo["full_name"]
            past = history.get(name)
            prev = prev_ranks.get(name)
            entries.append({
                **repo,
                "rank": rank,
                "prev_rank": prev,
                "delta": (prev - rank) if prev else 0,
                "is_new": past is None,
                "re_entry": past is not None and prev is None,
                "weeks": (past["weeks"] if past else 0) + 1,
                "peak": min(rank, past["peak"]) if past else rank,
            })
        for e in entries:
            history[e["full_name"]] = {"weeks": e["weeks"], "peak": e["peak"]}
        leader = entries[0]["full_name"] if entries else None
        no1 = (leader, no1[1] + 1 if leader == no1[0] else 1)
        if entries:
            entries[0]["no1_weeks"] = no1[1]
        charts.append({"date": ed["date"], "has_previous": bool(prev_ranks), "entries": entries})
        prev_ranks = {e["full_name"]: e["rank"] for e in entries}
    return charts


def chart_for(date: str, charts: list[dict]) -> dict | None:
    """The chart in effect on `date` (latest one published on or before it)."""
    current = None
    for chart in charts:
        if chart["date"] <= date:
            current = chart
    return current
