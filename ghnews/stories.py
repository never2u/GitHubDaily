"""Korean stories written from repository READMEs.

* Top news: a full article by Claude Sonnet 5.5 (headline, lead, body,
  key points). Day-specific numbers (stars today, streak) are added by the
  renderer, so one article is reused while the repo stays on top.
* Rising repos and the rest of the daily list: short blurbs by Claude
  Haiku 5.5 - longer for the five rising repos.

Everything is cached in data/stories.json and rewritten only when missing
or older than its TTL. Any failure leaves the translated description in
place.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.parse
from pathlib import Path

from .editorial import pick
from .fetch import _get
from .translate import is_korean

ARTICLE_MODEL = "claude-sonnet-5-5"
BLURB_MODEL = "claude-haiku-5-5"
ARTICLE_TTL_DAYS = 7
BLURB_TTL_DAYS = 14
README_CHARS = {"article": 8000, "long": 3000, "short": 1500}
BLURB_CHUNK = 6

ARTICLE_SYSTEM = """\
You are a reporter for a Korean tech newspaper that covers trending GitHub
repositories. Write in natural, readable Korean news style (평서문, ~다/~습니다
are both fine but be consistent). Base every statement only on the provided
metadata and README; never invent features, numbers, companies or quotes.
Keep product, library and command names in their original form. Do not
mention today's star counts or rankings - those are shown separately."""

ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "Korean headline, at most 40 characters"},
        "subheadline": {"type": "string", "description": "one-line Korean deck under the headline"},
        "lead": {"type": "string", "description": "1-2 sentence summary paragraph"},
        "sections": {
            "type": "array",
            "description": "3-4 sections, e.g. what it is / how it works / why now / who should use it",
            "items": {
                "type": "object",
                "properties": {"heading": {"type": "string"}, "text": {"type": "string"}},
                "required": ["heading", "text"],
                "additionalProperties": False,
            },
        },
        "highlights": {"type": "array", "items": {"type": "string"},
                       "description": "3-5 short key points"},
        "image_caption": {"type": "string",
                          "description": "short Korean caption for the repository's main image"},
    },
    "required": ["headline", "subheadline", "lead", "sections", "highlights", "image_caption"],
    "additionalProperties": False,
}

BLURB_SYSTEM = """\
You write short Korean introductions of GitHub repositories for a Korean
tech news site. Explain what the project does and why it is interesting or
useful, based only on the given metadata and README. Never invent features
or numbers. Keep product, library and command names in their original
form. Write natural Korean, no bullet points, no star counts."""

BLURB_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "summary": {"type": "string"}},
                "required": ["id", "summary"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


# --- README -----------------------------------------------------------------

def clean_readme(text: str) -> str:
    """Reduce Markdown/HTML to plain prose so the token budget goes to content."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)           # code blocks
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)            # images / badges
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)         # links -> text
    text = re.sub(r"<[^>]+>", " ", text)                         # html tags
    text = re.sub(r"^\s*\|.*\|\s*$", " ", text, flags=re.M)      # tables
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


_IMG_MD = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)")
_IMG_HTML = re.compile(r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
_IMG_SKIP = re.compile(
    r"shields\.io|badge|badgen|codecov|travis-ci|circleci|/workflows/|/actions/|contrib\.rocks|"
    r"star-history|deploy|button|logo|icon|avatar|sponsor|\.svg(\?|$)|data:image", re.I)


def find_image(raw: str, full_name: str) -> str | None:
    """First screenshot-like image in a README, as an absolute URL."""
    candidates = []
    for m in _IMG_HTML.finditer(raw):
        width = re.search(r"\bwidth=[\"']?(\d+)", m.group(0))
        if width and int(width.group(1)) < 200:
            continue  # small images are logos/icons
        candidates.append((m.start(), m.group(1)))
    candidates += [(m.start(), m.group(1)) for m in _IMG_MD.finditer(raw)]
    for _, url in sorted(candidates):
        if _IMG_SKIP.search(url):
            continue
        if url.startswith("//"):
            url = "https:" + url
        elif not url.startswith(("http://", "https://")):
            url = f"https://raw.githubusercontent.com/{full_name}/HEAD/{url.lstrip('./')}"
        m = re.match(r"https://github\.com/([^/]+/[^/]+)/(?:blob|raw)/(.+)", url)
        if m:
            url = f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}"
        return url
    return None


def social_card(full_name: str) -> str:
    """GitHub's generated social preview card - exists for every repository."""
    return f"https://opengraph.githubassets.com/1/{full_name}"


def fetch_readme_raw(full_name: str) -> str:
    try:
        return _get(f"https://api.github.com/repos/{urllib.parse.quote(full_name)}/readme",
                    "application/vnd.github.raw+json")
    except Exception:
        return ""


def fetch_readme(full_name: str) -> str:
    return clean_readme(fetch_readme_raw(full_name))


# --- cache ------------------------------------------------------------------

def load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"articles": {}, "blurbs": {}}


def save_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def _fresh(entry: dict | None, today: dt.date, ttl: int) -> bool:
    return bool(entry) and (today - dt.date.fromisoformat(entry["date"])).days < ttl


def plan(daily: list[dict], cache: dict, today: dt.date, layout: dict):
    """Which repos need a new article / blurb today, given the day's layout."""
    top = (pick(daily, [layout["top"]]) or [None])[0]
    rising, rest = pick(daily, layout.get("rising", [])), pick(daily, layout.get("fresh", []))
    article = top if top and not _fresh(cache["articles"].get(top["full_name"]), today, ARTICLE_TTL_DAYS) else None
    blurbs = []
    for repo, long in [(r, True) for r in rising] + [(r, False) for r in rest]:
        entry = cache["blurbs"].get(repo["full_name"])
        if not _fresh(entry, today, BLURB_TTL_DAYS) or (long and not entry.get("long")):
            blurbs.append((repo, long))
    return article, blurbs


# --- Claude calls -------------------------------------------------------------

def _meta_block(repo: dict) -> str:
    fields = {
        "repository": repo["full_name"],
        "description": repo.get("description") or "",
        "language": repo.get("language") or "",
        "topics": ", ".join(repo.get("topics") or []),
    }
    return "\n".join(f"{k}: {v}" for k, v in fields.items() if v)


def _json_text(response) -> dict:
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"unexpected stop_reason: {response.stop_reason}")
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def write_article(client, repo: dict, readme: str, usage) -> dict:
    """`readme` is the raw README; it is cleaned here and scanned for an image."""
    image = find_image(readme, repo["full_name"])
    readme = clean_readme(readme)
    response = client.beta.messages.create(
        model=ARTICLE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=ARTICLE_SYSTEM,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": ARTICLE_SCHEMA}},
        messages=[{"role": "user", "content": (
            "Write today's top story about this repository. Make it rich and informative, "
            "like the lead article of a newspaper.\n\n"
            f"{_meta_block(repo)}\n\nREADME (truncated):\n{readme[:README_CHARS['article']] or '(none)'}"
        )}],
    )
    usage.record(response)
    art = _json_text(response)
    art["sections"] = [{"heading": x["heading"].strip(), "text": x["text"].strip()}
                       for x in art["sections"] if x["text"].strip()]
    art["highlights"] = [h.strip() for h in art["highlights"] if h.strip()]
    if not is_korean(art["headline"] + art["lead"]) or not art["sections"]:
        raise RuntimeError("article is empty or not Korean")
    art["image"] = image
    return art


def write_blurbs(client, items: list[tuple[dict, bool, str]], usage) -> dict[str, str]:
    blocks = []
    for i, (repo, long, readme) in enumerate(items):
        length = "3-4 sentences" if long else "2-3 sentences"
        blocks.append(f"### id {i} ({length})\n{_meta_block(repo)}\nREADME (truncated):\n{readme or '(none)'}")
    response = client.messages.create(
        model=BLURB_MODEL,
        max_tokens=16000,
        system=BLURB_SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": BLURB_SCHEMA}},
        messages=[{"role": "user", "content": (
            "Write one Korean introduction per id, with the requested length.\n\n" + "\n\n".join(blocks)
        )}],
    )
    usage.record(response)
    out = {}
    for entry in _json_text(response)["items"]:
        idx, text = entry["id"], entry["summary"].strip()
        if 0 <= idx < len(items) and is_korean(text):
            out[items[idx][0]["full_name"]] = text
    return out


def write_stories(daily: list[dict], cache: dict, today: dt.date, usage, client=None,
                  readme=fetch_readme_raw, log=print, layout: dict | None = None) -> int:
    """Fill `cache` with today's missing stories. Returns how many were written.

    `readme` returns the raw README for a repository.
    """
    if layout is None:
        from .editorial import build_layout
        layout = build_layout({"trending": {"daily": daily}}, [])
    article_repo, blurb_jobs = plan(daily, cache, today, layout)
    if not article_repo and not blurb_jobs:
        log("stories: all cached")
        return 0
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            log("stories: ANTHROPIC_API_KEY not set, skipping")
            return 0
        import anthropic

        client = anthropic.Anthropic()

    written = 0
    if article_repo:
        try:
            art = write_article(client, article_repo, readme(article_repo["full_name"]), usage)
            cache["articles"][article_repo["full_name"]] = {"date": today.isoformat(), **art}
            written += 1
        except Exception as exc:
            log(f"stories: article for {article_repo['full_name']} failed: {exc}")

    jobs = [(repo, long, clean_readme(readme(repo["full_name"]))[:README_CHARS["long" if long else "short"]])
            for repo, long in blurb_jobs]
    for start in range(0, len(jobs), BLURB_CHUNK):
        chunk = jobs[start:start + BLURB_CHUNK]
        try:
            result = write_blurbs(client, chunk, usage)
        except Exception as exc:
            log(f"stories: blurb chunk {start // BLURB_CHUNK + 1} failed: {exc}")
            continue
        longs = {repo["full_name"]: long for repo, long, _ in chunk}
        for name, text in result.items():
            cache["blurbs"][name] = {"date": today.isoformat(), "long": longs[name], "text": text}
        written += len(result)
    log(f"stories: article {'1' if article_repo else '0'} needed, "
        f"{len(blurb_jobs)} blurbs needed, {written} written")
    return written


def attach(repos: list[dict], cache: dict) -> None:
    for repo in repos:
        name = repo["full_name"]
        if name in cache.get("articles", {}):
            repo["article"] = cache["articles"][name]
        if name in cache.get("blurbs", {}):
            repo["blurb"] = cache["blurbs"][name]["text"]
