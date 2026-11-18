"""The Bestandsgraph of the Agentic Historian (QLever, https://tei.dh.unibe.ch/sparql/).

The graph holds Dodis, Königsfelden, SSRQ and the Musiklexikon der Schweiz in CIDOC CRM, and a Human
Lineage layer (kinship, owl:sameAs; CC BY-SA 4.0, named graph <…/id/graph/humanlineage>). Two uses here:

  1. ids: every owl:sameAs of a person node that carries one of our authority URIs -> links/qlever.jsonl
     (the linker treats these as concordance ids, «sicher (Konkordanz)», like Metagrid);
  2. facts for the biographies: parents and children (crm:P152_has_parent), and in which holdings the
     person is mentioned (prov:wasDerivedFrom of the mentioning documents) -> links/qlever_facts.jsonl.

The vocabulary follows agentic_historian/knowledge_hub/queries.py (E21_Person, owl:sameAs into
https://hls-dhs-dss.ch/de/articles/…, https://d-nb.info/gnd/…, https://www.wikidata.org/entity/…).
Queries go in batches (VALUES), are cached, and a missing endpoint is reported, not fatal.

  python -m vv.qlever [--endpoint URL] [--batch 100] [--limit 2000]
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
from collections import Counter

from .common import LINKS, cached_json, env, get, ids_from_urls, read_jsonl, sources

PREFIXES = """PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX prov: <http://www.w3.org/ns/prov#>
"""
URI = {"hls": ["https://hls-dhs-dss.ch/de/articles/{}/", "https://hls-dhs-dss.ch/de/articles/{}"],
       "gnd": ["https://d-nb.info/gnd/{}"],
       "wikidata": ["https://www.wikidata.org/entity/{}", "https://www.wikidata.org/wiki/{}"]}


def uris(scheme: str, value: str) -> list[str]:
    return [t.format(value) for t in URI.get(scheme, [])]


def sparql(endpoint: str, query: str) -> list[dict]:
    url = endpoint + "?" + urllib.parse.urlencode({"query": PREFIXES + query})
    data = json.loads(get(url, pause=0.5, timeout=90, accept="application/sparql-results+json"))
    return [{k: v["value"] for k, v in b.items()} for b in data["results"]["bindings"]]


def same_as_query(batch: list[str]) -> str:
    values = " ".join(f"<{u}>" for u in batch)
    return f"""SELECT DISTINCT ?key ?other WHERE {{
  VALUES ?key {{ {values} }}
  ?p owl:sameAs ?key ; a crm:E21_Person ; owl:sameAs ?other .
}}"""


def facts_query(batch: list[str]) -> str:
    values = " ".join(f"<{u}>" for u in batch)
    return f"""SELECT DISTINCT ?key ?rel ?kinLabel ?kinLink ?holding WHERE {{
  VALUES ?key {{ {values} }}
  ?p owl:sameAs ?key ; a crm:E21_Person .
  {{ ?p crm:P152_has_parent ?kin . BIND("parent" AS ?rel) }} UNION
  {{ ?kin crm:P152_has_parent ?p . BIND("child" AS ?rel) }} UNION
  {{ ?doc crm:P67_refers_to ?p ; prov:wasDerivedFrom/rdfs:label ?holding . BIND("mentioned" AS ?rel) }}
  OPTIONAL {{ ?kin rdfs:label ?kinLabel }}
  OPTIONAL {{ ?kin owl:sameAs ?kinLink }}
}} LIMIT 20000"""


def authority_keys(limit: int) -> list[tuple[str, str]]:
    """hls/gnd/wikidata ids of the joint persons, persons in several sources first."""
    rows = read_jsonl(LINKS / "persons.jsonl")
    rows.sort(key=lambda r: -len(r["sources"]))
    out = []
    for r in rows:
        for s in ("hls", "gnd", "wikidata"):
            if v := r["ids"].get(s):
                out.append((s, v))
    return out[:limit]


def run(endpoint: str, batch: int = 100, limit: int = 2000) -> Counter:
    st = Counter()
    keys = authority_keys(limit)
    back = {u: (s, v) for s, v in keys for u in uris(s, v)}
    ids_rows, facts = {}, {}
    allu = sorted(back)
    for i in range(0, len(allu), batch):
        chunk = allu[i:i + batch]
        try:
            key = "|".join(chunk)
            same = cached_json("qlever", "sameas:" + key, lambda c=chunk: sparql(endpoint, same_as_query(c)))
            fact = cached_json("qlever", "facts:" + key, lambda c=chunk: sparql(endpoint, facts_query(c)))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
            st[f"Endpoint nicht erreichbar ({type(e).__name__})"] += 1
            break
        for row in same:
            s, v = back[row["key"]]
            key = f"{s}:{v}"
            got = {k: x for k, x in ids_from_urls([row["other"]]).items() if not (k == s and x == v)}
            if got:
                ids_rows.setdefault(key, {"key": key, "ids": {}})["ids"].update(got)
        for row in fact:
            s, v = back[row["key"]]
            f = facts.setdefault(f"{s}:{v}", {"key": f"{s}:{v}", "parents": [], "children": [], "holdings": []})
            if row["rel"] == "mentioned":
                if row.get("holding") and row["holding"] not in f["holdings"]:
                    f["holdings"].append(row["holding"])
            else:
                kin = {"label": row.get("kinLabel"), "link": row.get("kinLink")}
                lst = f["parents" if row["rel"] == "parent" else "children"]
                if kin not in lst:
                    lst.append(kin)
        st["Abfragen"] += 1
    if st["Abfragen"]:
        for name, rows in (("qlever", ids_rows), ("qlever_facts", facts)):
            with (LINKS / f"{name}.jsonl").open("w") as fh:
                for k in sorted(rows):
                    fh.write(json.dumps(rows[k], ensure_ascii=False, sort_keys=True) + "\n")
    st["Personen mit weiteren Ids"] = len(ids_rows)
    st["Personen mit Fakten"] = len(facts)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default=env("VV_SPARQL_ENDPOINT") or sources()["qlever"]["endpoint"])
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--limit", type=int, default=2000)
    a = ap.parse_args()
    print(f"qlever ({a.endpoint}): {dict(run(a.endpoint, a.batch, a.limit))}")


if __name__ == "__main__":
    main()
