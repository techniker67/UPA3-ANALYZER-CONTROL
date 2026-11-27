# Quiescent current / DC offset with a Fluke 287/289

The program can log a Fluke 287 or 289 multimeter via the Fluke IR-USB cable (e.g. IR189USB) — typically the voltage across an emitter resistor (quiescent current) or the DC offset at the speaker output, in **mV DC**. It works **without the UPA**: choose the tile **MULTIMETER** in the start menu (or the tile **Ruhestrom** in the UPA view). The view shows only the meter: settings on the left, display and chart on the right. *⌂ MENÜ* returns to the start menu (blocked while recording; a live display is stopped).

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

Tested with Fluke 287, firmware V1.41, Fluke USB-IR cable (FTDI): live display identical to the meter reading (97.12 mV), 10-minute recording with time marks at 3/5/10 min, storage on a network share.

## Second meter (MM2): Voltcraft VC-7055BT

Optional, since v1.8.0 (status: verification). A Voltcraft VC-7055BT (identical to OWON XDM1041) on RS-232 runs in parallel with the Fluke, e.g. quiescent current L on the Fluke and R on the Voltcraft.

1. Meter: *Port → Serial*, 115200 baud. Connect a USB-RS-232 adapter (FTDI) with a **null-modem cable** (the meter has a male DB9).
2. Multimeter window → section **MM2**: port (default COM5, *Suchen* finds it), **EIN**, designation, set value and tolerance.
3. Switch the meter to **V DC** by hand. *Live-Abgleich* / *Aufzeichnen* / *Stop* control both meters; interval, duration and time marks apply to both.

The software only reads (`*IDN?`, `FUNC?`, `RANGE?`, `AUTO?`, `MEAS1?`) and never sends `SYST:REM`, so the keys stay usable. Overload (`1E+9`) shows as OL. With auto-ranging the meter briefly reports exactly 0 V while switching ranges; up to two such readings in a row are discarded as a gap (“Bereichswechsel”) and do not affect min/max or time marks. A recording stores MM2 as its own series (CSV `upa_ruhe_mm2_…`, chart, own entry in the test report). If MM2 fails, the Fluke keeps running.
