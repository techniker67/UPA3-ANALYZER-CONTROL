"""Fluke 287/289 ueber das IR-USB-Kabel (Ruhestrom / Offset).

Schnittstelle (am Geraet getestet 21.11.2026, Fluke 287 V1.41, Kabel FTDI):
  115200 Baud, 8N1, Befehle mit CR abgeschlossen.
  "ID"  -> "0\\rFLUKE 287,V1.41,<Seriennr>\\r"
  "QM"  -> "0\\r9.470E0,VDC,NORMAL,NONE\\r"   (Wert in Grundeinheit V, Einheit, Status, Zusatz)
  Erste Zeile = Quittung: 0 = ok, 1 = Syntaxfehler, 2 = Ausfuehrungsfehler.
Die Software fragt nur ab und verstellt am Messgeraet nichts.
"""
import math
import threading
import time
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
except Exception:          # pragma: no cover
    serial = None
    list_ports = None

BAUD = 115200
UEBERLAUF = 9e37           # Fluke meldet OL als 9.99999999E+37


class FlukeFehler(Exception):
    pass


class Fluke:
    def __init__(self, port):
        self.port = port
        self.ser = None
        self.ident = ""
        self.lock = threading.Lock()

    def oeffnen(self):
        if serial is None:
            raise FlukeFehler("pyserial fehlt")
        try:
            self.ser = serial.Serial(self.port, BAUD, timeout=0.2)
        except Exception as e:
            raise FlukeFehler(f"{self.port} nicht nutzbar ({e})")
        time.sleep(0.2)
        antw = self._befehl("ID", 1.0)
        if len(antw) < 2 or antw[0] != "0" or "FLUKE" not in antw[1].upper():
            self.schliessen()
            raise FlukeFehler(f"{self.port}: kein Fluke 287/289 ({antw!r})")
        self.ident = antw[1]
        return self.ident

    def schliessen(self):
        try:
            if self.ser:
                self.ser.close()
        finally:
            self.ser = None

    def _befehl(self, cmd, warte=0.8):
        """Befehl senden und die Antwortzeilen (ohne CR) liefern."""
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.write((cmd + "\r").encode("ascii"))
            ende = time.time() + warte
            daten = b""
            while time.time() < ende:
                n = self.ser.in_waiting
                if n:
                    daten += self.ser.read(n)
                    if daten.count(b"\r") >= 2 or daten.startswith((b"1\r", b"2\r")):
                        break
                else:
                    time.sleep(0.01)
        return [z for z in daten.decode("ascii", "replace").split("\r") if z != ""]

    def messen(self):
        """Ein Messwert: dict(wert, einheit, status) – wert in Grundeinheit, None bei OL/Fehler."""
        antw = self._befehl("QM", 0.8)
        if not antw or antw[0] != "0" or len(antw) < 2:
            raise FlukeFehler(f"keine gueltige Antwort auf QM ({antw!r})")
        teile = antw[1].split(",")
        try:
            wert = float(teile[0])
        except ValueError:
            wert = None
        if wert is not None and abs(wert) >= UEBERLAUF:
            wert = None
        return {"wert": wert, "einheit": teile[1] if len(teile) > 1 else "",
                "status": teile[2] if len(teile) > 2 else ""}


def suchen(ausser=()):
    """Port mit angeschlossenem Fluke suchen (andere Ports, z. B. der AR488, bleiben unberuehrt)."""
    if list_ports is None:
        return None, "pyserial fehlt"
    ausser = {a.upper() for a in ausser if a}
    for p in list_ports.comports():
        if p.device.upper() in ausser:
            continue
        f = Fluke(p.device)
        try:
            ident = f.oeffnen()
            return p.device, ident
        except FlukeFehler:
            pass
        finally:
            f.schliessen()
    return None, "kein Fluke gefunden – FlukeView Forms geschlossen? IR-Kopf aufgesteckt? Fluke an?"


def als_mv(m, name="Fluke"):
    """Messwert in mV (nur Spannungsfunktionen). Liefert (mV oder None, Hinweis).
    name = Geraet im Hinweistext (Fluke oder Voltcraft)."""
    e = (m.get("einheit") or "").upper()
    if m.get("wert") is None:
        return None, "Überlauf (OL)"
    if e in ("VDC", "VAC", "VAC_PLUS_DC", "V"):
        return m["wert"] * 1000.0, ("" if e == "VDC" else f"Achtung: {e} statt V DC")
    return None, f"{name} steht auf {e or '?'} – bitte {'mV' if name == 'Fluke' else 'V'} DC wählen"


# ---------------------------------------------------------------------------
class Logger:
    """Messlauf: Live (nur Anzeige) oder Aufzeichnung mit Dauer und Zeitmarken."""

    def __init__(self, fluke, p, log, stop):
        self.f, self.p, self.log, self.stop = fluke, p, log, stop
        self.punkte = []            # (t_s, mV oder None, Hinweis)
        self.marken = []            # dict(minute, t, wert, ok)
        self.t0 = None
        self.letzter = None
        self.hinweis = ""
        self.letzte_m = {}          # letzte Rohantwort (Einheit, Bereich ...)
        self.name = getattr(fluke, "name", "Fluke")

    def ok(self, v):
        soll, tol = self.p.get("soll"), self.p.get("tol")
        if v is None or soll is None or tol is None:
            return None
        return abs(v - soll) <= tol

    def trend(self, fenster=10.0):
        """mV pro Minute aus den letzten 'fenster' Sekunden (lineare Regression)."""
        if not self.punkte:
            return None
        t_end = self.punkte[-1][0]
        xs = [(t, v) for t, v, _ in self.punkte if v is not None and t >= t_end - fenster]
        if len(xs) < 3:
            return None
        n = len(xs)
        mt = sum(t for t, _ in xs) / n
        mv = sum(v for _, v in xs) / n
        nen = sum((t - mt) ** 2 for t, _ in xs)
        if nen <= 0:
            return 0.0
        return sum((t - mt) * (v - mv) for t, v in xs) / nen * 60.0

    def statistik(self, ab_t=0.0):
        """Min/Max/Mittel ab Zeitpunkt ab_t (s). Fuer das Protokoll ab der ersten
        Zeitmarke, damit Anklemm- und Abgleichspitzen nicht als Min/Max erscheinen."""
        vs = [v for t, v, _ in self.punkte if v is not None and t >= ab_t]
        if not vs:
            return {}
        return {"min": min(vs), "max": max(vs), "mittel": sum(vs) / len(vs), "n": len(vs),
                "ab_t": ab_t}

    def ist_ol(self, hinweis):
        return bool(hinweis) and "OL" in hinweis

    def laufen(self, emit):
        intervall = max(0.5, float(self.p.get("intervall") or 1.0))
        dauer = self.p.get("dauer_s")                    # None = bis Stop
        marken = sorted(m for m in (self.p.get("marken_min") or []) if m > 0)
        offen = list(marken)
        self.t0 = time.time()
        naechste = self.t0
        fehler_folge = 0
        while not self.stop():
            jetzt = time.time()
            t = jetzt - self.t0
            if dauer and t > dauer + 0.01:
                break
            try:
                m = self.f.messen()
                self.letzte_m = m
                v, self.hinweis = als_mv(m, self.name)
                fehler_folge = 0
            except FlukeFehler as e:
                fehler_folge += 1
                v, self.hinweis = None, str(e)
                if fehler_folge >= 5:
                    raise FlukeFehler(f"Verbindung zum {self.name} verloren: {e}")
            self.punkte.append((round(t, 2), v, self.hinweis))
            self.letzter = v
            while offen and t >= offen[0] * 60.0:
                mm = offen.pop(0)
                mk = {"minute": mm, "t": round(t, 1), "wert": v, "ok": self.ok(v)}
                if v is None and self.ist_ol(self.hinweis):
                    mk["ol"] = True
                    if self.p.get("soll") is not None:
                        mk["ok"] = False             # Ueberlauf liegt sicher ausserhalb
                self.marken.append(mk)
                self.log(f"Zeitmarke {mm:g} min: " + (f"{v:.3f} mV" if v is not None
                                                      else ("OL" if mk.get("ol") else "kein Wert")))
            emit()
            naechste += intervall
            while not self.stop() and time.time() < naechste:
                time.sleep(min(0.05, max(0.0, naechste - time.time())))
            if time.time() > naechste + intervall:      # nach Haenger nicht nachholen
                naechste = time.time()

    def luecken(self):
        return luecken(self.punkte)

    def verlauf(self, max_punkte=600):
        """Fuer die Anzeige verdichtet (Mittelwert je Abschnitt)."""
        pts = [(t, v) for t, v, _ in self.punkte if v is not None]
        if len(pts) <= max_punkte:
            return pts
        schritt = len(pts) / max_punkte
        out = []
        for i in range(max_punkte):
            teil = pts[int(i * schritt):int((i + 1) * schritt)] or [pts[-1]]
            out.append((teil[len(teil) // 2][0], sum(v for _, v in teil) / len(teil)))
        return out


def luecken(punkte):
    """Abschnitte ohne Messwert: [(t_von, t_bis, "OL" oder "kein Wert")].
    Ein Abschnitt reicht vom ersten Punkt ohne Wert bis zum naechsten gueltigen
    Punkt (bzw. bis zum letzten Punkt, wenn der Lauf ohne Wert endet)."""
    out, start, ol = [], None, True
    for t, v, h in punkte:
        if v is None:
            if start is None:
                start, ol = t, True
            ol = ol and bool(h) and "OL" in h
        elif start is not None:
            out.append((start, t, "OL" if ol else "kein Wert"))
            start = None
    if start is not None:
        out.append((start, max(punkte[-1][0], start + 0.5), "OL" if ol else "kein Wert"))
    return out


def zeit_txt(s):
    s = int(round(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def jetzt_iso():
    return datetime.now().isoformat(timespec="seconds")


def mv_txt(v, nk=3):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nk}f}"
