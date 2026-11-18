# Vernetzte Vormoderne

Ein gemeinsamer Index der Personen und Orte aus Rechtsquellen, Klosterakten und Briefwechseln der
Schweiz, etwa 1200–1800. Dazu kommen eine gemeinsame Karte und Kurzbiografien. Das Repo ist das
Gegenstück zu [vernetzte-schweiz](https://github.com/thodel/vernetzte-schweiz) für die Vormoderne.

Plan, Entscheide und offene Fragen: [PLAN.md](PLAN.md). Weitere Dokumentation:
[Datenvertrag](docs/datenvertrag.md), [Verknüpfung](docs/verknuepfung.md), [Biografien](docs/biografien.md).

## Quellen

- **SSRQ:** Sammlung Schweizerischer Rechtsquellen, Druckbände, neu gelesen und registriert
  ([ssrq_print](https://thodel.github.io/ssrq_print_pages/)).
- **Königsfelden:** Urkunden und Akten des Klosters und des Oberamts Königsfelden 1308–1662
  ([Zenodo](https://doi.org/10.5281/zenodo.10950031), CC BY 4.0).
- **St. Galler Missiven:** Briefverkehr der Stadt St. Gallen 1400–1650
  ([sg-missiven-data](https://dhbern.github.io/sg-missiven-data/)).
- **Thuner Missiven:** Burgerarchiv Thun, maschinell gelesen und registriert
  ([thun-missiven-data](https://dhbern.github.io/thun-missiven-data/)).
- **Bullinger Digital:** Briefwechsel Heinrich Bullingers 1523–1575
  ([bullinger-korpus-tei](https://github.com/bullinger-digital/bullinger-korpus-tei)).
- **Konkordanzen:**
  - [Metagrid](https://metagrid.ch) (SAGW);
  - der Bestandsgraph des Agentic Historian (QLever, mit Human-Lineage-Schicht).
- **Biografien:** HLS (CC BY-SA 4.0) und HBLS, über die Datenbanken von `hls_mcp` und `hbls_mcp`.

Jede Quelle ist in [config/sources.toml](config/sources.toml) an einen Commit bzw. eine Version gebunden.

## Grundsatz

Zusammengeführt wird nur, was **sicher** dieselbe Person ist:
- eine gleiche Id, die eine Quelle selbst setzt;
- oder eine Konkordanz (Metagrid, Bestandsgraph).

Ist die Übereinstimmung «wahrscheinlich» oder «möglich», bleiben es **zwei Personen**. Eine Kante
«möglicherweise dieselbe Person» verbindet sie und nennt ihren Beleg.

## Betrieb

```bash
make fetch      # Quellen am gepinnten Stand -> data/raw/
make norm       # Adapter -> data/norm/<quelle>/{persons,places}.jsonl
make metagrid   # Konkordanzen (gedrosselt, kumulativ) -> links/metagrid.jsonl
make qlever     # owl:sameAs und Verwandtschaft aus dem Bestandsgraphen -> links/qlever*.jsonl
make link       # gemeinsamer Index -> links/{persons,places}.jsonl, links/*_edges.csv
make bio        # Steckbriefe; mit Modell (tei): Kurzbiografien -> links/bios.jsonl
make site       # Daten der Seite -> site/data/
make serve      # http://localhost:8000
make test
```

## Lizenz

- **Code und Seite:** MIT.
- **Verknüpfungen in `links/`:** CC0 1.0. Ausgenommen sind die Biografien in `links/bios.jsonl`: Sie
  bauen auf dem HLS auf und stehen unter CC BY-SA 4.0, mit Nennung des Artikels.
- **Angaben der Quellen** (Namen, Schreibweisen, Daten in `data/norm/`): unter den Lizenzen der
  Quellen, siehe `config/sources.toml`. Für die St. Galler Missiven gilt CC BY-NC 4.0. Für Bullinger
  Digital ist die Lizenz noch zu klären ([PLAN.md](PLAN.md), Frage 3).
