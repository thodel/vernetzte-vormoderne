"""Metagrid (SAGW, metagrid.ch): what the registers say of each other.

Metagrid collects, per person, the concordance between registers (HLS, GND, SSRQ, Bullinger Digital, Dodis,
histhub, VIAF, hallerNet, …). It does not measure; it reports the registers' own statements. Here a Metagrid
concordance counts as «sicher» (Konkordanz), like a shared id, and the linker refuses it where it would give
one person two values of a scheme (vv.link).

Looked up by the providers whose ids our sources carry: `ssrq` (per…) and `bullinger` (P…).
  https://api.metagrid.ch/widget/<provider>/person/<id>.json?lang=de&include=true

  python -m vv.metagrid [--limit 1000] [--pause 0.3]   -> links/metagrid.jsonl (cumulative; answers cached)
"""
from __future__ import annotations

import argparse
import json
import urllib.error
from collections import Counter
from datetime import date

from .common import LINKS, NORM, SOURCES, cached_json, get, ids_from_urls, read_jsonl

WIDGET = "https://api.metagrid.ch/widget/{provider}/person/{id}.json?lang=de&include=true"
PROVIDER = {"ssrq": "ssrq", "bullinger": "bullinger"}


def lookup(scheme: str, value: str, pause: float = 0.3):
    def fetch():
        try:
            data = json.loads(get(WIDGET.format(provider=PROVIDER[scheme], id=value), pause=pause, timeout=30))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        rows = data if isinstance(data, list) else [data]
        urls = [v["url"] for row in rows if isinstance(row, dict) for v in row.values()
                if isinstance(v, dict) and v.get("url")]
        return urls or None
    return cached_json("metagrid", f"{scheme}:{value}", fetch)


def keys_by_priority() -> list[tuple[str, str]]:
    """Ids worth asking for: persons with the most documents first, each key once."""
    weight = Counter()
    for s in SOURCES:
        for r in read_jsonl(NORM / s / "persons.jsonl"):
            for scheme in PROVIDER:
                if v := r["ids"].get(scheme):
                    weight[(scheme, v)] += 1 + r.get("docs", 0)
    return [k for k, _ in weight.most_common()]


def run(limit: int = 1000, pause: float = 0.3) -> Counter:
    path = LINKS / "metagrid.jsonl"
    done = {row["key"]: row for row in read_jsonl(path)}
    st = Counter()
    asked = 0
    for scheme, value in keys_by_priority():
        key = f"{scheme}:{value}"
        if key in done:
            continue
        if asked >= limit:
            break
        asked += 1
        try:
            urls = lookup(scheme, value, pause)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            st[f"Fehler {type(e).__name__}"] += 1
            continue
        ids = {k: v for k, v in ids_from_urls(urls or []).items() if not (k == scheme and v == value)}
        done[key] = {"key": key, "ids": ids, "urls": urls or [], "at": date.today().isoformat()}
        st["mit Konkordanz" if ids else "ohne"] += 1
    LINKS.mkdir(exist_ok=True)
    with path.open("w") as fh:
        for k in sorted(done):
            fh.write(json.dumps(done[k], ensure_ascii=False, sort_keys=True) + "\n")
    st["gesamt"] = len(done)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=1000, help="new lookups in this run")
    ap.add_argument("--pause", type=float, default=0.3)
    a = ap.parse_args()
    print(f"metagrid: {dict(run(a.limit, a.pause))} -> {LINKS / 'metagrid.jsonl'}")


if __name__ == "__main__":
    main()
