# Verknüpfung: zusammenführen nach Sicherheit

Stand 18.11.2026. Code: `vv/link.py`, Konkordanzen `vv/metagrid.py`, `vv/qlever.py`.

## Grundsatz

Zusammengeführt wird nur, was **sicher** dieselbe Person (derselbe Ort) ist. Ist die Sicherheit
«wahrscheinlich» oder geringer, entstehen **zwei Personen**. Sie sind durch eine Kante
«möglicherweise dieselbe Person» verbunden, und diese Kante trägt ihren Beleg. Ein späterer Beleg,
etwa eine neue Konkordanz oder eine Prüfung von Hand, kann aus einer Kante eine Zusammenführung machen.
Umgekehrt geht das nicht, ohne dass jemand eine Zusammenführung zurücknimmt.

| Stufe | Beleg | Folge |
|---|---|---|
| sicher | gleiche Id, die eine Quelle selbst setzt (SSRQ-Register `per…`/`loc…`, HLS, GND, Wikidata, Bullinger `P…`, GeoNames) | zusammengeführt |
| sicher (Konkordanz) | Metagrid oder `owl:sameAs` im Bestandsgraphen (QLever) verbindet zwei Ids | zusammengeführt |
| wahrscheinlich | Thun: Kandidat «wahrscheinlich»; Name gleich (gefaltet), Jahre passen, gleicher Ort oder Belege ≤ 10 Jahre auseinander; Orte: gleicher Name, ≤ 3 km | Kante |
| möglich | Thun: Kandidat «möglich»; Nachname und Vorname gleich, Jahre widersprechen nicht; Orte: gleicher Name, ≤ 15 km oder ohne Koordinaten | Kante |
| Konflikt | eine Zusammenführung ergäbe zwei Werte desselben Schemas (zwei HLS-Artikel, zwei SSRQ-Ids …) | Kante, nicht zusammengeführt |

## Ablauf

1. **Eigene Ids zuerst.** Was eine Quelle selbst behauptet, wird vor den Konkordanzen verbunden. Eine
   Konkordanz kann so nicht auseinanderreissen, was eine Edition gesetzt hat.
2. **Konkordanzen.** Metagrid wird nach `ssrq` (`per…`) und `bullinger` (`P…`) gefragt, der
   Bestandsgraph nach HLS, GND und Wikidata. Gilt die Zusammenführung, hält der Datensatz fest, über wen
   die Id kam (`via`).
3. **Vorschläge einer Quelle.** Die Kandidaten des automatisch erzeugten Thuner Registers werden Kanten
   zu der Person, die die vorgeschlagene Id trägt.
4. **Namen.**
   - **Blöcke:** gebildet nach gefaltetem Nachnamen und erstem Vornamen. Gefaltet heisst: ſ/s, u/v/w,
     i/j/y, th/t, ck/k, Doppelbuchstaben, ohne «von», «zum» usw.
   - **Paare:** verglichen werden nur Paare aus verschiedenen Quellen. Innerhalb einer Quelle gilt deren
     eigene Bündelung.
   - **Grosse Blöcke:** Blöcke über 150 Datensätze («Hans Müller») werden übersprungen und gezählt.

## Gemeinsame Ids

- **SSRQ-Register:** Königsfelden, die St. Galler Missiven und Teile des Thuner Registers verwenden die
  Ids des SSRQ-Personen- und Ortsregisters. Eine Königsfelder Person `per000089` und der SSRQ-Eintrag
  mit derselben Id sind darum nach der Zuordnung der Editoren dieselbe Person. Ob dieselbe Id in zwei
  Projekten wirklich dieselbe Person meint, hängt am SSRQ-Register; Konflikte werden gezählt.
- **Joint-Id:** Die gemeinsame Person trägt die Id des am breitesten geteilten Normdatums:
  HLS vor GND, Wikidata, SSRQ, Bullinger, GeoNames. Sonst gilt die Id ihres ersten Datensatzes. Damit
  bleibt die Joint-Id stabil, solange sich die Normdaten nicht ändern.

## Ausgaben

- **`links/persons.jsonl`, `links/places.jsonl`:** die gemeinsamen Personen bzw. Orte mit ihren
  Datensätzen (`members`), Quellen, Ids und Jahren.
- **`links/person_edges.csv`, `links/place_edges.csv`:** die Kanten, je Paar die stärkste.
- **`links/*_summary.json`:** die Zählungen.
- **`links/metagrid.jsonl`, `links/qlever.jsonl`:** die Konkordanzen. Sie sind kumulativ; die Antworten
  liegen in `data/cache/`.

## Offen

- **Personen im SSRQ-Superregister:** Zwei Personen aus verschiedenen Bänden sind dort getrennte
  Cluster. Wie sie zusammengehen, entscheidet `ssrq_print`; hier werden SSRQ-Datensätze nicht
  untereinander verglichen.
- **Orte:** Die Zuordnung stützt sich auf Koordinaten unterschiedlicher Güte. SSRQ-Koordinaten sind
  gradiert, die Thuner sind automatisch. Eine Ortskante mit «≤ 3 km» ist darum nur so gut wie die
  schlechtere der beiden Koordinaten.
