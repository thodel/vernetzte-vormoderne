"""SSRQ print volumes (ssrq_print): persons and places of the super-register, with their pieces.

Input (data/raw/ssrq, the published site at the pinned commit):
  r/data/persons-*.json  {cluster id: {l: label, v: variants, d: description, D: {volume: [piece ids]},
                          a: [[scheme, id, label, url]]}}   (a: only links graded «match» are published)
  r/data/places-*.json   same shape; k/places.json [id, label, lat, lon, n, volumes, grade, [from, to]]
  s/documents.json       [piece id, volume, canton, no, year, date, regest, …]
"""
from __future__ import annotations

import json
import re

from ..common import RAW, norm_id, person, place

SITE = "https://thodel.github.io/ssrq_print_pages/"


def _years(D: dict, year_of: dict) -> list[int] | None:
    ys = [year_of[p] for ps in D.values() for p in ps if year_of.get(p)]
    return [min(ys), max(ys)] if ys else None


def _ids(links: list) -> dict:
    out = {}
    for scheme, lid, _label, url in links:
        if scheme == "ssrq":
            out["ssrq"] = norm_id("ssrq", lid)
        elif scheme == "hls":
            out["hls"] = norm_id("hls", url or lid)
        elif scheme in ("gnd", "wikidata"):
            out[scheme] = norm_id(scheme, url or lid)
    return {k: v for k, v in out.items() if v}


def load():
    raw = RAW / "ssrq"
    year_of = {r[0]: r[4] for r in json.loads((raw / "s" / "documents.json").read_text()) if r[4]}
    canton_of = {r[0]: r[2] for r in json.loads((raw / "s" / "documents.json").read_text())}
    coords = {r[0]: r for r in json.loads((raw / "k" / "places.json").read_text())}
    persons, places = [], []
    for f in sorted((raw / "r" / "data").glob("persons-*.json")):
        for cid, c in json.loads(f.read_text()).items():
            if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", c["l"])) < 2:  # page numbers and OCR debris read as lemmas
                continue
            docs = sum(len(v) for v in c["D"].values())
            cantons = sorted({canton_of.get(p) for ps in c["D"].values() for p in ps} - {None})
            persons.append(person("ssrq", cid, c["l"], forms=c.get("v") or [], note=c.get("d") or None,
                                  years=_years(c["D"], year_of), ids=_ids(c.get("a") or []), docs=docs,
                                  places=cantons, url=f"{SITE}r/eintrag.html?id={cid}",
                                  extra={"volumes": sorted(c["D"])}))
    for f in sorted((raw / "r" / "data").glob("places-*.json")):
        for cid, c in json.loads(f.read_text()).items():
            k = coords.get(cid)
            places.append(place("ssrq", cid, c["l"] or (c.get("d") or "")[:60], forms=c.get("v") or [],
                                lat=k[2] if k else None, lon=k[3] if k else None,
                                coord_grade=k[6] if k else None, ids=_ids(c.get("a") or []),
                                docs=sum(len(v) for v in c["D"].values()), years=_years(c["D"], year_of),
                                url=f"{SITE}r/eintrag.html?id={cid}"))
    return persons, places
