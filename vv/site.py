"""Static site data: search index, person pages, the joint map.

  python -m vv.site   -> site/data/{stats,places}.json, site/data/index/<letter>.json, site/data/p/<xx>.json

Person pages are read from 256 chunks (first two hex digits of sha1(jid)), so the browser loads only what
it shows. Places on the map are the joint places with coordinates, coloured by the sources that know them.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date

from .common import LINKS, NORM, SITE, SOURCES, fold, read_jsonl, sources

KEEP = ("name", "forms", "years", "birth", "death", "roles", "occupation", "places", "note", "ids", "via",
        "docs", "url", "source", "cands")


def chunk(jid: str) -> str:
    return hashlib.sha1(jid.encode()).hexdigest()[:2]


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def edges(kind: str) -> dict:
    out = defaultdict(list)
    p = LINKS / f"{kind}_edges.csv"
    if p.exists():
        for r in csv.DictReader(p.open()):
            out[r["a"]].append([r["b"], r["grade"], r["evidence"]])
            out[r["b"]].append([r["a"], r["grade"], r["evidence"]])
    return out


def build() -> dict:
    data = SITE / "data"
    cfg = sources()
    recs = {r["id"]: r for s in SOURCES for r in read_jsonl(NORM / s / "persons.jsonl")}
    joint = read_jsonl(LINKS / "persons.jsonl")
    label = {j["jid"]: j["label"] for j in joint}
    bios = {b["jid"]: b for b in read_jsonl(LINKS / "bios.jsonl")}
    pe = edges("person")
    chunks, index = defaultdict(dict), defaultdict(list)
    for j in joint:
        b = bios.get(j["jid"], {})
        page = {"jid": j["jid"], "label": j["label"], "years": j.get("years"), "ids": j["ids"],
                "sources": j["sources"],
                "members": [{k: recs[m].get(k) for k in KEEP if recs[m].get(k)} for m in j["members"] if m in recs],
                "edges": [[o, label.get(o, o), g, why] for o, g, why in pe.get(j["jid"], [])][:30],
                "bio": {k: b[k] for k in ("bio", "unsicher", "model", "belege", "generated", "hls") if b.get(k)},
                "steckbrief": b.get("steckbrief")}
        chunks[chunk(j["jid"])][j["jid"]] = page
        letter = (fold(j["label"])[:1] or "_")
        index[letter if letter.isalpha() else "_"].append(
            [j["jid"], j["label"], j.get("years"), j["sources"], int(bool(b.get("bio"))), len(pe.get(j["jid"], []))])
    for c, pages in chunks.items():
        dump(data / "p" / f"{c}.json", pages)
    for letter, rows in index.items():
        dump(data / "index" / f"{letter}.json", sorted(rows, key=lambda r: fold(r[1])))

    places = []
    precs = {r["id"]: r for s in SOURCES for r in read_jsonl(NORM / s / "places.jsonl")}
    for p in read_jsonl(LINKS / "places.jsonl"):
        if p.get("lat") is None:
            continue
        ms = [precs[m] for m in p["members"] if m in precs]
        places.append([p["jid"], p["label"], round(p["lat"], 5), round(p["lon"], 5), p["sources"],
                       sum(m.get("docs") or 0 for m in ms), [[m["source"], m["name"], m.get("url")] for m in ms][:8]])
    dump(data / "places.json", places)

    psum = json.loads((LINKS / "persons_summary.json").read_text())
    lsum = json.loads((LINKS / "places_summary.json").read_text())
    by_src = Counter(s for j in joint for s in j["sources"])
    stats = {"generated": date.today().isoformat(), "persons": psum, "places": lsum,
             "persons_by_source": dict(by_src), "bios": sum(1 for b in bios.values() if b.get("bio")),
             "map_places": len(places),
             "sources": {k: {"title": v["title"], "short": v.get("short", k), "site": v.get("site"),
                             "license": v.get("license"), "at": v.get("commit") or v.get("version")}
                         for k, v in cfg.items() if k in SOURCES}}
    dump(data / "stats.json", stats)
    return {"persons": len(joint), "chunks": len(chunks), "map_places": len(places)}


def main():
    print(f"site: {build()} -> {SITE / 'data'}")


if __name__ == "__main__":
    main()
