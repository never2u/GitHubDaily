import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ghnews import translate
from ghnews.__main__ import build_site


def edition(*descs):
    repos = [{"full_name": f"o/r{i}", "rank": i + 1, "url": f"https://github.com/o/r{i}",
              "description": d, "language": "Go", "stars": 1, "forks": 0, "stars_gained": 1}
             for i, d in enumerate(descs)]
    return {"date": "2026-10-15", "trending": {"daily": repos, "weekly": repos[:1]}, "new_arrivals": []}


class FakeClient:
    def __init__(self, stop_reason="end_turn", fail=False):
        self.calls = []
        self.stop_reason, self.fail = stop_reason, fail
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise ConnectionError("boom")
        lines = kwargs["messages"][0]["content"].splitlines()
        items = [json.loads(l) for l in lines if l.startswith("{")]
        body = json.dumps({"translations": [{"id": it["id"], "ko": "한글:" + it["text"]} for it in items]})
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=body)])


class TranslateTest(unittest.TestCase):
    def test_translates_only_new_and_changed(self):
        cache = {"o/r0": {"src": "cached text", "ko": "캐시됨"}, "o/r1": {"src": "old text", "ko": "옛"}}
        client = FakeClient()
        n = translate.translate_edition(edition("cached text", "new text", "", "third one"), cache, client,
                                        log=lambda *_: None)
        self.assertEqual(n, 2)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["model"], "claude-haiku-5-5")
        self.assertEqual(cache["o/r1"], {"src": "new text", "ko": "한글:new text"})
        self.assertEqual(cache["o/r0"]["ko"], "캐시됨")
        self.assertNotIn("o/r2", cache)  # empty description skipped

    def test_non_korean_results_are_retried(self):
        cache = {"o/r0": {"src": "中文描述", "ko": "中文描述"}}
        self.assertEqual(translate.pending(edition("中文描述"), cache), {"o/r0": "中文描述"})
        mixed = {"o/r0": {"src": "x", "ko": "압축 플러그인입니다. 上下文压缩插件"}}
        self.assertEqual(translate.pending(edition("x"), mixed), {"o/r0": "x"})
        self.assertTrue(translate.is_korean("Claude Code용 SwiftUI 스킬"))

        class EchoClient(FakeClient):  # returns the input untranslated
            def create(self, **kwargs):
                r = super().create(**kwargs)
                body = json.loads(r.content[0].text)
                for t in body["translations"]:
                    t["ko"] = t["ko"].removeprefix("한글:")
                r.content[0].text = json.dumps(body)
                return r

        cache = {}
        translate.translate_edition(edition("中文描述"), cache, EchoClient(), log=lambda *_: None)
        self.assertEqual(cache, {})

    def test_chunking(self):
        client = FakeClient()
        cache = {}
        translate.translate_edition(edition(*[f"desc {i}" for i in range(95)]), cache, client, log=lambda *_: None)
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(len(cache), 95)

    def test_failures_keep_english(self):
        for client in (FakeClient(fail=True), FakeClient(stop_reason="refusal")):
            cache = {}
            self.assertEqual(translate.translate_edition(edition("some text"), cache, client, log=lambda *_: None), 0)
            self.assertEqual(cache, {})
            self.assertEqual(len(client.calls), 2)                # first try + one retry

    def test_retry_with_feedback_recovers(self):
        class FlakyClient(FakeClient):  # rejected (Chinese left) on the first call only
            def create(self, **kwargs):
                r = super().create(**kwargs)
                body = json.loads(r.content[0].text)
                for t in body["translations"]:
                    t["ko"] = "도구입니다 网盘直链下载助手" if len(self.calls) == 1 else "넷디스크(网盘) 도구입니다"
                r.content[0].text = json.dumps(body)
                return r

        client, cache = FlakyClient(), {}
        n = translate.translate_edition(edition("一个基于 JavaScript 的网盘工具"), cache, client, log=lambda *_: None)
        self.assertEqual(n, 1)
        self.assertIn("rejected", client.calls[1]["messages"][0]["content"])
        self.assertTrue(translate.is_korean(cache["o/r0"]["ko"]))

    def test_names_in_brackets_are_allowed(self):
        self.assertTrue(translate.is_korean("바이두 넷디스크(百度网盘)를 지원합니다"))
        self.assertTrue(translate.is_korean("【网盘直链下载助手】를 바탕으로 만든 도구"))
        self.assertFalse(translate.is_korean("압축 플러그인입니다. 上下文压缩插件"))

    def test_bare_names_are_not_translated(self):
        client, cache = FakeClient(), {}
        translate.translate_edition(edition("jackie-fmri-sim"), cache, client, log=lambda *_: None)
        self.assertEqual(client.calls, [])
        self.assertTrue(cache["o/r0"]["keep"])
        self.assertEqual(translate.pending(edition("jackie-fmri-sim"), cache), {})   # not retried daily

    def test_no_api_key_is_noop(self):
        import os
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            self.assertEqual(translate.translate_edition(edition("a"), {}, log=lambda *_: None), 0)
        finally:
            if old is not None:
                os.environ["ANTHROPIC_API_KEY"] = old

    def test_site_uses_korean_with_english_tooltip(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, out = Path(tmp, "data"), Path(tmp, "site")
            data.mkdir()
            ed = edition("Fast agent framework", "Untranslated tool")
            Path(data, "2026-10-15.json").write_text(json.dumps(ed))
            translate.save_cache(data / "translations.json",
                                 {"o/r0": {"src": "Fast agent framework", "ko": "빠른 에이전트 프레임워크"}})
            self.assertEqual(build_site(data, out, "https://example.com/"), 1)
            html = (out / "index.html").read_text()
            self.assertIn('title="Fast agent framework" lang="ko">빠른 에이전트 프레임워크', html)
            self.assertIn('lang="en">Untranslated tool', html)


if __name__ == "__main__":
    unittest.main()
