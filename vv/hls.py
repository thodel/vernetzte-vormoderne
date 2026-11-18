"""HLS articles (hls-dhs-dss.ch, CC BY-SA 4.0): facts and text of a person's article, for the biographies.

Read from the database of hls_mcp (VV_HLS_DB: `articles`, `persons`), not from the website: the site refuses
automated clients, and we do not work around that. The article gives birth and death, the author and the
version; the text is input to the biography, which names article, author and version (CC BY-SA 4.0 asks for
that, docs/biografien.md).
"""
from __future__ import annotations

import html
import re
import sqlite3
from functools import lru_cache

from .common import env

URL = "https://hls-dhs-dss.ch/de/articles/{}/"


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse(body: str) -> dict:
    """Author, birth, death and paragraphs of an article's HTML (the text unit or the whole page)."""
    author = re.search(r'hls-article-author-function">[^<]*</span>(.*?)</div>', body, re.S)
    paras = [_clean(p) for p in re.findall(r"<p>(.*?)</p>", body, re.S)]
    born = re.search(r'class="hls-dnais"[^>]*>([^<]+)<', body)
    died = re.search(r'class="hls-ddec"[^>]*>([^<]+)<', body)
    return {"author": _clean(author.group(1)) if author else None, "birth": born.group(1).strip() if born else None,
            "death": died.group(1).strip() if died else None, "text": "\n".join(p for p in paras if p)}


@lru_cache(maxsize=1)
def _db():
    path = env("VV_HLS_DB")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True) if path else None


@lru_cache(maxsize=4096)
def article(hls_id: str) -> dict | None:
    con = _db()
    if con is None or not hls_id:
        return None
    row = con.execute("SELECT id, version, title, content_html FROM articles WHERE id = ?", (hls_id,)).fetchone()
    if not row:
        return None
    aid, version, title, body = row
    out = {"id": aid, "url": URL.format(aid), "title": title, "version": version, **parse(body or "")}
    p = con.execute("SELECT birth_date, death_date FROM persons WHERE article_id = ?", (aid,)).fetchone()
    if p:
        out["birth"] = out["birth"] or p[0]
        out["death"] = out["death"] or p[1]
    return out
