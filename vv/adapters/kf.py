"""Königsfelden (Staatsarchiv Aargau, Zenodo 10.5281/zenodo.10950031, CC BY 4.0).

The registers use the ids of the SSRQ person and place database (per…, loc…): a Königsfelden person and
an SSRQ register entry with the same id are the same person by the editors' own assignment.
Input: data/raw/kf/registers/{people,places}.xml, data/raw/kf/docs/*.xml (persName/@ref, origDate/@when).
"""
from __future__ import annotations

import re
from collections import defaultdict

from lxml import etree

from ..common import RAW, norm_id, person, place

NS = {"t": "http://www.tei-c.org/ns/1.0", "xml": "http://www.w3.org/XML/1998/namespace"}
XID = "{http://www.w3.org/XML/1998/namespace}id"
SITE = "https://koenigsfelden.sources-online.org/"


def _txt(el, path):
    x = el.find(path, NS)
    return " ".join("".join(x.itertext()).split()) if x is not None else None


def _year(s: str | None) -> int | None:
    m = re.search(r"(1[0-9]{3})", s or "")
    return int(m.group(1)) if m else None


def _mentions(raw):
    """id -> (number of documents, [first, last] year)"""
    docs, years = defaultdict(set), defaultdict(list)
    for f in sorted((raw / "docs").glob("*.xml")):
        tree = etree.parse(str(f))
        d = tree.find(".//t:origDate", NS)
        y = _year(d.get("when") or d.get("notBefore") or "".join(d.itertext())) if d is not None else None
        for el in tree.iterfind(".//t:persName[@ref]", NS):
            for r in re.findall(r"(per\d{6}|loc\d{6})", el.get("ref")):
                docs[r].add(f.stem)
                if y:
                    years[r].append(y)
        for el in tree.iterfind(".//t:placeName[@ref]", NS):
            for r in re.findall(r"(loc\d{6})", el.get("ref")):
                docs[r].add(f.stem)
                if y:
                    years[r].append(y)
    return {k: (len(v), [min(years[k]), max(years[k])] if years[k] else None) for k, v in docs.items()}


def load():
    raw = RAW / "kf"
    seen = _mentions(raw)
    persons, places = [], []
    for el in etree.parse(str(raw / "registers" / "people.xml")).iterfind(".//t:person", NS):
        pid = el.get(XID)
        name = _txt(el, "t:persName[@type='main']") or _txt(el, "t:persName") or pid
        first = el.find("t:event/t:label", NS)
        ev = el.find("t:event", NS)
        n, yrs = seen.get(pid, (0, None))
        if not yrs and ev is not None and first is not None and first.text == "Ersterwähnung":
            y = _year(ev.get("when-custom") or ev.get("when"))
            yrs = [y, y] if y else None
        ids = {"ssrq": pid}
        for idno in el.iterfind(".//t:idno", NS):
            t = (idno.get("type") or "").lower()
            if t in ("hls", "gnd", "wikidata"):
                ids[t] = norm_id(t, idno.text or "")
        persons.append(person("kf", pid, name, occupation=_txt(el, "t:occupation"), birth=_txt(el, "t:birth"),
                              death=_txt(el, "t:death"), years=yrs, docs=n, ids={k: v for k, v in ids.items() if v},
                              url=f"{SITE}"))
    for el in etree.parse(str(raw / "registers" / "places.xml")).iterfind(".//t:place", NS):
        lid = el.get(XID)
        name = _txt(el, "t:placeName[@xml:lang='deu']") or _txt(el, "t:placeName") or lid
        geo = (_txt(el, ".//t:geo") or "").split()
        ids = {"ssrq": lid}
        for idno in el.iterfind(".//t:idno", NS):
            t = (idno.get("type") or "").lower()
            if t in ("hls", "gnd", "wikidata", "geonames"):
                ids[t] = norm_id(t, idno.text or "")
        n, yrs = seen.get(lid, (0, None))
        places.append(place("kf", lid, name, lat=float(geo[0]) if len(geo) == 2 else None,
                            lon=float(geo[1]) if len(geo) == 2 else None, kind=_txt(el, "t:note[@type='type']"),
                            ids={k: v for k, v in ids.items() if v}, docs=n, years=yrs, url=SITE))
    return persons, places
