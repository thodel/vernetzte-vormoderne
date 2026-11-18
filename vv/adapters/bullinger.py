"""Bullinger Digital (bullinger-digital/bullinger-korpus-tei): the person and place index, and the letters
(CMIF) for years, roles and places of writing. CMIF names persons by GND only, so letters count for the
persons with a GND number.
"""
from __future__ import annotations

import re
from collections import defaultdict

from lxml import etree

from ..common import RAW, norm_id, person, place

NS = {"t": "http://www.tei-c.org/ns/1.0"}
XID = "{http://www.w3.org/XML/1998/namespace}id"
SITE = "https://www.bullinger-digital.ch/"


def _name(pn) -> str:
    sur = pn.findtext("t:surname", default="", namespaces=NS).strip()
    fore = pn.findtext("t:forename", default="", namespaces=NS).strip()
    return f"{fore} {sur}".strip() or " ".join("".join(pn.itertext()).split())


def _letters(raw):
    """gnd -> {n, years, roles, places}"""
    acc = defaultdict(lambda: {"n": 0, "years": [], "roles": set(), "places": set()})
    tree = etree.parse(str(raw / "data" / "cmif" / "bullinger-korpus-cmif.xml"))
    for cd in tree.iterfind(".//t:correspDesc", NS):
        when = cd.find(".//t:correspAction[@type='sent']/t:date", NS)
        y = int(m.group(0)) if when is not None and (m := re.search(r"1[45]\d\d", when.get("when") or "")) else None
        where = cd.findtext(".//t:correspAction[@type='sent']/t:placeName", namespaces=NS)
        for act in cd.iterfind("t:correspAction", NS):
            for pn in act.iterfind("t:persName", NS):
                g = norm_id("gnd", pn.get("ref") or "") if "d-nb.info" in (pn.get("ref") or "") else None
                if not g:
                    continue
                a = acc[g]
                a["n"] += 1
                a["roles"].add("sender" if act.get("type") == "sent" else "recipient")
                if y:
                    a["years"].append(y)
                if where and act.get("type") == "sent":
                    a["places"].add(where)
    return acc


def load():
    raw = RAW / "bullinger"
    letters = _letters(raw)
    persons, places = [], []
    for el in etree.parse(str(raw / "data" / "index" / "persons.xml")).iterfind(".//t:person", NS):
        pid = el.get(XID)
        main = el.find("t:persName[@type='main']", NS)
        name = _name(main) if main is not None else pid
        forms = [_name(p) for p in el.iterfind("t:persName[@type='alias']", NS)]
        ids = {"bullinger": pid}
        for idno in el.iterfind("t:idno", NS):
            st = (idno.get("subtype") or idno.get("type") or "").lower()
            if st in ("gnd", "hls") and (v := norm_id(st, idno.text or "")):
                ids[st] = v
        lt = letters.get(ids.get("gnd", ""), {})
        ys = lt.get("years") or []
        persons.append(person("bullinger", pid, name, forms=forms, ids=ids, docs=lt.get("n", 0),
                              years=[min(ys), max(ys)] if ys else None, roles=sorted(lt.get("roles", [])),
                              places=sorted(lt.get("places", [])), url=f"{SITE}persons/{pid}"))
    for el in etree.parse(str(raw / "data" / "index" / "localities.xml")).iterfind(".//t:place", NS):
        lid = el.get(XID)
        name = el.findtext("t:settlement", namespaces=NS) or el.findtext("t:district", namespaces=NS) or lid
        geo = (el.findtext(".//t:geo", namespaces=NS) or "").split()
        ids = {}
        for idno in el.iterfind("t:idno", NS):
            st = (idno.get("subtype") or "").lower()
            if st == "geonames" and (m := re.search(r"(\d+)", idno.text or "")):
                ids["geonames"] = m.group(1)
        places.append(place("bullinger", lid, name.strip(), lat=float(geo[0]) if len(geo) == 2 else None,
                            lon=float(geo[1]) if len(geo) == 2 else None, ids=ids,
                            kind=el.findtext("t:country", namespaces=NS), url=f"{SITE}localities/{lid}"))
    return persons, places
