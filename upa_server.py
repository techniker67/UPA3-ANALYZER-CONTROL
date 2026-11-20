#!/usr/bin/env python3
"""
upa_server.py - lokale Web-Oberflaeche fuer den R&S UPA3 (AR488-GPIB)
=====================================================================
Start:   python upa_server.py                 (COM4, nur dieser PC)
         python upa_server.py --port COM5
         python upa_server.py --listen 0.0.0.0 (spaeter Mini-PC: im Netz erreichbar)

Oeffnet automatisch http://127.0.0.1:8488 im Browser.
Nur Python-Standardbibliothek + pyserial.
"""
import argparse
import json
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import upa_core as core
import upa_paths as paths
import upa_programs as progs
import upa_report as report
import upa_window as window
from upa_version import __version__, DATUM, GETESTETE_FIRMWARE

# Speicherorte: siehe upa_paths.py (Programm- und Datenordner getrennt)

FREQ_MIN, FREQ_MAX = 10.0, 50000.0
LEVEL_MIN, LEVEL_MAX = 0.001, 5.0
MAX_POINTS = 61


class App:
    def __init__(self, port, addr):
        self.lock = threading.Lock()
        self.port = port
        self.addr = addr
        self.busy = False
        self.stop_flag = False
        self.phase = "idle"          # idle | booting | ready | measuring | error
        self.boot_ok = False
        self.steps = []
        self.log_lines = []
        self.points = []
        self.sweep_meta = {}
        self.last_csv = None
        self.version = ""
        self.on_quit = None          # vom Programmfenster gesetzt: Fenster schliessen
        try:                         # zuletzt festgelegter Pruefling
            self.pruefling = report.pruefling_pruefen(load_settings().get("pruefling"))
        except ValueError:
            self.pruefling = None
        self._reset_steps()

    # ---- Zustand --------------------------------------------------------
    def _reset_steps(self):
        self.steps = ([{"id": "a_" + i, "group": "ADAPTER", "label": l, "status": "pending",
                        "detail": ""} for i, l in core.ADAPTER_STEPS] +
                      [{"id": "u_" + i, "group": "UPA", "label": l, "status": "pending",
                        "detail": ""} for i, l in core.UPA_STEPS])

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        with self.lock:
            self.log_lines.append(f"{ts}  {msg}")
            self.log_lines = self.log_lines[-500:]
        try:   # Protokolldatei (fuer Ferndiagnose ueber die Desktop-Bruecke)
            with open(paths.data("upa_log.txt"), "a", encoding="utf-8") as fh:
                fh.write(datetime.now().strftime("%Y-%m-%d ") + f"{ts}  {msg}\n")
        except Exception:
            pass

    def set_step(self, sid, status, detail=""):
        with self.lock:
            for s in self.steps:
                if s["id"] == sid:
                    s["status"] = status
                    s["detail"] = detail
        if status in ("ok", "fail"):
            self.log(f"[{'OK' if status == 'ok' else 'FEHLER'}] {sid}: {detail}")

    def state(self, since=0):
        with self.lock:
            return {
                "phase": self.phase, "busy": self.busy, "boot_ok": self.boot_ok,
                "port": self.port, "addr": self.addr, "version": self.version,
                "steps": self.steps, "points": self.points, "meta": self.sweep_meta,
                "log": self.log_lines[since:], "log_len": len(self.log_lines),
                "last_csv": os.path.basename(self.last_csv) if self.last_csv else None,
                "sound": bool(find_sound()), "p78": bool(load_p78()),
                "app_version": __version__, "app_datum": DATUM,
                "fw_getestet": bool(self.version) and any(g in self.version for g in GETESTETE_FIRMWARE),
                "firma": load_settings().get("firma", ""),
                "pruefling": self.pruefling,
                "pruefling_ordner": report.ordnername(self.pruefling) if self.pruefling else None,
                "diagramme": report.plt is not None,
                "limits": {"fmin": FREQ_MIN, "fmax": FREQ_MAX, "umin": LEVEL_MIN,
                           "umax": LEVEL_MAX, "nmax": MAX_POINTS},
            }

    # ---- Jobs -----------------------------------------------------------
    def _start(self, target, phase):
        with self.lock:
            if self.busy:
                return False
            self.busy = True
            self.stop_flag = False
            self.phase = phase
        threading.Thread(target=self._run, args=(target,), daemon=True).start()
        return True

    def _run(self, target):
        try:
            target()
        except Exception as e:
            self.log(f"FEHLER: {e}")
            with self.lock:
                self.phase = "error"
        finally:
            with self.lock:
                self.busy = False

    def boot(self, port, addr):
        def job():
            with self.lock:
                self.port = port
                self.addr = addr
                self.boot_ok = False
                self._reset_steps()
            self.log(f"=== System-Initialisierung auf {port}, GPIB-Adresse {addr} ===")
            ok, total, ver = core.adapter_check(
                port, self.addr, lambda i, s, d="": self.set_step("a_" + i, s, d), self.log)
            self.version = ver
            self.log(f"Adapter-Check: {ok}/{total}")
            if ver:
                if any(g in ver for g in GETESTETE_FIRMWARE):
                    self.log(f"Adapter-Firmware getestet: {ver}")
                else:
                    self.log(f"HINWEIS: Adapter-Firmware nicht getestet ({ver}). Getestet mit: "
                             f"{', '.join(GETESTETE_FIRMWARE)}. Messungen pruefen!")
            if ok != total:
                with self.lock:
                    self.phase = "error"
                self.log("Adapter nicht voll gruen - UPA-Verbindung wird NICHT aufgebaut.")
                return
            good = core.upa_check(port, self.addr,
                                  lambda i, s, d="": self.set_step("u_" + i, s, d),
                                  self.log, lambda: self.stop_flag)
            with self.lock:
                self.boot_ok = good
                self.phase = "ready" if good else "error"
            self.log("SYSTEM BEREIT." if good else "UPA-Verbindung fehlgeschlagen.")
            if good:
                save_settings({"port": port, "addr": addr})   # beim naechsten Start vorbelegt
        return self._start(job, "booting")

    def run_prog(self, prog, p):
        def job():
            with self.lock:
                self.points = []
                self.sweep_meta = {"start": datetime.now().isoformat(timespec="seconds"),
                                   "prog": prog["id"], "name": prog["name"], "label": p["label"],
                                   "pruefling": self.pruefling,
                                   "adapter": self.version,
                                   "n": p["n"], "params": {k: v for k, v in p.items() if k != "label"}}
            self.log(f"=== {prog['name']}: Kanaele {'+'.join(p['channels'])}, {p['n']} Messungen, "
                     f"Filter {'+'.join(progs._filters(p)) or 'keine'}, Bereich {p['rng']} ===")

            def emit(pt):
                with self.lock:
                    pt["i"] = len(self.points) + 1
                    self.points.append(pt)
                u_ = pt.get("u")
                us = ("---" if u_ is None else f"{u_*1e6:.3g} uV" if u_ < 1e-3
                      else f"{u_*1e3:.4g} mV" if u_ < 0.1 else f"{u_:.4f} V")
                fs = f"{pt['f']:g} Hz" if pt.get("f") is not None else ""
                xs = f"  FNCT {pt['fnct_line']}" if pt.get("fnct_line") else ""
                vs = f"  (Lesevers. {pt['versuche']})" if pt.get("versuche") else ""
                self.log(f"  [{pt['ch']}] -> {us} {fs}{xs}{vs}")
                for c in pt.get("neu_ok", []):
                    self.log(f"  [OK] neuer Befehl angenommen: {c}")
                if pt.get("abbruch"):
                    self.log("ABBRUCH: " + pt["abbruch"])

            u = core.UPA(self.port, self.addr)
            try:
                pre = u.spoll()
                if pre.startswith("FLUT"):
                    raise RuntimeError("Alte Flut aktiv - Adapter-USB kurz ziehen, dann neu.")
                u.init_bus()
                progs.run(u, prog, p, emit, self.log, lambda: self.stop_flag)
                if self.stop_flag:
                    self.log("Gestoppt durch Benutzer.")
            finally:
                u.close()
                self.log("Freigabe: REM/LLD aus.")
                self.ablegen()
                with self.lock:
                    self.phase = "ready"
        return self._start(job, "measuring")

    def ablegen(self):
        """CSV, Diagramm und Eintrag in messungen.json schreiben (Geraeteordner,
        wenn ein Pruefling festgelegt ist). Fehler beim Diagramm/Eintrag
        verhindern nie das Speichern der CSV."""
        meta, pts = self.sweep_meta, list(self.points)
        pr = meta.get("pruefling")
        ziel = report.ordner(pr)
        self.last_csv = write_csv(pts, meta, ziel)
        rel = os.path.relpath(self.last_csv, paths.DATA_DIR)
        self.log(f"CSV gespeichert: {rel}")
        if not pr:
            return
        basis = os.path.splitext(self.last_csv)[0]
        png = None
        try:
            titel = f"{meta.get('name')} – {report.bezeichnung(pr)}"
            if report.diagramm(meta.get("prog"), titel, pts, basis + ".png"):
                png = os.path.basename(basis + ".png")
                self.log(f"Diagramm gespeichert: {png}")
        except Exception as e:
            self.log(f"Diagramm nicht erstellt: {e}")
        try:
            report.eintrag_speichern(ziel, {
                "programm": meta.get("prog"), "name": meta.get("name"),
                "start": meta.get("start"), "ende": datetime.now().isoformat(timespec="seconds"),
                "bezeichnung": meta.get("label", ""), "csv": os.path.basename(self.last_csv),
                "png": png, "adapter": meta.get("adapter"), "software": __version__,
                "parameter": {k: v for k, v in meta.get("params", {}).items()
                              if k not in ("atten_tab", "atten_tabs")},
                "ergebnis": report.zusammenfassung(meta.get("prog"), pts),
                "abgebrochen": any(p.get("abbruch") for p in pts) or bool(self.stop_flag)})
        except Exception as e:
            self.log(f"messungen.json nicht aktualisiert: {e}")

    def set_pruefling(self, d):
        pr = report.pruefling_pruefen(d)     # ValueError bei unvollstaendiger Eingabe
        with self.lock:
            self.pruefling = pr
        save_settings({"pruefling": pr or {}})
        if pr:
            report.ordner(pr)
            self.log(f"Prüfling: {report.bezeichnung(pr)} -> Messungen/{report.ordnername(pr)}")
        else:
            self.log("Kein Prüfling - Messungen landen direkt in Messungen/.")


CSV_COLS = ["i", "ch", "x", "f_soll", "f", "u_soll", "u", "u_true", "p_w", "gain", "gain_db",
            "att_k", "fnct", "fnct_line", "versuche", "step", "ref_u", "ref_raw", "noise_u", "sn_db", "xt_u", "xt_db", "dir",
            "abbruch", "raw"]


def write_csv(points, meta, ziel=None):
    ziel = ziel or paths.mess_dir()
    os.makedirs(ziel, exist_ok=True)
    name = ("upa_" + str(meta.get("prog", "messung")) + "_"
            + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
    path = os.path.join(ziel, name)
    with open(path, "w", encoding="utf-8") as fh:
        firma = load_settings().get("firma", "")
        fh.write(f"# UPA-Software v{__version__}" + (f" · {firma}" if firma else "") + "\n")
        fh.write(f"# Adapter: {meta.get('adapter') or 'unbekannt'}\n")
        if meta.get("pruefling"):
            fh.write(f"# Prüfling: {report.bezeichnung(meta['pruefling'])}\n")
        fh.write(f"# {meta.get('name')}  {meta.get('start')}  {meta.get('label', '')}  "
                 f"Parameter: {json.dumps(meta.get('params', {}), ensure_ascii=False)}\n")
        fh.write(";".join(CSV_COLS) + "\n")
        for pt in points:
            row = []
            for c in CSV_COLS:
                v = pt.get(c)
                v = "" if v is None else str(v)
                row.append(v.replace(";", ",").replace("\r", " ").replace("\n", " | "))
            fh.write(";".join(row) + "\n")
    return path


def find_sound():
    """Erste MP3 mit 'ready' im Namen (Datenordner, Programmordner, dessen Elternordner)."""
    for d in (paths.DATA_DIR, paths.PROG_DIR, os.path.dirname(paths.PROG_DIR)):
        try:
            for n in sorted(os.listdir(d)):
                if n.lower().endswith(".mp3") and "ready" in n.lower():
                    return os.path.join(d, n)
        except OSError:
            pass
    return None


def load_settings():
    """Einstellungen (Firmenname ...) aus upa_einstellungen.json - optional."""
    try:
        with open(paths.data("upa_einstellungen.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_settings(neu):
    """Werte in upa_einstellungen.json ergaenzen/ueberschreiben (Rest bleibt)."""
    try:
        d = load_settings()
        d.update(neu)
        with open(paths.data("upa_einstellungen.json"), "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
    except Exception:
        pass


def load_p78():
    """Kalibriertabelle des P78 (Programmordner)."""
    try:
        with open(paths.data("p78_kalibrierung.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        d["punkte"] = sorted([float(f), float(k)] for f, k in d["punkte"])
        kan = d.get("kanaele") or {"L": d["punkte"]}
        d["kanaele"] = {c: sorted([float(f), float(k)] for f, k in t) for c, t in kan.items()}
        return d
    except Exception:
        return None


def _f(body, k, default):
    v = body.get(k, default)
    return float(default if v in (None, "") else v)


def validate_run(body):
    """Pruefen + Parameter bauen. Liefert (prog, params) oder wirft ValueError."""
    prog = progs.BY_ID.get(body.get("prog"))
    if not prog:
        raise ValueError("Unbekanntes Messprogramm")
    if prog["status"] == "locked":
        raise ValueError(f"{prog['name']} ist gesperrt: {prog.get('lock', '')}")
    ui = prog["ui"]
    ch = body.get("channels", "L")
    channels = {"L": ["L"], "R": ["R"], "LR": ["L", "R"]}.get(ch)
    if not channels:
        raise ValueError("Kanal muss L, R oder LR sein")
    rng = body.get("rng", "HOLD(10)")
    if rng not in ("HOLD(10)", "AUTO"):
        raise ValueError("Bereich muss HOLD(10) oder AUTO sein")
    atten_tab = atten_tabs = None
    if body.get("atten") == "p78":
        kal = load_p78()
        if not kal:
            raise ValueError(f"p78_kalibrierung.json fehlt im Datenordner {paths.DATA_DIR}")
        atten_tab = kal["punkte"]
        atten_tabs = kal["kanaele"]
        fehlt = [c for c in channels if c not in atten_tabs]
        if fehlt:
            raise ValueError(f"P78-Kalibrierung fehlt fuer Kanal {', '.join(fehlt)}")
        atten = kal.get("faktor_1khz", atten_tab[0][1])
    else:
        atten = _f(body, "atten", 1)
    load = _f(body, "load", 0)
    if not (1 <= atten <= 100) or not (0 <= load <= 10000):
        raise ValueError("Abschwaecher 1-100, Last 0-10000 Ohm")
    if atten_tab and rng != "AUTO":
        rng = "AUTO"          # P78: nur mit 4 Stellen sinnvoll (Kalibrierung lief mit AUTO)
    p = {"channels": channels, "rng": rng, "atten": atten, "atten_tab": atten_tab,
         "atten_tabs": atten_tabs, "load": load,
         "lp22": bool(body.get("lp22")), "hp22": bool(body.get("hp22")),
         "label": str(body.get("label", ""))[:80]}

    def chk_level(v):
        if not (LEVEL_MIN <= v <= LEVEL_MAX):
            raise ValueError(f"Pegel muss zwischen {LEVEL_MIN} und {LEVEL_MAX} V liegen")
        return v

    def chk_freq(f):
        if not (FREQ_MIN <= f <= FREQ_MAX):
            raise ValueError(f"Frequenz {f:g} Hz ausserhalb {FREQ_MIN:g}-{FREQ_MAX:g} Hz")
        return f

    n = 0
    if ui.get("level"):
        p["level"] = chk_level(_f(body, "level", 0.5))
    if ui.get("fixfreq"):
        p["fixfreq"] = chk_freq(_f(body, "fixfreq", 1000))
    if ui.get("freqs"):
        freqs = [chk_freq(float(f)) for f in body.get("freqs", [])]
        if not freqs:
            raise ValueError("Keine Frequenzen")
        p["freqs"] = freqs
        n = len(freqs)
    if ui.get("levelsweep"):
        a, b, k = _f(body, "lstart", 0.05), _f(body, "lstop", 1.0), int(_f(body, "ln", 8))
        chk_level(a); chk_level(b)
        if not (b > a and 2 <= k <= MAX_POINTS):
            raise ValueError("Pegel-Sweep: Endpegel > Startpegel, 2-61 Punkte")
        p["levels"] = [round(a * (b / a) ** (i / (k - 1)), 4) for i in range(k)]
        n = k
    if n > MAX_POINTS:
        raise ValueError(f"Maximal {MAX_POINTS} Punkte")
    p["n"] = max(n, 1) * len(channels)
    return prog, p


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def make_handler(app):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, data, ctype="application/json; charset=utf-8", extra=None):
            if isinstance(data, (dict, list)):
                data = json.dumps(data).encode("utf-8")
            elif isinstance(data, str):
                data = data.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except Exception:
                return {}

        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                with open(os.path.join(paths.RES_DIR, "index.html"), "rb") as fh:
                    return self._send(200, fh.read(), "text/html; charset=utf-8")
            if u.path == "/api/state":
                since = 0
                for kv in u.query.split("&"):
                    if kv.startswith("since="):
                        try:
                            since = int(kv[6:])
                        except ValueError:
                            pass
                return self._send(200, app.state(since))
            if u.path == "/api/programs":
                return self._send(200, progs.PROGRAMS)
            if u.path == "/api/ports":
                return self._send(200, core.list_ports())
            if u.path == "/sound/ready":
                p = find_sound()
                if not p:
                    return self._send(404, {"error": "keine MP3"})
                with open(p, "rb") as fh:
                    return self._send(200, fh.read(), "audio/mpeg")
            if u.path == "/api/csv":
                if not app.last_csv or not os.path.isfile(app.last_csv):
                    return self._send(404, {"error": "noch keine Messung"})
                with open(app.last_csv, "rb") as fh:
                    return self._send(200, fh.read(), "text/csv; charset=utf-8",
                                      {"Content-Disposition":
                                       f'attachment; filename="{os.path.basename(app.last_csv)}"'})
            return self._send(404, {"error": "unbekannt"})

        def do_POST(self):
            u = urlparse(self.path)
            body = self._body()
            if u.path == "/api/boot":
                port = str(body.get("port") or app.port).strip()
                try:
                    addr = int(body.get("addr", app.addr))
                except (TypeError, ValueError):
                    addr = -1
                if not (0 <= addr <= 30):
                    return self._send(400, {"error": "GPIB-Adresse muss 0 bis 30 sein"})
                if not app.boot(port, addr):
                    return self._send(409, {"error": "beschaeftigt"})
                return self._send(200, {"ok": True})
            if u.path == "/api/run":
                if not app.boot_ok:
                    return self._send(409, {"error": "Erst System-Initialisierung erfolgreich abschliessen"})
                try:
                    prog, p = validate_run(body)
                except (ValueError, TypeError) as e:
                    return self._send(400, {"error": str(e)})
                if not app.run_prog(prog, p):
                    return self._send(409, {"error": "beschaeftigt"})
                return self._send(200, {"ok": True})
            if u.path == "/api/pruefling":
                if app.busy:
                    return self._send(409, {"error": "Während einer Messung nicht änderbar"})
                try:
                    app.set_pruefling(body)
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                return self._send(200, {"ok": True, "pruefling": app.pruefling})
            if u.path == "/api/quit":
                if app.busy:
                    return self._send(409, {"error": "Bitte erst die laufende Messung stoppen"})
                app.log("Beenden ueber QUIT - Software wird geschlossen.")
                self._send(200, {"ok": True})
                # Serverschleife aus einem eigenen Thread beenden (nicht aus dem Handler),
                # danach ggf. das Programmfenster schliessen
                srv = self.server

                def beenden():
                    srv.shutdown()
                    if app.on_quit:
                        app.on_quit()
                threading.Timer(0.5, beenden).start()
                return None
            if u.path == "/api/stop":
                app.stop_flag = True
                app.log("Stop angefordert - Abbruch nach dem laufenden Punkt.")
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "unbekannt"})
    return H


class Server(ThreadingHTTPServer):
    # Unter Windows wuerde SO_REUSEADDR einen zweiten Start auf demselben Port
    # stillschweigend zulassen - dort deshalb aus, damit "Port belegt" erkannt wird.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


def main():
    # Datenordner zuerst bestimmen - die Vorgaben fuer Port/Adresse kommen daraus
    vor = argparse.ArgumentParser(add_help=False)
    vor.add_argument("--data", help="Datenordner (Einstellungen, Kalibrierung, Messungen, Protokoll); "
                                     "Vorgabe: Dokumente/UPA-Analyzer-Control")
    va, _ = vor.parse_known_args()
    if va.data:
        paths.set_data_dir(va.data)
    meldungen = paths.prepare()

    ap = argparse.ArgumentParser(parents=[vor])
    ein = load_settings()
    ap.add_argument("--port", default=ein.get("port", "COM4"),
                    help="serieller Port des AR488 (COM4 / /dev/ttyACM0); Vorgabe: zuletzt erfolgreich")
    ap.add_argument("--addr", type=int, default=int(ein.get("addr", 7)),
                    help="GPIB-Adresse des UPA (0-30); Vorgabe: zuletzt erfolgreich")
    ap.add_argument("--http", type=int, default=8488, help="HTTP-Port der Oberflaeche")
    ap.add_argument("--listen", default="127.0.0.1",
                    help="127.0.0.1 = nur dieser PC (Standard); 0.0.0.0 = im Netz")
    ap.add_argument("--browser", action="store_true",
                    help="Oberflaeche im Browser statt im eigenen Programmfenster")
    ap.add_argument("--no-browser", action="store_true",
                    help="weder Fenster noch Browser oeffnen (nur Server, z. B. Mini-PC/Test)")
    ap.add_argument("--selbsttest", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.selbsttest:              # Build-Pruefung: Diagramm-Erzeugung ohne Geraet
        print("Selbsttest:", report.selbsttest(paths.data("selbsttest")))
        return 0
    fenster = window.available() and not a.browser and not a.no_browser

    app = App(a.port, a.addr)
    app.log(f"UPA-Software v{__version__} - Datenordner: {paths.DATA_DIR}")
    for m in meldungen:
        app.log(m)
    if core.serial is None:
        app.log("pyserial fehlt -> in der Konsole: pip install pyserial")
    url = f"http://127.0.0.1:{a.http}/"
    try:
        srv = Server((a.listen, a.http), make_handler(app))
    except OSError:
        # meist: Software laeuft schon
        if fenster:
            window.message_box("Die UPA-Software laeuft bereits.\n\n"
                               f"(Port {a.http} ist belegt.)")
            return 0
        print(f"  Port {a.http} ist belegt - die UPA-Software laeuft vermutlich schon.")
        print(f"  Oeffne {url}")
        if not a.no_browser:
            webbrowser.open(url)
        time.sleep(4)
        return 0
    print("=" * 60)
    print(f"  UPA-Software v{__version__} ({DATUM}) laeuft:  {url}")
    print(f"  Adapter-Port: {a.port}   GPIB-Adresse: {a.addr}")
    print(f"  Datenordner:  {paths.DATA_DIR}")
    for m in meldungen:
        print(f"  {m}")
    print("  Beenden: QUIT in der Oberflaeche, dieses Fenster schliessen oder Strg+C")
    print("=" * 60)
    if fenster:
        # Server im Hintergrund, Programmfenster im Hauptthread (so verlangt es pywebview)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        app.log("Oberflaeche im Programmfenster.")
        if window.run(app, url, f"UPA·3 // Analyzer Control  v{__version__}", paths.data("webview")):
            srv.shutdown()        # Fenster zu (X oder QUIT) -> Software beenden
            srv.server_close()
            print("  UPA-Software beendet.")
            return 0
        webbrowser.open(url)      # Fenster ging nicht -> Browser wie bisher
        try:
            t.join()
        except KeyboardInterrupt:
            srv.shutdown()
        srv.server_close()
        print("  UPA-Software beendet.")
        return 0
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    srv.server_close()
    print("  UPA-Software beendet.")


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        # installierte Version: bei einem Startfehler das Fenster nicht sofort schliessen
        try:
            sys.exit(main() or 0)
        except SystemExit:
            raise
        except Exception:
            import traceback
            txt = traceback.format_exc()
            if sys.stdout is None:        # Fenster-Version ohne Konsole
                window.message_box("Fehler beim Start:\n\n" + txt[-1500:])
            else:
                print(txt)
                input("\nFehler beim Start - Enter druecken zum Schliessen ...")
            sys.exit(1)
    sys.exit(main() or 0)
