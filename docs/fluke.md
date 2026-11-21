# Quiescent current / DC offset with a Fluke 287/289

The program can log a Fluke 287 or 289 multimeter via the Fluke IR-USB cable (e.g. IR189USB) — typically the voltage across an emitter resistor (quiescent current) or the DC offset at the speaker output, in **mV DC**. It works **without the UPA**: in the start screen choose *Ohne UPA fortfahren*, or select the tile **Ruhestrom** at any time.

## Setup

1. Close FlukeView Forms (it would block the COM port).
2. Put the IR head on the meter, switch the meter to **mV DC**.
3. Tile **Ruhestrom** → *Suchen* finds the meter on any COM port (the GPIB adapter's port is skipped). The port is remembered.

The software only *reads* the meter (`ID`, `QM` at 115200 baud, 8N1); it never changes a setting.

## Modes

| Button | Use |
|---|---|
| **▶ Live-Abgleich** | Large reading with trend (mV/min) and green/red tolerance colour — for adjusting the trimmer. Nothing is saved. |
| **● Aufzeichnen** | Logs for the chosen duration (10 min … 2 h or until *Stop*) at 1–10 s interval, records the values at the time marks (default 10 and 120 min) and saves CSV, chart and summary in the device folder. The result appears in the test report. |

Fields: designation (e.g. *Ruhestrom L*, *Offset R* — several runs per device are fine), set value and tolerance in mV, duration, time marks in minutes, interval.

Tested with Fluke 287, firmware V1.41, Fluke USB-IR cable (FTDI).
