# Changelog – UPA-Software

Versionsschema: MAJOR.MINOR.PATCH. PATCH = Korrektur, MINOR = neue Funktion, 1.0.0 = erste GitHub-Veröffentlichung.

## 0.8.3 – 2026-11-20
- **Windows-Installation:** GitHub baut automatisch eine `Setup.exe` (PyInstaller + Inno Setup) – keine Python-Installation nötig. Startmenü-Eintrag, optionale Desktop-Verknüpfung, Verknüpfung „Messdaten-Ordner", Deinstallation. Installierbar ohne Administratorrechte. Der Datenordner bleibt beim Deinstallieren erhalten.
- Jeder Bau wird automatisch getestet (Programmstart, Oberfläche, Version, QUIT).
- Zweiter Start, während die Software schon läuft: öffnet die vorhandene Oberfläche statt eines Fehlers.
- Installierte Version: Startfehler bleiben im Fenster lesbar.

## 0.8.2 – 2026-11-20
- Schaltfläche **⏻ QUIT** oben rechts: beendet die Software nach Rückfrage, das Konsolenfenster schließt sich. Während einer Messung gesperrt (erst Stop). Der Browser-Tab zeigt „SYSTEM SHUTDOWN" und schließt sich, soweit der Browser das erlaubt.
- `UPA_Software_starten.bat`: Fenster bleibt nur noch bei einem Fehler offen.

## 0.8.1 – 2026-11-20
- Hinweistexte unter den Messprogrammen für Anwender umformuliert (praktische Tipps statt Entwicklungsnotizen); Symbol ℹ statt ✓. Gesperrte Programme nennen nur noch, was fehlt.

## 0.8.0 – 2026-11-20
- Eigener Datenordner, getrennt vom Programm: `Dokumente/UPA-Analyzer-Control` mit `upa_einstellungen.json`, `p78_kalibrierung.json`, `upa_log.txt` und `Messungen/`. Ein Update oder eine Neuinstallation überschreibt nichts mehr.
- Beim ersten Start werden Einstellungen und P78-Kalibrierung aus dem bisherigen Programmordner in den Datenordner **kopiert**; die Originale bleiben liegen. Alte Messungen bleiben im bisherigen Ordner `Messungen/`.
- Datenordner wählbar: Startoption `--data <Ordner>`, Umgebungsvariable `UPA_DATA` oder Datei `portable` im Programmordner (dann bleibt alles im Programmordner, z. B. für USB-Stick).
- Der Datenordner wird beim Start im Konsolenfenster und im Protokoll angezeigt. Die Messkette ist unverändert.

## 0.7.0 – 2026-11-20
- P78-Kalibrierung für Kanal R (Terzen 20 Hz–20 kHz); `p78_kalibrierung.json` enthält jetzt je Kanal eine Tabelle (`kanaele.L`, `kanaele.R`), die Software wählt automatisch die passende. R weicht von L höchstens 0,03 dB ab.

## 0.6.0 – 2026-11-20
- GPIB-Adresse im Startfenster frei wählbar (0–30); Prüfschritt heißt neutral „GPIB-Adresse (++addr)"; Kopfzeile zeigt die aktive Adresse.
- Port und Adresse werden nach erfolgreicher Initialisierung in `upa_einstellungen.json` gespeichert und beim nächsten Start vorbelegt.
- Start-Skript für Linux (`upa_software_starten.sh`), `requirements.txt`.

## 0.5.0 – 2026-11-20
- Adapter-Firmware (`++ver`) wird in jeder CSV (Kopfzeile `# Adapter: …`) und im Protokoll festgehalten; Tooltip an der Anzeige ADAPTER.
- Liste getesteter Firmware in `upa_version.py` (`GETESTETE_FIRMWARE`, aktuell 0.53.26 (JW)); andere Versionen laufen, erzeugen aber einen Hinweis im Protokoll.

## 0.4.0 – 2026-11-19
- P78-Abschwächer kalibriert (Terzen 20 Hz–20 kHz, Kanal L, 40-cm-Kabel): `p78_kalibrierung.json`, frequenzabhängige Korrektur (log-f-Interpolation). Kontrolle: ±0,02 dB über 20 Hz–20 kHz.
- Mit P78 automatisch Bereich AUTO (4 Stellen); AUTO ist jetzt Vorgabe aller Programme.
- Aktive Frequenz/Pegel im Ausgangsfenster orange markiert, gemeinsamer 1-Hz-Blinktakt mit „MESSUNG".
- Status „GETESTET" statt „BEWÄHRT"; Startfenster „YOUR SYSTEM IS READY".
- Versionsnummer und Firmenname in der Oberfläche und in den CSV-Dateien.

## 0.3.0 – 2026-11-19
- Messprogramm-Menü nach Katalog: Frequenzgang, Pegel/Gain, THD+N über f, THD+N über Pegel, Störabstand, Kanaltrennung (alle am Gerät getestet); SINAD, S/N bewertet, Wow & Flutter, Azimut/Phase gesperrt.
- Neue Befehle werden einzeln per `++spoll` geprüft (Abbruch vor dem Trigger).
- Klirr-Auslesung: Nachlesen bis der Wert fertig ist (AR488 `read_tmo_ms` 1200 ms).
- Kanäle L/R/L+R, Filter TP 22 kHz / HP 22 Hz, Abschwächer, Lastangabe → Leistung.

## 0.2.0 – 2026-11-19
- Lokale Web-Oberfläche (TRON-Look) mit Boot-Sequenz: Adapter-Check (9 Punkte) → UPA-Verbindung → Messung freigeben; Sound.
- Frequenzgang mit Pegel und gemessener Frequenz, CSV-Ablage, Protokoll `upa_log.txt`.

## 0.1.0 – 2026-11-19
- Stabile Messkette (v14–v16): `DELIMITER(TYPE(NL/EOI))` beendet die „NOT TRIGGERED"-Flut; `TRIGGER(MODE(LEV/FREQ))` + genau 2 Reads.
