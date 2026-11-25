"""Voltcraft VC-7055BT (baugleich OWON XDM1041) ueber RS-232 als zweites Multimeter (MM2).

Schnittstelle (am Geraet getestet 25.11.2026, FW V3.0.0, FTDI-USB-Seriell + Nullmodemkabel,
Testskript vc7055_test.py v1-v3):
  115200 Baud, 8N1, Befehle mit LF abgeschlossen, Antwort endet mit CR LF, kein Echo.
  "*IDN?"   -> "Voltcraft,VC7055BT,2210062,V3.0.0,3"
  "FUNC?"   -> '"VOLT"' | '"VOLT AC"' | '"RES"' ...
  "RANGE?"  -> "5 V" | "50 V" | "50 M<Ohm in GBK>"
  "AUTO?"   -> "1" | "0"
  "MEAS1?"  -> "5.156087E+00"   (Grundeinheit; Ueberlauf = "1E+9")
Alle Abfragen funktionieren OHNE SYST:REM - die Software sendet SYST:REM nie,
das Geraet bleibt von Hand bedienbar. CONF? antwortet nicht und wird nicht benutzt.
"""
import threading
import time

try:
    import serial
    from serial.tools import list_ports
except Exception:          # pragma: no cover
    serial = None
    list_ports = None

from upa_fluke import FlukeFehler as MessFehler

BAUD = 115200
UEBERLAUF = 9.9e8          # VC-7055BT meldet OL als 1E+9

# FUNC?-Antwort -> Einheitenkennung wie beim Fluke (VDC, VAC, ...)
FUNKTIONEN = {"VOLT": "VDC", "VOLT DC": "VDC", "VOLT AC": "VAC", "CURR": "ADC", "CURR DC": "ADC",
              "CURR AC": "AAC", "RES": "OHM", "FRES": "OHM 4W", "FREQ": "Hz", "PER": "s",
              "CAP": "F", "DIOD": "DIODE", "CONT": "DURCHGANG", "TEMP": "TEMP"}


class Voltcraft:
    name = "Voltcraft"

    def __init__(self, port):
        self.port = port
        self.ser = None
        self.ident = ""
        self.funktion = ""         # Rohtext aus FUNC?, z. B. VOLT
        self.bereich = ""          # Rohtext aus RANGE?, z. B. 50 mV
        self.auto = None
        self.lock = threading.Lock()
        self._n = 0

    def oeffnen(self):
        if serial is None:
            raise MessFehler("pyserial fehlt")
        try:
            self.ser = serial.Serial(self.port, BAUD, bytesize=8, parity="N", stopbits=1, timeout=0.2,
                                     write_timeout=2, rtscts=False, dsrdtr=False, xonxoff=False)
        except Exception as e:
            raise MessFehler(f"{self.port} nicht nutzbar ({e})")
        time.sleep(0.3)
        antw = self._frage("*IDN?", 1.5)
        if "VC7055" not in antw.upper().replace("-", "") and "XDM" not in antw.upper():
            self.schliessen()
            raise MessFehler(f"{self.port}: kein VC-7055BT ({antw!r})")
        t = [x.strip() for x in antw.split(",")]
        self.ident = (f"{t[0]} {t[1]} · FW {t[3]} · SN {t[2]}" if len(t) >= 4 else antw)
        return self.ident

    def schliessen(self):
        try:
            if self.ser:
                self.ser.close()
        finally:
            self.ser = None

    def _frage(self, cmd, warte=1.0):
        """Abfrage senden, eine Antwortzeile (ohne CR LF) liefern, '' bei keiner Antwort."""
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.write((cmd + "\n").encode("ascii"))
            ende = time.time() + warte
            daten = b""
            while time.time() < ende:
                n = self.ser.in_waiting
                if n:
                    daten += self.ser.read(n)
                    if daten.endswith(b"\n"):
                        break
                else:
                    time.sleep(0.01)
        try:
            txt = daten.decode("gbk")        # Ohm-Zeichen kommt als GBK (A6 B8)
        except UnicodeDecodeError:
            txt = daten.decode("ascii", "replace")
        return txt.strip()

    def messen(self):
        """Ein Messwert: dict(wert, einheit, status, bereich) – wert in Grundeinheit, None bei OL."""
        f = self._frage("FUNC?").strip('"').strip().upper()
        if not f:
            raise MessFehler("keine Antwort auf FUNC?")
        self.funktion = f
        if self._n % 5 == 0:                 # Bereich aendert sich selten
            self.bereich = self._frage("RANGE?")
            self.auto = self._frage("AUTO?") == "1"
        self._n += 1
        roh = self._frage("MEAS1?")
        try:
            wert = float(roh)
        except ValueError:
            raise MessFehler(f"keine gueltige Antwort auf MEAS1? ({roh!r})")
        status = "NORMAL"
        if abs(wert) >= UEBERLAUF:
            wert, status = None, "OL"
        return {"wert": wert, "einheit": FUNKTIONEN.get(f, f), "status": status,
                "bereich": self.bereich, "auto": self.auto}


def suchen(ausser=()):
    """Port mit angeschlossenem VC-7055BT suchen (AR488- und Fluke-Port bleiben unberuehrt)."""
    if list_ports is None:
        return None, "pyserial fehlt"
    ausser = {a.upper() for a in ausser if a}
    for p in list_ports.comports():
        if p.device.upper() in ausser:
            continue
        v = Voltcraft(p.device)
        try:
            return p.device, v.oeffnen()
        except MessFehler:
            pass
        finally:
            v.schliessen()
    return None, "kein VC-7055BT gefunden – Port → Serial, 115200 Baud? Nullmodemkabel gesteckt?"
