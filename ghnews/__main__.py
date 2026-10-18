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
from .fetch import collect
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


def build_site(data_dir: Path, out_dir: Path, base_url: str) -> int:
    editions = load_editions(data_dir)
    assign_layouts(editions)
    cache = translate.load_cache(data_dir / "translations.json")
    story_cache = stories.load_cache(data_dir / "stories.json")
    for edition in editions:
        translate.apply(edition, cache)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub 트렌딩 뉴스 사이트 생성기")
    parser.add_argument("--data", default="data", type=Path, help="edition JSON directory")
    parser.add_argument("--out", default="site", type=Path, help="output directory")
    parser.add_argument("--date", help="edition date (YYYY-MM-DD), default today (KST)")
    parser.add_argument("--no-fetch", action="store_true", help="only rebuild from saved data")
    parser.add_argument("--no-translate", action="store_true", help="skip Korean translation and stories")
    parser.add_argument("--base-url", default=os.environ.get("SITE_URL", "https://never2u.github.io/JerrySpace/"))
    args = parser.parse_args()

    args.data.mkdir(parents=True, exist_ok=True)
    if not args.no_fetch:
        today = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(KST).date()
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
                usage = Usage()
                cache_path = args.data / "translations.json"
                cache = translate.load_cache(cache_path)
                if translate.translate_edition(edition, cache, usage=usage):
                    translate.save_cache(cache_path, cache)

                story_path = args.data / "stories.json"
                story_cache = stories.load_cache(story_path)
                if stories.write_stories(edition["trending"].get("daily", []), story_cache, today, usage,
                                         layout=edition["layout"]):
                    stories.save_cache(story_path, story_cache)
                for line in usage.report():
                    print(line)
        else:
            print("nothing collected; keeping previous editions")

    count = build_site(args.data, args.out, args.base_url)
    print(f"built {count} edition(s) into {args.out}/")


if __name__ == "__main__":
    main()
