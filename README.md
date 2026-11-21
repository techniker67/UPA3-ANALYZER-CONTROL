<img src="assets/icon.png" width="96" align="left" alt="">

# UPA3-ANALYZER-CONTROL

Windows program for the **Rohde & Schwarz UPA** audio analyzer (tested on a UPA3), controlled over IEC bus (GPIB) with a low-cost **AR488** USB–GPIB adapter.
Built for daily use on the repair bench: frequency response, gain, THD+N, signal-to-noise and crosstalk — with charts, CSV files and a printable test report (PDF + DOCX).

> **Version 1.0.1** — stable release (first public release: 1.0.0). All measurement programs marked *GETESTET* (tested) have been verified on a real UPA3.
> The user interface is currently in German; an English UI is planned.

🇩🇪 [Deutsche Kurzfassung weiter unten](#deutsch)

---

## Features

- **Own program window** (maximized, freely resizable, zoom with Ctrl + mouse wheel) — installed with a regular Windows setup, no Python required.
- **Start-up check of the whole chain**: adapter (9 steps incl. firmware, GPIB address and stability), remote takeover of the UPA, loopback test measurement at 1 kHz / 0.3 V with frequency plausibility check, release back to local.
- **Measurement programs** for the left, right or both channels:

  | Program | Analyzer option | Status |
  |---|---|---|
  | Frequency response (level + measured frequency) | B6 | tested |
  | Level / gain at a fixed frequency (power into a given load) | B6 | tested |
  | THD+N vs. frequency | B8 | tested |
  | THD+N vs. level (up to clipping) | B8 | tested |
  | Signal-to-noise, unweighted 22 Hz–22 kHz | B6 | tested |
  | Crosstalk vs. frequency | B6 | tested |
  | SINAD, weighted S/N (A/CCIR), wow & flutter, azimuth/phase | – | locked until verified |

- Filters LP 22 kHz / HP 22 Hz, range AUTO (4 digits) or HOLD (3 digits), live charts (log frequency axis, THD+N in % or dB).
- **Device under test**: enter manufacturer, type and serial number (optionally an order number) — all following measurements are collected in one folder with CSV, chart (PNG) and a summary of the key results.
- **Test report** as **PDF and DOCX** from the selected measurements: device data, result overview, one page per measurement with settings, chart and measured values, remarks, signature line. Open, print or edit in Word directly from the program.
- **Storage folder** freely selectable, e.g. a network share; if it is unreachable, data is saved locally and a warning is shown.
- **External attenuator** with a per-channel calibration table (log-f interpolation), e.g. for power amplifiers.
- Free choice of COM port and GPIB address (0–30); the last working values are remembered.
- **Robust bus handling**: every command that has not been verified on the device is checked individually via serial poll before triggering — no endless error loops on the analyzer. Every bus command is logged.

## Requirements

- R&S UPA audio analyzer with IEC bus (options as listed above)
- AR488-compatible GPIB adapter — tested: [ESP32-S2 adapter by DiyEMC](https://www.diyemc.com/Products/Esp32s2Ar488/) with firmware **0.53.26 (JW)**; other adapters and versions run but are flagged in the log
- Windows 10 or 11 (64 bit). The program window uses Microsoft Edge WebView2, which is part of current Windows versions.

## Installation

1. Download `UPA-Analyzer-Control-<version>-Setup.exe` from [Releases](../../releases) and run it — no administrator rights required.
2. The setup creates a Start-menu entry, an optional desktop shortcut and a shortcut **“Messdaten-Ordner”** (data folder).
3. Updates: simply install the new version over the old one. Uninstalling keeps your data.

The installer is not code-signed yet, so Windows SmartScreen may warn: click *More info* → *Run anyway*. Signing via the SignPath Foundation is being applied for — see the [Code signing policy](docs/code-signing-policy.md).

## First steps

1. Connect the AR488 adapter (USB) and the UPA (IEC bus). For the start-up check, connect generator output L to analyzer input L (loopback).
2. Start **UPA-Analyzer-Control**, enter COM port and GPIB address in the start screen and start the initialisation. When all steps are green: *YOUR SYSTEM IS READY*.
3. Click **PRÜFLING** in the top bar and enter manufacturer, type and serial number (optionally an order number and the storage folder).
4. Choose a measurement program, set generator level, channels and filters, press **Start**.
5. Click **▤ PROTOKOLL**, select the measurements and create the test report (PDF + DOCX).
6. Exit with **⏻ QUIT** (or the window's close button) — the UPA is released to local operation.

Wiring, measurement details and attenuator calibration: [docs/hardware-setup.md](docs/hardware-setup.md) · [docs/measurements.md](docs/measurements.md) · [docs/attenuator-calibration.md](docs/attenuator-calibration.md)

## Data folder

Program and user data are kept apart, so updates never overwrite settings, calibration or measurements.
User data lives in **`Documents\UPA-Analyzer-Control`**:

| File / folder | Content |
|---|---|
| `upa_einstellungen.json` | company name, storage folder, last COM port, GPIB address and device under test |
| `p78_kalibrierung.json` | attenuator calibration (optional) |
| `Messungen\` | default storage folder: one subfolder per device under test (`<order no.>` or `<manufacturer>_<type>_<serial>`) with CSV files, charts, `messungen.json` and test reports |
| `upa_log.txt` | log of every bus command |

**Company name:** copy `upa_einstellungen.beispiel.json` to `upa_einstellungen.json` in the data folder and enter your company name — it appears in the program, in every CSV and in the test report.
**Start-up sound:** an MP3 file with “ready” in its name in the data folder is played when the system is ready; otherwise speech synthesis is used.

## Run from source (developers)

Requires Python 3.9 or newer.

```bash
pip install -r requirements.txt                          # pyserial
pip install pywebview matplotlib reportlab python-docx   # program window, charts, test report
python upa_server.py --port COM4 --addr 7
```

Without the optional packages the program still runs: the GUI then opens in the browser at <http://127.0.0.1:8488>, and charts/test reports are unavailable.
On Windows, `UPA_Software_starten.bat` starts it with a console window; on Linux/macOS use `./upa_software_starten.sh --port /dev/ttyACM0`.

Start options:

| Option | Meaning |
|---|---|
| `--port`, `--addr` | COM port and GPIB address (otherwise the last working values) |
| `--browser` | use the browser instead of the program window |
| `--no-browser` | server only, no window (e.g. headless mini PC) |
| `--http <port>` | port of the internal web server (default 8488) |
| `--listen 0.0.0.0` | reachable from the network — only in a trusted LAN |
| `--data <folder>` | other data folder (also: environment variable `UPA_DATA`, or an empty file `portable` in the program folder) |

The Windows setup is built and tested automatically by GitHub Actions on every change — see [docs/release.md](docs/release.md).

## Related projects & thanks

Many thanks to **Hans W. ([DiyEMC](https://www.diyemc.com/Products/Esp32s2Ar488/))** for the ESP32-S2 GPIB adapter and its firmware, which this software was developed and tested with.

- [AR488-compatible ESP32-S2 adapter](https://www.diyemc.com/Products/Esp32s2Ar488/) (DiyEMC) — the adapter hardware: ESP32-S2 module with USB, ESD protection on all GPIB lines, firmware update via USB.
- [AR488](https://github.com/Twilight-Logic/AR488) by Twilight-Logic — the original Arduino GPIB adapter firmware with Prologix-compatible `++` commands.
- [douardda/AR488-ESP32](https://github.com/douardda/AR488-ESP32) — the original port of AR488 to the ESP32.
- [WilheJo/AR488-ESP32](https://github.com/WilheJo/AR488-ESP32) — ESP32 port with the pinouts of the adapter revisions 4 and 5.
- [WilheJo-Org1/AR488](https://github.com/WilheJo-Org1/AR488) — the Arduino-based AR488 firmware with the adapter's pinout, kept in sync with upstream; the AR488 manual (all `++` commands) is included there.
- [Astralix/AR488-ESP32](https://github.com/Astralix/AR488-ESP32) — further development with `++spoll` for addresses 0–30 and WiFi; background in the article [AR488 on ESP32 at dc3ax.de](https://dc3ax.de/blog/ar488-esp32-gpib/). Not yet tested with this software.
- [mikrocontroller.net forum thread](https://www.mikrocontroller.net/topic/574123) (German) — group order, hardware revisions, firmware and user experience with the adapter.

Tested so far with firmware **0.53.26 (JW)**. Feedback with other adapters and firmware versions is welcome — please open an issue.

## Roadmap

- English user interface
- Weighted S/N (A/CCIR), SINAD, wow & flutter, azimuth/phase — once verified on a real device
- Before/after measurements in the test report
- Code-signed installer (SignPath Foundation)

## Code signing policy

Free code signing provided by SignPath.io, certificate by SignPath Foundation (application in preparation). Details, team roles and privacy statement: [Code signing policy](docs/code-signing-policy.md). Bundled open-source components: [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

**Privacy:** this program will not transfer any information to other networked systems unless specifically requested by the user.

## Disclaimer

This is an independent workshop project. It is **not affiliated with or endorsed by Rohde & Schwarz**; “Rohde & Schwarz” and “UPA” are trademarks of their respective owners.
The software sends remote-control commands to your instrument. Use it at your own risk — see [LICENSE](LICENSE).
Service manuals and other R&S documents are not included and must be obtained separately.

---

## Deutsch

Windows-Programm zur Steuerung des **R&S UPA Audioanalysators** über einen **AR488-GPIB-Adapter** – für den Reparaturtisch: Frequenzgang, Verstärkung, THD+N, Störabstand und Kanaltrennung mit Diagrammen, CSV-Dateien und Prüfprotokoll (PDF + DOCX).

- **Installation:** `Setup.exe` unter [Releases](../../releases) herunterladen und starten – ohne Python, ohne Administratorrechte. Updates einfach drüber installieren; Daten bleiben erhalten.
- **Start:** über das Startmenü „UPA-Analyzer-Control". Im Startfenster COM-Port und GPIB-Adresse eintragen, initialisieren (dafür Generator L auf Eingang L stecken).
- **Prüfling** (Hersteller, Typ, Seriennummer, optional Auftragsnummer und Ablageordner) in der Kopfzeile festlegen – alle Messungen landen dann in einem eigenen Ordner.
- **▤ PROTOKOLL** erstellt das Prüfprotokoll als PDF und DOCX; Drucken direkt aus dem Programm.
- **Daten:** `Dokumente\UPA-Analyzer-Control` (Einstellungen, Kalibrierung, Messungen, Protokoll); der Ablageordner für Messungen ist frei wählbar, z. B. ein NAS.

Getestet mit UPA3 und dem [ESP32-S2-GPIB-Adapter von DiyEMC](https://www.diyemc.com/Products/Esp32s2Ar488/) (Firmware 0.53.26 (JW)) – vielen Dank an Hans W. für Adapter und Firmware. Links zu AR488, den ESP32-Varianten und dem Forumsthread unter „Related projects & thanks". Die Oberfläche ist derzeit deutsch. Kein offizielles Produkt von Rohde & Schwarz; Nutzung auf eigene Gefahr.

---

© 2026 Vintage Audio Repair Magdeburg · MIT License
