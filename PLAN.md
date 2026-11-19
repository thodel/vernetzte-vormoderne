# Vernetzte Vormoderne — Plan

Stand 18.11.2026 (M0). Ein eigenständiger Demonstrator wie `vernetzte-schweiz`. Die Quellen werden
in ihren eigenen Repos ausgewertet. Hier werden sie zu einem gemeinsamen Personen- und Ortsindex
zusammengeführt, auf einer gemeinsamen Karte gezeigt und mit Kurzbiografien versehen.

## Entscheide (18.11.2026)

| Frage | Entscheid |
|---|---|
| Was wird zusammengeführt? | Nur «sicher»: gleiche Id aus einer Quelle oder eine Konkordanz (Metagrid, Bestandsgraph). Bei «wahrscheinlich» oder weniger entstehen zwei Personen mit einer Kante «möglicherweise dieselbe Person». |
| Gemeinsame Achse | Das SSRQ-Personen- und Ortsregister (`per…`, `loc…`). Königsfelden, die St. Galler Missiven und Teile des Thuner Registers verwenden es. Daneben gelten HLS, GND, Wikidata und Bullinger-Ids. |
| Konkordanzen | Metagrid (für `ssrq`- und `bullinger`-Ids) und der QLever-Bestandsgraph des Agentic Historian (`owl:sameAs`, Human Lineage). |
| Biografien | Für Personen mit HLS-Artikel oder mehreren Quellen. Das HLS ist erste Grundlage, angereichert mit HBLS und den Quellbelegen. Jeder Satz trägt Belegkürzel. Maschinell erstellt und so gekennzeichnet. |
| HLS-Zugang | Über die Datenbank von `hls_mcp`, nicht über die Website: die lehnt automatisierte Abrufe ab. |
| Modell | gpt-oss-120b über GPUStack. Die Grenze wird mit `ssrq_print` geteilt: 2 Aufrufe gleichzeitig tags, 4 nachts. |
| Karte | Gemeinsame Orte mit Koordinaten, Farbe nach Quelle. Orte in mehreren Quellen dunkel; nur möglicherweise gleiche Orte bleiben eigene Punkte. |
| Sprache | Seite und Dokumentation deutsch, Code englisch. |

## Meilensteine

**M0 — Gerüst und erste Fassung.** ✔ 18.11.2026.
- **Adapter:** Fünf Adapter liefern den Datenvertrag (`docs/datenvertrag.md`).
- **Verknüpfer:** zusammenführen nach Sicherheit, mit Konfliktschutz.
- **Konkordanzen:** Metagrid- und QLever-Abfragen.
- **Biografien:** Steckbriefe für alle Personen; Kurzbiografien nur für eine erste Probe.
- **Seite:** Suche, Personenseiten, Karte.

Stand der ersten Läufe:
- **Gemeinsamer Index:** 64 611 Personen, 372 davon in mehreren Quellen. Metagrid ist für die 3 040
  meistbelegten Ids abgefragt (2 017 mit Konkordanz) und hat 99 Zusammenführungen beigetragen.
- **Kanten «möglicherweise dieselbe Person»:** 4 132; Konflikte (verweigerte Zusammenführungen): 21.
- **Karte:** 8 711 Orte.

**M1 — Konkordanzen vollständig.**
- Metagrid für alle `per…`- und `P…`-Ids, gedrosselt über mehrere Nächte.
- Der Bestandsgraph, sobald der Endpoint wieder antwortet: am 18.11. gab `/sparql/` 404 zurück, und der
  Tunnel auf tei war inaktiv.
- Danach messen, wie viele Personen mehrere Quellen haben und wie viele Konflikte entstehen.

**M2 — Prüfstichprobe.** Je Stufe und Quellpaar 50 Kanten von Hand prüfen. Daraus folgt, ob
«wahrscheinlich» bei Namen + Jahren + Ort zu einer Zusammenführung werden darf.

**M3 — Biografien.** Alle Personen mit HLS-Artikel oder mehreren Quellen. Eine Stichprobe von 50
Biografien wird gegen die Belege gelesen: falsche Angaben, übernommene Sätze, Angaben aus nicht
zusammengeführten Personen.

**M4 — weitere Quellen.** Kandidaten:
- Zürcher Ratsmanuale und Editionen (Zentrale Serien);
- die SSRQ-Online-Edition (editio-data);
- Dodis (aus dem Bestandsgraphen);
- weitere Missiven-Bestände.

Dazu eine Konkordanz der Dokumente (thodel/ssrq_print#11) und Missiven ↔ Stücke (#12).

## Offene Fragen

1. ~~Sichtbarkeit~~ Entschieden am 19.11.2026: Repo und Seite sind öffentlich
   (https://thodel.github.io/vernetzte-vormoderne/). Die St. Galler Register stehen unter CC BY-NC 4.0;
   das ist im README und in der Fusszeile vermerkt.
2. **SSRQ-Superregister.** Personen aus verschiedenen Bänden bleiben getrennte Cluster, solange
   `ssrq_print` sie nicht bündelt. Sollen hier SSRQ-Datensätze untereinander als mögliche Entsprechungen
   verglichen werden?
3. **Lizenz Bullinger Digital** (korpus-tei ohne Lizenzangabe): bei Bullinger Digital nachfragen.
4. **HBLS-Zuordnung.** Nach Name und Jahren ist sie höchstens «wahrscheinlich». Soll sie als eigene
   Quelle mit Kanten in den Index (wie Thun), statt nur in die Biografie?
5. **Seiten-Links in die Quellprojekte.** Die Missiven-Viewer verlinken Personen über Hash-Routen. Zu
   prüfen ist, ob `#/actors/<n>` (SG) und `#/names/<id>` (Thun) die Personen öffnen.
