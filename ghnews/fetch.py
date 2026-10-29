"""Collect "hot" repositories from GitHub.

Two sources are used:
  * github.com/trending (daily / weekly / monthly) - scraped HTML, gives
    "stars gained in period", which is the best signal for what is hot.
  * GitHub Search API - repositories created recently, sorted by stars.
    Used for the "new arrivals" section and as a fallback when trending
    scraping fails.

Only the Python standard library is used so the job runs anywhere.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import urllib.parse
import urllib.request

USER_AGENT = "ghnews/1.0 (+https://github.com/never2u/JerrySpace)"
TIMEOUT = 30

PERIODS = ("daily", "weekly", "monthly")


def _get(url: str, accept: str = "text/html") -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _to_int(text: str | None) -> int:
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


_ARTICLE_RE = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)
_NAME_RE = re.compile(r'<h2[^>]*>\s*<a[^>]*href="/([^"/]+/[^"/]+)"', re.S)
_DESC_RE = re.compile(r'<p class="col-9[^"]*">(.*?)</p>', re.S)
_LANG_RE = re.compile(r'itemprop="programmingLanguage">([^<]+)<')
_STARS_RE = re.compile(r'href="/[^"]+/stargazers"[^>]*>(.*?)</a>', re.S)
_FORKS_RE = re.compile(r'href="/[^"]+/forks"[^>]*>(.*?)</a>', re.S)
_GAINED_RE = re.compile(r"([\d,]+)\s+stars?\s+(today|this week|this month)")
_AVATARS_RE = re.compile(r'Built by(.*?)</span>', re.S)
_AVATAR_RE = re.compile(r'<a[^>]*href="/([^"/]+)"')


def parse_trending(page: str) -> list[dict]:
    """Parse the github.com/trending HTML into a list of repo dicts."""
    repos = []
    for rank, block in enumerate(_ARTICLE_RE.findall(page), start=1):
        name = _NAME_RE.search(block)
        if not name:
            continue
        full_name = name.group(1).strip()
        desc = _DESC_RE.search(block)
        lang = _LANG_RE.search(block)
        stars = _STARS_RE.search(block)
        forks = _FORKS_RE.search(block)
        gained = _GAINED_RE.search(_strip_tags(block))
        builders = _AVATARS_RE.search(block)
        repos.append(
            {
                "rank": rank,
                "full_name": full_name,
                "owner": full_name.split("/")[0],
                "url": f"https://github.com/{full_name}",
                "description": _strip_tags(desc.group(1)) if desc else "",
                "language": lang.group(1).strip() if lang else None,
                "stars": _to_int(_strip_tags(stars.group(1))) if stars else 0,
                "forks": _to_int(_strip_tags(forks.group(1))) if forks else 0,
                "stars_gained": _to_int(gained.group(1)) if gained else 0,
                "built_by": _AVATAR_RE.findall(builders.group(1))[:5] if builders else [],
            }
        )
    return repos


def fetch_trending(period: str = "daily", language: str = "") -> list[dict]:
    path = f"/{urllib.parse.quote(language)}" if language else ""
    return parse_trending(_get(f"https://github.com/trending{path}?since={period}"))


def parse_search(payload: str) -> list[dict]:
    items = json.loads(payload).get("items", [])
    repos = []
    for rank, it in enumerate(items, start=1):
        repos.append(
            {
                "rank": rank,
                "full_name": it["full_name"],
                "owner": it["owner"]["login"],
                "url": it["html_url"],
                "description": (it.get("description") or "").strip(),
                "language": it.get("language"),
                "stars": it.get("stargazers_count", 0),
                "forks": it.get("forks_count", 0),
                "stars_gained": it.get("stargazers_count", 0),
                "topics": it.get("topics", [])[:6],
                "created_at": it.get("created_at"),
                "built_by": [it["owner"]["login"]],
            }
        )
    return repos


def fetch_new_arrivals(today: dt.date, days: int = 7, limit: int = 30) -> list[dict]:
    """Repositories created in the last `days` days, most starred first."""
    since = (today - dt.timedelta(days=days)).isoformat()
    query = urllib.parse.urlencode(
        {"q": f"created:>{since}", "sort": "stars", "order": "desc", "per_page": limit}
    )
    return parse_search(
        _get(f"https://api.github.com/search/repositories?{query}", "application/vnd.github+json")
    )


def collect(today: dt.date | None = None, log=print) -> dict:
    """Gather everything for one edition. Failures degrade to empty sections."""
    today = today or dt.date.today()
    edition = {"date": today.isoformat(), "trending": {}, "new_arrivals": []}

    for period in PERIODS:
        try:
            edition["trending"][period] = fetch_trending(period)
            log(f"trending/{period}: {len(edition['trending'][period])} repos")
        except Exception as exc:  # network / markup change - keep going
            log(f"trending/{period} failed: {exc}")
            edition["trending"][period] = []

    try:
        edition["new_arrivals"] = fetch_new_arrivals(today)
        log(f"new_arrivals: {len(edition['new_arrivals'])} repos")
    except Exception as exc:
        log(f"new_arrivals failed: {exc}")

    # If scraping broke entirely, fall back to recent-star leaders so the
    # front page is never empty.
    if not edition["trending"]["daily"] and edition["new_arrivals"]:
        log("falling back to search results for daily trending")
        edition["trending"]["daily"] = edition["new_arrivals"][:25]
        edition["fallback"] = True

    return edition


def fetch_created_dates(edition: dict, cache: dict, log=print) -> int:
    """Fill `cache` (name -> "YYYY-MM-DD") with creation dates of this edition's repos.

    Creation dates never change, so each repository is looked up once.
    """
    names = {r["full_name"] for repos in edition.get("trending", {}).values() for r in repos}
    for a in edition.get("new_arrivals", []):
        if a.get("created_at"):
            cache.setdefault(a["full_name"], a["created_at"][:10])
    todo = sorted(n for n in names if n not in cache)
    for name in todo:
        try:
            meta = json.loads(_get(f"https://api.github.com/repos/{urllib.parse.quote(name)}",
                                   "application/vnd.github+json"))
            cache[name] = meta["created_at"][:10]
        except Exception as exc:
            log(f"created date for {name} failed: {exc}")
    log(f"created dates: {len(todo)} looked up")
    return len(todo)
