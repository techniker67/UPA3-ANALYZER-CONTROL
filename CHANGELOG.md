# Changelog – UPA-Software

Versionsschema: MAJOR.MINOR.PATCH. PATCH = Korrektur, MINOR = neue Funktion, 1.0.0 = erste GitHub-Veröffentlichung.

## 0.13.2 – 2026-11-21
- Icon-Datei neu aufgebaut (16–128 px als klassische Bitmaps, 256 px als PNG) – manche Windows-Funktionen lesen PNG-Einträge in kleinen Größen nicht und fielen auf das Standard-Icon zurück.
- Fenster-Icon zusätzlich als Fensterklassen-Icon und mehrfach gesetzt; großes Icon mindestens 48 px für die Taskleiste.
- Build prüft jetzt, dass die .exe das Programm-Icon trägt.
- README: Abschnitt „Related projects & thanks" (AR488, AR488-ESP32, Astralix-Fork, dc3ax-Artikel, Forumsthread).

## 0.13.1 – 2026-11-21
- Taskleiste zeigt jetzt das Programm-Icon: Fenster-Icon wird direkt gesetzt, eigene AppUserModelID für Programm und Verknüpfungen (vorher erschien teils das Standard-Icon).
- README komplett überarbeitet: Installation und erste Schritte mit dem Programmfenster; Browser/Quellcode nur noch im Entwickler-Abschnitt.

## 0.13.0 – 2026-11-20
- **Auftragsnummer** (optional) im Prüfling-Dialog, z. B. `R-20246281650-003`. Ist sie angegeben, heißt der Messordner genau so; die Protokoll-Dateinamen bleiben `Pruefprotokoll_<Hersteller>_<Typ>_<Seriennr>_<Datum>`. Im Protokoll steht die Auftragsnummer in der Kopfzeile und in der Gerätetabelle.
- **Ablageordner für Messungen** wählbar (Prüfling-Dialog), z. B. ein Netzlaufwerk `\\NAS\Messdaten`. Wird beim Übernehmen geprüft (anlegen + Schreibtest). Leer = `Dokumente\UPA-Analyzer-Control\Messungen`.
- Ist der Ablageordner bei einer Messung nicht erreichbar, wird lokal gespeichert und im Protokollfenster gewarnt.
- Vorhandene Einstellung `"ablage"` in `upa_einstellungen.json` wird übernommen.

## 0.12.0 – 2026-11-20
- **Eigenes Programm-Icon** im TRON-Look: Sinuskurve auf dem Raster eines analogen Oszilloskop-Bildschirms, Cyan auf Schwarz. Für .exe, Startmenü, Desktop, Taskleiste, Installer und Fenster; vereinfachte Fassung für 16–32 px. Auch in der Kopfzeile und im Startbildschirm.

## 0.11.2 – 2026-11-20
- Prüfprotokoll im Hausstil der Reparaturberichte: Calibri, Akzentfarbe #2E5A88, Kopfzeilen der Tabellen weiß auf Blau, Zebrastreifen, feine Rahmen, Kopfzeile mit Gerät und Linie, Fußzeile „Seite x von y | Firma | …", nummerierte Abschnitte (1. Prüfling und Messsystem, 2. Ergebnisübersicht, 3.x Messergebnisse, 4. Bemerkung), 2 cm Rand.
- DOCX mit echten Überschrift-Formaten (Navigation in Word), festen Spaltenbreiten und wiederholter Tabellenkopfzeile.
- Diagramme in den Hausfarben (Kanal L blau, R rot) und in Calibri.

## 0.11.1 – 2026-11-20
- Prüfprotokoll (PDF und DOCX): jede Messung beginnt auf einer neuen Seite.

## 0.11.0 – 2026-11-20
- **Prüfprotokoll** (Schaltfläche ▤ PROTOKOLL): Messungen des Prüflings auswählen, optionale Bemerkung, dann **PDF und DOCX** im Geräteordner erstellen. Inhalt: Prüfling und Messsystem, Ergebnisübersicht, je Messung Einstellungen, Diagramm und Messwerttabelle, Bemerkung, Datum/Unterschrift. Firmenname in Kopf und Fußzeile.
- Aus dem Dialog: PDF öffnen, Drucken (PDF-Betrachter, Strg+P), DOCX öffnen, Geräteordner öffnen.
- Interner Zwischenspeicher des Programmfensters liegt jetzt unter `%LOCALAPPDATA%\UPA-Analyzer-Control` statt im Datenordner. Der alte Ordner `Dokumente\UPA-Analyzer-Control\webview` kann gelöscht werden.
- Selbsttest der installierten Version erzeugt zusätzlich ein Beispielprotokoll.

## 0.10.0 – 2026-11-20
- **Prüfling** (Hersteller, Typ, Seriennummer) oben in der Kopfzeile festlegen. Alle folgenden Messungen landen im **Geräteordner** `Messungen/<Hersteller>_<Typ>_<Seriennr>/`:
  - CSV wie bisher (Kopfzeile jetzt mit Prüfling),
  - **Diagramm als PNG** (helle Druckdarstellung, deutsche Dezimalkommas) für Frequenzgang, THD+N über f/Pegel, Kanaltrennung,
  - `messungen.json` mit allen Messungen und Kernergebnissen je Kanal, `geraet.json`.
- Der Prüfling bleibt bis zur Änderung gespeichert (auch über Neustarts); während einer Messung nicht änderbar. „Kein Prüfling" = Ablage wie bisher direkt in `Messungen/`.
- Grundlage für das Prüfprotokoll (PDF/DOCX) im nächsten Schritt.

## 0.9.0 – 2026-11-20
- **Eigenes Programmfenster** statt Browser (pywebview / Edge-WebView2): startet maximiert in der Bildschirmauflösung, frei veränderbar, Zoom mit Strg + Mausrad bzw. Strg +/−/0. Kein Konsolenfenster mehr in der installierten Version.
- QUIT und das Fenster-X beenden die Software vollständig; während einer Messung wird beides abgelehnt (erst Stop).
- Zweiter Start bei laufender Software: Hinweis „läuft bereits".
- Ohne pywebview (Quellcode-Variante) oder wenn das Fenster nicht startet: wie bisher im Browser. Startoption `--browser` erzwingt den Browser.
- Build-Test prüft zusätzlich das Programmfenster; GitHub-Bausteine auf aktuelle Versionen.

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
