"""One adapter per source: load() -> (persons, places) in the shape of docs/datenvertrag.md.

  python -m vv.adapters [--source ssrq,kf,…]   -> data/norm/<source>/{persons,places}.jsonl
"""
from __future__ import annotations

import argparse
import importlib

from ..common import NORM, SOURCES, write_jsonl


def run(names) -> dict:
    out = {}
    for name in names:
        persons, places = importlib.import_module(f".{name}", __name__).load()
        out[name] = (write_jsonl(NORM / name / "persons.jsonl", persons),
                     write_jsonl(NORM / name / "places.jsonl", places))
        print(f"{name}: {out[name][0]} persons, {out[name][1]} places", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    a = ap.parse_args()
    run(a.source.split(",") if a.source else SOURCES)


if __name__ == "__main__":
    main()
