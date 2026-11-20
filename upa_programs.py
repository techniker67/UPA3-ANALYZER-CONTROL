#!/usr/bin/env python3
"""
upa_programs.py - Messprogramme nach UPA_Messroutinen_Katalog (19.11.2026)
=========================================================================
Jedes Programm nutzt UPA.measure() aus upa_core. Status:
  ok     = Messkette am Geraet bewiesen (v16); evtl. neue Filter werden
           beim Lauf einzeln per ++spoll geprueft
  test   = nutzt noch nicht verifizierte Befehle/Ausleseformate -> erster
           Lauf ist ein Verifikationslauf (Rohwerte werden angezeigt)
  locked = Syntax/Zubehoer laut Katalog §4 noch offen -> nicht startbar
"""
import math

CH = {"L": ("LEFT UNBAL", "LEFT UNBAL"), "R": ("RIGHT UNBAL", "RIGHT UNBAL")}
OTHER = {"L": "R", "R": "L"}

PROGRAMS = [
    {"id": "fr", "name": "Frequenzgang", "sub": "Pegel über f · L/R", "opt": "B6", "status": "ok",
     "x": "freq", "est": 22,
     "ui": {"freqs": True, "level": True},
     "def": {"lp22": False, "hp22": False, "rng": "AUTO", "ch": "L", "preset": "std10", "level": 0.5},
     "note": "Messkette getestet (v16). TP 22 kHz bewusst AUS: senkt 20 kHz um 0,64 dB (gemessen 19.11.)."},
    {"id": "gain", "name": "Pegel / Gain", "sub": "1 kHz · Verstärkung · Leistung", "opt": "B6", "status": "ok",
     "x": "none", "est": 22,
     "ui": {"level": True, "fixfreq": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "level": 0.5, "fixfreq": 1000},
     "note": "Ausgangspegel / Generatorpegel. Mit P78-Faktor und Last → Leistung."},
    {"id": "thdf", "name": "THD+N über f", "sub": "Klirr · fester Pegel", "opt": "B8", "status": "ok",
     "x": "freq", "est": 22,
     "ui": {"freqs": True, "level": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "preset": "oct", "level": 0.5},
     "note": "Bestätigt 19.11.: Befehle angenommen, Ausgabe DISPC = Klirr in %, Werte = Geräteanzeige (−88 dB Systemgrenze). 31,5 Hz–16 kHz vollständig, reproduzierbar (2 Läufe). ~15 s/Punkt."},
    {"id": "thdl", "name": "THD+N über Pegel", "sub": "1 kHz · bis Clipping", "opt": "B8", "status": "ok",
     "x": "level", "est": 22,
     "ui": {"levelsweep": True, "fixfreq": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "fixfreq": 1000,
             "lstart": 0.05, "lstop": 1.0, "ln": 8},
     "note": "Bestätigt 19.11. (Loopback 50 mV–1 V). Endpegel bewusst wählen: Gain × Pegel! Leistung nur mit Lastangabe (Ω). Stop jederzeit möglich."},
    {"id": "sn", "name": "Störabstand S/N", "sub": "unbewertet 22 Hz–22 kHz", "opt": "B6", "status": "ok",
     "x": "none", "est": 45,
     "ui": {"level": True, "fixfreq": True},
     "def": {"lp22": True, "hp22": True, "rng": "AUTO", "ch": "L", "level": 0.5, "fixfreq": 1000},
     "note": "Bestätigt 19.11. (Kanal L): Eigenrauschen Loopback ≈ 5 µV → ~100 dB re 0,5 V. UPA liefert Rauschen nur in 1-µV-Schritten (±1 dB bei ~5 µV). Kanal R noch ungeprüft."},
    {"id": "xt", "name": "Kanaltrennung", "sub": "Übersprechen über f", "opt": "B6", "status": "ok",
     "x": "freq", "est": 45,
     "ui": {"freqs": True, "level": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "preset": "xt3", "level": 0.5},
     "note": "Bestätigt 19.11.: UPA-Kanaltrennung ≈ −96 dB bis 1 kHz, −86 dB bei 10 kHz. Nur kurze, gut geschirmte, gleiche Kabel – das 1-m-Kabel bringt ~45 µV Brumm (→ nur −81 dB)."},
    {"id": "sinad", "name": "SINAD", "sub": "Signal / (Rausch+Klirr)", "opt": "B8", "status": "locked",
     "x": "freq", "est": 22, "ui": {}, "def": {},
     "lock": "Syntax NOISE(SINAD …) im Katalog noch offen – erst im Handbuch nachschlagen."},
    {"id": "snw", "name": "S/N bewertet", "sub": "A / CCIR", "opt": "B2", "status": "locked",
     "x": "none", "est": 45, "ui": {}, "def": {},
     "lock": "Welcher FILTER(SPEC(n)) = A / CCIR ist, steht noch nicht fest (Katalog §4)."},
    {"id": "wf", "name": "Wow & Flutter", "sub": "DIN 45507 · 3150 Hz", "opt": "B9", "status": "locked",
     "x": "none", "est": 30, "ui": {}, "def": {},
     "lock": "WOWFLUTTER(DIN …) Syntax/Ausgabe offen; Bezugsband/-platte 3150 Hz nötig."},
    {"id": "phase", "name": "Azimut / Phase", "sub": "10 kHz · L/R", "opt": "B6", "status": "locked",
     "x": "none", "est": 30, "ui": {}, "def": {},
     "lock": "PHASE(ON) Ausleseformat offen; Azimut-Band B5 nötig."},
]
BY_ID = {p["id"]: p for p in PROGRAMS}


def _filters(p):
    f = []
    if p.get("lp22"):
        f.append("FILTER(LP22KHZ)")
    if p.get("hp22"):
        f.append("FILTER(HP22HZ)")
    return f


def att(p, f, ch="L"):
    """Abschwaecherfaktor bei Frequenz f fuer Kanal ch: fester Wert oder
    Kalibriertabelle des Kanals (log-f-Interpolation, ausserhalb Randwert)."""
    tab = (p.get("atten_tabs") or {}).get(ch) or p.get("atten_tab")
    if not tab:
        return p["atten"]
    if f is None or f <= tab[0][0]:
        return tab[0][1]
    if f >= tab[-1][0]:
        return tab[-1][1]
    for (f0, k0), (f1, k1) in zip(tab, tab[1:]):
        if f0 <= f <= f1:
            t = (math.log10(f) - math.log10(f0)) / (math.log10(f1) - math.log10(f0))
            return k0 + t * (k1 - k0)
    return tab[-1][1]


def _pt(ch, x, r, p, **extra):
    """Messpunkt fuer Oberflaeche/CSV aufbereiten."""
    u = r.get("volt")
    f = r.get("hz") or r.get("freq_soll")
    k = att(p, f, ch)
    ut = u * k if u is not None else None
    d = {"ch": ch, "x": x, "f_soll": r.get("freq_soll"), "u_soll": r.get("level_soll"),
         "f": r.get("hz"), "u": u, "u_true": ut,
         "fnct": r.get("values", {}).get("FNCT"), "fnct_line": r.get("lines", {}).get("FNCT"),
         "raw": (r.get("raw") or "").strip(), "abbruch": r.get("abbruch"),
         "neu_ok": r.get("neu_ok", []), "versuche": r.get("versuche"), "att_k": round(k, 4)}
    if ut is not None and p.get("load"):
        d["p_w"] = ut * ut / p["load"]
    d.update(extra)
    return d


def _db(a, b):
    try:
        return 20 * math.log10(a / b)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def run(u, prog, p, emit, log, stop):
    """Fuehrt Programm prog mit Parametern p aus. emit(punkt) je Ergebnis.
    Bricht bei erstem Abbruch ab (keine Folgefehler)."""
    pid = prog["id"]
    flt = _filters(p)
    rng = p["rng"]

    def m(freq, level, out, inp, mode="LEV/FREQ", func=(), rng_=None):
        return u.measure(freq, level, output=out, inp=inp, mode=mode, filters=flt,
                         func=func, rng=rng_ or rng)

    for ch in p["channels"]:
        out, inp = CH[ch]
        if pid == "fr":
            for f in p["freqs"]:
                if stop():
                    return
                r = m(f, p["level"], out, inp)
                emit(_pt(ch, f, r, p))
                if r["abbruch"]:
                    return
        elif pid == "gain":
            r = m(p["fixfreq"], p["level"], out, inp)
            ut = r["volt"] * att(p, r.get("hz") or p["fixfreq"], ch) if r.get("volt") is not None else None
            g = ut / p["level"] if ut is not None else None
            emit(_pt(ch, p["fixfreq"], r, p, gain=g, gain_db=_db(ut, p["level"])))
            if r["abbruch"]:
                return
        elif pid in ("thdf", "thdl"):
            pts = ([(f, p["level"]) for f in p["freqs"]] if pid == "thdf"
                   else [(p["fixfreq"], lv) for lv in p["levels"]])
            for f, lv in pts:
                if stop():
                    return
                r = m(f, lv, out, inp, mode="LEV/FNCT", func=["DISTORTION(TOTAL)"])
                emit(_pt(ch, f if pid == "thdf" else lv, r, p))
                if r["abbruch"]:
                    return
        elif pid == "sn":
            log(f"  [{ch}] Referenz {p['fixfreq']} Hz ...")
            r1 = m(p["fixfreq"], p["level"], out, inp)
            if r1["abbruch"]:
                emit(_pt(ch, p["fixfreq"], r1, p, step="Referenz"))
                return
            if stop():
                return
            log(f"  [{ch}] Generator AUS, Rauschen messen ...")
            r2 = m(p["fixfreq"], p["level"], out.split()[0] + " OFF", inp, mode="LEV", rng_="AUTO")
            sn = _db(r1.get("volt"), r2.get("volt"))
            emit(_pt(ch, p["fixfreq"], r2, p, step="Rauschen", ref_u=r1.get("volt"),
                     noise_u=r2.get("volt"), sn_db=sn, ref_raw=(r1.get("raw") or "").strip()))
            if r2["abbruch"]:
                return
        elif pid == "xt":
            oinp = CH[OTHER[ch]][1]
            for f in p["freqs"]:
                if stop():
                    return
                r1 = m(f, p["level"], out, inp)                       # angeregter Kanal
                if r1["abbruch"]:
                    emit(_pt(ch, f, r1, p, step="Referenz"))
                    return
                r2 = m(f, p["level"], out, oinp, mode="LEV", rng_="AUTO")  # Nachbarkanal
                emit(_pt(ch, f, r2, p, ref_u=r1.get("volt"), ref_u_true=(r1["volt"] * att(p, f, ch)
                         if r1.get("volt") is not None else None), xt_u=r2.get("volt"),
                         xt_db=_db(r2.get("volt"), r1.get("volt")),
                         dir=f"{ch}→{OTHER[ch]}"))
                if r2["abbruch"]:
                    return
