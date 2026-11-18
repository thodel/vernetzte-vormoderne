"""St. Gallen Missiven (dhbern/sg-missiven-data): the edition's person and place registers.

person.xml: persName main/alternative, <birth when> (in this export: the first dated mention, not a birth),
listBibl/bibl/ptr[@type] -> ssrq (per…), histhub, hls, gnd …; place.xml likewise (loc…, coordinates).
"""
from __future__ import annotations

import re

from lxml import etree

from ..common import RAW, ids_from_urls, norm_id, person, place

NS = {"t": "http://www.tei-c.org/ns/1.0"}
XID = "{http://www.w3.org/XML/1998/namespace}id"
SITE = "https://dhbern.github.io/sg-missiven-data/"
PARSER = etree.XMLParser(recover=True, huge_tree=True)  # the export header has a broken <ref> in <p>


def _t(el, path):
    x = el.find(path, NS)
    return " ".join("".join(x.itertext()).split()) if x is not None else None


def _ids(el) -> dict:
    urls = [p.get("target") or "" for p in el.iterfind(".//t:ptr", NS)]
    ids = ids_from_urls(urls)
    for p in el.iterfind(".//t:ptr", NS):
        t, u = (p.get("type") or "").lower(), p.get("target") or ""
        if t == "ssrq" and (v := norm_id("ssrq", u)):
            ids["ssrq"] = v
        if t == "histhub" and (m := re.search(r"/(\d+)$", u)):
            ids["histhub"] = m.group(1)
    for idno in el.iterfind(".//t:idno", NS):
        t = (idno.get("type") or "").lower()
        if t in ("hls", "gnd", "wikidata", "geonames") and (v := norm_id(t, idno.text or "")):
            ids[t] = v
    return ids


def load():
    raw = RAW / "sg"
    persons, places = [], []
    for el in etree.parse(str(raw / "person" / "person.xml"), PARSER).iterfind(".//t:person", NS):
        pid = el.get(XID)
        main = _t(el, "t:persName[@type='main']") or pid
        alts = [" ".join("".join(x.itertext()).split()) for x in el.iterfind("t:persName[@type='alternative']", NS)]
        alts = [re.sub(r"\s*\(\d{4}[-0-9]*\)$", "", a) for a in alts]
        ys = [int(x) for b in el.iterfind("t:birth", NS) for x in re.findall(r"1\d{3}", b.get("when") or "")]
        ys += [int(x) for b in el.iterfind("t:death", NS) for x in re.findall(r"1\d{3}", b.get("when") or "")]
        num = pid.rsplit("-", 1)[-1]
        persons.append(person("sg", pid, main, forms=alts, years=[min(ys), max(ys)] if ys else None,
                              ids=_ids(el), url=f"{SITE}#/actors/{num}"))
    for el in etree.parse(str(raw / "place" / "place.xml"), PARSER).iterfind(".//t:place", NS):
        lid = el.get(XID)
        main = _t(el, "t:placeName[@type='main']") or lid
        geo = (_t(el, ".//t:geo") or "").replace(",", " ").split()
        num = lid.rsplit("-", 1)[-1]
        places.append(place("sg", lid, main, forms=[_t(el, "t:placeName[@type='full']") or ""],
                            lat=float(geo[0]) if len(geo) == 2 else None, lon=float(geo[1]) if len(geo) == 2 else None,
                            kind=el.get("type"), ids=_ids(el), url=f"{SITE}#/places/{num}"))
    return persons, places
