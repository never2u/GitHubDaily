import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from ghnews.__main__ import build_site
from ghnews.editorial import annotate, briefing, fmt_num, headline_for
from ghnews.fetch import parse_search, parse_trending

FIX = Path(__file__).parent / "fixtures"


def repo(name, rank, gained=10, lang="Python"):
    return {"full_name": name, "rank": rank, "url": f"https://github.com/{name}", "description": "d",
            "language": lang, "stars": 100, "forks": 1, "stars_gained": gained}


class ParseTest(unittest.TestCase):
    def test_trending(self):
        repos = parse_trending((FIX / "trending.html").read_text())
        self.assertEqual(len(repos), 2)
        r = repos[0]
        self.assertEqual(r["full_name"], "acme/rocket")
        self.assertEqual(r["description"], "Blazing fast & tiny agent framework")
        self.assertEqual(r["language"], "Python")
        self.assertEqual((r["stars"], r["forks"], r["stars_gained"]), (12345, 1024, 2101))
        self.assertEqual(r["built_by"], ["alice", "bob"])
        self.assertEqual(repos[1]["full_name"], "zed/notes")
        self.assertIsNone(repos[1]["language"])
        self.assertEqual(repos[1]["stars_gained"], 95)

    def test_search(self):
        repos = parse_search((FIX / "search.json").read_text())
        self.assertEqual([r["full_name"] for r in repos], ["new/shiny", "new/other"])
        self.assertEqual(repos[1]["description"], "")
        self.assertEqual(repos[0]["topics"], ["cli", "rust"])


class EditorialTest(unittest.TestCase):
    def test_fmt_num(self):
        self.assertEqual([fmt_num(n) for n in (5, 1234, 45678, 2_500_000)], ["5", "1.2k", "46k", "2.5M"])

    def test_annotate(self):
        history = [
            {"trending": {"daily": [repo("a/a", 1), repo("b/b", 9)]}},
            {"trending": {"daily": [repo("a/a", 2)]}},
        ]
        out = {r["full_name"]: r for r in annotate([repo("b/b", 2), repo("a/a", 1), repo("c/c", 3)], history)}
        self.assertTrue(out["c/c"]["is_new"])
        self.assertFalse(out["b/b"]["is_new"])
        self.assertEqual(out["b/b"]["rank_delta"], 7)
        self.assertEqual(out["a/a"]["streak"], 3)
        self.assertEqual(out["b/b"]["streak"], 2)

    def test_first_edition_has_no_new_badges(self):
        self.assertFalse(annotate([repo("a/a", 1)], [])[0]["is_new"])

    def test_headlines(self):
        self.assertIn("5일 연속", headline_for({**repo("a/x", 1), "streak": 5}))
        self.assertIn("신규 진입", headline_for({**repo("a/x", 1, 1500), "is_new": True}))
        self.assertIn("급상승", headline_for({**repo("a/x", 1), "rank_delta": 6}))

    def test_briefing(self):
        daily = annotate([repo("a/a", 1, 50), repo("b/b", 2, 900)], [])
        lines = briefing({"new_arrivals": []}, daily)
        self.assertIn("b/b", lines[0])


class BuildTest(unittest.TestCase):
    def test_build_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, out = Path(tmp, "data"), Path(tmp, "site")
            data.mkdir()
            trending = parse_trending((FIX / "trending.html").read_text())
            arrivals = parse_search((FIX / "search.json").read_text())
            for i, day in enumerate(["2026-10-14", "2026-10-15"]):
                ed = {"date": day, "trending": {"daily": trending[: i + 1], "weekly": trending, "monthly": []},
                      "new_arrivals": arrivals}
                Path(data, f"{day}.json").write_text(json.dumps(ed))
            self.assertEqual(build_site(data, out, "https://example.com/news"), 2)

            index = (out / "index.html").read_text()
            self.assertIn("acme/rocket", index)
            self.assertIn("NEW", index)  # zed/notes is new on the second day
            self.assertIn("2026년 10월 15일 (목)", index)
            self.assertIn("&amp;", index)
            self.assertTrue((out / "archive" / "2026-10-14.html").exists())
            feed = (out / "feed.xml").read_text()
            self.assertIn("https://example.com/news/archive/2026-10-15.html", feed)
            import xml.dom.minidom
            xml.dom.minidom.parseString(feed)


if __name__ == "__main__":
    unittest.main()
