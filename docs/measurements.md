# Measurement programs

All programs can run on the left, right or both channels. Default range is **AUTO** (4 digits); **HOLD(10)** gives 3 digits but faster readings.

| Program | Default settings | Notes |
|---|---|---|
| Frequency response | 10 points, 0.5 V, filters off | LP 22 kHz is off on purpose — it lowers 20 kHz by about 0.64 dB. Measured frequency is shown next to each point. |
| Level / Gain | 1 kHz, 0.5 V, LP 22 kHz | Output / generator level. With attenuator factor and load (Ω) the power is calculated. |
| THD+N vs. frequency | octave points, 0.5 V, LP 22 kHz | ≈ 15 s per point at low frequencies. |
| THD+N vs. level | 1 kHz, 50 mV … 1 V, 8 steps | Choose the end level carefully: gain × generator level! Can be stopped at any time. |
| Signal-to-noise | 1 kHz reference, then generator off, LP 22 kHz + HP 22 Hz | Unweighted. The UPA reports noise in 1 µV steps (≈ ±1 dB near 5 µV). |
| Crosstalk | 3 points, 0.5 V | Reference on the driven channel, then the other input is measured. |

Locked (not yet startable): SINAD, weighted S/N (A/CCIR), wow & flutter, azimuth/phase — they will be enabled once their commands and output formats are verified on a real device.

## Reference: loopback results (UPA3, 40 cm cable)

These values show the limits of the measuring system itself:

| Measurement | Result |
|---|---|
| Frequency response 20 Hz–20 kHz | flat, 0.496 V at 0.5 V setting |
| THD+N 31.5 Hz–16 kHz at 0.5 V | 0.0031–0.0050 % (≈ −88 dB) |
| THD+N vs. level at 1 kHz | 0.0094 % at 50 mV, flat from ≈ 180 mV |
| Signal-to-noise | ≈ 98–100 dB re 0.5 V (5–6 µV) |
| Crosstalk | ≈ −96 dB up to 1 kHz, −86 dB at 10 kHz |

## CSV files

Each run writes a CSV to `Messungen/` with a header containing software version, company name (if set), adapter firmware and all run parameters, followed by one row per point (raw and corrected values, number of read attempts, attenuator factor used).
