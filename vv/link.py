"""The joint index: combine the sources' persons (and places) by certainty.

Rule (docs/verknuepfung.md, decided 18.11.2026):
  * «sicher» — the records share an authority id: one the source itself asserts (SSRQ register id per…,
    HLS, GND, Wikidata, Bullinger id, …), or one a concordance adds (Metagrid, the Bestandsgraph's
    owl:sameAs through QLever). These records are MERGED into one joint person.
  * «wahrscheinlich» / «möglich» — a graded proposal (the Thun register's candidates) or a name match
    (same folded surname and forename, compatible years, a shared place). These stay TWO persons, joined
    by an edge «möglicherweise dieselbe Person», shown with its evidence.
A merge that would give one joint person two different values of the same scheme (two HLS articles, two
GND numbers, two SSRQ ids) is refused: the edge becomes «Konflikt» and both persons stay apart.

  python -m vv.link [--kind persons|places]   -> links/{persons,places}.jsonl, links/{person,place}_edges.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from itertools import combinations

from .common import LINKS, NORM, SOURCES, fold, name_key, read_jsonl

#: schemes that identify a person or place; one value per joint entity
SCHEMES = ("hls", "gnd", "wikidata", "ssrq", "bullinger", "dodis", "histhub", "viaf", "geonames")
UNIQUE = ("hls", "gnd", "wikidata", "ssrq", "bullinger", "dodis", "geonames")
#: the order a joint id is taken from: the most widely shared authority first
JID_ORDER = ("hls", "gnd", "wikidata", "ssrq", "bullinger", "geonames")
GRADES = ("sicher", "wahrscheinlich", "möglich", "Konflikt")
BLOCK_MAX = 150          # a name block larger than this is too common to compare pairwise (counted, skipped)
YEAR_SLACK = 30          # years between two attestation spans that still fit one life


class Joint:
    """Union-find over record ids that refuses a union giving one entity two values of a unique scheme."""

    def __init__(self, records: dict):
        self.parent = {r: r for r in records}
        self.ids = {r: {s: {v} for s, v in rec["ids"].items() if s in UNIQUE} for r, rec in records.items()}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b) -> bool | None:
        """True merged, None already one, False refused (conflict)."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return None
        ia, ib = self.ids[ra], self.ids[rb]
        if any(ia.get(s) and ib.get(s) and ia[s] != ib[s] for s in UNIQUE):
            return False
        self.parent[rb] = ra
        for s, v in ib.items():
            ia.setdefault(s, set()).update(v)
        return True


def extra_ids() -> dict:
    """Concordance ids keyed by «scheme:value»: Metagrid and QLever (vv.metagrid, vv.qlever)."""
    out = defaultdict(dict)
    for name in ("metagrid", "qlever"):
        for row in read_jsonl(LINKS / f"{name}.jsonl"):
            for s, v in row["ids"].items():
                if s in SCHEMES and v:
                    out[row["key"]].setdefault(s, (v, name))
    return out


def years_fit(a, b, slack=YEAR_SLACK) -> bool | None:
    if not a or not b:
        return None
    return a[0] - slack <= b[1] and b[0] - slack <= a[1]


def km(a, b) -> float | None:
    if None in (a.get("lat"), a.get("lon"), b.get("lat"), b.get("lon")):
        return None
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dl = math.radians(b["lon"] - a["lon"])
    return 6371 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))


def person_pair(a, b) -> tuple[str, str] | None:
    """Grade a name match between two persons of different sources, or None."""
    fit = years_fit(a.get("years"), b.get("years"))
    if fit is False:
        return None
    full_a = {fold(f) for f in a["forms"]}
    full_b = {fold(f) for f in b["forms"]}
    same_full = bool(full_a & full_b)
    shared_place = bool({fold(p) for p in a.get("places") or []} & {fold(p) for p in b.get("places") or []})
    if same_full and fit and (shared_place or (a.get("years") and b.get("years")
                                               and abs(a["years"][0] - b["years"][0]) <= 10)):
        return "wahrscheinlich", "name+jahre" + ("+ort" if shared_place else "")
    return "möglich", "name" + ("+jahre" if fit else "")


def place_pair(a, b) -> tuple[str, str] | None:
    d = km(a, b)
    if d is not None and d > 15:
        return None
    if d is not None and d <= 3:
        return "wahrscheinlich", f"name+{d:.1f} km"
    return "möglich", "name" + (f"+{d:.0f} km" if d is not None else "")


def build(kind: str = "persons") -> dict:
    records = {}
    for s in SOURCES:
        for r in read_jsonl(NORM / s / f"{kind}.jsonl"):
            records[r["id"]] = r
    extra = extra_ids()
    for r in records.values():  # concordance ids: added to the record, with where they came from
        r["via"] = {}
        for s, v in list(r["ids"].items()):
            for s2, (v2, by) in extra.get(f"{s}:{v}", {}).items():
                if s2 not in r["ids"]:
                    r["ids"][s2], r["via"][s2] = v2, by
    joint = Joint(records)
    edges, st = [], Counter()

    # 1. sicher: shared ids. The records' own ids before the concordances', so a concordance cannot pull
    #    apart what a source asserts.
    own, conc = defaultdict(list), defaultdict(list)
    for rid, r in records.items():
        for s_, v in r["ids"].items():
            if s_ in SCHEMES:
                (conc if s_ in r["via"] else own)[(s_, v)].append(rid)

    def merge(rids, tag, key):
        for other in rids[1:]:
            res = joint.union(rids[0], other)
            if res is False:
                edges.append((rids[0], other, "Konflikt", f"{key[0]}:{key[1]}"))
                st["Konflikt"] += 1
            elif res:
                st[tag] += 1
    for key, rids in own.items():
        merge(rids, "sicher", key)
    for key, rids in conc.items():
        merge(own.get(key, [])[:1] + rids, "sicher (Konkordanz)", key)

    # 2. proposals of a source (Thun): to whatever holds the proposed id, as an edge only
    holder = {k: rids[0] for k, rids in [*conc.items(), *own.items()]}
    for rid, r in records.items():
        for c in r.get("cands") or []:
            for s, v in c["ids"].items():
                other = holder.get((s, v))
                if other and joint.find(other) != joint.find(rid):
                    edges.append((rid, other, c["grade"] if c["grade"] in GRADES else "möglich",
                                  f"{r['source']}-kandidat:{c.get('rule') or ''}:{s}:{v}"))
                    st["kandidat " + c["grade"]] += 1
                    break

    # 3. name matches across sources: blocked by folded surname (persons) or name (places)
    blocks = defaultdict(list)
    for rid, r in records.items():
        keys = {name_key(f) for f in r["forms"]} if kind == "persons" else {(fold(f), "") for f in r["forms"]}
        for k in keys:
            if k[0] and (kind == "places" or k[1]):
                blocks[k].append(rid)
    seen = set()
    for rids in blocks.values():
        rids = sorted(set(rids))
        if len(rids) > BLOCK_MAX:
            st["Block zu gross (übersprungen)"] += 1
            continue
        for a, b in combinations(rids, 2):
            ra, rb = records[a], records[b]
            if ra["source"] == rb["source"] or joint.find(a) == joint.find(b) or (a, b) in seen:
                continue
            seen.add((a, b))
            g = person_pair(ra, rb) if kind == "persons" else place_pair(ra, rb)
            if g:
                edges.append((a, b, g[0], g[1]))
                st[g[0]] += 1

    # joint entities
    groups = defaultdict(list)
    for rid in records:
        groups[joint.find(rid)].append(rid)
    out, jid_of = [], {}
    for members in groups.values():
        recs = [records[m] for m in members]
        ids = {}
        for r in recs:
            for s, v in r["ids"].items():
                ids.setdefault(s, v)
        jid = next((f"{s}-{ids[s]}" for s in JID_ORDER if s in ids), members[0].replace(":", "-"))
        for m in members:
            jid_of[m] = jid
        best = max(recs, key=lambda r: ("hls" in r["ids"], r["docs"], -len(r["name"])))
        ys = [y for r in recs if r.get("years") for y in r["years"]]
        out.append({"jid": jid, "label": best["name"], "members": sorted(members),
                    "sources": sorted({r["source"] for r in recs}), "ids": ids,
                    "years": [min(ys), max(ys)] if ys else None,
                    **({"lat": next((r["lat"] for r in recs if r.get("lat") is not None), None),
                        "lon": next((r["lon"] for r in recs if r.get("lon") is not None), None)}
                       if kind == "places" else {})})
    uniq = {}
    for a, b, g, why in edges:
        ja, jb = jid_of[a], jid_of[b]
        if ja == jb:
            continue
        key = tuple(sorted((ja, jb)))
        if key not in uniq or GRADES.index(g) < GRADES.index(uniq[key][2]):
            uniq[key] = (a, b, g, why)
    LINKS.mkdir(exist_ok=True)
    with (LINKS / f"{kind}.jsonl").open("w") as fh:
        for e in sorted(out, key=lambda e: e["jid"]):
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    with (LINKS / f"{kind[:-1]}_edges.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["a", "b", "record_a", "record_b", "grade", "evidence"])
        for (ja, jb), (a, b, g, why) in sorted(uniq.items()):
            w.writerow([ja, jb, a, b, g, why])
    multi = sum(len(e["sources"]) > 1 for e in out)
    summary = {"records": len(records), "joint": len(out), "joint_several_sources": multi,
               "edges": dict(Counter(v[2] for v in uniq.values())), "steps": dict(st)}
    (LINKS / f"{kind}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["persons", "places"], nargs="*", default=["persons", "places"])
    a = ap.parse_args()
    for k in a.kind:
        print(k, json.dumps(build(k), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
