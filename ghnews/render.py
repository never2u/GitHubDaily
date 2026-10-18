"""Render editions to static HTML pages and an RSS feed."""

from __future__ import annotations

import datetime as dt
from email.utils import format_datetime
from html import escape

from .editorial import briefing, fmt_num, headline_for, language_breakdown, pick

SITE_TITLE = "깃허브 데일리"
SITE_TAGLINE = "오늘 GitHub에서 가장 뜨거운 오픈소스 소식"

PERIOD_LABELS = {"daily": "오늘", "weekly": "이번 주", "monthly": "이번 달"}
GAIN_LABELS = {"daily": "오늘", "weekly": "이번 주", "monthly": "이번 달"}

WEEKDAYS = "월화수목금토일"

PUBLISHER = "데이드림"
# Publisher e-mail, reversed and base64-encoded so it never appears in the page
# source (or this repo) as plain text; the page decodes it only on click.
PUBLISHER_MAIL = "bW9jLmxpYW1nQDc3ZG5hbHJldmVu"

CSS = """
:root{--bg:#f7f5f0;--paper:#fffdf8;--ink:#1d1b16;--muted:#6b665c;--rule:#d9d3c5;
--accent:#b3261e;--accent-ink:#fff;--chip:#ece7db;--up:#1a7f37;--new:#b3261e;--star:#a86500}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15140f;--paper:#1c1b16;
--ink:#ece8de;--muted:#a49e90;--rule:#3a372e;--accent:#ff8a7a;--accent-ink:#1c1b16;--chip:#2a2821;
--up:#56d364;--new:#ff8a7a;--star:#e3b341}}
:root[data-theme="dark"]{--bg:#15140f;--paper:#1c1b16;--ink:#ece8de;--muted:#a49e90;--rule:#3a372e;
--accent:#ff8a7a;--accent-ink:#1c1b16;--chip:#2a2821;--up:#56d364;--new:#ff8a7a;--star:#e3b341}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 "Pretendard","Apple SD Gothic Neo","Noto Sans KR",system-ui,sans-serif}
a{color:inherit}
.wrap{max-width:1120px;margin:0 auto;padding:0 16px}
header.mast{border-bottom:3px double var(--ink);padding:28px 0 12px;text-align:center}
.mast h1{font:900 clamp(2.2rem,7vw,4rem)/1 "Noto Serif KR",Georgia,serif;margin:0;letter-spacing:-.02em}
.mast h1 a{text-decoration:none}
.mast .tag{color:var(--muted);margin:8px 0 0}
.dateline{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;border-bottom:1px solid var(--ink);
padding:6px 0;font-size:.85rem;color:var(--muted)}
.dateline a{text-decoration:none}
.brief{background:var(--paper);border:1px solid var(--rule);padding:16px 20px;margin:24px 0}
.brief h2{margin:0 0 8px;font-size:.8rem;letter-spacing:.12em;color:var(--accent)}
.brief ul{margin:0;padding-left:1.2em}
.lead{display:grid;grid-template-columns:2fr 1fr;gap:24px;margin:24px 0;padding-bottom:24px;
border-bottom:1px solid var(--rule)}
.lead .kicker{color:var(--accent);font-weight:700;font-size:.8rem;letter-spacing:.1em}
.lead h2{font:800 clamp(1.6rem,4vw,2.4rem)/1.2 "Noto Serif KR",Georgia,serif;margin:6px 0 12px}
.lead h2 a{text-decoration:none}
.lead p.desc{font-size:1.1rem;margin:0 0 12px}
.side h3{font-size:.8rem;letter-spacing:.1em;margin:0 0 8px;color:var(--muted)}
.side ol{margin:0;padding:0;list-style:none}
.side li{border-top:1px solid var(--rule);padding:10px 0}
.side li a{font-weight:700;text-decoration:none}
.meta{display:flex;flex-wrap:wrap;gap:12px;color:var(--muted);font-size:.85rem}
.meta .gain{color:var(--star);font-weight:700}
.badge{display:inline-block;font-size:.7rem;font-weight:700;padding:1px 6px;border-radius:3px;
vertical-align:middle;margin-left:6px}
.badge.new{background:var(--new);color:var(--accent-ink)}
.badge.up{color:var(--up);border:1px solid var(--up)}
.badge.streak{border:1px solid var(--muted);color:var(--muted)}
section{margin:32px 0}
section>h2{font:800 1.4rem "Noto Serif KR",Georgia,serif;border-top:3px solid var(--ink);padding-top:8px;
margin:0 0 4px}
section>.sub{color:var(--muted);margin:0 0 16px;font-size:.9rem}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 16px}
.filters button{border:1px solid var(--rule);background:var(--chip);color:var(--ink);border-radius:999px;
padding:4px 12px;font:inherit;font-size:.85rem;cursor:pointer}
.filters button[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:0 24px}
.card{border-top:1px solid var(--rule);padding:14px 0}
.card .rank{font:800 1.1rem Georgia,serif;color:var(--muted);margin-right:6px}
.card h3{margin:0 0 4px;font-size:1.05rem;line-height:1.35;overflow-wrap:anywhere}
.card h3 a{text-decoration:none}
.card .hl{margin:0 0 6px;font-weight:600}
.card p{margin:0 0 8px;color:var(--ink);opacity:.85;font-size:.93rem}
.topics{display:flex;flex-wrap:wrap;gap:4px;margin:0 0 6px}
.topics span{background:var(--chip);font-size:.72rem;padding:1px 6px;border-radius:3px}
.langbar{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:8px 0}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.8rem;color:var(--muted)}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px}
.archive li{margin:4px 0}
.article .lead-p{font-size:1.12rem;font-weight:600;margin:0 0 12px}
.article p{margin:0 0 12px}
.facts{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.85rem;color:var(--muted);margin:0 0 14px}
.facts b{color:var(--star)}
.points{background:var(--paper);border:1px solid var(--rule);padding:12px 16px;margin:4px 0 16px}
.points h4{margin:0 0 6px;font-size:.78rem;letter-spacing:.1em;color:var(--accent)}
.points ul{margin:0;padding-left:1.2em}
.side .blurb{font-size:.9rem;margin:4px 0}
.deck{font-size:1.1rem;color:var(--muted);margin:-4px 0 10px}
.hero{margin:6px 0 14px}
.hero img{display:block;width:100%;max-height:440px;object-fit:contain;background:var(--paper);
border:1px solid var(--rule);border-radius:4px}
.hero figcaption{font-size:.8rem;color:var(--muted);margin-top:6px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:1px;background:var(--rule);
border:1px solid var(--rule);margin:0 0 16px}
.stats div{background:var(--paper);padding:10px 12px}
.stats b{display:block;font:800 1.3rem Georgia,serif;color:var(--star)}
.stats span{font-size:.75rem;color:var(--muted)}
.article h3{font-size:1.05rem;margin:18px 0 6px}
.builders h4{margin:0 0 8px;font-size:.78rem;letter-spacing:.1em;color:var(--muted)}
.builders div{display:flex;flex-wrap:wrap;gap:10px 16px;margin-bottom:12px}
.builders a{display:flex;align-items:center;gap:6px;text-decoration:none;font-size:.85rem}
.builders img{width:28px;height:28px;border-radius:50%;background:var(--chip)}
.cta a{font-weight:700}
.compact{list-style:none;margin:0;padding:0;columns:2 320px;column-gap:32px}
.compact li{break-inside:avoid;display:flex;gap:10px;align-items:baseline;border-top:1px solid var(--rule);
padding:8px 0;font-size:.92rem}
.compact .n{font:800 1rem Georgia,serif;color:var(--muted);min-width:1.4em;text-align:right}
.compact a{font-weight:700;text-decoration:none;overflow-wrap:anywhere}
.compact small{color:var(--muted);margin-left:auto;white-space:nowrap;padding-left:8px}
.compact small b{color:var(--star)}
.steady{margin-top:20px}
.steady h3{font-size:.8rem;letter-spacing:.1em;color:var(--muted);margin:0 0 6px}
.quiet{color:var(--muted);font-size:.92rem;margin:0}
.chart{width:100%;border-collapse:collapse}
.chart td{border-top:1px solid var(--rule);padding:10px 8px;vertical-align:top}
.chart .pos{font:800 1.4rem Georgia,serif;width:2.2em;text-align:center}
.chart .mv{width:4.5em;font-size:.8rem;font-weight:700;text-align:center;white-space:nowrap}
.mv.up{color:var(--up)}.mv.down{color:var(--accent)}.mv.same{color:var(--muted)}
.mv.new{color:var(--new)}
.chart .name a{font-weight:700;text-decoration:none;overflow-wrap:anywhere}
.chart .name p{margin:2px 0 0;font-size:.88rem;opacity:.85}
.chart .stat{font-size:.8rem;color:var(--muted);white-space:nowrap;text-align:right}
.chart tr.no1 .pos{color:var(--accent)}
.crown{display:inline-block;font-size:.72rem;font-weight:700;background:var(--accent);color:var(--accent-ink);
padding:1px 6px;border-radius:3px;margin-left:6px}
footer .pub{color:var(--ink);font-weight:700}
footer button{font:inherit;color:inherit;background:none;border:0;padding:0;text-decoration:underline;cursor:pointer}
@media (max-width:600px){.chart .stat{display:none}}
footer{border-top:3px double var(--ink);margin-top:48px;padding:16px 0 40px;color:var(--muted);font-size:.85rem}
.notice{background:var(--chip);padding:8px 12px;font-size:.85rem;margin:16px 0}
@media (max-width:760px){.lead{grid-template-columns:1fr}}
"""

FILTER_JS = """
document.querySelectorAll('[data-m]').forEach(function(b){
  b.addEventListener('click',function(){
    var a=atob(b.dataset.m).split('').reverse().join('');
    location.href='mai'+'lto:'+a;
  });
});
document.querySelectorAll('[data-filter-for]').forEach(function(bar){
  var grid=document.getElementById(bar.dataset.filterFor);
  bar.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b) return;
    bar.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed',x===b)});
    var lang=b.dataset.lang;
    grid.querySelectorAll('.card').forEach(function(c){
      c.hidden = lang!=='*' && c.dataset.lang!==lang;
    });
  });
});
"""

LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Go": "#00ADD8",
    "Rust": "#dea584", "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "C#": "#178600",
    "Swift": "#F05138", "Kotlin": "#A97BFF", "Ruby": "#701516", "PHP": "#4F5D95", "Shell": "#89e051",
    "Jupyter Notebook": "#DA5B0B", "HTML": "#e34c26", "CSS": "#563d7c", "Dart": "#00B4AB",
    "Zig": "#ec915c", "Vue": "#41b883", "Lua": "#000080", "MDX": "#fcb32c",
}


def korean_date(d: dt.date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def _badges(repo: dict) -> str:
    out = []
    if repo.get("is_new"):
        out.append('<span class="badge new">NEW</span>')
    elif repo.get("rank_delta", 0) > 0:
        out.append(f'<span class="badge up">▲{repo["rank_delta"]}</span>')
    if repo.get("streak", 1) >= 3:
        out.append(f'<span class="badge streak">{repo["streak"]}일 연속</span>')
    return "".join(out)


def _meta(repo: dict, gain_label: str | None) -> str:
    parts = []
    if repo.get("language"):
        color = LANG_COLORS.get(repo["language"], "#8b8b8b")
        parts.append(f'<span><i style="display:inline-block;width:9px;height:9px;border-radius:50%;'
                     f'background:{color};margin-right:4px"></i>{escape(repo["language"])}</span>')
    parts.append(f'<span>★ {fmt_num(repo.get("stars", 0))}</span>')
    if repo.get("forks"):
        parts.append(f'<span>⑂ {fmt_num(repo["forks"])}</span>')
    if gain_label and repo.get("stars_gained"):
        parts.append(f'<span class="gain">+{fmt_num(repo["stars_gained"])} {gain_label}</span>')
    return f'<div class="meta">{"".join(parts)}</div>'


def _desc(repo: dict) -> str:
    """Korean description when available; the English original goes in a tooltip."""
    ko, en = repo.get("description_ko"), repo.get("description") or ""
    if ko:
        return f'<span title="{escape(en)}" lang="ko">{escape(ko)}</span>'
    return f'<span lang="en">{escape(en)}</span>' if en else ""


def _intro(repo: dict) -> str:
    """AI-written introduction when available, else the (translated) description."""
    if repo.get("blurb"):
        return escape(repo["blurb"])
    if repo.get("article"):
        return escape(repo["article"]["lead"])
    return _desc(repo)


def _card(repo: dict, gain_label: str | None, with_headline: bool = False) -> str:
    lang = escape(repo.get("language") or "기타")
    topics = repo.get("topics") or []
    topics_html = (
        '<div class="topics">' + "".join(f"<span>{escape(t)}</span>" for t in topics) + "</div>"
        if topics else ""
    )
    hl = f'<p class="hl">{escape(headline_for(repo))}</p>' if with_headline else ""
    intro = _intro(repo)
    desc = f"<p>{intro}</p>" if intro else ""
    return (
        f'<article class="card" data-lang="{lang}">'
        f'<h3><span class="rank">{repo["rank"]}</span>'
        f'<a href="{escape(repo["url"])}" target="_blank" rel="noopener">{escape(repo["full_name"])}</a>'
        f"{_badges(repo)}</h3>{hl}{desc}{topics_html}{_meta(repo, gain_label)}</article>"
    )


def _filters(grid_id: str, repos: list[dict]) -> str:
    langs = [l for l, _ in language_breakdown(repos, top=8)]
    buttons = ['<button type="button" data-lang="*" aria-pressed="true">전체</button>']
    buttons += [f'<button type="button" data-lang="{escape(l)}" aria-pressed="false">{escape(l)}</button>'
                for l in langs]
    return f'<div class="filters" data-filter-for="{grid_id}">{"".join(buttons)}</div>'


def _section(sec_id: str, title: str, sub: str, repos: list[dict], gain_label: str | None,
             headlines: bool = False, filters: bool = True) -> str:
    if not repos:
        return ""
    cards = "".join(_card(r, gain_label, headlines) for r in repos)
    grid_id = f"grid-{sec_id}"
    return (
        f'<section id="{sec_id}"><h2>{escape(title)}</h2><p class="sub">{escape(sub)}</p>'
        f'{_filters(grid_id, repos) if filters else ""}<div class="grid" id="{grid_id}">{cards}</div></section>'
    )


def _lang_bar(repos: list[dict]) -> str:
    breakdown = language_breakdown(repos, top=8)
    total = sum(c for _, c in breakdown) or 1
    bar = "".join(
        f'<span title="{escape(l)} {c}" style="width:{c / total * 100:.2f}%;'
        f'background:{LANG_COLORS.get(l, "#8b8b8b")}"></span>'
        for l, c in breakdown
    )
    legend = "".join(
        f'<span><i style="background:{LANG_COLORS.get(l, "#8b8b8b")}"></i>{escape(l)} {c}</span>'
        for l, c in breakdown
    )
    return f'<div class="langbar">{bar}</div><div class="legend">{legend}</div>'


def _page(title: str, body: str, root: str, date: dt.date) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(SITE_TAGLINE)}">
<link rel="alternate" type="application/rss+xml" title="{SITE_TITLE}" href="{root}feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700;900&family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="mast">
<h1><a href="{root}index.html">{SITE_TITLE}</a></h1>
<p class="tag">{SITE_TAGLINE}</p>
</header>
<div class="dateline"><span>{korean_date(date)}</span>
<span><a href="{root}archive.html">지난 호 보기</a> · <a href="{root}feed.xml">RSS</a></span></div>
{body}
<footer><p>발행인 <span class="pub">{PUBLISHER}</span> ·
<button type="button" data-m="{PUBLISHER_MAIL}">메일 보내기</button></p>
<p>데이터 출처: github.com/trending, GitHub Search API · 매일 오전 8시 발행 ·
<a href="https://github.com/never2u/JerrySpace">소스 코드</a></p></footer>
</div>
<script>{FILTER_JS}</script>
</body>
</html>
"""


def _hero(top: dict, art: dict | None) -> str:
    """Main image: the README screenshot when found, else GitHub's social card."""
    card = f"https://opengraph.githubassets.com/1/{top['full_name']}"
    src = (art or {}).get("image") or card
    caption = (art or {}).get("image_caption") or f"{top['full_name']} 소개 이미지"
    source = "README" if (art or {}).get("image") else "GitHub"
    return (f'<figure class="hero"><img src="{escape(src)}" alt="{escape(caption)}" loading="eager" '
            f'referrerpolicy="no-referrer" onerror="this.onerror=null;this.src=\'{escape(card)}\'">'
            f'<figcaption>{escape(caption)} <span>· 이미지 출처: {source}</span></figcaption></figure>')


def _stat_box(top: dict) -> str:
    cells = [("오늘 받은 별", f'+{fmt_num(top.get("stars_gained", 0))}'),
             ("누적 별", fmt_num(top.get("stars", 0))),
             ("포크", fmt_num(top.get("forks", 0)))]
    if top.get("streak", 1) >= 2:
        cells.append(("트렌딩", f'{top["streak"]}일째'))
    if top.get("language"):
        cells.append(("언어", escape(top["language"])))
    return '<div class="stats">' + "".join(
        f'<div><b>{v}</b><span>{k}</span></div>' for k, v in cells) + "</div>"


def _builders(top: dict) -> str:
    people = [p for p in top.get("built_by", []) if p and p != "claude"][:5]
    if not people:
        return ""
    faces = "".join(
        f'<a href="https://github.com/{escape(p)}" target="_blank" rel="noopener" title="{escape(p)}">'
        f'<img src="https://github.com/{escape(p)}.png?size=64" alt="{escape(p)}" loading="lazy" '
        f'referrerpolicy="no-referrer"><span>{escape(p)}</span></a>' for p in people)
    return f'<div class="builders"><h4>만든 사람들</h4><div>{faces}</div></div>'


def _top_story(top: dict) -> str:
    """Headline, image, numbers, the full article (when written) and the makers."""
    link = f'href="{escape(top["url"])}" target="_blank" rel="noopener"'
    name_line = (f'<div class="facts"><span><strong>{escape(top["full_name"])}</strong>{_badges(top)}</span>'
                 f'<span>{escape(headline_for(top))}</span></div>')
    art = top.get("article")
    if not art:
        return (f'<h2><a {link}>{escape(headline_for(top))}</a></h2>{name_line}{_hero(top, None)}'
                f'{_stat_box(top)}<p class="desc">{_intro(top) or "설명이 없는 저장소입니다."}</p>'
                f'{_builders(top)}<p class="cta"><a {link}>저장소 바로가기 →</a></p>')
    if art.get("sections"):
        body = "".join(f'<h3>{escape(x["heading"])}</h3><p>{escape(x["text"])}</p>' for x in art["sections"])
    else:  # articles cached before sections existed
        body = "".join(f"<p>{escape(p)}</p>" for p in art.get("body", []))
    points = "".join(f"<li>{escape(h)}</li>" for h in art.get("highlights", []))
    points_html = f'<div class="points"><h4>핵심 포인트</h4><ul>{points}</ul></div>' if points else ""
    deck = f'<p class="deck">{escape(art["subheadline"])}</p>' if art.get("subheadline") else ""
    return (f'<h2><a {link}>{escape(art["headline"])}</a></h2>{deck}{name_line}{_hero(top, art)}'
            f'{_stat_box(top)}<div class="article"><p class="lead-p">{escape(art["lead"])}</p>{body}</div>'
            f'{points_html}{_builders(top)}<p class="cta"><a {link}>저장소 바로가기 →</a></p>')


def _compact_list(repos: list[dict], gain_label: str, numbered: bool = True, streak: bool = False) -> str:
    """One line per repo: rank, name and a number - for sections that may repeat."""
    items = []
    for i, r in enumerate(repos, start=1):
        extra = f' · {r["streak"]}일째' if streak and r.get("streak", 1) >= 2 else ""
        items.append(
            f'<li>{f"<span class=n>{i}</span>" if numbered else ""}'
            f'<a href="{escape(r["url"])}" target="_blank" rel="noopener">{escape(r["full_name"])}</a>'
            f'<small><b>★ +{fmt_num(r.get("stars_gained", 0))}</b> {gain_label}{extra}</small></li>')
    return f'<ol class="compact">{"".join(items)}</ol>'


def _movement(e: dict, has_previous: bool) -> str:
    if not has_previous:
        return '<td class="mv same">첫 차트</td>'
    if e["is_new"]:
        return '<td class="mv new">NEW</td>'
    if e["re_entry"]:
        return '<td class="mv new">재진입</td>'
    if e["delta"] > 0:
        return f'<td class="mv up">▲ {e["delta"]}</td>'
    if e["delta"] < 0:
        return f'<td class="mv down">▼ {-e["delta"]}</td>'
    return '<td class="mv same">–</td>'


CHART_SHOWN = 10


def _chart_section(chart: dict | None) -> str:
    if not chart or not chart["entries"]:
        return ""
    d = dt.date.fromisoformat(chart["date"])
    monday = d - dt.timedelta(days=d.weekday())
    rows = []
    for e in chart["entries"][:CHART_SHOWN]:
        crown = ""
        if e["rank"] == 1 and e.get("no1_weeks", 1) >= 2:
            crown = f'<span class="crown">{e["no1_weeks"]}주 연속 1위</span>'
        elif e["rank"] == 1 and chart["has_previous"]:
            crown = '<span class="crown">새 1위</span>'
        intro = _desc(e)  # charts repeat week to week: keep it to the one-line description
        rows.append(
            f'<tr class="{"no1" if e["rank"] == 1 else ""}"><td class="pos">{e["rank"]}</td>'
            f'{_movement(e, chart["has_previous"])}'
            f'<td class="name"><a href="{escape(e["url"])}" target="_blank" rel="noopener">'
            f'{escape(e["full_name"])}</a>{crown}{f"<p>{intro}</p>" if intro else ""}</td>'
            f'<td class="stat">★ +{fmt_num(e.get("stars_gained", 0))} 주간<br>'
            f'최고 {e["peak"]}위 · 차트 {e["weeks"]}주</td></tr>'
        )
    sub = (f"{monday.month}월 {monday.day}일 주간 · 매주 월요일 갱신 · 일주일간 받은 별 순위"
           + (" · 순위 변동은 지난주 차트 대비" if chart["has_previous"] else ""))
    return (f'<section id="chart"><h2>주간 인기 차트 Top {min(CHART_SHOWN, len(chart["entries"]))}</h2><p class="sub">{escape(sub)}</p>'
            f'<table class="chart"><tbody>{"".join(rows)}</tbody></table></section>')


def render_edition(edition: dict, daily: list[dict], root: str = "", chart: dict | None = None) -> str:
    date = dt.date.fromisoformat(edition["date"])
    trending = edition.get("trending", {})
    parts = []

    if edition.get("fallback"):
        parts.append('<p class="notice">오늘은 트렌딩 페이지를 가져오지 못해 최근 생성된 인기 저장소로 대신합니다.</p>')

    lines = briefing(edition, daily)
    if lines:
        parts.append('<aside class="brief"><h2>오늘의 브리핑</h2><ul>'
                     + "".join(f"<li>{escape(l)}</li>" for l in lines) + "</ul></aside>")

    layout = edition.get("layout") or {}
    if daily:
        top = (pick(daily, [layout.get("top")]) or daily[:1])[0]
        runners = pick(daily, layout.get("rising", []))
        side = "".join(
            f'<li><a href="{escape(r["url"])}" target="_blank" rel="noopener">{escape(r["full_name"])}</a>'
            f'{_badges(r)}<div>{escape(headline_for(r))}</div>'
            f'{f"<p class=blurb>{_intro(r)}</p>" if _intro(r) else ""}{_meta(r, "오늘")}</li>'
            for r in runners
        ) or '<li><p class="quiet">오늘은 새로 떠오른 저장소가 없습니다.</p></li>'
        parts.append(
            '<div class="lead"><div>'
            '<div class="kicker">오늘의 톱뉴스</div>'
            f'{_top_story(top)}'
            '<h3 style="margin:20px 0 4px;font-size:.8rem;letter-spacing:.1em;color:var(--muted)">오늘의 언어 지형</h3>'
            f'{_lang_bar(daily)}'
            '</div><div class="side"><h3>함께 떠오르는 저장소</h3>'
            f'<ol>{side}</ol></div></div>'
        )

        fresh, steady = pick(daily, layout.get("fresh", [])), pick(daily, layout.get("steady", []))
        cards = "".join(_card(r, "오늘", True) for r in fresh) if fresh else ""
        body = (f'<div class="grid">{cards}</div>' if cards
                else '<p class="quiet">오늘은 새로 트렌딩에 오른 저장소가 없습니다.</p>')
        if steady:
            body += ('<div class="steady"><h3>계속 트렌딩 중</h3>'
                     f'{_compact_list(steady, "오늘", numbered=False, streak=True)}</div>')
        parts.append('<section id="daily"><h2>오늘의 트렌딩</h2>'
                     '<p class="sub">오늘 새로 트렌딩에 오른 저장소 · 이미 소개한 저장소는 한 줄로 모았습니다</p>'
                     f'{body}</section>')

    arrivals = pick(edition.get("new_arrivals", []), layout.get("arrivals", [])) if layout \
        else edition.get("new_arrivals", [])[:4]
    parts.append(_section("new", "주목받는 신작", "최근 7일 안에 만들어진 저장소 중 아직 소개하지 않은 것",
                          arrivals, None, filters=False))
    parts.append(_chart_section(chart))
    monthly = trending.get("monthly", [])[:10]
    if monthly:
        parts.append('<section id="monthly"><h2>이번 달 결산 Top 10</h2>'
                     '<p class="sub">지난 30일간 별을 가장 많이 받은 저장소</p>'
                     f'{_compact_list(monthly, "이번 달")}</section>')

    if not daily and not any(trending.values()):
        parts.append('<p class="notice">이번 호에는 수집된 소식이 없습니다.</p>')

    return _page(f"{SITE_TITLE} — {korean_date(date)}", "".join(parts), root, date)


def render_archive(dates: list[str]) -> str:
    items = "".join(
        f'<li><a href="archive/{d}.html">{korean_date(dt.date.fromisoformat(d))}</a></li>' for d in dates
    )
    body = f'<section><h2>지난 호</h2><p class="sub">발행된 모든 호 목록</p><ul class="archive">{items}</ul></section>'
    latest = dt.date.fromisoformat(dates[0]) if dates else dt.date.today()
    return _page(f"{SITE_TITLE} — 지난 호", body, "", latest)


def render_feed(editions: list[tuple[dict, list[dict]]], base_url: str) -> str:
    base_url = base_url.rstrip("/") + "/"
    items = []
    for edition, daily in editions:
        date = dt.date.fromisoformat(edition["date"])
        pub = format_datetime(dt.datetime.combine(date, dt.time(9, 0), dt.timezone.utc))
        link = f"{base_url}archive/{edition['date']}.html"
        top = sorted(daily, key=lambda r: -r.get("stars_gained", 0))[:10]
        desc = "<ul>" + "".join(f"<li>{escape(l)}</li>" for l in briefing(edition, daily)) + "</ul><ol>" + "".join(
            f'<li><a href="{escape(r["url"])}">{escape(r["full_name"])}</a> — '
            f'{escape(headline_for(r))}</li>' for r in top) + "</ol>"
        lead = (pick(daily, [(edition.get("layout") or {}).get("top")]) or daily[:1] or [None])[0]
        art = (lead or {}).get("article")
        if art:
            desc = f"<p><strong>{escape(art['headline'])}</strong> — {escape(art['lead'])}</p>" + desc
        title = (art["headline"] if art else headline_for(top[0])) if top else "오늘의 GitHub 소식"
        items.append(
            f"<item><title>{escape(f'[{korean_date(date)}] {title}')}</title>"
            f"<link>{escape(link)}</link><guid isPermaLink=\"true\">{escape(link)}</guid>"
            f"<pubDate>{pub}</pubDate><description>{escape(desc)}</description></item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>{SITE_TITLE}</title><link>{escape(base_url)}</link>"
        f"<description>{SITE_TAGLINE}</description><language>ko</language>"
        + "".join(items) + "</channel></rss>\n"
    )
