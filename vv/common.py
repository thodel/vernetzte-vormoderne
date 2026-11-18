"""Shared helpers: paths, the data contract's record shapes, name folding, polite cached HTTP."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import tomllib
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "sources.toml"
RAW = ROOT / "data" / "raw"          # fetched sources at their pinned commit (not in git)
NORM = ROOT / "data" / "norm"        # one JSONL per source and kind (the data contract, in git)
CACHE = ROOT / "data" / "cache"      # answers of external services (not in git)
LINKS = ROOT / "links"               # edges and the joint index (in git)
SITE = ROOT / "site"

UA = "vernetzte-vormoderne/0.1 (research project, DH Bern; cached, gentle)"
SOURCES = ("ssrq", "kf", "sg", "thun", "bullinger")


def sources() -> dict:
    return tomllib.loads(CONFIG.read_text())


# ------------------------------------------------------------------ records (docs/datenvertrag.md)

def person(source: str, local_id: str, name: str, **kw) -> dict:
    """A person as one source knows it. ids: scheme -> value (hls, gnd, wikidata, ssrq, bullinger, …)."""
    rec = {"id": f"{source}:{local_id}", "source": source, "local_id": local_id, "name": name,
           "forms": [], "years": None, "birth": None, "death": None, "roles": [], "occupation": None,
           "places": [], "note": None, "ids": {}, "docs": 0, "url": None}
    rec.update({k: v for k, v in kw.items() if v not in (None, "", [], {})})
    rec["forms"] = sorted({f for f in [name, *rec["forms"]] if f})
    return rec


def place(source: str, local_id: str, name: str, **kw) -> dict:
    rec = {"id": f"{source}:{local_id}", "source": source, "local_id": local_id, "name": name,
           "forms": [], "lat": None, "lon": None, "kind": None, "ids": {}, "docs": 0, "years": None,
           "url": None}
    rec.update({k: v for k, v in kw.items() if v not in (None, "", [], {})})
    rec["forms"] = sorted({f for f in [name, *rec["forms"]] if f})
    return rec


def write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.open()] if path.exists() else []


# ------------------------------------------------------------------ authority ids

HLS_URL = re.compile(r"hls-dhs-dss\.ch/(?:de|fr|it)/articles/0*(\d+)")
GND_URL = re.compile(r"d-nb\.info/gnd/([0-9X-]+)")
WD_URL = re.compile(r"wikidata\.org/(?:wiki|entity)/(Q\d+)")
SSRQ_PER = re.compile(r"\b(per\d{6})\b")
SSRQ_LOC = re.compile(r"\b(loc\d{6})\b")


def norm_id(scheme: str, value: str) -> str | None:
    """One spelling per scheme, so equal ids compare equal: hls 6 digits, gnd as is, wikidata Q…"""
    v = (value or "").strip()
    if not v:
        return None
    if scheme == "hls":
        m = HLS_URL.search(v) or re.fullmatch(r"(?:per-|hls:)?0*(\d+)/?", v)
        return f"{int(m.group(1)):06d}" if m else None
    if scheme == "gnd":
        m = GND_URL.search(v)
        return (m.group(1) if m else v.rsplit("/", 1)[-1]) or None
    if scheme == "wikidata":
        m = WD_URL.search(v) or re.fullmatch(r"(Q\d+)", v)
        return m.group(1) if m else None
    if scheme == "ssrq":
        m = SSRQ_PER.search(v) or SSRQ_LOC.search(v)
        return m.group(1) if m else None
    return v


def ids_from_urls(urls) -> dict:
    """Authority ids found in a list of URLs (Metagrid, register pointers)."""
    out = {}
    for u in urls:
        for scheme, rx in (("hls", HLS_URL), ("gnd", GND_URL), ("wikidata", WD_URL)):
            if rx.search(u):
                out.setdefault(scheme, norm_id(scheme, u))
        if "ssrq-sds-fds.ch" in u and (m := SSRQ_PER.search(u) or SSRQ_LOC.search(u)):
            out.setdefault("ssrq", m.group(1))
        if m := re.search(r"bullinger-digital\.ch/persons/(P\d+)", u):
            out.setdefault("bullinger", m.group(1))
        if m := re.search(r"dodis\.ch/(P\d+)", u):
            out.setdefault("dodis", m.group(1))
        if m := re.search(r"data\.histhub\.ch/person/(\d+)", u):
            out.setdefault("histhub", m.group(1))
        if m := re.search(r"viaf\.org/viaf/(\d+)", u):
            out.setdefault("viaf", m.group(1))
    return {k: v for k, v in out.items() if v}


# ------------------------------------------------------------------ names

_PARTICLES = {"von", "vom", "zu", "zum", "zur", "de", "di", "da", "der", "die", "am", "im", "an", "uf", "ab",
              "in", "und", "dem", "den"}


def fold(s: str) -> str:
    """Lower case, no diacritics, the historical letter variants merged (ſ/s, v/u, y/i, j/i, w/u, th/t, ck/k)."""
    s = unicodedata.normalize("NFKD", (s or "").replace("ſ", "s").replace("ß", "ss"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z ]+", " ", s)
    for a, b in (("tz", "z"), ("th", "t"), ("ck", "k"), ("dt", "t"), ("ph", "f"), ("y", "i"), ("j", "i"), ("v", "u"),
                 ("w", "u"), ("z", "s"), ("c", "k")):
        s = s.replace(a, b)
    s = re.sub(r"(.)\1+", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _folded_particles() -> set[str]:
    return {fold(p) for p in _PARTICLES}


def name_key(name: str) -> tuple[str, str]:
    """(surname-ish, forename-ish), folded. Handles «Surname, Forename» and «Forename von Surname»."""
    name = re.sub(r"\(.*?\)", " ", name or "")
    if "," in name:
        last, first = name.split(",", 1)
    else:
        parts = name.split()
        if not parts:
            return "", ""
        first, last = parts[0], " ".join(parts[1:])
    particles = _folded_particles()
    last = " ".join(w for w in fold(last).split() if w not in particles)
    first = (fold(first).split() or [""])[0]
    return last, first


# ------------------------------------------------------------------ HTTP (gentle, cached)

_last = [0.0]


def get(url: str, pause: float = 0.5, timeout: int = 60, accept: str | None = None) -> bytes:
    wait = pause - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA, **({"Accept": accept} if accept else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    finally:
        _last[0] = time.time()


def cached_json(kind: str, key: str, fetch, refresh: bool = False):
    """The cached answer of an external service, or fetch() it once. None (not found) is cached too."""
    p = CACHE / kind / (hashlib.sha1(key.encode()).hexdigest()[:20] + ".json")
    if p.exists() and not refresh:
        return json.loads(p.read_text())["v"]
    v = fetch()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"key": key, "v": v}, ensure_ascii=False))
    return v


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
