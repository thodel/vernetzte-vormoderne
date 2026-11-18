"""Fetch every source at its pinned commit into data/raw/<source>/ (not in git).

  python -m vv.fetch [--source ssrq,kf,…]

GitHub files come from raw.githubusercontent.com at the commit in config/sources.toml; a branch name is
resolved to its commit once and written to data/raw/<source>/COMMIT (pin it in sources.toml afterwards).
Königsfelden comes as the Zenodo zip of the pinned version.
"""
from __future__ import annotations

import argparse
import fnmatch
import io
import json
import re
import zipfile

from .common import RAW, SOURCES, get, sources


def expand(pattern: str, repo: str, sha: str) -> list[str]:
    """A path, or a glob in one directory (listed through the GitHub contents API at the commit)."""
    if "*" not in pattern:
        return [pattern]
    folder, _, pat = pattern.rpartition("/")
    listing = json.loads(get(f"https://api.github.com/repos/{repo}/contents/{folder}?ref={sha}",
                             accept="application/vnd.github+json"))
    return sorted(f"{folder}/{x['name']}" for x in listing if fnmatch.fnmatch(x["name"], pat))


def resolve(repo: str, ref: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        return ref
    data = json.loads(get(f"https://api.github.com/repos/{repo}/commits/{ref}", accept="application/vnd.github+json"))
    return data["sha"]


def fetch_github(name: str, cfg: dict) -> str:
    sha = resolve(cfg["repo"], cfg["commit"])
    dst = RAW / name
    for pat in cfg["files"]:
        for path in expand(pat, cfg["repo"], sha):
            out = dst / path
            if out.exists():
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(get(f"https://raw.githubusercontent.com/{cfg['repo']}/{sha}/{path}", pause=0.2))
    (dst / "COMMIT").write_text(sha + "\n")
    return sha


def fetch_zenodo(name: str, cfg: dict) -> str:
    dst = RAW / name
    if (dst / "VERSION").exists() and (dst / "VERSION").read_text().strip() == cfg["version"]:
        return cfg["version"]
    rec = json.loads(get(f"https://zenodo.org/api/records/{cfg['zenodo']}"))
    f = next(x for x in rec["files"] if x["key"] == cfg["zip"])
    outer = zipfile.ZipFile(io.BytesIO(get(f["links"]["self"], timeout=600)))
    dst.mkdir(parents=True, exist_ok=True)
    archives = [outer]  # the record's file is the repository archive; older records nest it once more
    archives += [zipfile.ZipFile(io.BytesIO(outer.read(m))) for m in outer.namelist() if m.endswith(".zip")]
    for z in archives:
        for m in z.namelist():
            if "/data/registers/" in m or "/data/docs/" in m:
                rel = m.split("/data/", 1)[1]
                if rel and not rel.endswith("/"):
                    (dst / rel).parent.mkdir(parents=True, exist_ok=True)
                    (dst / rel).write_bytes(z.read(m))
    (dst / "VERSION").write_text(cfg["version"] + "\n")
    return cfg["version"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="comma-separated; default all")
    a = ap.parse_args()
    cfg = sources()
    for name in (a.source.split(",") if a.source else SOURCES):
        c = cfg[name]
        at = fetch_zenodo(name, c) if "zenodo" in c else fetch_github(name, c)
        print(f"{name}: {at}", flush=True)


if __name__ == "__main__":
    main()
