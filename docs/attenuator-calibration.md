# External attenuator calibration

To measure power amplifiers, an external voltage divider ahead of the analyzer input is common. The software corrects its division factor frequency-dependently, per channel, using log-frequency interpolation between the calibration points. In the GUI this is the attenuator option **“P78 - kalibriert”** (named after the divider used during development).

When the calibrated attenuator is selected, the range is forced to AUTO (4 digits), because the 3-digit HOLD range is too coarse for the correction.

## File format

The table is read from `p78_kalibrierung.json` in the program folder. It is device-specific and therefore **not part of this repository** (see `.gitignore`). Structure (values below are placeholders, not real data):

```json
{
  "name": "P78",
  "beschreibung": "Divider at analyzer input L and R, 40 cm cable",
  "datum": "YYYY-MM-DD",
  "faktor_1khz": 19.40,
  "punkte":  [[20.0, 19.36], [1000.0, 19.40], [20000.0, 19.45]],
  "kanaele": {
    "L": [[20.0, 19.36], [1000.0, 19.40], [20000.0, 19.45]],
    "R": [[20.0, 19.35], [1000.0, 19.39], [20000.0, 19.44]]
  }
}
```

- Each point is `[frequency in Hz, division factor]` (input voltage / voltage at the analyzer).
- `kanaele` holds one table per channel; `punkte` (channel L) is kept for older versions.
- Outside the table range the nearest end value is used.

## How to calibrate

1. Generator directly to the analyzer input: measure the reference level per frequency (third-octave points 20 Hz–20 kHz, range AUTO, filters off).
2. Same generator setting with the divider (and its cable) inserted: measure again.
3. Factor = reference / divided level for each frequency; repeat for the right channel.
4. Replace points disturbed by mains hum (50/60 Hz) with the neighbouring value.

A check run with the finished table should show the corrected level within about ±0.02 dB of the reference.
