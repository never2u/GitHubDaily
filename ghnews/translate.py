"""Translate repository descriptions to Korean with Claude, with a cache.

Only descriptions that are not already in the cache (or whose English text
changed) are sent to the API, so most days translate a few dozen short
lines. Any failure leaves those descriptions in English - the site still
builds.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

MODEL = "claude-haiku-5-5"
CHUNK_SIZE = 40
MAX_DESC_CHARS = 400

HANGUL = re.compile("[\uac00-\ud7a3]")

SYSTEM_PROMPT = """\
You translate short GitHub repository descriptions into natural Korean for a
Korean tech news site. Descriptions may be written in any language (English,
Chinese, Japanese, ...); always translate them into Korean. Keep product names, library names, code identifiers,
acronyms and emoji as they are. Write concise, natural Korean (not a stiff
word-for-word translation) and keep the original meaning; do not add
information. If a description is already Korean, return it unchanged."""

SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "ko": {"type": "string"}},
                "required": ["id", "ko"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}


def load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def edition_repos(edition: dict):
    for repos in edition.get("trending", {}).values():
        yield from repos
    yield from edition.get("new_arrivals", [])


def pending(edition: dict, cache: dict) -> dict[str, str]:
    """full_name -> English description for everything not yet translated."""
    todo = {}
    for repo in edition_repos(edition):
        desc = (repo.get("description") or "").strip()
        if not desc:
            continue
        cached = cache.get(repo["full_name"])
        if cached and cached.get("src") == desc and HANGUL.search(cached.get("ko", "")):
            continue
        todo[repo["full_name"]] = desc
    return todo


def _translate_chunk(client, items: list[tuple[str, str]]) -> dict[str, str]:
    numbered = "\n".join(
        json.dumps({"id": i, "text": desc[:MAX_DESC_CHARS]}, ensure_ascii=False)
        for i, (_, desc) in enumerate(items)
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{
            "role": "user",
            "content": "Translate each description into Korean. Return one entry per id.\n\n" + numbered,
        }],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"unexpected stop_reason: {response.stop_reason}")
    text = next(b.text for b in response.content if b.type == "text")
    out = {}
    for entry in json.loads(text)["translations"]:
        idx, ko = entry["id"], entry["ko"].strip()
        # Only accept output that is actually Korean; anything else stays
        # pending and is retried on the next run.
        if 0 <= idx < len(items) and HANGUL.search(ko):
            out[items[idx][0]] = ko
    return out


def translate_edition(edition: dict, cache: dict, client=None, log=print) -> int:
    """Fill `cache` with Korean for this edition's new descriptions.

    Returns the number of newly translated descriptions.
    """
    todo = pending(edition, cache)
    if not todo:
        log("translate: nothing new")
        return 0
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            log(f"translate: ANTHROPIC_API_KEY not set, {len(todo)} descriptions stay English")
            return 0
        import anthropic

        client = anthropic.Anthropic()

    items = list(todo.items())
    done = 0
    for start in range(0, len(items), CHUNK_SIZE):
        chunk = items[start:start + CHUNK_SIZE]
        try:
            result = _translate_chunk(client, chunk)
        except Exception as exc:  # API error, refusal, bad JSON - keep English
            log(f"translate: chunk {start // CHUNK_SIZE + 1} failed: {exc}")
            continue
        for name, ko in result.items():
            cache[name] = {"src": todo[name], "ko": ko}
        done += len(result)
    log(f"translate: {done}/{len(items)} new descriptions translated")
    return done


def apply(edition: dict, cache: dict) -> None:
    """Attach `description_ko` to every repo whose translation is current."""
    for repo in edition_repos(edition):
        cached = cache.get(repo["full_name"])
        if cached and cached.get("src") == (repo.get("description") or "").strip():
            repo["description_ko"] = cached["ko"]
