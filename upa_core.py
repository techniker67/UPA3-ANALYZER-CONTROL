#!/usr/bin/env python3
"""
upa_core.py - Geraete-Kern der UPA-Software
===========================================
Enthaelt NUR am Geraet bewiesene Ablaeufe:

  * Adapter-Check   = Logik aus ar488_selftest.py (9 Pruefpunkte)
  * UPA-Messkette   = 1:1 aus upa_messreihe_v16.py (19.11.2026):
      REM-Init (++ren 1 -> ++llo -> CLEAR), DELIMITER(TYPE(NL/EOI)),
      TRIGGER(MODE(LEV/FREQ)), TRIGGER(SINGLE), GENAU 2x ++read eoi,
      Freigabe ++loc -> ++ren 0.

Keine Abhaengigkeit ausser pyserial. Laeuft unter Windows (COMx) und Linux
(/dev/ttyACM0) gleich.
"""
import re
import time

try:
    import serial
except ImportError:          # Server meldet das sauber in der Oberflaeche
    serial = None

DELIM_CMD = "DELIMITER(TYPE(NL/EOI))"

# Am Geraet bewiesene Befehle (v14-v16). Alles andere wird einzeln geprueft.
PROVEN = {"OUTPUT(LEFT UNBAL)", "INPUT(LEFT UNBAL)", "MEASUREMENT(AC)",
          "MEASUREMENT(LEVEL VOLT)", "DETECTOR(RMS)", "RANGE(LEVEL HOLD(10))",
          "TRIGGER(MODE(LEV))", "TRIGGER(MODE(LEV/FREQ))",
          # am Geraet bestaetigt 19.11.2026 (GUI-Laeufe, spoll '0'):
          "FILTER(LP22KHZ)", "DISTORTION(TOTAL)", "RANGE(LEVEL AUTO)",
          "TRIGGER(MODE(LEV/FNCT))",
          # bestaetigt 19.11.2026 20:27 (Stoerabstand):
          "OUTPUT(LEFT OFF)", "FILTER(HP22HZ)",
          # bestaetigt 19.11.2026 20:41 (Kanaltrennung L->R):
          "INPUT(RIGHT UNBAL)", "OUTPUT(RIGHT UNBAL)"}   # 20:48 (R->L)


def is_proven(cmd):
    return (cmd in PROVEN or cmd.startswith("SOURCE(FREQUENCY)")
            or cmd.startswith("SOURCE(LEVEL VOLT)"))


class Abbruch(Exception):
    """Gewollter Abbruch (Stop-Knopf oder Schutzregel gegriffen)."""


# ---------------------------------------------------------------------------
# Hilfsfunktionen (aus v16)
# ---------------------------------------------------------------------------
def parse_value(line):
    """Zahl am Zeilenende. '88888' = UPA-Kennung fuer ungueltig (z. B.
    'MEAHZ  DN 88888.E+8' bei zu kleinem Pegel) -> None."""
    if not line or "88888" in line:
        return None
    m = re.search(r"([+-]?\d+\.?\d*E[+-]?\d+)\s*$", line)
    if not m:
        m = re.search(r"([+-]?\d+\.\d+)\s*$", line)
    return float(m.group(1)) if m else None


def assign(lines):
    """Welche Zeile ist Pegel, welche Frequenz? Per Header, sonst Reihenfolge."""
    lv = fq = None
    for ln in lines:
        if not ln:
            continue
        hdr = ln.split()[0].upper() if ln.split() else ""
        if "VOLT" in hdr or "DB" in hdr:
            lv = lv or ln
        elif "HZ" in hdr or "FR" in hdr:
            fq = fq or ln
    rest = [ln for ln in lines if ln and ln not in (lv, fq)]
    if lv is None and rest:
        lv = rest.pop(0)
    if fq is None and rest:
        fq = rest.pop(0)
    return lv, fq


def kind(line):
    """Art eines Messwerts aus dem Alphaheader: LEV / FREQ / FNCT / None.
    Bestaetigt: 'MACVOLTRU', 'MACVOLT' = Pegel, 'MEAHZ' = Frequenz,
    'DISPC' = Klirr in Prozent."""
    if not line or not line.split():
        return None
    h = line.split()[0].upper()
    if "HZ" in h:
        return "FREQ"
    if "VOLT" in h or h.startswith(("MAC", "MDC")):
        return "LEV"
    if h.startswith(("DIS", "NOI", "SIN", "WOW", "PHA")) or h.endswith(("PC", "DB")):
        return "FNCT"
    return None


def classify(lines, teile):
    """Zeilen den Modus-Teilen zuordnen: erst per Header, Rest nach Reihenfolge."""
    out = {t: None for t in teile}
    rest = []
    for ln in lines:
        if not ln:
            continue
        k = kind(ln)
        if k in out and out[k] is None:
            out[k] = ln
        else:
            rest.append(ln)
    for t in teile:
        if out[t] is None and rest:
            out[t] = rest.pop(0)
    return out


def fmt_freq(f):
    f = float(f)
    return str(int(round(f))) if abs(f - round(f)) < 1e-9 else f"{f:.2f}".rstrip("0").rstrip(".")


def fmt_level(v):
    return f"{float(v):.4f}".rstrip("0").rstrip(".")


def list_ports():
    if serial is None:
        return []
    try:
        from serial.tools import list_ports as lp
        return [{"device": p.device, "desc": p.description or ""} for p in lp.comports()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Adapter-Check (Logik aus ar488_selftest.py)
# ---------------------------------------------------------------------------
ADAPTER_STEPS = [
    ("port",  "Port oeffnen"),
    ("ver",   "Firmware antwortet (++ver)"),
    ("mode",  "Controller-Modus (++mode 1)"),
    ("addr",  "GPIB-Adresse (++addr)"),
    ("eoi",   "++eoi lesbar"),
    ("eos",   "++eos lesbar"),
    ("auto",  "++auto lesbar"),
    ("tmo",   "++read_tmo_ms lesbar"),
    ("stab",  "Stabilitaet 10/10"),
]


def adapter_check(port, addr, step_cb, log):
    """Fuehrt die 9 Pruefpunkte aus. step_cb(id, status, detail).
    Liefert (ok_count, total, version)."""
    if serial is None:
        step_cb("port", "fail", "pyserial fehlt: pip install pyserial")
        return 0, len(ADAPTER_STEPS), ""
    ok = 0
    ver = ""
    step_cb("port", "run", port)
    try:
        ser = serial.Serial(port, 115200, timeout=2.0)
    except Exception as e:
        step_cb("port", "fail", str(e))
        log(f"Port {port} nicht zu oeffnen: {e}")
        return 0, len(ADAPTER_STEPS), ""
    try:
        time.sleep(2.0)
        ser.reset_input_buffer()
        step_cb("port", "ok", f"{port} offen")
        ok += 1

        def query(cmd):
            ser.reset_input_buffer()
            ser.write((cmd + "\n").encode("ascii"))
            time.sleep(0.05)
            return ser.readline().decode("ascii", errors="replace").strip()

        step_cb("ver", "run", "")
        ver = query("++ver")
        if ver:
            ok += 1
            step_cb("ver", "ok", ver)
        else:
            step_cb("ver", "fail", "keine Antwort")

        step_cb("mode", "run", "")
        mode = query("++mode")
        if mode != "1":
            ser.write(b"++mode 1\n"); time.sleep(0.05)
            mode = query("++mode")
        if mode == "1":
            ok += 1
            step_cb("mode", "ok", "1")
        else:
            step_cb("mode", "fail", mode or "(leer)")

        step_cb("addr", "run", "")
        ser.write(f"++addr {addr}\n".encode("ascii")); time.sleep(0.05)
        a = query("++addr")
        if a == str(addr):
            ok += 1
            step_cb("addr", "ok", a)
        else:
            step_cb("addr", "fail", a or "(leer)")

        for sid, cmd in (("eoi", "++eoi"), ("eos", "++eos"), ("auto", "++auto"),
                         ("tmo", "++read_tmo_ms")):
            step_cb(sid, "run", "")
            val = query(cmd)
            if val:
                ok += 1
                step_cb(sid, "ok", val)
            else:
                step_cb(sid, "fail", "keine Antwort")

        step_cb("stab", "run", "")
        good = 0
        for _ in range(10):
            if query("++ver"):
                good += 1
            time.sleep(0.1)
        if good == 10:
            ok += 1
            step_cb("stab", "ok", "10/10")
        else:
            step_cb("stab", "fail", f"{good}/10 - USB-Versorgung pruefen")
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return ok, len(ADAPTER_STEPS), ver


# ---------------------------------------------------------------------------
# UPA-Messkette (1:1 aus upa_messreihe_v16.py)
# ---------------------------------------------------------------------------
class UPA:
    def __init__(self, port="COM4", addr=7):
        if serial is None:
            raise RuntimeError("pyserial fehlt: pip install pyserial")
        self.port = port
        self.addr = addr
        self.ser = serial.Serial(port, 115200, timeout=0.2, write_timeout=2)
        time.sleep(2.0)
        self.ser.reset_input_buffer()

    def _w(self, cmd):
        try:
            self.ser.write((cmd + "\n").encode("ascii"))
        except Exception:
            pass

    def _collect(self, window):
        out = b""
        t0 = time.time()
        while time.time() - t0 < window:
            n = self.ser.in_waiting
            if n:
                out += self.ser.read(n)
            else:
                time.sleep(0.05)
        return out.decode("ascii", errors="replace")

    def _read_line(self, timeout):
        """Sammelt bis eine komplette Zeile da ist (oder Timeout). Kommt eine
        Zeile gerade an, wird bis zu 3 s laenger gewartet (nie halbe Zeilen)."""
        out = b""
        t0 = time.time()
        ende = t0 + timeout
        while time.time() < ende:
            n = self.ser.in_waiting
            if n:
                out += self.ser.read(n)
                if b"\n" in out:
                    time.sleep(0.1)
                    if self.ser.in_waiting:
                        out += self.ser.read(self.ser.in_waiting)
                    break
                ende = max(ende, time.time() + 3.0)
            else:
                time.sleep(0.05)
        return out.decode("ascii", errors="replace")

    def _read_value(self, total=40.0, log=None):
        """EINEN Messwert abholen, auch wenn er noch nicht fertig ist.
        AR488: ++read wartet max. ++read_tmo_ms (1200 ms) auf den UPA; ist der
        Wert noch nicht fertig, kommt NICHTS (kein 'NOT TRIGGERED', am Geraet
        gesehen 19.11.) -> einfach erneut ++read, bis eine Zeile da ist.
        Ein leerer Versuch verbraucht keinen Wert."""
        t0 = time.time()
        versuche = 0
        while time.time() - t0 < total:
            self._w("++read eoi")
            versuche += 1
            r = self._read_line(2.5)
            if self._extract(r) or "NOT TRIGGERED" in r:
                return r, versuche
        return "", versuche

    def ask(self, cmd, window=0.8):
        self.ser.reset_input_buffer()
        self._w(cmd)
        return self._collect(window).strip()

    def spoll(self):
        self.ser.reset_input_buffer()
        self._w("++spoll")
        r = self._collect(1.2).strip().replace("\r", " ").replace("\n", " ")
        if "NOT TRIGGERED" in r:
            return "FLUT(" + str(r.count("NOT TRIGGERED")) + "x NOT TRIGGERED)"
        return r

    def ifc(self):
        self._w("++ifc")
        time.sleep(0.3)
        self.ser.reset_input_buffer()

    def init_bus(self):
        for c in ["++mode 1", f"++addr {self.addr}", "++auto 0", "++eoi 1", "++eos 0"]:
            self._w(c)
            time.sleep(0.2)
        self.ifc()
        self._w("++ren 1"); time.sleep(0.25)
        self._w("++llo");   time.sleep(0.25)
        self._w("CLEAR");   time.sleep(0.25)
        self.ser.reset_input_buffer()

    def ensure_remote(self):
        self._w(f"++addr {self.addr}"); time.sleep(0.2)
        self._w("++llo");               time.sleep(0.2)
        self.ser.reset_input_buffer()

    @staticmethod
    def _extract(raw):
        for ln in raw.splitlines():
            ln = ln.strip()
            if ln and "LOCALMODE" not in ln and "NOT TRIGGERED" not in ln:
                return ln
        return None

    def measure(self, freq, level, output="LEFT UNBAL", inp="LEFT UNBAL",
                mode="LEV/FREQ", filters=(), func=(), rng="HOLD(10)", settle=3.0):
        """Eine Messung. Basis = v16-Kette. Alles, was NICHT am Geraet bewiesen
        ist (Filter, Funktion, RIGHT/OFF, AUTO, andere Modi), wird EINZELN
        gesendet und sofort per ++spoll geprueft -> Abbruch VOR dem Trigger,
        mit Name des abgelehnten Befehls. Gelesen wird GENAU so oft, wie der
        Modus Werte liefert (LEV=1, LEV/FREQ=2, LEV/FNCT=2, ...)."""
        info = {"freq_soll": freq, "level_soll": level, "mode": mode, "abbruch": None,
                "values": {}, "lines": {}, "raw": "", "neu_ok": []}
        self.ifc()
        self._w("++clr"); time.sleep(0.3)
        self.ser.reset_input_buffer()
        self.ensure_remote()
        info["spoll_start"] = self.spoll()

        self._w("STRING(SINGLE ALPHANUM)"); time.sleep(0.25)
        self._w(DELIM_CMD); time.sleep(0.25)
        info["spoll_delim"] = self.spoll()
        if info["spoll_delim"] != "0":
            info["abbruch"] = f"{DELIM_CMD} nicht angenommen (spoll={info['spoll_delim']!r})"
            return info

        kette = ([f"OUTPUT({output})",
                  f"SOURCE(FREQUENCY){fmt_freq(freq)}", f"SOURCE(LEVEL VOLT){fmt_level(level)}",
                  f"INPUT({inp})", "MEASUREMENT(AC)", "MEASUREMENT(LEVEL VOLT)"]
                 + list(func) + ["DETECTOR(RMS)"] + list(filters)
                 + [f"RANGE(LEVEL {rng})", f"TRIGGER(MODE({mode}))"])
        for c in kette:
            self._w(c); time.sleep(0.25)
            if not is_proven(c):
                sp = self.spoll()
                if sp != "0":
                    info["spoll_set"] = sp
                    info["abbruch"] = (f"UPA lehnt neuen Befehl ab: {c}  (spoll={sp!r}) "
                                       f"-> kein Trigger")
                    return info
                info["neu_ok"].append(c)
        info["spoll_set"] = self.spoll()
        if info["spoll_set"] != "0":
            info["abbruch"] = (f"Einstellung nicht angenommen (spoll={info['spoll_set']!r}) "
                               f"-> kein Trigger")
            return info

        self.ser.reset_input_buffer()
        self._w("TRIGGER(SINGLE)"); time.sleep(settle)
        teile = mode.split("/")
        raws = []
        for _ in teile:                          # GENAU so viele Reads wie Werte
            if "FNCT" in teile:
                # Klirrwert ist oft erst Sekunden nach dem Pegel fertig -> nachlesen
                r, n = self._read_value(40.0)
                info.setdefault("versuche", []).append(n)
                raws.append(r)
            else:
                self._w("++read eoi")
                raws.append(self._collect(5.0))      # bewaehrter v16-Weg, unveraendert
        info["raw"] = "".join(raws)
        info["raw_nt"] = info["raw"].count("NOT TRIGGERED")
        lines = [self._extract(r) for r in raws]
        if mode == "LEV/FREQ":
            lv, fq = assign(lines)
            zu = {"LEV": lv, "FREQ": fq}
        else:
            zu = classify(lines, teile)
        for t in teile:
            ln = zu.get(t)
            info["lines"][t] = ln
            info["values"][t] = parse_value(ln)
        info["volt"] = info["values"].get("LEV")
        info["hz"] = info["values"].get("FREQ")
        info["vline"] = info["lines"].get("LEV")
        info["fline"] = info["lines"].get("FREQ")
        info["spoll_nach_read"] = self.spoll()
        if info["spoll_nach_read"].startswith("FLUT"):
            info["abbruch"] = "Flut nach dem Lesen - Messung gestoppt (Adapter-USB kurz ziehen)"
        return info

    # -----------------------------------------------------------------------
    # Bandmessungen (Quelle = Messband, UPA-Generator AUS)
    # Neu ab v1.6.0 und noch in Verifikation: EINMAL einstellen, danach je
    # Messwert nur TRIGGER(SINGLE) + Lesen (Kernregel: nach dem Trigger nur
    # lesen, erst danach neu einstellen). Gelesen wird per _read_value (wartet,
    # bis der Wert fertig ist) - also weder zu frueh noch zu oft.
    # -----------------------------------------------------------------------
    def band_setup(self, inp="LEFT UNBAL", mode="LEV/FREQ", filters=(), func=(), rng="AUTO"):
        """Analysator fuer Bandmessungen einstellen. Liefert None oder Abbruchtext.
        Ungepruefte Befehle einzeln senden und per ++spoll pruefen (wie measure)."""
        self.ifc()
        self._w("++clr"); time.sleep(0.3)
        self.ser.reset_input_buffer()
        self.ensure_remote()
        self.neu_ok = []
        self._w("STRING(SINGLE ALPHANUM)"); time.sleep(0.25)
        self._w(DELIM_CMD); time.sleep(0.25)
        sp = self.spoll()
        if sp != "0":
            return f"{DELIM_CMD} nicht angenommen (spoll={sp!r})"
        kette = (["OUTPUT(LEFT OFF)", f"INPUT({inp})", "MEASUREMENT(AC)", "MEASUREMENT(LEVEL VOLT)"]
                 + list(func) + ["DETECTOR(RMS)"] + list(filters)
                 + [f"RANGE(LEVEL {rng})", f"TRIGGER(MODE({mode}))"])
        for c in kette:
            self._w(c); time.sleep(0.25)
            if not is_proven(c):
                sp = self.spoll()
                if sp != "0":
                    return f"UPA lehnt neuen Befehl ab: {c}  (spoll={sp!r}) -> kein Trigger"
                self.neu_ok.append(c)
        sp = self.spoll()
        if sp != "0":
            return f"Einstellung nicht angenommen (spoll={sp!r}) -> kein Trigger"
        self.band_mode = mode
        self.band_inp = inp
        return None

    def band_input(self, inp):
        """Eingang zwischen zwei Messwerten umschalten (bewiesene Befehle L/R)."""
        if inp != getattr(self, "band_inp", None):
            self._w(f"INPUT({inp})"); time.sleep(0.3)
            self.band_inp = inp

    def band_sample(self, total=20.0):
        """EIN Messwert-Satz: TRIGGER(SINGLE), dann genau so viele Werte lesen,
        wie der Modus liefert. 'NOT TRIGGERED' = Schutzregel -> Abbruch."""
        teile = self.band_mode.split("/")
        info = {"values": {}, "lines": {}, "raw": "", "abbruch": None, "versuche": []}
        self.ser.reset_input_buffer()
        self._w("TRIGGER(SINGLE)")
        time.sleep(0.3)
        raws = []
        for _ in teile:
            r, n = self._read_value(total)
            info["versuche"].append(n)
            raws.append(r)
            if "NOT TRIGGERED" in r:
                info["raw"] = "".join(raws)
                info["abbruch"] = "UPA meldet NOT TRIGGERED - Bandmessung gestoppt"
                return info
            if not self._extract(r):
                info["raw"] = "".join(raws)
                info["abbruch"] = f"Kein Messwert innerhalb {total:.0f} s - Bandmessung gestoppt"
                return info
        info["raw"] = "".join(raws)
        lines = [self._extract(r) for r in raws]
        if self.band_mode == "LEV/FREQ":
            lv, fq = assign(lines)
            zu = {"LEV": lv, "FREQ": fq}
        else:
            zu = classify(lines, teile)
        for t in teile:
            info["lines"][t] = zu.get(t)
            info["values"][t] = parse_value(zu.get(t))
        info["volt"] = info["values"].get("LEV")
        info["hz"] = info["values"].get("FREQ")
        return info

    def band_check(self):
        """Zwischenpruefung (alle paar Werte): (Abbruchtext oder None, spoll-Antwort).
        Abgebrochen wird nur bei einer Flut; andere Statusbytes werden protokolliert."""
        sp = self.spoll()
        if sp.startswith("FLUT"):
            return "Flut erkannt - Bandmessung gestoppt (Adapter-USB kurz ziehen)", sp
        return None, sp

    def measure_point(self, freq, level, output="LEFT UNBAL", inp="LEFT UNBAL",
                      hold=10, settle=3.0):
        """Bewiesene v16-Messung (Pegel + Frequenz), unveraendert."""
        return self.measure(freq, level, output=output, inp=inp, mode="LEV/FREQ",
                            rng=f"HOLD({hold})", settle=settle)

    def close(self):
        try:
            self.ifc()
            self._w("++loc");   time.sleep(0.3)
            self._w("++ren 0"); time.sleep(0.3)
            time.sleep(0.4)
            self.ser.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Ablaeufe fuer die Oberflaeche
# ---------------------------------------------------------------------------
UPA_STEPS = [
    ("pre",   "Bus frei (Vorab-spoll)"),
    ("rem",   "REM aktivieren (++ren 1, ++llo, CLEAR)"),
    ("auto",  "++auto = 0"),
    ("meas",  "Testmessung 1 kHz / 0,3 V (Loopback)"),
    ("freq",  "Gemessene Frequenz plausibel"),
    ("rel",   "Freigabe (REM/LLD aus)"),
]


def upa_check(port, addr, step_cb, log, stop):
    """Verbindungs-Check: REM + eine Testmessung ueber Loopback.
    Liefert True bei Erfolg."""
    step_cb("pre", "run", "")
    try:
        u = UPA(port, addr)
    except Exception as e:
        step_cb("pre", "fail", str(e))
        return False
    ok = False
    try:
        pre = u.spoll()
        log(f"Vorab-spoll: {pre!r}")
        if pre.startswith("FLUT"):
            step_cb("pre", "fail", "alte Flut - Adapter-USB kurz ziehen")
            return False
        step_cb("pre", "ok", pre or "(leer)")

        step_cb("rem", "run", "")
        u.init_bus()
        step_cb("rem", "ok", "REM aktiv")

        step_cb("auto", "run", "")
        av = u.ask("++auto")
        if av == "0":
            step_cb("auto", "ok", "0")
        else:
            step_cb("auto", "fail", repr(av))
            return False

        if stop():
            raise Abbruch()
        step_cb("meas", "run", "")
        r = u.measure_point(1000, 0.3)
        log(f"Testmessung: spoll set={r.get('spoll_set')!r} roh={r.get('raw', '')!r} "
            f"spoll n.read={r.get('spoll_nach_read')!r}")
        if r["abbruch"] or r.get("volt") is None:
            step_cb("meas", "fail", r["abbruch"] or "kein Pegelwert")
            return False
        step_cb("meas", "ok", f"{r['volt']:.4f} V")

        step_cb("freq", "run", "")
        hz = r.get("hz")
        if hz is not None and abs(hz - 1000) <= 10:
            step_cb("freq", "ok", f"{hz:g} Hz")
            ok = True
        else:
            step_cb("freq", "fail", f"{hz!r} Hz - Loopback/Eingang pruefen")
    finally:
        step_cb("rel", "run", "")
        u.close()
        step_cb("rel", "ok", "++loc, ++ren 0")
    return ok
