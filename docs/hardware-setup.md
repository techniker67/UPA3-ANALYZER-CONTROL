# Hardware setup

## Chain

```
PC (USB) ── AR488 adapter ── IEC bus (GPIB) ── R&S UPA
                                               Generator OUT L/R ──► DUT ──► Analyzer IN L/R
```

For a first test (and for the boot check) use a **loopback**: generator output L → analyzer input L (and R → R for the right channel). Use short, well-shielded cables of equal length — a 1 m cable picked up about 45 µV of hum in our tests and limited the measurable crosstalk to about −81 dB.

## AR488 adapter

- Tested: ESP32-S2 build, firmware **0.53.26 (JW)**. The software reads the version (`++ver`) at every start, writes it into the log and every CSV, and flags versions that have not been tested.
- The adapter appears as a serial port (Windows: `COMx`, Linux: `/dev/ttyACMx` or `/dev/ttyUSBx`).
- No manual configuration is needed: the software sets controller mode, address, EOI/EOS and auto-read itself and checks each setting during the boot check.

## UPA

- Set the IEC bus address on the instrument (default in this software: **7**; any address 0–30 can be chosen in the start screen).
- During a measurement the UPA is in remote mode (REM, local lockout). After the boot check and after every program it is released back to local, so the front panel works again.

## Bus details that matter

These points were found the hard way and are built into the software:

| Topic | Solution |
|---|---|
| Endless “NOT TRIGGERED” error flood | The UPA must terminate its answers with EOI: `DELIMITER(TYPE(NL/EOI))` is sent at the start of each measurement. |
| Status checks without disturbing the instrument | `++spoll` (serial poll) instead of querying the error register. |
| Number of values per trigger | Exactly as many reads as the trigger mode returns (`LEV` = 1, `LEV/FREQ` = 2, `LEV/FNCT` = 2). |
| Slow THD+N values at low frequencies | The adapter returns nothing if a value is not ready within its read timeout (1.2 s) — the software keeps polling until the value arrives. |
| Invalid values | `88888` from the UPA is treated as “no value”. |
| Unverified commands | Each command not yet proven on the device is sent individually and checked by serial poll; on rejection the run stops before triggering. |
