import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ghnews import stories
from ghnews.__main__ import build_site
from ghnews.chart import build_charts, chart_for
from ghnews.usage import Usage

TODAY = dt.date(2026, 10, 19)


def repo(name, gained=10):
    return {"full_name": name, "rank": 1, "url": f"https://github.com/{name}", "description": "desc",
            "language": "Go", "stars": 100, "forks": 1, "stars_gained": gained}


def ed(date, weekly, daily=()):
    return {"date": date, "trending": {"daily": [repo(n) for n in daily], "weekly": [repo(n) for n in weekly]},
            "new_arrivals": []}


class ChartTest(unittest.TestCase):
    def test_weekly_movement(self):
        editions = [
            ed("2026-10-05", ["a", "b", "c"]),          # Mon, week 41
            ed("2026-10-07", ["z", "y"]),               # same week: ignored
            ed("2026-10-12", ["a", "c", "d"]),          # week 42
            ed("2026-10-19", ["a", "d", "b"]),          # week 43
        ]
        charts = build_charts(editions)
        self.assertEqual([c["date"] for c in charts], ["2026-10-05", "2026-10-12", "2026-10-19"])
        self.assertFalse(charts[0]["has_previous"])
        w43 = {e["full_name"]: e for e in charts[2]["entries"]}
        self.assertEqual(w43["a"]["no1_weeks"], 3)
        self.assertEqual(w43["d"]["delta"], 1)          # 3 -> 2
        self.assertTrue(w43["b"]["re_entry"])           # charted in wk41, absent wk42
        self.assertEqual((w43["b"]["weeks"], w43["b"]["peak"]), (2, 2))
        w42 = {e["full_name"]: e for e in charts[1]["entries"]}
        self.assertTrue(w42["d"]["is_new"])
        self.assertEqual(w42["c"]["delta"], 1)
        self.assertEqual(chart_for("2026-10-14", charts)["date"], "2026-10-12")
        self.assertIsNone(chart_for("2026-10-01", charts))

    def test_new_leader_resets_streak(self):
        charts = build_charts([ed("2026-10-05", ["a", "b"]), ed("2026-10-12", ["b", "a"])])
        self.assertEqual(charts[1]["entries"][0]["no1_weeks"], 1)
        self.assertEqual(charts[1]["entries"][1]["delta"], -1)


class FakeClient:
    """Answers both the article (beta) and blurb calls with Korean text."""

    def __init__(self):
        self.calls = []
        self.messages = SimpleNamespace(create=self._blurbs)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._article))

    def _resp(self, model, body):
        return SimpleNamespace(model=model, stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=500),
                               content=[SimpleNamespace(type="text", text=json.dumps(body, ensure_ascii=False))])

    def _article(self, **kw):
        self.calls.append(kw)
        return self._resp(kw["model"], {"headline": "톱 기사", "lead": "요약입니다.",
                                        "body": ["첫 문단.", "둘째 문단."], "highlights": ["포인트"]})

    def _blurbs(self, **kw):
        self.calls.append(kw)
        ids = [int(line.split()[2]) for line in kw["messages"][0]["content"].splitlines() if line.startswith("### id")]
        return self._resp(kw["model"], {"items": [{"id": i, "summary": f"소개 {i}"} for i in ids]})


class StoriesTest(unittest.TestCase):
    def daily(self):
        return [repo(f"o/r{i}", gained=100 - i) for i in range(10)]

    def test_writes_article_and_blurbs_then_caches(self):
        cache, client, usage = {"articles": {}, "blurbs": {}}, FakeClient(), Usage()
        n = stories.write_stories(self.daily(), cache, TODAY, usage, client, readme=lambda _: "README", log=lambda *_: None)
        self.assertEqual(n, 10)                                   # 1 article + 9 blurbs
        art_call = client.calls[0]
        self.assertEqual(art_call["model"], "claude-sonnet-5-5")
        self.assertEqual(art_call["fallbacks"], "default")
        self.assertEqual({c["model"] for c in client.calls[1:]}, {"claude-haiku-5-5"})
        self.assertEqual(len(client.calls), 3)                    # 9 blurbs in chunks of 6
        self.assertTrue(cache["blurbs"]["o/r1"]["long"])          # rising -> long
        self.assertFalse(cache["blurbs"]["o/r9"]["long"])
        self.assertNotIn("o/r0", cache["blurbs"])                 # top story gets an article
        self.assertGreater(usage.cost(), 0)

        client2 = FakeClient()
        self.assertEqual(stories.write_stories(self.daily(), cache, TODAY, Usage(), client2,
                                               readme=lambda _: "", log=lambda *_: None), 0)
        self.assertEqual(client2.calls, [])

    def test_expiry_and_promotion(self):
        old = (TODAY - dt.timedelta(days=20)).isoformat()
        cache = {"articles": {"o/r0": {"date": old}},
                 "blurbs": {"o/r1": {"date": TODAY.isoformat(), "long": False, "text": "짧음"},
                            "o/r7": {"date": TODAY.isoformat(), "long": False, "text": "ok"}}}
        article, blurbs = stories.plan(self.daily(), cache, TODAY)
        self.assertEqual(article["full_name"], "o/r0")            # expired article
        names = [r["full_name"] for r, _ in blurbs]
        self.assertIn("o/r1", names)                              # promoted to rising: needs long
        self.assertNotIn("o/r7", names)

    def test_no_key_is_noop(self):
        import os
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            self.assertEqual(stories.write_stories(self.daily(), {"articles": {}, "blurbs": {}}, TODAY,
                                                   Usage(), log=lambda *_: None), 0)
        finally:
            if old is not None:
                os.environ["ANTHROPIC_API_KEY"] = old

    def test_clean_readme(self):
        md = "# Title\n![badge](x.svg) [link](http://a)\n```py\ncode\n```\n<p>para</p>\n| a | b |\n"
        self.assertEqual(stories.clean_readme(md), "# Title\n link\n para")


class SiteTest(unittest.TestCase):
    def test_page_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, out = Path(tmp, "data"), Path(tmp, "site")
            data.mkdir()
            e = ed("2026-10-19", ["o/r0", "o/r1"], daily=["o/r0", "o/r1"])
            e["trending"]["daily"][0]["stars_gained"] = 999
            e["new_arrivals"] = [repo("n/new")]
            Path(data, "2026-10-19.json").write_text(json.dumps(e))
            stories.save_cache(data / "stories.json", {
                "articles": {"o/r0": {"date": "2026-10-19", "headline": "AI 톱 헤드라인", "lead": "리드 문장",
                                      "body": ["본문 문단"], "highlights": ["핵심 하나"]}},
                "blurbs": {"o/r1": {"date": "2026-10-19", "long": True, "text": "떠오르는 소개"}}})
            build_site(data, out, "https://example.com/")
            html = (out / "index.html").read_text()
            for text in ("AI 톱 헤드라인", "리드 문장", "핵심 포인트", "떠오르는 소개",
                         "주간 인기 차트", "첫 차트", "주목받는 신작", "발행인", "데이드림"):
                self.assertIn(text, html)
            self.assertNotIn("갓 태어난", html)
            import base64
            from ghnews.render import PUBLISHER_MAIL
            address = base64.b64decode(PUBLISHER_MAIL).decode()[::-1]
            self.assertIn("@", address)
            self.assertNotIn(address, html)                       # never in plain text
            self.assertNotIn(address.split("@")[0], html)
            self.assertNotIn('<span lang="en">desc</span></p><div class="meta"><span><i style="display:inline-block;'
                             'width:9px;height:9px;border-radius:50%;background:#00ADD8;margin-right:4px"></i>Go</span>'
                             '<span>★ 100</span><span>⑂ 1</span><span class="gain">+999', html)  # top card uses lead
            self.assertIn("AI 톱 헤드라인", (out / "feed.xml").read_text())


if __name__ == "__main__":
    unittest.main()
