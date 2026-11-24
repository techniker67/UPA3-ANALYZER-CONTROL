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
import time

CH = {"L": ("LEFT UNBAL", "LEFT UNBAL"), "R": ("RIGHT UNBAL", "RIGHT UNBAL")}
OTHER = {"L": "R", "R": "L"}

PROGRAMS = [
    {"id": "fr", "name": "Frequenzgang", "sub": "Pegel über f · L/R", "opt": "B6", "status": "ok",
     "x": "freq", "est": 22,
     "ui": {"freqs": True, "level": True},
     "def": {"lp22": False, "hp22": False, "rng": "AUTO", "ch": "L", "preset": "std10", "level": 0.5},
     "note": "TP 22 kHz aus lassen – er senkt 20 kHz um ca. 0,6 dB."},
    {"id": "gain", "name": "Pegel / Gain", "sub": "1 kHz · Verstärkung · Leistung", "opt": "B6", "status": "ok",
     "x": "none", "est": 22,
     "ui": {"level": True, "fixfreq": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "level": 0.5, "fixfreq": 1000},
     "note": "Verstärkung = Ausgangspegel / Generatorpegel. Mit Abschwächer und Lastangabe (Ω) wird die Leistung berechnet."},
    {"id": "thdf", "name": "THD+N über f", "sub": "Klirr · fester Pegel", "opt": "B8", "status": "ok",
     "x": "freq", "est": 22,
     "ui": {"freqs": True, "level": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "preset": "oct", "level": 0.5},
     "note": "Bis ca. 15 s pro Punkt (tiefe Frequenzen länger). Eigenklirr des Messsystems ca. 0,004 % (−88 dB)."},
    {"id": "thdl", "name": "THD+N über Pegel", "sub": "1 kHz · bis Clipping", "opt": "B8", "status": "ok",
     "x": "level", "est": 22,
     "ui": {"levelsweep": True, "fixfreq": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "fixfreq": 1000,
             "lstart": 0.05, "lstop": 1.0, "ln": 8},
     "note": "Endpegel bewusst wählen: Verstärkung × Generatorpegel! Leistung nur mit Lastangabe (Ω). Stop jederzeit möglich."},
    {"id": "sn", "name": "Störabstand S/N", "sub": "unbewertet 22 Hz–22 kHz", "opt": "B6", "status": "ok",
     "x": "none", "est": 45,
     "ui": {"level": True, "fixfreq": True},
     "def": {"lp22": True, "hp22": True, "rng": "AUTO", "ch": "L", "level": 0.5, "fixfreq": 1000},
     "note": "Erst Bezugspegel, dann Generator aus und Rauschen messen. Auflösung 1 µV (bei sehr rauscharmen Geräten ca. ±1 dB). Messgrenze ca. 100 dB bei 0,5 V."},
    {"id": "xt", "name": "Kanaltrennung", "sub": "Übersprechen über f", "opt": "B6", "status": "ok",
     "x": "freq", "est": 45,
     "ui": {"freqs": True, "level": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "preset": "xt3", "level": 0.5},
     "note": "Kurze, gut geschirmte, gleich lange Kabel verwenden – lange Kabel fangen Brumm ein und verfälschen das Ergebnis. Messgrenze ca. −96 dB (1 kHz)."},
    # --- Bandmessungen (ab v1.6.0): Quelle = Messband, UPA-Generator AUS ----------
    {"id": "bspeed", "name": "Bandgeschwindigkeit", "sub": "Speed · Drift · 3000/3150 Hz", "opt": "BAND",
     "status": "test", "band": True, "x": "time", "est": 4,
     "ui": {"band": True, "sollf": True, "dauer": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "sollf": 3000, "dauer": 30},
     "note": "Speed-Messband abspielen (Kassette 3000 Hz, Spule 3150 Hz), dann starten. Liest Frequenz und Pegel "
             "über die Dauer: Abweichung in %, Drift. UPA-Generator bleibt aus. Erster Lauf = Verifikation."},
    {"id": "bfg", "name": "Wiedergabe-Frequenzgang", "sub": "ab Messband · Stufen automatisch", "opt": "BAND",
     "status": "test", "band": True, "x": "time", "est": 4,
     "ui": {"band": True, "dauer": True, "bezug": True},
     "def": {"lp22": False, "hp22": False, "rng": "AUTO", "ch": "LR", "dauer": 300, "bezug": 315},
     "note": "Frequenzgang-Messband abspielen und direkt starten. Die Software erkennt die Frequenzstufen selbst "
             "(L/R abwechselnd) und endet 20 s nach dem letzten Ton oder per Stop. Bezug 0 dB = Stufe am "
             "nächsten an der Bezugsfrequenz. Erster Lauf = Verifikation."},
    {"id": "azi", "name": "Azimut live", "sub": "Pegel L/R · 10 kHz · Maximum", "opt": "BAND",
     "status": "test", "band": True, "live": True, "x": "time", "est": 4,
     "ui": {"band": True, "dauer": True},
     "def": {"lp22": False, "hp22": False, "rng": "AUTO", "ch": "LR", "dauer": 600},
     "note": "Azimut-Band (10 kHz) abspielen. Zeigt Pegel L und R abwechselnd, den Höchstwert und den Abstand "
             "dazu – Kopf auf Maximum und L≈R stellen. Nichts wird gespeichert. (Phase L–R bräuchte laut Handbuch eine Sonderverkabelung.)"},
    # Abgleich live (aus Tools -> Abgleichliste gestartet, nicht in der Kachelleiste)
    {"id": "abgl", "name": "Abgleich live", "sub": "Generator fest · Pegel L/R laufend", "opt": "B6",
     "status": "test", "band": True, "live": True, "hidden": True, "x": "time", "est": 4,
     "ui": {"band": True, "dauer": True, "gen": True},
     "def": {"lp22": False, "hp22": False, "rng": "AUTO", "ch": "LR", "dauer": 900},
     "note": "Abgleich nach Liste: UPA-Generator gibt den Schritt-Ton an beiden Ausgängen L/R aus (oder aus = Messband), der Analysator "
             "liest L/R laufend. Nichts wird gespeichert – Ist-Werte im Abgleich-Dialog übernehmen."},
    {"id": "sinad", "name": "SINAD", "sub": "Signal / (Rausch+Klirr)", "opt": "B8", "status": "locked",
     "x": "freq", "est": 22, "ui": {}, "def": {},
     "lock": "Befehl noch nicht am Gerät geprüft."},
    {"id": "snw", "name": "S/N bewertet", "sub": "A / CCIR", "opt": "B2", "status": "locked",
     "x": "none", "est": 45, "ui": {}, "def": {},
     "lock": "Bewertungsfilter A / CCIR noch nicht am Gerät geprüft."},
    {"id": "wf", "name": "Wow & Flutter", "sub": "DIN · NAB · JIS (WRMS) + Speed", "opt": "B9", "status": "test",
     "band": True, "x": "time", "est": 4,
     "ui": {"band": True, "sollf": True, "dauer": True, "wfnorm": True},
     "def": {"lp22": True, "hp22": False, "rng": "AUTO", "ch": "L", "sollf": 3000, "dauer": 30, "wfnorm": "JIS"},
     "note": "Speed-/Flutter-Messband abspielen, dann starten. Misst W&F bewertet (WTD) nach gewählter Norm, dazu "
             "Frequenz und Geschwindigkeitsabweichung. JIS = WRMS (japanische Decks), DIN = Quasi-Peak 3150 Hz, "
             "NAB = Mittelwert. Die ersten 6 s zählen nicht (Einschwingen). Erster Lauf = Verifikation."},
    {"id": "phase", "name": "Phase L–R", "sub": "PHASE(ON) · Sonderverkabelung", "opt": "B6", "status": "locked",
     "x": "none", "est": 30, "ui": {}, "def": {},
     "lock": "Laut Handbuch 2.3.1.8 nur mit zusätzlicher Verkabelung (Differenz auf symmetrischen Eingang R). "
             "Für Azimut 'Azimut live' (Pegelmaximum, L≈R) nutzen."},
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


# Bandmessung: Ende erkennen, wenn so lange kein gueltiger Ton mehr kommt
BAND_PAUSE_S = 20.0
BAND_MIN_U = 0.5e-3          # unter 0,5 mV gilt als "kein Ton" (Pause zwischen Stufen)
BAND_CHECK_JEDE = 10         # alle n Werte ++spoll (Flut-Schutz)
WF_EINSCHWING_S = 6.0        # W&F-Gleichrichter (Quasi-Peak/RMS) einschwingen lassen
WF_NORMEN = ("DIN", "NAB", "JIS")


def run_band(u, prog, p, emit, log, stop):
    """Bandmessungen / Abgleich live. Beim Abgleich mit Generator werden am Ende
    beide Generatorausgaenge wieder abgeschaltet."""
    try:
        return _run_band(u, prog, p, emit, log, stop)
    finally:
        if prog["id"] == "abgl" and p.get("gen_v"):
            try:
                for h in u.gen_aus():
                    log("  Hinweis: " + h)
                log("  Generator L/R aus.")
            except Exception as e:
                log(f"  Generator konnte nicht abgeschaltet werden: {e}")


def _run_band(u, prog, p, emit, log, stop):
    """Bandmessungen: einmal einstellen (Generator aus), dann Werte im Takt
    des UPA lesen, bis Dauer, Stop, Bandende (bfg) oder Abbruch."""
    pid = prog["id"]
    chans = p["channels"]
    if pid == "wf":
        mode, func = "LEV/FREQ/FNCT", [f"WOWFLUTTER({p['wfnorm']} WTD)"]
    else:
        mode, func = "LEV/FREQ", []
    gen = (p["gen_f"], p["gen_v"]) if pid == "abgl" and p.get("gen_v") else None
    err = u.band_setup(CH[chans[0]][1], mode, _filters(p), func=func, rng="AUTO", gen=gen)
    for c in getattr(u, "neu_ok", []):
        log(f"  [OK] neuer Befehl angenommen: {c}")
    if err:
        emit({"ch": chans[0], "x": 0, "t": 0, "abbruch": err, "raw": "", "f": None, "u": None, "u_true": None})
        return
    log(f"  Analysator eingestellt ({'Generator ' + format(gen[0], 'g') + ' Hz / ' + format(gen[1], 'g') + ' V' if gen else 'Generator aus'}),"
        f" lese Werte – Kanal {'/'.join(chans)} ...")
    t0 = time.time()
    k = 0
    ton_gesehen, ruhe_seit = False, None
    while not stop() and time.time() - t0 < p["dauer"]:
        ch = chans[k % len(chans)]
        u.band_input(CH[ch][1])
        r = u.band_sample()
        t = round(time.time() - t0, 1)
        if (pid == "bfg" and ton_gesehen and r["abbruch"]
                and r["abbruch"].startswith("Kein Messwert")):
            log("  Bandende erkannt (kein Messwert mehr) – Messung beendet.")
            return
        r["freq_soll"] = p.get("sollf")
        extra = {"t": t}
        f = r.get("hz")
        if pid in ("bspeed", "wf") and f:
            extra["dev_pct"] = (f - p["sollf"]) / p["sollf"] * 100
        if pid == "wf":
            extra["wf_pc"] = r.get("values", {}).get("FNCT")
            extra["wf_line"] = r.get("lines", {}).get("FNCT")
            extra["ein"] = t < WF_EINSCHWING_S
        emit(_pt(ch, t, r, p, **extra))
        if r["abbruch"]:
            return
        k += 1
        if k % BAND_CHECK_JEDE == 0:
            fehler, sp = u.band_check()
            if fehler:
                log("ABBRUCH: " + fehler)
                return
            if sp != "0":
                log(f"  Hinweis: spoll={sp!r} nach {k} Werten (Messung läuft weiter)")
        if pid == "bfg":
            gueltig = bool(f) and (r.get("volt") or 0) > BAND_MIN_U
            if gueltig:
                ton_gesehen, ruhe_seit = True, None
            elif ton_gesehen:
                ruhe_seit = ruhe_seit or time.time()
                if time.time() - ruhe_seit > BAND_PAUSE_S:
                    log(f"  Bandende erkannt ({BAND_PAUSE_S:.0f} s kein Ton) – Messung beendet.")
                    return
    if not stop():
        log(f"  Messdauer {p['dauer']:.0f} s erreicht.")


def run(u, prog, p, emit, log, stop):
    """Fuehrt Programm prog mit Parametern p aus. emit(punkt) je Ergebnis.
    Bricht bei erstem Abbruch ab (keine Folgefehler)."""
    if prog.get("band"):
        return run_band(u, prog, p, emit, log, stop)
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
