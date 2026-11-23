# Changelog – UPA-Software

Versionsschema: MAJOR.MINOR.PATCH. PATCH = Korrektur, MINOR = neue Funktion, 1.0.0 = erste GitHub-Veröffentlichung.

## 1.6.0 – 2026-11-23
- **Bandmessungen (Tapedeck / Tonband)** – Quelle ist das Messband, der UPA-Generator bleibt aus. Alle drei Programme sind als *VERIFIKATION* markiert, bis sie am Gerät bestätigt sind:
  - **Wow & Flutter** (Option B9): `WOWFLUTTER(DIN|NAB|JIS WTD)` laut Handbuch 2.4.8, dazu Frequenz und Geschwindigkeitsabweichung je Wert (`TRIGGER(MODE(LEV/FREQ/FNCT))`). JIS = WRMS. Die ersten 6 s zählen nicht (Einschwingen). Ergebnis: W&F max./Mittel/min., Geschwindigkeit, Schwankung, Drift.
  - **Bandgeschwindigkeit**: nur bewährte Befehle (Pegel + Frequenz), Abweichung von 3000/3150 Hz in %, Drift.
  - **Wiedergabe-Frequenzgang**: erkennt die Frequenzstufen des Messbands selbst (L/R abwechselnd, Median je Stufe), Bezug 0 dB wählbar (Vorgabe 315 Hz), endet 20 s nach dem letzten Ton.
  - **Azimut live**: Pegel L/R, Höchstwert und Abstand zum Maximum, L–R; nichts wird gespeichert.
- Neu im Gerätekern: einmal einstellen, dann je Wert nur `TRIGGER(SINGLE)` + Lesen (wartet auf den Wert, Abbruch bei „NOT TRIGGERED“, alle 10 Werte ++spoll).
- Prüfprotokoll: Seiten und Diagramme für die Bandmessungen.
- Gesperrte Programme erscheinen nicht mehr in der Kachelleiste. Phase L–R bleibt gesperrt (laut Handbuch 2.3.1.8 nur mit Sonderverkabelung).

## 1.5.0 – 2026-11-22
- **Aufräumen im Protokoll-Fenster:** Jede Messung und jedes erstellte Protokoll hat ein **✕**. Nach Rückfrage wandern die Dateien (Messung: CSV + Diagramm, Protokoll: PDF + DOCX) in den Unterordner **`Papierkorb`** des Geräteordners – nichts wird endgültig gelöscht.
- **Papierkorb zeigen (n):** blendet die entfernten Einträge grau ein; **↺** holt sie zurück. Endgültig löschen: Ordner `Papierkorb` im Explorer löschen („Ordner öffnen“).
- Neue Liste **Erstellte Protokolle** mit allen Protokollen des Prüflings (neueste zuerst) und Knöpfen PDF / Drucken / DOCX – bisher wurden nur die letzten zwei angezeigt.
- Gesperrt während einer Messung oder Aufzeichnung; vorhandene Dateien werden nie überschrieben.

## 1.4.2 – 2026-11-21
- Ablageordner: Schaltfläche **DURCHSUCHEN** rechts im Feld (Einstellungen und Prüfling-Dialog) öffnet den Windows-Dialog „Ordner auswählen" – Desktop, Dokumente, Netzwerk → NAS usw. Im Browser-Betrieb ausgeblendet.

## 1.4.1 – 2026-11-21
- Ruhestrom-Diagramm im Protokoll: Die Spannungsachse reicht wieder über alle Messwerte (Minimum bis Maximum, Sollband immer enthalten) – der ganze Verlauf inkl. Anklemmen und Abgleich ist sichtbar, nichts wird mehr abgeschnitten. „Min / Max ab erster Zeitmarke" in der Tabelle bleibt.

## 1.4.0 – 2026-11-21
- **Startmenü** im Stil des Programm-Icons: große Kacheln *UPA-Messung* und *Multimeter*, darunter *Protokolle*, *Einstellungen* und *Beenden*; Prüfling-Zeile oben (gilt für UPA und Multimeter).
  - Status auf den Kacheln: „UPA initialisiert" / „Adapter an COM4" / „COM4 nicht gefunden", „IR-Kabel an COM3", laufende Aufzeichnung, Anzahl Messungen und Protokolle zum Prüfling.
  - *UPA-Messung* → Start-Check (*System starten*, *Ohne UPA fortfahren*, *⌂ Menü*), nach erfolgreicher Initialisierung direkt in die Messansicht; in derselben Sitzung ohne erneuten Check.
  - *Multimeter* → direkt in die Multimeter-Ansicht.
- **⌂ MENÜ** in jeder Ansicht statt ÜBERSICHT/QUIT; gesperrt während einer Messung oder Aufzeichnung. Beendet wird nur im Menü; das X am Fenster fragt nach.
- **Einstellungen** an einer Stelle: Prüfer/Firma, Ablageordner, UPA-Port und GPIB-Adresse, Fluke-Port, Versionshinweis.
- **Hinweis auf neue Versionen:** beim Start eine Anfrage an GitHub (abschaltbar); im Menü „Neue Version … verfügbar" mit Link zur Release-Seite.
- Ein Programmfenster mit umschaltbaren Ansichten statt mehrerer Fenster (kein Aus-/Einblenden mehr).

## 1.3.4 – 2026-11-21
- Kachel **„Ruhestrom"** im UPA-Fenster wechselt jetzt ins Multimeter-Fenster wie *▣ Nur Multimeter*: Das UPA-Fenster wird ausgeblendet, zurück über *⌂ ÜBERSICHT* (UPA-Fenster unverändert, maximiert). Immer nur ein Fenster sichtbar.
- Während einer laufenden UPA-Messung wird der Wechsel abgelehnt.

## 1.3.3 – 2026-11-21
- Prüfprotokoll-Dialog: neues Feld **„Prüfer / Firma"** – steht im Protokoll (Zeile „Prüfer") und in der Fußzeile, wird gemerkt. Leer = ohne. Bisher ließ sich der Name nur in `upa_einstellungen.json` eintragen.

## 1.3.2 – 2026-11-21
- Ruhestrom-Diagramm im Protokoll: Legende steht jetzt unter dem Diagramm (eine Zeile, rechts) und verdeckt keine Messwerte mehr; der Hinweis zur abgeschnittenen Achse steht links daneben (kürzer).

## 1.3.1 – 2026-11-21
- Fenster immer maximiert: Das Multimeter-Fenster öffnet maximiert, und beim Wechsel (⌂ ÜBERSICHT, Kachel „Ruhestrom", zweiter Programmstart) wird das jeweilige Fenster maximiert nach vorne geholt.
- Protokolldatei vermerkt, ob ein Fenster maximiert ist (zur Fehlersuche); die Build-Prüfung kontrolliert das.

## 1.3.0 – 2026-11-21
- **Startbildschirm mit drei Wegen:** *System starten* (UPA), *Ohne UPA fortfahren* (Hauptfenster ohne Start-Check) und neu **▣ Nur Multimeter** – öffnet nur das Multimeter-Fenster, das Hauptfenster wird ausgeblendet (auch aus der Taskleiste).
- **⌂ ÜBERSICHT** im Multimeter-Fenster (statt ✕ SCHLIESSEN): schließt das Multimeter-Fenster und holt das Hauptfenster zurück – ohne initialisierten UPA mit dem Startbildschirm. Während einer Aufzeichnung bleibt das Multimeter-Fenster offen, das Hauptfenster kommt nur nach vorne.
- **⏻ QUIT** auch im Multimeter-Fenster (beendet die Software, schließt alle Fenster).
- Sicherheitsnetz: Wird das Multimeter-Fenster geschlossen (auch per X), kommt ein ausgeblendetes Hauptfenster immer zurück. Ein zweiter Programmstart findet auch das Multimeter-Fenster.
- Build-Prüfung: Nur-Multimeter, zweiter Start dabei, ÜBERSICHT.

## 1.2.1 – 2026-11-21
- Multimeter-Fenster:
  - **▤ PROTOKOLL** auch hier – das Prüfprotokoll lässt sich direkt aus dem Multimeter-Fenster erstellen.
  - Linke Spalte wächst mit der Fensterbreite (bis 580 px); bei großem/maximiertem Fenster liegen Live-Abgleich, Aufzeichnen und Stop nebeneinander.

## 1.2.0 – 2026-11-21
- **Eigenes Multimeter-Fenster** für Ruhestrom/Offset: Die Kachel „Ruhestrom" (und „Ohne UPA fortfahren") öffnet ein zweites, frei skalierbares Fenster nur mit dem Fluke-Bereich – ohne UPA-Kacheln und Start-Check. Es lässt sich neben das Hauptfenster legen; ist es schon offen, wird es nach vorne geholt.
  - Aufteilung: links Einstellungen, rechts Anzeige und Verlauf; schmale Fenster stapeln alles untereinander.
  - „✕ SCHLIESSEN" schließt nur das Multimeter-Fenster (Live-Anzeige wird gestoppt); während einer Aufzeichnung gesperrt, auch das X.
  - QUIT im Hauptfenster schließt beide Fenster.
  - Ohne Programmfenster (Browser-Betrieb) öffnet sich das Multimeter als eigenes Browserfenster.
- Build-Prüfung: Multimeter-Fenster öffnen und mit QUIT schließen.

## 1.1.5 – 2026-11-21
- **Sicheres Beenden und Starten:**
  - Programm beendet sich nach X oder QUIT zuverlässig (vorher konnte ein Prozess ohne Fenster im Hintergrund bleiben – danach „Port belegt").
  - X am Fenster wird während einer Fluke-Aufzeichnung abgelehnt (vorher ging die Aufzeichnung verloren). Eine Live-Anzeige wird beim Beenden gestoppt, die Schnittstelle freigegeben.
  - Zweiter Start: das vorhandene Programmfenster wird nach vorne geholt. Läuft die Software ohne sichtbares Fenster, fragt das Programm, ob diese Instanz beendet und neu gestartet werden soll.
  - Protokolldatei: „Programmfenster angezeigt", „Programmfenster wird geschlossen", „Software beendet" – zur Fehlersuche.
- Build-Prüfung: zweiter Start und „Prozess nach QUIT wirklich beendet" werden getestet.

## 1.1.4 – 2026-11-21
- **Ruhestrom/Offset – Überlauf (OL) sichtbar statt Stillstand:**
  - Live: Die große Anzeige zeigt „OL Überlauf" in Rot; die Zeitachse läuft weiter, OL-Abschnitte erscheinen als rote Fläche mit „OL", die Linie wird dort unterbrochen.
  - Zeitmarken-Tabelle zeigt „OL" statt „--.---".
  - Protokoll-Diagramm: Linie an Messlücken unterbrochen (keine geraden Verbindungslinien mehr über OL-Phasen), OL-Abschnitte rot hinterlegt mit Legende „Überlauf (OL)".

## 1.1.3 – 2026-11-21
- **Ruhestrom/Offset – Auswertung:**
  - Diagramm: Spannungsachse richtet sich nach Sollband und den Werten ab der ersten Zeitmarke; Anklemm-/Abgleichspitzen davor werden abgeschnitten (mit Hinweis unter dem Diagramm). Das Toleranzband ist damit sichtbar.
  - „Min / Max" wird ab der ersten Zeitmarke gerechnet und so benannt („Min / Max ab 3 min"). Ohne Zeitmarke wie bisher über den ganzen Lauf.
  - Überlauf des Multimeters an einer Zeitmarke oder am Ende erscheint als „OL ✗ Überlauf" statt „–".
  - Endwert im Protokoll mit Laufzeit m:ss wie in der Ergebnisübersicht.
  - Zeitmarken-Text am rechten Rand läuft nicht mehr aus dem Diagramm.
- Ältere Einträge werden unverändert wie bisher ausgegeben.

## 1.1.2 – 2026-11-21
- **Diagramme: fehlende Achsenzahlen, Legende und Zeitmarken-Texte unter Windows behoben.** Die Calibri enthält eingebettete Pixelschriften für kleine Größen, die matplotlib (ab 3.11) leer zeichnet – bei 150 dpi trafen 7,5–9 pt genau diese Größen. Diagramme werden jetzt mit 300 dpi gespeichert (dazu schärfer im Druck). Der Selbsttest der Windows-Version prüft das künftig.
- Hinweis: Bereits gespeicherte Diagramme bleiben unverändert.

## 1.1.1 – 2026-11-21
- Ruhestrom/Offset am echten Fluke 287 getestet (Live-Anzeige deckungsgleich mit dem Messgerät, 10-min-Aufzeichnung mit Zeitmarken, Ablage auf dem NAS) – Kachel jetzt „GETESTET".

## 1.1.0 – 2026-11-21
- **Ruhestrom / Offset mit Fluke 287/289** (IR-USB-Kabel, nur lesend: `ID`, `QM`): neue Kachel „Ruhestrom" mit eigener Ansicht.
  - **Live-Abgleich**: große Anzeige in mV, Trend (mV/min), grün/rot nach Toleranzband – zum Einstellen am Trimmer, ohne Speichern.
  - **Aufzeichnung** 10 min / 30 min / 1 h / 2 h / bis Stop, Intervall 1–10 s, Zeitmarken (Vorgabe 10 und 120 min), Sollwert ± Toleranz, Bezeichnung (z. B. „Ruhestrom L", „Offset R").
  - Speicherung im Prüflingsordner: CSV, Verlaufsdiagramm mit Toleranzband, Eintrag mit Zeitmarken und Endwert; im Prüfprotokoll eigener Abschnitt.
  - Fluke-Port wird automatisch gesucht (AR488-Port bleibt unberührt) und gemerkt.
- Startfenster: **„Ohne UPA fortfahren"** – Fluke-Messungen auch ohne angeschlossenen UPA.
- Prüfprotokoll: Messsystem je nach verwendeten Geräten, Haken/Kreuz in der PDF mit Ersatzschrift.

## 1.0.1 – 2026-11-21
- Vorbereitung Code-Signatur (SignPath Foundation): `docs/code-signing-policy.md` (Rollen, Datenschutz, Umfang), `THIRD-PARTY-NOTICES.md`, Verweise in README und Release-Text.
- .exe und Setup tragen jetzt Produktname, Version und Herausgeber in den Datei-Eigenschaften; der Build prüft das.

## 1.0.0 – 2026-11-21
**Erste öffentliche Version.**
- Windows-Programm mit eigenem Fenster und Setup (ohne Python, ohne Administratorrechte), eigenes Icon.
- Start-Check der Messkette: AR488-Adapter (9 Schritte), Remote-Übernahme, Loopback-Testmessung, Freigabe.
- Messprogramme, alle am UPA3 getestet: Frequenzgang, Pegel/Verstärkung, THD+N über Frequenz und über Pegel, Störabstand, Kanaltrennung.
- Prüfling mit optionaler Auftragsnummer, Messordner je Gerät, frei wählbarer Ablageordner (auch Netzlaufwerk, lokaler Rückfall).
- Prüfprotokoll als PDF und DOCX (Übersicht, Diagramme, Messwerte, Bemerkung, Unterschrift), Drucken aus dem Programm.
- Abschwächer-Kalibrierung je Kanal, CSV-Export, Protokoll aller Busbefehle.
- Releases ab 1.0.0 sind reguläre Versionen (keine Vorabversion mehr).

## 0.13.3 – 2026-11-21
- README: getesteter Adapter mit Link zur DiyEMC-Seite, Dank an Hans W. (mit seiner Zustimmung), Verweis auf WilheJo/AR488-ESP32 (Pinout Rev. 4/5) ergänzt.

## 0.13.2 – 2026-11-21
- Icon-Datei neu aufgebaut (16–128 px als klassische Bitmaps, 256 px als PNG) – manche Windows-Funktionen lesen PNG-Einträge in kleinen Größen nicht und fielen auf das Standard-Icon zurück.
- Fenster-Icon zusätzlich als Fensterklassen-Icon und mehrfach gesetzt; großes Icon mindestens 48 px für die Taskleiste.
- Build prüft jetzt, dass die .exe das Programm-Icon trägt.
- README: Abschnitt „Related projects & thanks" (AR488 von Twilight-Logic, ESP32-Port von douardda, WilheJo-Org1/AR488 mit Handbuch, Astralix-Fork + dc3ax-Artikel, Forumsthread).

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
