"""Thun Missiven (dhbern/thun-missiven-data): the register generated automatically from the tagging.

Nothing in it is an editor's assertion. Its candidates (HLS, SSRQ, Königsfelden, Wikidata) are graded
«sicher» / «wahrscheinlich» / «möglich» by St. Gallen's measured rules. Only a «sicher» candidate becomes an
id of the record; the others stay proposals (`cands`), which the linker turns into «possibly the same»
edges, never into a merge (docs/verknuepfung.md).
"""
from __future__ import annotations

import json

from ..common import RAW, norm_id, person, place

SITE = "https://dhbern.github.io/thun-missiven-data/"
SCHEMES = ("hls", "ssrq", "gnd", "wikidata")


def _split(cands: list) -> tuple[dict, list]:
    ids, rest = {}, []
    for c in cands or []:
        cid = {s: norm_id(s, str(c[s])) for s in SCHEMES if c.get(s)}
        cid = {k: v for k, v in cid.items() if v}
        if not cid:
            continue
        if c.get("grade") == "sicher" and not ids:
            ids = cid
        else:
            rest.append({"ids": cid, "grade": c.get("grade") or "möglich", "rule": c.get("rule"),
                         "label": c.get("label")})
    return ids, rest


def load():
    raw = RAW / "thun" / "registers"
    persons, places = [], []
    for pid, e in json.loads((raw / "persons.json").read_text())["entries"].items():
        ids, cands = _split(e.get("candidates"))
        roles = sorted((e.get("roles") or {}).keys())
        persons.append(person("thun", pid, e["name"], forms=[f for f, _ in e.get("forms") or []],
                              years=e.get("years"), roles=roles, ids=ids, cands=cands,
                              docs=len(e.get("letters") or []), url=f"{SITE}#/names/{pid}"))
    for lid, e in json.loads((raw / "places.json").read_text())["entries"].items():
        ids, cands = _split(e.get("candidates"))
        geo = e.get("geo") or [None, None]
        places.append(place("thun", lid, e["name"], forms=[f for f, _ in e.get("forms") or []],
                            lat=geo[0], lon=geo[1], coord_grade=e.get("geo_grade"), ids=ids, cands=cands,
                            docs=len(e.get("letters") or []), years=e.get("years"), url=f"{SITE}#/places/{lid}"))
    return persons, places
