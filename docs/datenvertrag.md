# Datenvertrag

Jede Quelle wird von ihrem Adapter (`vv/adapters/<quelle>.py`) in dieselbe Form gebracht:
`data/norm/<quelle>/persons.jsonl` und `places.jsonl`, je eine Zeile pro Eintrag des Quellregisters.

## Person

| Feld | Inhalt |
|---|---|
| `id` | `<quelle>:<lokale id>`, z. B. `kf:per000089`, `ssrq:person5027446`, `bullinger:P2095` |
| `source`, `local_id` | Quelle und Id im Quellregister |
| `name`, `forms` | Ansetzung und alle Schreibweisen der Quelle |
| `years` | `[erstes, letztes]` Jahr der Belege, nicht die Lebensdaten |
| `birth`, `death` | Lebensdaten, wie die Quelle sie angibt (Text) |
| `roles` | Rollen in der Quelle (Aussteller, Empfänger, sender …) |
| `occupation`, `note` | Beruf/Amt; Beschreibung im Register |
| `places` | Orte bzw. Kantone, mit denen die Belege verbunden sind |
| `ids` | Normdaten und geteilte Ids: `hls`, `gnd`, `wikidata`, `ssrq` (`per…`), `bullinger`, `histhub`, `dodis`, `viaf` |
| `cands` | nur Vorschläge (Thun): `[{ids, grade, rule, label}]`, nie Ids |
| `docs` | Zahl der Dokumente/Briefe, in denen die Person vorkommt (soweit die Quelle sie liefert) |
| `url` | Seite der Person im Quellprojekt |

Ein Ort hat dieselben Felder ausser den personenbezogenen, dazu `lat`, `lon`, `kind` und `coord_grade`.

**Ids in einer Schreibweise:**
- HLS sechsstellig (`021574`);
- GND wie in der GND;
- Wikidata `Q…`;
- SSRQ `per`/`loc` mit sechs Ziffern.

## Quellen

| Quelle | Stand | Personen | Orte | Ids aus der Quelle |
|---|---|---|---|---|
| SSRQ (Druckbände, ssrq_print) | Commit in `config/sources.toml` | Superregister-Cluster | ja, Koordinaten gradiert | `per…` (Register), HLS (nur «match») |
| Königsfelden | Zenodo 10.5281/zenodo.10950031 | `people.xml` | `places.xml` | `per…`/`loc…` = SSRQ-Register, HLS/GND bei Orten |
| SG Missiven | Commit | `person.xml` | `place.xml` | SSRQ, histhub (über Metagrid) |
| Thun Missiven | Commit | automatisch erzeugtes Register | ja, automatisch | nur «sicher» als Id; Rest `cands` |
| Bullinger | Commit | `persons.xml` | `localities.xml` | GND, HLS, Bullinger `P…`; Briefe (CMIF) über die GND |

Die Rohdaten (`data/raw/`) sind nicht im Repo; `make fetch` lädt sie am gepinnten Stand.
