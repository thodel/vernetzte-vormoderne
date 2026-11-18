"""HBLS (Historisch-Biographisches Lexikon der Schweiz, 1921–1934): family articles and their members.

The HBLS has no ids that our sources share. A member is matched to a joint person by surname (the article's
headword), forename and life years: at best «wahrscheinlich», so it never merges anything; the biography uses
it as context and says so. Needs the database of hbls_mcp (`articles`, `members`) at VV_HBLS_DB.
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache

from .common import env, fold, name_key


@lru_cache(maxsize=1)
def _db():
    path = env("VV_HBLS_DB")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True) if path else None


@lru_cache(maxsize=1)
def _heads() -> dict:
    """folded headword (no spaces) -> article ids; the HBLS spells as the 1920s did, so match folded."""
    out = {}
    for aid, hw in _db().execute("SELECT id, headword FROM articles WHERE id IN (SELECT article_id FROM members)"):
        out.setdefault(fold(hw or "").replace(" ", ""), []).append(aid)
    return out


def match(label: str, years: list[int] | None) -> dict | None:
    """The HBLS member best fitting a person: same surname headword, same forename, years fit (±10)."""
    con = _db()
    if con is None or not years:
        return None
    last, first = name_key(label)
    if not last or not first:
        return None
    head = last.split()[-1]
    aids = [a for k, v in _heads().items() if k.startswith(head.replace(" ", "")) for a in v][:50]
    if not aids:
        return None
    rows = con.execute(
        "SELECT a.id, a.headword, a.volume, a.page, a.pdf_url, a.article_text, m.given, m.birth_year, m.death_year "
        f"FROM members m JOIN articles a ON a.id = m.article_id WHERE a.id IN ({','.join('?' * len(aids))})",
        aids).fetchall()
    best = None
    for aid, hw, vol, page, pdf, text, given, by, dy in rows:
        if (fold(given or "").split() or [""])[0] != first:
            continue
        lo, hi = by or (dy - 80 if dy else None), dy or (by + 80 if by else None)
        if lo is None or not (lo - 10 <= years[1] and years[0] <= hi + 10):
            continue
        cand = {"article": aid, "headword": hw, "volume": vol, "page": page, "pdf": pdf, "given": given,
                "birth": by, "death": dy, "grade": "wahrscheinlich" if by and dy else "möglich",
                "excerpt": _excerpt(text or "", given or "")}
        if best is None or (cand["grade"] == "wahrscheinlich" and best["grade"] != "wahrscheinlich"):
            best = cand
    return best


def _excerpt(text: str, given: str, width: int = 700) -> str:
    i = text.find(given) if given else -1
    return text[max(0, i - 80): i + width] if i >= 0 else text[:width]
