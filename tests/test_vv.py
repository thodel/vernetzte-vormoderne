import csv
import json

import pytest

from vv import common, link
from vv.common import fold, ids_from_urls, name_key, norm_id, person


def test_fold_and_name_key():
    assert fold("Thůrn") == fold("Turn")
    assert fold("ſchwytz") == fold("Schwiz")
    assert name_key("Landenberg, Wildhans von") == ("landenberg", "uildhans")
    assert name_key("Hans von Klingenberg") == ("klingenberg", "hans")


def test_norm_id():
    assert norm_id("hls", "https://hls-dhs-dss.ch/de/articles/021574/") == "021574"
    assert norm_id("hls", "per-25549") == "025549"
    assert norm_id("ssrq", "https://www.ssrq-sds-fds.ch/persons-db-edit/?query=per009962") == "per009962"
    assert norm_id("wikidata", "https://www.wikidata.org/wiki/Q68978") == "Q68978"
    ids = ids_from_urls(["https://www.bullinger-digital.ch/persons/P20126", "https://d-nb.info/gnd/11860371X",
                         "https://dodis.ch/P58258"])
    assert ids == {"bullinger": "P20126", "gnd": "11860371X", "dodis": "P58258"}


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(link, "NORM", tmp_path / "norm")
    monkeypatch.setattr(link, "LINKS", tmp_path / "links")
    monkeypatch.setattr(link, "SOURCES", ("a", "b", "c"))

    def put(src, rows):
        common.write_jsonl(tmp_path / "norm" / src / "persons.jsonl", rows)
    return put, tmp_path


def test_merge_only_when_sure(world):
    put, tmp = world
    put("a", [person("a", "1", "Hans von Klingenberg", ids={"ssrq": "per000001"}, years=[1440, 1450]),
              person("a", "2", "Ulrich Zwick", years=[1500, 1510])])
    put("b", [person("b", "x", "Klingenberg, Hans von", ids={"ssrq": "per000001", "hls": "012345"}),
              person("b", "y", "Zwick, Ulrich", years=[1505, 1505])])
    put("c", [])
    s = link.build("persons")
    rows = [json.loads(x) for x in (tmp / "links" / "persons.jsonl").open()]
    merged = next(r for r in rows if "a:1" in r["members"])
    assert merged["members"] == ["a:1", "b:x"] and merged["jid"] == "hls-012345"
    zw = [r for r in rows if any(m in r["members"] for m in ("a:2", "b:y"))]
    assert len(zw) == 2, "a name match alone never merges"
    edges = list(csv.DictReader((tmp / "links" / "person_edges.csv").open()))
    assert any(e["grade"] in ("wahrscheinlich", "möglich") and {e["record_a"], e["record_b"]} == {"a:2", "b:y"}
               for e in edges)
    assert s["joint"] == 3


def test_conflict_is_refused(world):
    put, tmp = world
    put("a", [person("a", "1", "Anna Meier", ids={"ssrq": "per000002", "hls": "000001"})])
    put("b", [person("b", "1", "Anna Meier", ids={"ssrq": "per000002", "hls": "000002"})])
    put("c", [])
    link.build("persons")
    rows = [json.loads(x) for x in (tmp / "links" / "persons.jsonl").open()]
    assert len(rows) == 2
    edges = list(csv.DictReader((tmp / "links" / "person_edges.csv").open()))
    assert edges and all(e["grade"] in ("Konflikt", "wahrscheinlich", "möglich") for e in edges)


def test_candidates_are_edges_not_merges(world):
    put, tmp = world
    put("a", [person("a", "1", "Peter Schopfer", ids={"ssrq": "per027248"})])
    put("b", [person("b", "t1", "Peter Schopffer",
                     cands=[{"ids": {"ssrq": "per027248"}, "grade": "möglich", "rule": "ssrq"}])])
    put("c", [])
    link.build("persons")
    rows = [json.loads(x) for x in (tmp / "links" / "persons.jsonl").open()]
    assert len(rows) == 2
    edges = list(csv.DictReader((tmp / "links" / "person_edges.csv").open()))
    assert any("kandidat" in e["evidence"] or e["grade"] == "möglich" for e in edges)


def test_concordance_merges(world, monkeypatch):
    put, tmp = world
    put("a", [person("a", "1", "Johannes Aal", ids={"bullinger": "P1"})])
    put("b", [person("b", "1", "Johann Aal", ids={"ssrq": "per000009"})])
    put("c", [])
    (tmp / "links").mkdir(parents=True, exist_ok=True)
    row = {"key": "bullinger:P1", "ids": {"ssrq": "per000009"}}
    (tmp / "links" / "metagrid.jsonl").write_text(json.dumps(row) + "\n")
    link.build("persons")
    rows = [json.loads(x) for x in (tmp / "links" / "persons.jsonl").open()]
    assert len(rows) == 1 and rows[0]["members"] == ["a:1", "b:1"]


def test_hls_parse():
    from vv.hls import parse
    html = ('<div class="hls-article-text-author"><span class="hls-article-author-function">Autorin/Autor:</span>'
            ' Hans Muster </div><p><span class="hls-dnais">1.1.1500</span> Bern, '
            '<span class="hls-ddec">2.2.1560</span> Basel. Ratsherr.</p>')
    a = parse(html)
    assert a["author"] == "Hans Muster" and a["birth"] == "1.1.1500" and "Ratsherr" in a["text"]
