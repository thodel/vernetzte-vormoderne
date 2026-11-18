"""Short biographies of the joint persons: HLS/HBLS first, enriched by what the sources attest.

Every joint person gets a «Steckbrief» built without a model (years, sources, roles, offices, life data).
Persons with an HLS article or attested in several sources also get a biography written by the text model
from an evidence pack:
  * the HLS article (facts and text; CC BY-SA 4.0: the biography names article, author and version),
  * an HBLS family article whose member fits by name and years (context only, flagged as such),
  * every source record merged into the person («sicher»): name forms, years, roles, offices, places,
    the register's description, the number of documents,
  * kinship and holdings from the Bestandsgraph (QLever, Human Lineage layer),
  * NOT the persons that are only «wahrscheinlich»/«möglich» the same: they are listed so the model can
    say that they were kept apart, never used as facts.
Each sentence carries its sources ([HLS], [HBLS], [SSRQ], [KF], [SG], [Thun], [Bullinger], [Graph]).

Model: an OpenAI-compatible endpoint (GPUStack): VV_LLM_BASE_URL (or GPUSTACK_BASE_URL), VV_LLM_API_KEY
(or GPUSTACK_API_KEY), VV_LLM_MODEL (default gpt-oss-120b). At most VV_LLM_SLOTS calls at a time across
processes (default 2). Answers are cached by model, prompt and evidence.

  python -m vv.bio [--limit 50] [--no-llm] [--jid hls-021574]   -> links/bios.jsonl
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import fcntl
import hashlib
import json
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from . import hbls, hls
from .common import CACHE, LINKS, NORM, SOURCES, env, read_jsonl, sources

SHORT = {k: v.get("short", k) for k, v in sources().items()}
TAG = {"ssrq": "SSRQ", "kf": "KF", "sg": "SG", "thun": "Thun", "bullinger": "Bullinger"}

PROMPT = """Du schreibst Kurzbiografien für ein Personenregister zur Vormoderne (Schweiz, ca. 1200–1800).
Grundlage ist ausschliesslich das Belegpaket (JSON). Erfinde nichts, ergänze nichts aus eigenem Wissen.

Regeln:
- 3 bis 6 Sätze, Deutsch, sachlich, im Präteritum. Zuerst Lebensdaten und Herkunft, dann Ämter und Tätigkeiten,
  dann, was die Quellen zeigen (z. B. «erscheint 1440–1453 in Missiven der Stadt St. Gallen als Empfänger»).
- Jeder Satz endet mit den Kürzeln seiner Belege in eckigen Klammern: [HLS], [HBLS], [SSRQ], [KF], [SG], [Thun],
  [Bullinger], [Graph]. Mehrere: [HLS][SSRQ].
- Das HLS ist die erste Grundlage, wenn vorhanden. Formuliere mit eigenen Worten, kopiere keine Sätze.
- Ein HBLS-Eintrag ist nur über Name und Jahre zugeordnet: nenne ihn mit «laut HBLS (Zuordnung nach Name und
  Jahren)».
- Widersprechen sich Belege (Jahre, Ämter), nenne beide Angaben.
- Personen unter «nicht_zusammengefuehrt» sind NICHT diese Person. Verwende ihre Angaben nicht. Erwähne sie
  höchstens in einem letzten Satz: «Nicht zusammengeführt wurde …, weil die Übereinstimmung unsicher ist.»
- Wenn die Belege für eine Biografie zu dünn sind, schreibe einen einzigen Satz mit dem, was belegt ist.

Antworte als JSON: {"bio": "...", "unsicher": ["kurze Hinweise auf Unsicherheiten"]}"""


# ------------------------------------------------------------------ evidence

def load_index():
    recs = {r["id"]: r for s in SOURCES for r in read_jsonl(NORM / s / "persons.jsonl")}
    joint = {j["jid"]: j for j in read_jsonl(LINKS / "persons.jsonl")}
    apart = defaultdict(list)
    path = LINKS / "person_edges.csv"
    if path.exists():
        for row in csv.DictReader(path.open()):
            if row["grade"] in ("wahrscheinlich", "möglich"):
                apart[row["a"]].append((row["b"], row["grade"], row["evidence"]))
                apart[row["b"]].append((row["a"], row["grade"], row["evidence"]))
    facts = {r["key"]: r for r in read_jsonl(LINKS / "qlever_facts.jsonl")}
    return recs, joint, apart, facts


def steckbrief(j: dict, recs: dict) -> str:
    members = [recs[m] for m in j["members"] if m in recs]
    parts = [j["label"]]
    life = next(((r.get("birth"), r.get("death")) for r in members if r.get("birth") or r.get("death")), None)
    if life:
        parts.append(f"({life[0] or '?'}–{life[1] or '?'})")
    occ = sorted({r["occupation"] for r in members if r.get("occupation")})
    if occ:
        parts.append("· " + ", ".join(occ))
    bits = []
    for r in members:
        ys = f" {r['years'][0]}–{r['years'][1]}" if r.get("years") and r["years"][0] != r["years"][1] else (
            f" {r['years'][0]}" if r.get("years") else "")
        role = f", {'/'.join(r['roles'])}" if r.get("roles") else ""
        what = ", ".join(x for x in (f"{r['docs']} Dok." if r.get("docs") else "", role.lstrip(", ")) if x)
        bits.append(f"{SHORT.get(r['source'], r['source'])}{ys}" + (f" ({what})" if what else ""))
    return " ".join(parts) + ". Belegt in: " + "; ".join(bits) + "."


def evidence(j: dict, recs: dict, apart: dict, facts: dict, joint: dict) -> dict:
    members = [recs[m] for m in j["members"] if m in recs]
    pack = {"person": j["label"], "jahre_belegt": j.get("years"), "ids": j["ids"], "quellen": []}
    for r in members:
        pack["quellen"].append({k: v for k, v in {
            "kuerzel": TAG[r["source"]], "quelle": SHORT.get(r["source"]), "name": r["name"],
            "schreibweisen": r["forms"][:8], "jahre": r.get("years"), "geburt": r.get("birth"),
            "tod": r.get("death"), "beruf_amt": r.get("occupation"), "rollen": r.get("roles"),
            "orte": r.get("places")[:8] if r.get("places") else None, "registertext": (r.get("note") or "")[:600],
            "dokumente": r.get("docs")}.items() if v})
    if h := j["ids"].get("hls"):
        art = hls.article(h)
        if art and art.get("text"):
            pack["hls"] = {"kuerzel": "HLS", "titel": art["title"], "geburt": art["birth"], "tod": art["death"],
                           "text": art["text"][:3000]}
    if m := hbls.match(j["label"], j.get("years")):
        pack["hbls"] = {"kuerzel": "HBLS", "zuordnung": m["grade"], "familie": m["headword"], "vorname": m["given"],
                        "geburt": m["birth"], "tod": m["death"], "auszug": m["excerpt"]}
    for s in ("hls", "gnd", "wikidata"):
        if (f := facts.get(f"{s}:{j['ids'].get(s)}")) and (f["parents"] or f["children"] or f["holdings"]):
            pack["graph"] = {"kuerzel": "Graph", "eltern": [p["label"] for p in f["parents"] if p.get("label")],
                             "kinder": [c["label"] for c in f["children"] if c.get("label")],
                             "bestaende": f["holdings"]}
            break
    others = []
    for m in j["members"]:
        for other, grade, why in apart.get(j["jid"], []) if m == j["members"][0] else []:
            o = joint.get(other)
            if o:
                others.append({"name": o["label"], "jahre": o.get("years"), "grad": grade, "grund": why})
    if others:
        pack["nicht_zusammengefuehrt"] = others[:5]
    return pack


# ------------------------------------------------------------------ model

def slots_now() -> int:
    """Machine-wide cap, by day and by night (default 2, from 23:00 to 07:00 4), as on tei for gpt-oss."""
    h = datetime.now().hour
    start, end = (int(x) for x in env("VV_LLM_NIGHT", "23-7").split("-"))
    night = (start <= h or h < end) if start > end else (start <= h < end)
    return int(env("VV_LLM_SLOTS_NIGHT", "4") if night else env("VV_LLM_SLOTS_DAY", "2"))


@contextlib.contextmanager
def slot():
    """One of N lock files. VV_LLM_SLOT_DIR shares them with other pipelines on the same machine (on tei:
    ~/ssrq_print/data/llm_slots), so all of them together stay within the cap."""
    d = Path(env("VV_LLM_SLOT_DIR") or CACHE / "llm_slots")
    d.mkdir(parents=True, exist_ok=True)
    while True:
        for i in range(slots_now()):
            fh = open(d / f"{i}.lock", "w")  # noqa: SIM115 — held across the yield
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                fh.close()
                continue
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
                fh.close()
            return
        time.sleep(0.5)


def ask(pack: dict) -> dict:
    base = (env("VV_LLM_BASE_URL") or env("GPUSTACK_BASE_URL") or "https://gpustack.unibe.ch/v1").rstrip("/")
    key = env("VV_LLM_API_KEY") or env("GPUSTACK_API_KEY")
    model = env("VV_LLM_MODEL", "gpt-oss-120b")
    text = json.dumps(pack, ensure_ascii=False, sort_keys=True)
    h = hashlib.sha1((model + PROMPT + text).encode()).hexdigest()
    p = CACHE / "bio" / f"{h}.json"
    if p.exists():
        return json.loads(p.read_text())
    if not base:
        raise RuntimeError("no model endpoint (VV_LLM_BASE_URL)")
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 2000,
                       "response_format": {"type": "json_object"},
                       "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": text}]})
    req = urllib.request.Request(f"{base}/chat/completions", data=body.encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with slot(), urllib.request.urlopen(req, timeout=300) as r:
        ans = json.loads(json.loads(r.read())["choices"][0]["message"]["content"])
    ans["model"] = model
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ans, ensure_ascii=False))
    return ans


def priority(j: dict) -> tuple:
    return ("hls" in j["ids"], len(j["sources"]), len(j["members"]))


def run(limit: int | None, use_llm: bool, only: str | None = None) -> dict:
    recs, joint, apart, facts = load_index()
    old = {b["jid"]: b for b in read_jsonl(LINKS / "bios.jsonl")}
    todo = [j for j in joint.values() if ("hls" in j["ids"] or len(j["sources"]) > 1)]
    if only:
        todo = [joint[only]]
    todo.sort(key=priority, reverse=True)
    st = defaultdict(int)
    for k, j in enumerate(todo):
        row = {"jid": j["jid"], "label": j["label"], "steckbrief": steckbrief(j, recs)}
        if use_llm and (limit is None or st["llm"] < limit):
            try:
                pack = evidence(j, recs, apart, facts, joint)
                ans = ask(pack)
                row.update(bio=ans.get("bio"), unsicher=ans.get("unsicher") or [], model=ans.get("model"),
                           belege=sorted({q["kuerzel"] for q in pack["quellen"]} | {x for x in ("hls", "hbls", "graph")
                                                                                     if x in pack}),
                           generated=date.today().isoformat())
                if "hls" in pack:
                    art = hls.article(j["ids"]["hls"])
                    row["hls"] = {"url": art["url"], "author": art["author"], "version": art["version"],
                                  "licence": "CC BY-SA 4.0"}
                st["llm"] += 1
            except Exception as e:  # noqa: BLE001 — one person failing must not stop the run
                st[f"Fehler {type(e).__name__}"] += 1
                if j["jid"] in old and old[j["jid"]].get("bio"):
                    row = {**old[j["jid"]], "steckbrief": row["steckbrief"]}
        elif j["jid"] in old and old[j["jid"]].get("bio"):
            row = {**old[j["jid"]], "steckbrief": row["steckbrief"]}
        old[j["jid"]] = row
        st["steckbrief"] += 1
        if k % 100 == 0:
            print(f"  {k}/{len(todo)} {dict(st)}", flush=True)
    with (LINKS / "bios.jsonl").open("w") as fh:
        for jid in sorted(old):
            fh.write(json.dumps(old[jid], ensure_ascii=False, sort_keys=True) + "\n")
    return dict(st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="model biographies in this run")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--jid")
    a = ap.parse_args()
    print(f"bios: {run(a.limit, not a.no_llm, a.jid)} -> {LINKS / 'bios.jsonl'}")


if __name__ == "__main__":
    main()
