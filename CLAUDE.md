# CLAUDE.md – Arbeitsregeln für UPA-Analyzer-Control

Diese Datei liest Claude zu Beginn jeder Sitzung in diesem Repo automatisch.
Sie enthält die **dauerhaften** Regeln und Erkenntnisse. Den aktuellen Stand
(offene PRs, nächste Aufgaben) führt die Übergabe-Datei
`claude/UPA_Software_Stand.md` im claude.ai-Projekt „HiFi- Geräte Reparatur“.

## Projekt
Windows-Programm, das einen **Rohde & Schwarz UPA3** (Audioanalysator) über einen
**AR488-GPIB-Adapter** steuert, Messprogramme fährt und **Prüfprotokolle
(PDF + DOCX)** im Hausstil erzeugt. Zusätzlich Logger für ein **Fluke 287**.
Entwickelt für Vintage Audio Repair Magdeburg (Erik, GitHub `techniker67`), MIT-Lizenz.

## Verbindliche Arbeitsregeln (Erik)
1. **Immer nur EINE Variable pro Testlauf ändern.**
2. **Auf Bewährtem aufbauen.** Nichts voraussetzen, was nicht am Gerät bestätigt ist.
3. **Keine Schleifen-/Flut-Fehler produzieren** (GPIB-Erfahrung: endloses „NOT TRIGGERED“).
4. **Jede Änderung: Zweig → Pull Request.** Erik prüft, merged und testet auf seinem PC.
5. **Releases startet Erik** (Actions → Windows-Installer → Run workflow, Branch main,
   Haken „Release mit Setup.exe veroeffentlichen“).
6. **Keine neuen Funktionen ohne Eriks Bestätigung.** Ideen vorschlagen, dann warten.
7. **Neue Messprogramme bleiben auf `status: "test"`** (VERIFIKATION), bis Erik
   Prüfprotokolle vom echten Gerät geliefert hat. Erst dann `"ok"` und die neuen
   Befehle in `PROVEN` (`upa_core.py`) aufnehmen.
8. Sprache Deutsch, knapp und direkt. Erik ist Elektronik-Praktiker, kein
   Programmierer: Ergebnisse und Bedienung erklären, nicht den Code.

## Technischer Ablauf
- Commits mit Eriks Identität:
  `git -c user.name="techniker67" -c user.email="techniker67@users.noreply.github.com" commit …`
- Push: `git -c push.negotiate=true push -u origin <zweig>`
- PR: `gh api repos/techniker67/UPA3-ANALYZER-CONTROL/pulls -f title=… -f head=<zweig> -f base=main -F body=@datei`
- CI: `.github/workflows/windows-installer.yml` baut PyInstaller + Inno Setup je PR.
- Nicht möglich aus der Claude-Sitzung (403): Tags pushen, Zweige löschen,
  Repo-Einstellungen, Actions-Artefakte laden → macht Erik.
- Je PR, der das Programm ändert: `upa_version.py` (`__version__`, `DATUM`) und
  `CHANGELOG.md` anpassen, README/`docs/` mitziehen.
  Schema: PATCH = Korrektur, MINOR = neue Funktion / neues Messprogramm.

## Aufbau
| Datei | Inhalt |
|---|---|
| `upa_version.py` | Version, Datum, `GETESTETE_FIRMWARE` |
| `upa_paths.py` | Programm-, Ressourcen-, Datenordner (`--data`, `UPA_DATA`, Datei `portable`) |
| `upa_core.py` | Adapter-Check, Messkette `measure()`, `PROVEN`-Befehlsliste, Band-Messweg `band_*` |
| `upa_programs.py` | Messprogramme mit `status` ok / test / locked |
| `upa_abgleich.py` | Abgleichlisten (.json) für das Fenster ABGLEICH |
| `upa_fluke.py` | Fluke-287-Logger (Logger-Klasse auch für MM2) |
| `upa_voltcraft.py` | MM2 Voltcraft VC-7055BT (RS-232, nur lesen) |
| `upa_report.py` | Diagramme (matplotlib, DPI 300), Auswertungen |
| `upa_protokoll.py` | Prüfprotokoll PDF + DOCX, Papierkorb |
| `upa_server.py` | HTTP-Server 127.0.0.1:8488, API, Jobs, CSV |
| `upa_window.py` | pywebview-Fenster |
| `index.html` | Oberfläche im TRON-Stil (monochrom-leuchtend auf Schwarz, Glow, Grid, Monospace) |

## Hardware bei Erik
- UPA3 SN 372.6014.02, Optionen B2/B6/B8/B9, **GPIB-Adresse 7**.
- AR488 (ESP32-S2, Build Hans W./DiyEMC) an **COM4**, Firmware **0.53.26 (JW)** –
  vorerst **nicht** updaten, alle Verifikationen hängen daran.
- Fluke 287 (FW V1.41) an **COM3**, IR-USB-Kabel (FTDI), 115200 8N1, nur lesend (`ID`, `QM`).
- Voltcraft VC-7055BT (FW V3.0.0, SN 2210062) als MM2 an **COM5** (FTDI + Nullmodem), 115200 8N1,
  Abschluss LF, kein Echo. Nur lesen: `*IDN?`, `FUNC?` (`"VOLT"`, `"VOLT AC"`, `"RES"`), `RANGE?`
  (Ω als GBK), `AUTO?`, `MEAS1?` (Überlauf `1E+9`). **Kein `SYST:REM`** (sperrt nur die Tasten),
  `CONF?` antwortet nicht. Befunde: Projektdoc `claude/VC-7055BT_Befunde.md`.
- Asymmetrische HiFi-Messung über BNC; der UPA hat keinen symmetrischen XLR-Eingang.

## GPIB / UPA – nicht neu herausfinden!
- Adapter: `++mode 1`, `++addr 7`, `++auto 0`, `++eoi 1`, `++eos 0`.
  **`++auto 1` ist ungeeignet** (Dauerschleife von Lesevorgängen).
- **REM nur mit dieser Reihenfolge:** `++ren 1` → `++llo` → `CLEAR`.
  Im Local-Mode antwortet der UPA endlos „UPA IN LOCALMODE“.
- `DELIMITER(TYPE(NL/EOI))` zu Beginn jeder Messung (fehlendes EOI war die Ursache
  der „NOT TRIGGERED“-Flut).
- Ausgabeformat `STRING(SINGLE ALPHANUM)`: 9 Zeichen Header + Wert,
  z. B. `MACVOLTRU 00.992E+0`. Wert = erste Zeile ohne LOCALMODE/NOT TRIGGERED.
  `88888` = kein Wert.
- **Ein Trigger = genau so viele Reads, wie der Triggermodus Werte liefert**
  (LEV = 1, LEV/FREQ = 2, LEV/FNCT = 2, LEV/FREQ/FNCT = 3). Nach `TRIGGER(SINGLE)`
  kein anderer Befehl vor dem Lesen.
- Status nur per `++spoll`. Ungeprüfte Befehle einzeln senden, per spoll prüfen,
  bei Ablehnung **vor** dem Trigger abbrechen.
- Antwortzeit 2–3 s, schwankend → aktiv pollen (AR488 read_tmo 1,2 s, wiederholt
  `++read eoi`), nicht fest warten.
- Autoranging ohne stabiles Signal terminiert nicht → fester Bereich
  `RANGE(LEVEL HOLD(n))` (Ausnahme: Bandmessungen und Messungen mit P78 → AUTO).
- `measure()` braucht ca. 20 s pro Punkt; für Bandmessungen den schnelleren `band_*`-Weg.
- Generator startet mit 0 V – Amplitude immer explizit setzen.
- **Generatorausgang:** `OUTPUT(LEFT …)` und `OUTPUT(RIGHT …)` sind EIN Zustand, der
  letzte Befehl gewinnt. Beide Ausgänge gleichzeitig: **`OUTPUT(BOTH UNBAL)`** – steht nicht
  im Handbuch (E-7), an Eriks UPA3 am 25.11.2026 bestätigt (Taste L+R → `OUTPUT?` meldet
  BOTH; als Setzbefehl Status 0, Rücklesen ok, LEDs L+R); 17:26 im Abgleich live bestätigt →
  in `PROVEN`. `OUTPUT(RIGHT OFF)` weiterhin ungeprüft.
- **Setup abfragen ohne CLEAR** (Tastenstellung bleibt): `++ren 1` → `DELIMITER(TYPE(NL/EOI))`
  → Abfrage (z. B. `OUTPUT?`) → 3 s warten → genau EIN `++read eoi` → `++spoll` → `++loc` →
  `++ren 0`. Ohne DELIMITER bzw. zu früh gelesen: „NOT TRIGGERED“-Flut, Adapter hängt, UPA
  bleibt auf REM. Weg, unbekannte Befehle zu finden: am Gerät von Hand einstellen, abfragen.
- Hängt der Adapter (keine `++`-Antwort): USB physisch neu stecken.

## Messtechnik
- W&F-Modi: DIN (3,15 kHz, Quasi-Peak), NAB (3,00 kHz, Mittelwert),
  **JIS = WRMS** (3 kHz, RMS; Skala japanischer Deck-Sollwerte), AM.
  IEC-Bus z. B. `WOWFLUTTER(DIN WTD)`. Handbuchseite 2.156 (Syntaxtabelle) fehlt im Scan.
- THD+N mit Tiefpass 22 kHz. Loopback-Restwert ca. 0,007–0,012 % (1 kHz).
- Phase L–R (`PHASE(ON)`) braucht Sonderverkabelung am symmetrischen Eingang →
  gesperrt; Azimut über Pegelmaximum.
- P78-Abschwächer 20:1: 19,38:1 bis 1 kHz, −1,28 dB @ 10 kHz, −2,25 dB @ 20 kHz →
  Kalibriertabelle je Kanal (`docs/attenuator-calibration.md`).

## Windows-Eigenheiten
- matplotlib zeichnet Calibri-Bitmapgrößen leer → DPI 300 + Selbsttest.
- pywebview 6.2.1: Ordnerdialog `create_file_dialog(webview.FileDialog.FOLDER, …)`;
  closing-Handler nicht blockieren.
- FlukeView Forms muss geschlossen sein, sonst ist COM3 belegt.

## Testen ohne Hardware (in der Claude-Sitzung)
`sys.modules["serial"]`, `serial.tools`, `serial.tools.list_ports` (`comports = lambda: []`)
durch Fake-Module ersetzen; für Messabläufe `upa_core.adapter_check`/`upa_check` auf
Erfolg patchen und `upa_core.UPA` durch eine Fake-Klasse ersetzen. Dann
`upa_server.main()` mit `--data /tmp/X --http 8491 --no-browser`, Oberfläche per
Playwright prüfen. Fluke-Fake: `ID` → `0\rFLUKE 287,V1.41,…\r`,
`QM` → `0\r<Wert>,VDC,NORMAL,NONE\r`, OL = `9.99999999E+37`.
