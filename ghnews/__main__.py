"""CLI: collect today's edition and (re)build the static site.

    python -m ghnews                 # fetch + build
    python -m ghnews --no-fetch      # rebuild site from saved data only
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from .editorial import annotate, assign_layouts
from .fetch import collect, fetch_created_dates
from .render import render_archive, render_edition, render_feed
from . import stories, translate
from .chart import build_charts, chart_for
from .usage import Usage

FEED_SIZE = 20
KST = dt.timezone(dt.timedelta(hours=9))  # editions are dated in Korean time


def load_editions(data_dir: Path) -> list[dict]:
    """All saved editions, newest first."""
    editions = []
    for path in sorted(data_dir.glob("[0-9]*.json"), reverse=True):
        editions.append(json.loads(path.read_text(encoding="utf-8")))
    return editions


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def build_site(data_dir: Path, out_dir: Path, base_url: str) -> int:
    editions = load_editions(data_dir)
    assign_layouts(editions)
    cache = translate.load_cache(data_dir / "translations.json")
    story_cache = stories.load_cache(data_dir / "stories.json")
    created = load_json(data_dir / "repos.json")
    for edition in editions:
        translate.apply(edition, cache)
        for repos in [*edition.get("trending", {}).values(), edition.get("new_arrivals", [])]:
            for r in repos:
                if r["full_name"] in created:
                    r["created"] = created[r["full_name"]]
        for repos in edition.get("trending", {}).values():
            stories.attach(repos, story_cache)
    charts = build_charts(editions)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "archive").mkdir(exist_ok=True)

    annotated = []
    for i, edition in enumerate(editions):
        daily = annotate(edition.get("trending", {}).get("daily", []), editions[i + 1:])
        annotated.append((edition, daily))
        page = render_edition(edition, daily, root="../", chart=chart_for(edition["date"], charts))
        (out_dir / "archive" / f"{edition['date']}.html").write_text(page, encoding="utf-8")

    if annotated:
        latest, daily = annotated[0]
        page = render_edition(latest, daily, chart=chart_for(latest["date"], charts))
        (out_dir / "index.html").write_text(page, encoding="utf-8")
    (out_dir / "archive.html").write_text(
        render_archive([e["date"] for e in editions]), encoding="utf-8")
    (out_dir / "feed.xml").write_text(render_feed(annotated[:FEED_SIZE], base_url), encoding="utf-8")
    (out_dir / ".nojekyll").write_text("")
    return len(editions)


API_PROBLEM_FILE = ".api_problem"


def api_problem(client=None) -> str | None:
    """A one-line reason when the Claude API cannot be used at all (bad key, no access); None when it can.

    One free call up front, so a dead key is reported once and clearly instead of failing every request.
    """
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None                       # no key configured: the documented English-only mode
        import anthropic

        client = anthropic.Anthropic()
    try:
        client.models.retrieve(translate.MODEL)
    except Exception as exc:
        name = type(exc).__name__
        if name == "AuthenticationError":
            return ("The ANTHROPIC_API_KEY secret was rejected (401 invalid x-api-key): the key was deleted, "
                    "disabled or mistyped. Create a new key in the Claude Console and update the repository secret.")
        if name == "PermissionDeniedError":
            return "The ANTHROPIC_API_KEY secret has no permission to use the API (403). Check the key's workspace."
    return None


def enrich(edition: dict, data_dir: Path, today: dt.date) -> None:
    """Add what Claude and the GitHub API provide: creation dates, translations, stories."""
    created_path = data_dir / "repos.json"
    created = load_json(created_path)
    if fetch_created_dates(edition, created):
        save_json(created_path, created)

    problem = api_problem()
    if problem:
        # Shown as an annotation on the run, and the workflow's alert job fails so GitHub e-mails the owner.
        print(f"::error title=Claude API key problem::{problem} Today's edition is published untranslated.")
        Path(API_PROBLEM_FILE).write_text(problem, encoding="utf-8")
        return

    usage = Usage()
    cache_path = data_dir / "translations.json"
    cache = translate.load_cache(cache_path)
    if translate.translate_edition(edition, cache, usage=usage):
        translate.save_cache(cache_path, cache)

    story_path = data_dir / "stories.json"
    story_cache = stories.load_cache(story_path)
    if stories.write_stories(edition["trending"].get("daily", []), story_cache, today, usage,
                             layout=edition["layout"]):
        stories.save_cache(story_path, story_cache)
    for line in usage.report():
        print(line)


def status(data_dir: Path, today: dt.date) -> str:
    """'missing' (no edition today), 'incomplete' (translations / top article missing) or 'complete'."""
    path = data_dir / f"{today.isoformat()}.json"
    if not path.exists():
        return "missing"
    edition = json.loads(path.read_text(encoding="utf-8"))
    if translate.pending(edition, translate.load_cache(data_dir / "translations.json")):
        return "incomplete"
    top = (edition.get("layout") or {}).get("top")
    if top and top not in stories.load_cache(data_dir / "stories.json")["articles"]:
        return "incomplete"
    return "complete"


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub 트렌딩 뉴스 사이트 생성기")
    parser.add_argument("--data", default="data", type=Path, help="edition JSON directory")
    parser.add_argument("--out", default="site", type=Path, help="output directory")
    parser.add_argument("--date", help="edition date (YYYY-MM-DD), default today (KST)")
    parser.add_argument("--no-fetch", action="store_true", help="only rebuild from saved data")
    parser.add_argument("--fill", action="store_true",
                        help="complete today's saved edition (translations, stories) without re-collecting")
    parser.add_argument("--status", action="store_true", help="print whether today's edition is complete")
    parser.add_argument("--no-translate", action="store_true", help="skip Korean translation and stories")
    parser.add_argument("--base-url", default=os.environ.get("SITE_URL", "https://never2u.github.io/JerrySpace/"))
    args = parser.parse_args()
    today = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(KST).date()

    args.data.mkdir(parents=True, exist_ok=True)
    if args.status:
        print(status(args.data, today))
        return
    if args.fill:
        # Complete today's edition and, when a bad day left gaps, the two before it; nothing is collected again.
        editions = load_editions(args.data)
        assign_layouts(editions)
        recent = [e for e in editions if 0 <= (today - dt.date.fromisoformat(e["date"])).days <= 2]
        if not any(e["date"] == today.isoformat() for e in recent):
            raise SystemExit(f"no edition for {today} to fill")
        for edition in sorted(recent, key=lambda e: e["date"]):
            day = dt.date.fromisoformat(edition["date"])
            if status(args.data, day) == "incomplete":
                print(f"filling {edition['date']}")
                enrich(edition, args.data, day)
    elif not args.no_fetch:
        edition = collect(today)
        has_content = edition["trending"].get("daily") or edition["new_arrivals"]
        if has_content:
            saved = load_editions(args.data)
            earlier = [e for e in saved if e["date"] != edition["date"]]
            # A same-day re-run keeps the top story already published, if still trending.
            published = next((e.get("top_story") for e in saved if e["date"] == edition["date"]), None)
            if published in {r["full_name"] for r in edition["trending"].get("daily", [])}:
                edition["top_story"] = published
            assign_layouts(earlier + [edition])
            print(f"layout: {edition['layout']}")
            path = args.data / f"{edition['date']}.json"
            path.write_text(json.dumps(edition, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"saved {path}")
            if not args.no_translate:
                enrich(edition, args.data, today)
        else:
            print("nothing collected; keeping previous editions")

    count = build_site(args.data, args.out, args.base_url)
    print(f"built {count} edition(s) into {args.out}/")


if __name__ == "__main__":
    main()
