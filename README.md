# UPA3-ANALYZER-CONTROL

Local web GUI for the **Rohde & Schwarz UPA** audio analyzer (tested on a UPA3), controlled over IEC bus (GPIB) with a low-cost **AR488** USB–GPIB adapter.
Built for daily use on the repair bench: frequency response, gain, THD+N, signal-to-noise and crosstalk — with charts, CSV export and a log of every bus command.

> **Status:** pre-release (v0.8.2). All measurement programs marked *GETESTET* have been verified on real hardware.
> The user interface is currently in German; an English UI is planned.

🇩🇪 [Deutsche Kurzfassung weiter unten](#deutsch)

---

## Features

- **Boot check** of the whole chain before measuring: adapter (9 steps incl. GPIB address and stability), remote takeover of the UPA, loopback test measurement at 1 kHz / 0.3 V with frequency plausibility check, and release back to local.
- **Measurement programs** (left/right/both channels):

  | Program | Analyzer option | Status |
  |---|---|---|
  | Frequency response (level + measured frequency) | B6 | tested |
  | Level / Gain at 1 kHz (with power into a given load) | B6 | tested |
  | THD+N vs. frequency | B8 | tested |
  | THD+N vs. level (up to clipping) | B8 | tested |
  | Signal-to-noise, unweighted 22 Hz–22 kHz | B6 | tested |
  | Crosstalk vs. frequency | B6 | tested |
  | SINAD, weighted S/N (A/CCIR), wow & flutter, azimuth/phase | – | locked until verified |

- Filters LP 22 kHz / HP 22 Hz, range AUTO (4 digits) or HOLD (3 digits).
- **External attenuator support** with a per-channel calibration table (log-f interpolation), e.g. for measuring power amplifiers.
- Charts (log frequency axis, THD in % or dB), result tables, CSV export with a header containing software version, adapter firmware and all parameters.
- Free choice of COM port and GPIB address (0–30); the last working values are remembered.
- Robust bus handling: every command that has not been verified on the device is checked individually via serial poll before the measurement is triggered — no endless error loops on the analyzer.

## Requirements

- R&S UPA audio analyzer with IEC bus (options as listed above)
- AR488 GPIB adapter (tested: ESP32-S2 build, firmware **0.53.26 (JW)**; other versions run but are flagged in the log)
- Python 3.9 or newer and `pyserial`
- Windows, Linux or macOS with a current browser

## Quick start

```bash
pip install -r requirements.txt
python upa_server.py --port COM4 --addr 7      # Windows
./upa_software_starten.sh --port /dev/ttyACM0   # Linux/macOS
```

On Windows you can simply double-click `UPA_Software_starten.bat`. To exit, use **⏻ QUIT** in the top right corner — the console window closes as well.
The GUI opens at <http://127.0.0.1:8488>. Port and address can also be entered in the start screen.

Options: `--http <port>` (GUI port, default 8488), `--listen 0.0.0.0` (reachable from the network — only in a trusted LAN), `--no-browser`.

## Data folder

Program and user data are kept apart, so updates never overwrite your settings, calibration or measurements.
All user data lives in **`Documents/UPA-Analyzer-Control`** (shown in the console window at start):

| File / folder | Content |
|---|---|
| `upa_einstellungen.json` | company name, last working COM port and GPIB address |
| `p78_kalibrierung.json` | attenuator calibration (optional, see docs) |
| `Messungen/` | one CSV per run |
| `upa_log.txt` | log of every bus command |

Other locations: start option `--data <folder>`, environment variable `UPA_DATA`, or an empty file named `portable` in the program folder (everything stays in the program folder, e.g. on a USB stick).
On first start, settings and calibration found in the program folder are **copied** to the data folder; the originals are left untouched.

## Configuration (optional)

Copy `upa_einstellungen.beispiel.json` to `upa_einstellungen.json` in the data folder and enter your company name — it is shown in the GUI and written into every CSV.
An MP3 file with “ready” in its name placed in the data folder (or the program folder) is played when the system is ready; otherwise speech synthesis is used.

More details: [docs/hardware-setup.md](docs/hardware-setup.md) · [docs/measurements.md](docs/measurements.md) · [docs/attenuator-calibration.md](docs/attenuator-calibration.md)

## Roadmap

- **0.8** – separate data folder ✔, installable Windows program (installer built automatically on GitHub)
- **0.9** – job field (repair order number / device), before/after measurements, central storage on a network share
- **1.0** – DOCX test report, first public release

## Disclaimer

This is an independent hobby/workshop project. It is **not affiliated with or endorsed by Rohde & Schwarz**; “Rohde & Schwarz” and “UPA” are trademarks of their respective owners.
The software sends remote-control commands to your instrument. Use it at your own risk — see [LICENSE](LICENSE).
Service manuals and other R&S documents are not included and must be obtained separately.

---

## Deutsch

Lokale Web-Oberfläche zur Steuerung des **R&S UPA Audioanalysators** über einen **AR488-GPIB-Adapter**. Gedacht für den Reparaturtisch: Frequenzgang, Verstärkung, THD+N, Störabstand und Kanaltrennung mit Diagrammen, CSV-Export und Protokoll.

**Start:** `pip install -r requirements.txt`, dann `UPA_Software_starten.bat` doppelklicken (oder `python upa_server.py --port COM4 --addr 7`). Die Oberfläche öffnet sich unter <http://127.0.0.1:8488>; COM-Port und GPIB-Adresse lassen sich auch im Startfenster einstellen.

Einstellungen, Kalibrierung, Messungen und Protokoll liegen im Ordner `Dokumente/UPA-Analyzer-Control`. Die Oberfläche ist derzeit deutsch. Getestet mit UPA3 und AR488 (ESP32-S2, Firmware 0.53.26 (JW)). Kein offizielles Produkt von Rohde & Schwarz; Nutzung auf eigene Gefahr.

---

© 2026 Vintage Audio Repair Magdeburg · MIT License
