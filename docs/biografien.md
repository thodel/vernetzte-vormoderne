# Kurzbiografien

Code: `vv/bio.py`, `vv/hls.py`, `vv/hbls.py`.

## Was geschrieben wird

- **Steckbrief für jede gemeinsame Person:** ohne Modell aus den Belegen gebaut. Er nennt Name,
  Lebensdaten, Amt, die Quellen mit Jahren und Rollen.
- **Kurzbiografie:** für Personen mit HLS-Artikel oder mit Belegen in mehreren Quellen. 3–6 Sätze,
  geschrieben vom Textmodell (gpt-oss-120b über GPUStack) aus einem **Belegpaket**:
  1. **HLS-Artikel:** Lebensdaten und Text, aus der Datenbank von `hls_mcp` (`VV_HLS_DB`). Die Website
     des HLS lehnt automatisierte Abrufe ab, das umgehen wir nicht.
  2. **HBLS-Familienartikel:** einer, dessen Mitglied nach Name und Jahren passt (`VV_HBLS_DB`). Das ist
     höchstens «wahrscheinlich»; die Biografie sagt «laut HBLS (Zuordnung nach Name und Jahren)».
  3. **Quelldatensätze:** jeder, der sicher zur Person gehört: Schreibweisen, Jahre, Rollen, Ämter, Orte,
     Registertext, Zahl der Dokumente.
  4. **Bestandsgraph (QLever):** Eltern und Kinder (Human-Lineage-Schicht) und die Bestände, in denen
     die Person genannt wird.
  5. **«nicht_zusammengefuehrt»:** die Personen, die nur möglicherweise dieselben sind. Das Modell darf
     ihre Angaben nicht verwenden, höchstens sagen, dass sie getrennt blieben.

## Belegkürzel

Jeder Satz endet mit den Kürzeln seiner Belege: `[HLS] [HBLS] [SSRQ] [KF] [SG] [Thun] [Bullinger] [Graph]`.
Die Seite zeigt sie klein. Wer einen Satz prüfen will, findet die Belege in der Tabelle darunter.

## Lizenz und Nennung

- **HLS-Texte:** stehen unter CC BY-SA 4.0. Eine Biografie, die auf einem HLS-Artikel aufbaut, steht
  darum ebenfalls unter CC BY-SA 4.0 und nennt Artikel, Autorin oder Autor und Version.
- **HBLS:** 1921–1934 erschienen; zitiert wird nach Band und Seite.
- **Kennzeichnung:** Die Biografien sind maschinell erstellt und nicht redigiert. Die Seite sagt das bei
  jeder Biografie, mit Modell und Datum.

## Betrieb

Auf tei, wo die Datenbanken und GPUStack liegen:

```bash
export VV_HLS_DB=/home/dh/hls_db/hls.db VV_HBLS_DB=/home/dh/hbls_data/hbls.db
export VV_LLM_SLOT_DIR=/home/dh/ssrq_print/data/llm_slots   # teilt die Grenze (2 tags, 4 nachts) mit ssrq_print
. ~/ssrq_print/scripts/env_tei.sh                            # GPUSTACK_BASE_URL, GPUSTACK_API_KEY
.venv/bin/python -m vv.bio --limit 200
```

Die Antworten werden nach Modell, Prompt und Belegpaket zwischengespeichert. Ändert sich ein Beleg,
wird die Biografie neu geschrieben, sonst nicht.
