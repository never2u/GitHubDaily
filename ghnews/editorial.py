"""Turn raw trending data into "news": headlines, badges and story angles.

Everything here is pure (no I/O) so it is easy to test.
"""

from __future__ import annotations

from collections import Counter


def fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1_000:.0f}k"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def annotate(today: list[dict], history: list[dict]) -> list[dict]:
    """Add news badges to today's daily trending list.

    `history` is a list of earlier editions, newest first.
    Adds: is_new, prev_rank, rank_delta, streak (days in a row on trending).
    """
    previous_ranks = {}
    if history:
        for r in history[0].get("trending", {}).get("daily", []):
            previous_ranks[r["full_name"]] = r["rank"]

    out = []
    for repo in today:
        repo = dict(repo)
        name = repo["full_name"]
        prev = previous_ranks.get(name)
        repo["prev_rank"] = prev
        repo["is_new"] = bool(history) and prev is None
        repo["rank_delta"] = (prev - repo["rank"]) if prev else 0

        streak = 1
        for past in history:
            names = {r["full_name"] for r in past.get("trending", {}).get("daily", [])}
            if name not in names:
                break
            streak += 1
        repo["streak"] = streak
        out.append(repo)
    return out


def headline_for(repo: dict) -> str:
    """A one-line, newspaper-style headline for a repo."""
    name = repo["full_name"].split("/")[1]
    gained = repo.get("stars_gained", 0)
    if repo.get("streak", 1) >= 5:
        return f"{repo['streak']}일 연속 트렌딩, 식지 않는 {name} 열풍"
    if repo.get("is_new") and gained:
        return f"신규 진입 {name}, 하루 만에 ★{fmt_num(gained)} 돌풍"
    if repo.get("rank_delta", 0) >= 5:
        return f"{name}, 순위 {repo['rank_delta']}계단 급상승"
    if gained:
        return f"{name}, 오늘 하루 ★{fmt_num(gained)} 획득"
    return f"주목할 저장소: {name}"


def language_breakdown(repos: list[dict], top: int = 6) -> list[tuple[str, int]]:
    counts = Counter(r["language"] or "기타" for r in repos)
    return counts.most_common(top)


def briefing(edition: dict, daily: list[dict]) -> list[str]:
    """Short bullet-style summary lines for the top of the page / RSS."""
    lines = []
    if daily:
        top = max(daily, key=lambda r: r.get("stars_gained", 0))
        lines.append(
            f"오늘 가장 뜨거운 저장소는 {top['full_name']} "
            f"(★ +{fmt_num(top.get('stars_gained', 0))})."
        )
        new = [r for r in daily if r.get("is_new")]
        if new:
            lines.append(f"트렌딩 신규 진입 {len(new)}개 — " + ", ".join(r["full_name"] for r in new[:3]) + ".")
        langs = language_breakdown(daily, top=3)
        if langs:
            lines.append("주요 언어: " + ", ".join(f"{l} {c}개" for l, c in langs) + ".")
        long_runners = sorted((r for r in daily if r.get("streak", 1) >= 3), key=lambda r: -r["streak"])
        if long_runners:
            r = long_runners[0]
            lines.append(f"{r['full_name']}은(는) {r['streak']}일째 트렌딩에 머물고 있습니다.")
    arrivals = edition.get("new_arrivals") or []
    if arrivals:
        a = arrivals[0]
        lines.append(f"주목받는 신작 1위는 {a['full_name']} (★ {fmt_num(a['stars'])}).")
    return lines


TOP_STORY_COOLDOWN = 7  # editions before the same repo can lead again


def pick_top(daily: list[dict], recent: list[str]) -> str:
    """Hottest repo that has not led the paper in the recent editions.

    `recent` holds earlier top stories, newest first. If every repo led
    recently, the one that led longest ago is chosen.
    """
    ranked = sorted(daily, key=lambda r: -r.get("stars_gained", 0))
    for repo in ranked:
        if repo["full_name"] not in recent:
            return repo["full_name"]
    return max(ranked, key=lambda r: recent.index(r["full_name"]))["full_name"]


FEATURE_COOLDOWN = 7  # editions before a repo can be featured again
RISING_MAX = 3
FRESH_MAX = 6
ARRIVALS_MAX = 4


def build_layout(edition: dict, history: list[dict]) -> dict:
    """Decide which repos each "fresh" section shows today.

    `history` is the earlier editions (with layouts), newest first. A repo
    featured with text (top story, rising, today's cards, new arrivals) in
    the last FEATURE_COOLDOWN editions is not featured again, so quiet days
    produce shorter sections instead of repeated stories.
    """
    daily = edition.get("trending", {}).get("daily") or []
    recent = [e["layout"] for e in history[:FEATURE_COOLDOWN] if e.get("layout")]
    ranked = sorted(daily, key=lambda r: -r.get("stars_gained", 0))

    featured = set()
    for l in recent:
        featured |= {l.get("top"), *l.get("rising", []), *l.get("fresh", [])}
    top = edition.get("top_story")
    if not top and daily:
        unseen = [r for r in daily if r["full_name"] not in featured]
        top = pick_top(unseen or daily, [l["top"] for l in recent if l.get("top")])
    yesterday = {r["full_name"] for r in history[0].get("trending", {}).get("daily", [])} if history else set()

    rising = [r["full_name"] for r in ranked if r["full_name"] != top and r["full_name"] not in featured][:RISING_MAX]
    taken = {top, *rising}
    fresh = [r["full_name"] for r in daily
             if r["full_name"] not in taken | featured | yesterday][:FRESH_MAX]
    steady = [r["full_name"] for r in daily if r["full_name"] not in taken | set(fresh)]

    shown = set()
    for l in recent:
        shown |= set(l.get("arrivals", []))
    arrivals = [a["full_name"] for a in edition.get("new_arrivals", []) if a["full_name"] not in shown][:ARRIVALS_MAX]
    return {"top": top, "rising": rising, "fresh": fresh, "steady": steady, "arrivals": arrivals}


def assign_layouts(editions: list[dict]) -> None:
    """Fill in `layout` (and `top_story`) for editions lacking one, oldest first."""
    done = []
    for ed in sorted(editions, key=lambda e: e["date"]):
        if not ed.get("layout"):
            ed["layout"] = build_layout(ed, done[::-1])
        ed["top_story"] = ed["layout"]["top"]
        done.append(ed)


def pick(repos: list[dict], names: list[str]) -> list[dict]:
    """The repos named in `names`, in that order."""
    by_name = {r["full_name"]: r for r in repos}
    return [by_name[n] for n in names if n in by_name]
