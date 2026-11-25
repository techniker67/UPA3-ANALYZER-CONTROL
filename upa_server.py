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
import upa_fluke as fluke
import upa_voltcraft as voltcraft
import upa_protokoll as protokoll
import upa_abgleich as abgleich
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
        self.update = None           # neuere Version auf GitHub: {"version", "url"}
        self.ordner_waehlen = None   # vom Programmfenster gesetzt: Dialog "Ordner auswaehlen"
        # Fluke 287 (Ruhestrom/Offset) - unabhaengig vom UPA, eigener Port und Thread
        self.fl_busy = False
        self.fl_stop = False
        self.fl = None               # laufender/letzter fluke.Logger
        self.fl_p = {}
        self.fl_ident = ""
        self.fl_port = load_settings().get("fluke_port", "")
        self.fl_csv = None
        # MM2: Voltcraft VC-7055BT (RS-232) - laeuft gemeinsam mit dem Fluke-Lauf
        self.m2 = None               # laufender/letzter fluke.Logger fuer MM2
        self.m2_p = {}
        self.m2_ident = ""
        self.m2_port = load_settings().get("mm2_port", "") or "COM5"
        self.m2_csv = None
        paths.set_ablage(load_settings().get("ablage", ""))
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
                "stufen": (report.band_stufen(self.points, (self.sweep_meta.get("params") or {}).get("bezug"))
                           if self.sweep_meta.get("prog") == "bfg" else None),
                "log": self.log_lines[since:], "log_len": len(self.log_lines),
                "last_csv": os.path.basename(self.last_csv) if self.last_csv else None,
                "sound": bool(find_sound()), "p78": bool(load_p78()),
                "app_version": __version__, "app_datum": DATUM,
                "fw_getestet": bool(self.version) and any(g in self.version for g in GETESTETE_FIRMWARE),
                "firma": load_settings().get("firma", ""),
                "pruefling": self.pruefling,
                "pegelbezug": pegelbezug(self.pruefling),
                "pruefling_ordner": report.ordnername(self.pruefling) if self.pruefling else None,
                "ablage": paths.ABLAGE, "ablage_lokal": paths.mess_dir_lokal(),
                "diagramme": report.plt is not None,
                "fluke": self.fluke_state(),
                "update": self.update, "datenordner": paths.DATA_DIR,
                "ordnerwahl": self.ordner_waehlen is not None,
                "update_pruefen": load_settings().get("update_pruefen", True) is not False,
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

    # ---- Fluke 287 -------------------------------------------------------
    @property
    def beschaeftigt(self):
        return self.busy or self.fl_busy

    def beenden_grund(self):
        """None, wenn die Software beendet werden darf, sonst der Hinweis.
        Eine Fluke-Live-Anzeige speichert nichts und wird beim Beenden gestoppt."""
        if self.busy:
            return "Bitte erst die laufende Messung stoppen."
        if self.fl_busy and self.fl_p.get("modus") == "rec":
            return "Bitte erst die Fluke-Aufzeichnung stoppen (STOP) – sonst geht sie verloren."
        return None

    def menue_grund(self):
        """Zurueck ins Menue: nicht waehrend einer UPA-Messung oder Fluke-Aufzeichnung.
        Eine Fluke-Live-Anzeige wird dabei gestoppt."""
        grund = self.beenden_grund()
        if not grund and self.fl_busy:
            self.fl_stop = True
        return grund

    def update_pruefen(self):
        """Im Hintergrund bei GitHub nachsehen, ob es ein neueres Release gibt."""
        if load_settings().get("update_pruefen", True) is False:
            return

        def pruefen():
            try:
                import urllib.request
                req = urllib.request.Request(RELEASE_API, headers={
                    "Accept": "application/vnd.github+json", "User-Agent": "UPA-Analyzer-Control"})
                with urllib.request.urlopen(req, timeout=6) as r:
                    j = json.loads(r.read().decode("utf-8"))
                tag = str(j.get("tag_name", "")).lstrip("vV")
                url = str(j.get("html_url", ""))
                if version_tupel(tag) > version_tupel(__version__) and url.startswith(REPO_URL):
                    self.update = {"version": tag, "url": url}
                    self.log(f"Neue Version {tag} auf GitHub verfügbar.")
            except Exception:
                pass                 # offline o. ae. - kein Hinweis
        threading.Thread(target=pruefen, daemon=True).start()

    def aufraeumen(self, warten=3.0):
        """Vor dem Beenden: Fluke-Lauf stoppen und Schnittstelle freigeben."""
        if self.fl_busy:
            self.fl_stop = True
            ende = time.time() + warten
            while self.fl_busy and time.time() < ende:
                time.sleep(0.05)

    @staticmethod
    def _logger_state(lg, st):
        if lg:
            pk = lg.punkte
            st.update({"t": pk[-1][0] if pk else 0.0, "wert": lg.letzter, "hinweis": lg.hinweis,
                       "trend": lg.trend(), "ok": lg.ok(lg.letzter), "stat": lg.statistik(),
                       "verlauf": lg.verlauf(), "luecken": lg.luecken(),
                       "marken": list(lg.marken), "n": len(pk)})
        return st

    def fluke_state(self):
        p = self.fl_p
        st = {"busy": self.fl_busy, "port": self.fl_port, "ident": self.fl_ident,
              "modus": p.get("modus"), "bezeichnung": p.get("bezeichnung", ""),
              "soll": p.get("soll"), "tol": p.get("tol"), "dauer_s": p.get("dauer_s"),
              "csv": os.path.basename(self.fl_csv) if self.fl_csv else None}
        self._logger_state(self.fl, st)
        q = self.m2_p
        m2 = {"an": bool(q), "port": self.m2_port, "ident": self.m2_ident,
              "bezeichnung": q.get("bezeichnung", ""), "soll": q.get("soll"), "tol": q.get("tol"),
              "csv": os.path.basename(self.m2_csv) if self.m2_csv else None}
        self._logger_state(self.m2, m2)
        if self.m2:
            lm = self.m2.letzte_m or {}
            m2.update({"funktion": lm.get("einheit", ""), "bereich": lm.get("bereich", ""),
                       "auto": lm.get("auto")})
        st["mm2"] = m2
        return st

    def mm2_suchen(self):
        if self.fl_busy:
            raise ValueError("Multimeter-Messung läuft")
        port, info = voltcraft.suchen(ausser=[self.port, self.fl_port])
        if not port:
            raise ValueError(info)
        self.m2_port, self.m2_ident = port, info
        save_settings({"mm2_port": port})
        self.log(f"MM2 gefunden an {port}: {info}")
        return port, info

    def fluke_suchen(self):
        if self.fl_busy:
            raise ValueError("Fluke-Messung läuft")
        port, info = fluke.suchen(ausser=[self.port])
        if not port:
            raise ValueError(info)
        self.fl_port, self.fl_ident = port, info
        save_settings({"fluke_port": port})
        self.log(f"Fluke gefunden an {port}: {info}")
        return port, info

    def fluke_start(self, p):
        with self.lock:
            if self.fl_busy:
                return False
            self.fl_busy, self.fl_stop = True, False
            self.fl_p, self.fl, self.fl_csv = p, None, None
            self.m2_p, self.m2, self.m2_csv = {}, None, None

        def job():
            f = v = None
            m2_thread = None
            try:
                port = p.get("port") or self.fl_port
                if not port:
                    port, _ = self.fluke_suchen()
                f = fluke.Fluke(port)
                self.fl_ident = f.oeffnen()
                if port != self.fl_port:
                    self.fl_port = port
                    save_settings({"fluke_port": port})
                art = "Live-Anzeige (Abgleich)" if p["modus"] == "live" else \
                    "Aufzeichnung " + (fluke.zeit_txt(p["dauer_s"]) if p["dauer_s"] else "bis Stop")
                soll = f", Soll {p['soll']:g} ± {p['tol']:g} mV" if p.get("soll") is not None else ""
                self.log(f"=== Fluke {port} ({self.fl_ident}): {art}{soll}"
                         + (f" – {p['bezeichnung']}" if p.get("bezeichnung") else "") + " ===")
                q = p.get("mm2")
                if q:                                    # MM2 Voltcraft: Fehler beenden nur MM2
                    try:
                        v = voltcraft.Voltcraft(q.get("port") or self.m2_port)
                        self.m2_ident = v.oeffnen()
                        if v.port != self.m2_port:
                            self.m2_port = v.port
                            save_settings({"mm2_port": v.port})
                        p2 = dict(p, soll=q["soll"], tol=q["tol"], bezeichnung=q["bezeichnung"])
                        self.m2_p = p2
                        sl = f", Soll {q['soll']:g} ± {q['tol']:g} mV" if q.get("soll") is not None else ""
                        self.log(f"=== MM2 {v.port} ({self.m2_ident}): nur lesen{sl}"
                                 + (f" – {q['bezeichnung']}" if q.get("bezeichnung") else "") + " ===")
                    except voltcraft.MessFehler as e:
                        self.log(f"FEHLER MM2: {e} – Messung läuft nur mit dem Fluke.")
                        if v:
                            v.schliessen()
                        v = None
                self.fl = fluke.Logger(f, p, self.log, lambda: self.fl_stop)
                self.fl.meta = {"start": fluke.jetzt_iso(), "pruefling": self.pruefling}
                if v:
                    self.m2 = fluke.Logger(v, self.m2_p, lambda t: self.log("MM2 " + t), lambda: self.fl_stop)
                    self.m2.meta = dict(self.fl.meta)

                    def m2_lauf():
                        try:
                            self.m2.laufen(lambda: None)
                        except voltcraft.MessFehler as e:
                            self.log(f"FEHLER MM2: {e} – Fluke läuft weiter.")
                    m2_thread = threading.Thread(target=m2_lauf, daemon=True)
                    m2_thread.start()
                try:
                    self.fl.laufen(lambda: None)
                finally:
                    if m2_thread:
                        if self.fl.punkte and not self.fl_stop:
                            # Fluke fertig (Dauer erreicht): MM2 hoechstens 2 Intervalle nachlaufen lassen
                            m2_thread.join(2 * float(p.get("intervall") or 1) + 1)
                        self.fl_stop = True
                        m2_thread.join(5)
                if p["modus"] == "rec":
                    self.fluke_ablegen()
                    if self.m2:
                        self.fluke_ablegen(mm2=True)
            except fluke.FlukeFehler as e:
                self.log(f"FEHLER Fluke: {e}")
            except Exception as e:
                self.log(f"FEHLER Fluke: {e}")
            finally:
                self.fl_stop = True
                if m2_thread:
                    m2_thread.join(5)
                if f:
                    f.schliessen()
                if v:
                    v.schliessen()
                with self.lock:
                    self.fl_busy = False
                self.log("Multimeter-Messung beendet." if v else "Fluke-Messung beendet.")
        threading.Thread(target=job, daemon=True).start()
        return True

    def fluke_ablegen(self, mm2=False):
        """Aufzeichnung speichern: CSV, Diagramm, Eintrag in messungen.json.
        mm2=True: dasselbe fuer MM2 (Voltcraft) als eigene Messreihe."""
        if mm2:
            lg, p, ident, port, name = self.m2, self.m2_p, self.m2_ident, self.m2_port, "MM2"
        else:
            lg, p, ident, port, name = self.fl, self.fl_p, self.fl_ident, self.fl_port, "Fluke"
        if not lg or not lg.punkte:
            self.log(f"{name}: keine Messwerte – nichts gespeichert.")
            return
        pr = lg.meta.get("pruefling")
        ziel = report.ordner(pr)
        if report.WARNUNG:
            self.log("ACHTUNG: " + report.WARNUNG)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pfad = os.path.join(ziel, f"upa_ruhe_{'mm2_' if mm2 else ''}{stamp}.csv")
        firma = load_settings().get("firma", "")
        with open(pfad, "w", encoding="utf-8", newline="") as fh:
            fh.write(f"# UPA-Software v{__version__}" + (f" · {firma}" if firma else "") + "\n")
            fh.write(f"# Multimeter: {ident} an {port}\n")
            if pr:
                fh.write(f"# Prüfling: {report.bezeichnung(pr)}\n")
            fh.write(f"# Bezeichnung: {p.get('bezeichnung', '')} · Soll: {p.get('soll')} mV ± {p.get('tol')} mV"
                     f" · Dauer: {p.get('dauer_s') or 'bis Stop'} s · Intervall: {p.get('intervall')} s\n")
            fh.write("t_s;zeit;wert_mV;im_toleranzband;hinweis\n")
            for t, v, h in lg.punkte:
                ok = lg.ok(v)
                fh.write(f"{t};{fluke.zeit_txt(t)};{'' if v is None else f'{v:.4f}'};"
                         f"{'' if ok is None else ('ja' if ok else 'nein')};{h}\n")
        if mm2:
            self.m2_csv = pfad
        else:
            self.fl_csv = pfad
        self.log(f"CSV gespeichert: {pfad}")
        if not pr:
            return
        basis = os.path.splitext(pfad)[0]
        png = None
        try:
            titel = f"{p.get('bezeichnung') or 'Ruhestrom / Offset'} – {report.bezeichnung(pr)}"
            if report.diagramm_ruhe(titel, lg.punkte, p.get("soll"), p.get("tol"), lg.marken, basis + ".png"):
                png = os.path.basename(basis + ".png")
                self.log(f"Diagramm gespeichert: {png}")
        except Exception as e:
            self.log(f"Diagramm nicht erstellt: {e}")
        ab_t = lg.marken[0]["t"] if lg.marken else 0.0      # Min/Max ab erster Zeitmarke
        stat, ende = lg.statistik(ab_t), lg.punkte[-1]
        ende_ol = ende[1] is None and lg.ist_ol(ende[2])
        ende_ok = False if ende_ol and p.get("soll") is not None else lg.ok(ende[1])
        werte = []
        for m in lg.marken:
            werte.append((f"nach {m['minute']:g} min", report.ruhe_wert(m["wert"], m["ok"], m.get("ol"))))
        werte.append((f"Endwert ({fluke.zeit_txt(ende[0])})", report.ruhe_wert(ende[1], ende_ok, ende_ol)))
        if stat:
            werte.append((f"Min / Max ab {lg.marken[0]['minute']:g} min" if lg.marken else "Min / Max",
                          report._komma(f"{stat['min']:.3f} / {stat['max']:.3f} mV")))
        if p.get("soll") is not None:
            werte.append(("Sollwert", report._komma(f"{p['soll']:g} ± {p['tol']:g} mV")))
        try:
            report.eintrag_speichern(ziel, {
                "programm": "ruhe", "name": "Ruhestrom / Offset",
                "start": lg.meta.get("start"), "ende": fluke.jetzt_iso(),
                "bezeichnung": p.get("bezeichnung", ""), "csv": os.path.basename(pfad), "png": png,
                "adapter": ident, "software": __version__,
                "parameter": {k: p.get(k) for k in ("soll", "tol", "dauer_s", "intervall", "marken_min")},
                "marken": lg.marken, "ende_wert": ende[1], "ende_t": ende[0], "ende_ol": ende_ol, "statistik": stat,
                "ergebnis": [{"kanal": p.get("bezeichnung") or "–", "werte": werte}],
                "abgebrochen": bool(p.get("dauer_s")) and ende[0] < p["dauer_s"] - 2})
        except Exception as e:
            self.log(f"messungen.json nicht aktualisiert: {e}")

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
                if prog.get("live"):
                    self.log("Live-Anzeige – nichts gespeichert.")
                else:
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
        if report.WARNUNG:
            self.log("ACHTUNG: " + report.WARNUNG)
        self.last_csv = write_csv(pts, meta, ziel)
        self.log(f"CSV gespeichert: {self.last_csv}")
        if not pr:
            return
        basis = os.path.splitext(self.last_csv)[0]
        png = None
        try:
            titel = f"{meta.get('name')} – {report.bezeichnung(pr)}"
            if report.diagramm(meta.get("prog"), titel, pts, basis + ".png",
                               (meta.get("params") or {}).get("bezug") or 315):
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
                "ergebnis": report.zusammenfassung(meta.get("prog"), pts, (meta.get("params") or {}).get("bezug")),
                "abgebrochen": any(p.get("abbruch") for p in pts) or bool(self.stop_flag)})
        except Exception as e:
            self.log(f"messungen.json nicht aktualisiert: {e}")

    def set_pruefling(self, d):
        pr = report.pruefling_pruefen(d)     # ValueError bei unvollstaendiger Eingabe
        with self.lock:
            self.pruefling = pr
        save_settings({"pruefling": pr or {}})
        if pr:
            ziel = report.ordner(pr)
            self.log(f"Prüfling: {report.bezeichnung(pr)} -> {ziel}")
            if report.WARNUNG:
                self.log("ACHTUNG: " + report.WARNUNG)
        else:
            self.log(f"Kein Prüfling - Messungen landen direkt in {paths.mess_dir()}.")

    def set_ablage(self, pfad):
        """Ablageordner pruefen (anlegen, Schreibtest) und speichern. Leer = lokal."""
        pfad = str(pfad or "").strip().strip('"')
        if pfad:
            try:
                os.makedirs(pfad, exist_ok=True)
                test = os.path.join(pfad, ".upa_schreibtest")
                with open(test, "w") as fh:
                    fh.write("ok")
                os.remove(test)
            except OSError as e:
                raise ValueError(f"Ablageordner nicht erreichbar/beschreibbar: {pfad} ({e.strerror or e})")
        paths.set_ablage(pfad)
        save_settings({"ablage": pfad})
        self.log(f"Ablageordner: {paths.mess_dir()}")


CSV_COLS = ["i", "ch", "x", "f_soll", "f", "u_soll", "u", "u_true", "p_w", "gain", "gain_db",
            "att_k", "fnct", "fnct_line", "versuche", "step", "ref_u", "ref_raw", "noise_u", "sn_db", "xt_u", "xt_db", "dir",
            "t", "dev_pct", "wf_pc", "wf_line", "ein", "abbruch", "raw"]


def validate_fluke(b):
    """Parameter fuer Ruhestrom/Offset pruefen."""
    modus = b.get("modus")
    if modus not in ("live", "rec"):
        raise ValueError("Modus live oder rec")
    def zahl(k):
        v = b.get(k)
        return None if v in (None, "") else float(v)
    soll, tol = zahl("soll"), zahl("tol")
    if soll is not None and (tol is None or tol <= 0):
        raise ValueError("Zum Sollwert bitte eine Toleranz > 0 angeben")
    if soll is None:
        tol = None
    dauer_min = zahl("dauer_min") or 0
    if dauer_min < 0 or dauer_min > 24 * 60:
        raise ValueError("Dauer 0 (bis Stop) bis 1440 min")
    intervall = zahl("intervall") or 1.0
    if not 0.5 <= intervall <= 60:
        raise ValueError("Intervall 0,5 bis 60 s")
    marken = []
    for teil in str(b.get("marken", "") or "").replace(";", ",").split(","):
        teil = teil.strip().replace(",", ".")
        if teil:
            m = float(teil)
            if m <= 0:
                raise ValueError("Zeitmarken in Minuten > 0")
            marken.append(m)
    port = str(b.get("port", "") or "").strip()
    mm2 = None
    if b.get("mm2_an") in (True, "1", 1, "true", "EIN"):
        s2, t2 = zahl("mm2_soll"), zahl("mm2_tol")
        if s2 is not None and (t2 is None or t2 <= 0):
            raise ValueError("MM2: zum Sollwert bitte eine Toleranz > 0 angeben")
        if s2 is None:
            t2 = None
        p2 = str(b.get("mm2_port", "") or "").strip()
        if len(p2) > 40 or any(c in p2 for c in '"<>|*?;&'):
            raise ValueError("Ungültiger MM2-Port")
        mm2 = {"port": p2, "soll": s2, "tol": t2,
               "bezeichnung": str(b.get("mm2_bezeichnung", "") or "").strip()[:60]}
    return {"mm2": mm2, "modus": modus, "soll": soll, "tol": tol, "dauer_s": dauer_min * 60 if modus == "rec" and dauer_min else None,
            "intervall": intervall, "marken_min": sorted(set(marken)) if modus == "rec" else [],
            "bezeichnung": str(b.get("bezeichnung", "") or "").strip()[:60], "port": port}


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


def oeffnen(pfad, drucken=False):
    """Datei/Ordner mit dem Standardprogramm oeffnen bzw. drucken (Windows)."""
    if os.name != "nt":
        return False, f"Bitte selbst öffnen: {pfad}"
    try:
        # Drucken bewusst ueber den PDF-Betrachter (Strg+P): dort Drucker und
        # Seiten waehlbar - kein stilles Drucken auf den Standarddrucker
        os.startfile(pfad)
        return True, "PDF geöffnet – mit Strg+P drucken." if drucken else ""
    except OSError as e:
        return False, f"Öffnen nicht möglich: {e}"


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


REPO_URL = "https://github.com/techniker67/UPA3-ANALYZER-CONTROL"
RELEASE_API = "https://api.github.com/repos/techniker67/UPA3-ANALYZER-CONTROL/releases/latest"


def version_tupel(v):
    """'1.4.0' -> (1, 4, 0); Unlesbares -> ()."""
    try:
        return tuple(int(x) for x in str(v).split("-")[0].split("."))
    except ValueError:
        return ()


def validate_einstellungen(b, app):
    """Einstellungen aus dem Menue pruefen. Liefert die zu speichernden Werte."""
    neu = {}
    if "firma" in b:
        neu["firma"] = " ".join(str(b.get("firma") or "").split())[:80]
    for k in ("port", "fluke_port", "mm2_port"):
        if k in b:
            v = str(b.get(k) or "").strip()
            if len(v) > 40 or any(c in v for c in '"<>|*?;&'):
                raise ValueError("Ungültiger Port: " + v)
            neu[k] = v
    if "addr" in b:
        a = int(b.get("addr"))
        if not 0 <= a <= 30:
            raise ValueError("GPIB-Adresse 0 bis 30")
        neu["addr"] = a
    if "update_pruefen" in b:
        neu["update_pruefen"] = bool(b.get("update_pruefen"))
    return neu


PEGELBEZUG_STD = 0.775     # 0 dB = 0,775 V (dBs/dBu) - Vorgabe der meisten Service-Manuals


def pegelbezug(pr):
    """Bezugspegel (V fuer 0 dB) des Prueflings, sonst zuletzt benutzter, sonst 0,775 V."""
    st = load_settings()
    je = st.get("pegelbezug") if isinstance(st.get("pegelbezug"), dict) else {}
    try:
        if pr and report.ordnername(pr) in je:
            return float(je[report.ordnername(pr)])
        return float(st.get("pegelbezug_letzt", PEGELBEZUG_STD))
    except (TypeError, ValueError):
        return PEGELBEZUG_STD


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
    if prog.get("band"):
        # Bandmessung: Quelle = Messband, Generator aus, Bereich AUTO, kein Abschwaecher
        if atten_tab or atten != 1:
            raise ValueError("Bandmessungen ohne Abschwächer (Line-Ausgang des Decks direkt an den UPA)")
        p["rng"] = "AUTO"
        dauer = _f(body, "dauer", prog["def"].get("dauer", 30))
        if not (10 <= dauer <= 3600):
            raise ValueError("Dauer 10 bis 3600 s")
        p["dauer"] = dauer
        if ui.get("sollf"):
            p["sollf"] = _f(body, "sollf", prog["def"].get("sollf", 3000))
            if not (100 <= p["sollf"] <= 20000):
                raise ValueError("Sollfrequenz 100 bis 20000 Hz")
        if ui.get("bezug"):
            p["bezug"] = _f(body, "bezug", prog["def"].get("bezug", 315))
            if not (20 <= p["bezug"] <= 20000):
                raise ValueError("Bezugsfrequenz 20 bis 20000 Hz")
        if ui.get("gen"):
            p["gen_v"] = _f(body, "gen_v", 0) or 0.0          # 0 = Generator aus (Messband)
            p["gen_f"] = _f(body, "gen_f", 1000)
            p["gen_aus"] = "LR" if body.get("gen_aus") == "LR" else "folgt"   # Generatorausgang
            if p["gen_v"] and not (LEVEL_MIN <= p["gen_v"] <= LEVEL_MAX):
                raise ValueError(f"Generatorpegel {LEVEL_MIN} bis {LEVEL_MAX} V")
            if not (FREQ_MIN <= p["gen_f"] <= FREQ_MAX):
                raise ValueError(f"Frequenz {FREQ_MIN} bis {FREQ_MAX} Hz")
        if ui.get("wfnorm"):
            p["wfnorm"] = str(body.get("wfnorm", prog["def"].get("wfnorm", "JIS")))
            if p["wfnorm"] not in progs.WF_NORMEN:
                raise ValueError("W&F-Norm DIN, NAB oder JIS")
        p["n"] = 0           # offen: endet nach Zeit, Stop oder Bandende
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
            if u.path in ("/icon.png", "/favicon.ico"):
                pfad = os.path.join(paths.RES_DIR, "assets", "icon.png" if u.path == "/icon.png" else "icon.ico")
                if os.path.exists(pfad):
                    with open(pfad, "rb") as fh:
                        return self._send(200, fh.read(), "image/png" if pfad.endswith(".png") else "image/x-icon",
                                          )
                return self._send(404, {"error": "kein Icon"})
            if u.path == "/api/state":
                since = 0
                for kv in u.query.split("&"):
                    if kv.startswith("since="):
                        try:
                            since = int(kv[6:])
                        except ValueError:
                            pass
                return self._send(200, app.state(since))
            if u.path == "/api/abgleich":
                pr = app.pruefling
                if not pr:
                    return self._send(200, {"liste": None, "pruefling": None})
                try:
                    liste, pfad = abgleich.laden(report.ordner(pr))
                except Exception as e:
                    return self._send(200, {"liste": None, "error": f"Abgleichliste fehlerhaft: {e}"})
                return self._send(200, {"liste": liste, "datei": os.path.basename(pfad) if pfad else None,
                                        "ordner": report.ordner(pr), "pruefling": pr})
            if u.path == "/api/protokoll":
                pr = app.pruefling
                if not pr:
                    return self._send(200, {"pruefling": None, "messungen": [], "dateien": []})
                ordner = report.ordner(pr)
                def kurz(e):
                    return {"csv": e["csv"], "name": protokoll.PROG_NAMEN.get(e["programm"], e.get("name")),
                            "start": e.get("start"), "abgebrochen": e.get("abgebrochen"),
                            "bezeichnung": e.get("bezeichnung", ""),
                            "kanaele": [c["kanal"] for c in e.get("ergebnis", [])]}
                ms = [kurz(e) for e in protokoll.messungen(ordner)]
                dateien = sorted(n for n in os.listdir(ordner) if n.startswith("Pruefprotokoll_"))
                korb_ms, korb_pr = protokoll.im_papierkorb(ordner)
                return self._send(200, {"pruefling": pr, "ordner": ordner, "messungen": ms,
                                        "dateien": dateien, "protokolle": protokoll.protokolle(ordner),
                                        "papierkorb": {"messungen": [kurz(e) for e in korb_ms],
                                                       "protokolle": korb_pr},
                                        "formate": protokoll.verfuegbar(),
                                        "firma": load_settings().get("firma", "")})
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
            if u.path == "/api/ablage":
                if app.beschaeftigt:
                    return self._send(409, {"error": "Während einer Messung nicht änderbar"})
                try:
                    app.set_ablage(body.get("pfad", ""))
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                return self._send(200, {"ok": True, "ablage": paths.ABLAGE})
            if u.path == "/api/pruefling":
                if app.beschaeftigt:
                    return self._send(409, {"error": "Während einer Messung nicht änderbar"})
                try:
                    app.set_pruefling(body)
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                return self._send(200, {"ok": True, "pruefling": app.pruefling})
            if u.path == "/api/protokoll":
                pr = app.pruefling
                if not pr:
                    return self._send(400, {"error": "Kein Prüfling festgelegt"})
                firma = load_settings().get("firma", "")
                if "firma" in body:          # Pruefer/Firma aus dem Dialog - wird gemerkt
                    neu = " ".join(str(body.get("firma") or "").split())[:80]
                    if neu != firma:
                        save_settings({"firma": neu})
                        app.log(f"Prüfer/Firma für Protokolle: {neu or '(ohne)'}")
                        firma = neu
                try:
                    dateien = protokoll.erstellen(report.ordner(pr), body.get("auswahl") or None,
                                                  str(body.get("bemerkung", ""))[:2000],
                                                  firma, __version__)
                except Exception as e:
                    app.log(f"Prüfprotokoll nicht erstellt: {e}")
                    return self._send(400, {"error": str(e)})
                app.log("Prüfprotokoll erstellt: " + ", ".join(dateien))
                return self._send(200, {"ok": True, "dateien": dateien})
            if u.path.startswith("/api/abgleich/"):
                pr = app.pruefling
                if not pr:
                    return self._send(400, {"error": "Erst einen Prüfling festlegen – die Abgleichliste "
                                                     "wird in seinem Ordner abgelegt"})
                ordner = report.ordner(pr)
                try:
                    if u.path == "/api/abgleich/laden":
                        liste = abgleich.pruefen(body.get("liste"))
                        alt, alt_pfad = abgleich.laden(ordner)
                        if alt and alt["ergebnisse"] and not body.get("ersetzen"):
                            return self._send(409, {"error": "Im Geräteordner liegt schon eine Abgleichliste mit "
                                                             "Ist-Werten", "frage": True})
                        if alt_pfad and os.path.basename(alt_pfad) != abgleich.dateiname(liste):
                            os.replace(alt_pfad, alt_pfad + ".alt")
                        pfad = abgleich.speichern(ordner, liste)
                        hinweis = ""
                        g = liste["geraet"]
                        if g["typ"] and g["typ"].lower() not in (pr.get("typ") or "").lower():
                            hinweis = f"Achtung: Liste ist für {g['hersteller']} {g['typ']}, Prüfling ist {pr.get('hersteller')} {pr.get('typ')}"
                        app.log(f"Abgleichliste geladen: {os.path.basename(pfad)} ({len(liste['schritte'])} Schritte)")
                        return self._send(200, {"ok": True, "liste": liste, "datei": os.path.basename(pfad),
                                                "hinweis": hinweis})
                    if u.path == "/api/abgleich/ergebnis":
                        liste = abgleich.ergebnis(ordner, body.get("nr"), body)
                        return self._send(200, {"ok": True, "liste": liste})
                    if u.path == "/api/abgleich/pdf":
                        name = abgleich.abgleichblatt(ordner, load_settings().get("firma", ""), __version__)
                        app.log("Abgleichblatt erstellt: " + name)
                        return self._send(200, {"ok": True, "datei": name})
                except (ValueError, RuntimeError, OSError) as e:
                    return self._send(400, {"error": str(e)})
                return self._send(404, {"error": "unbekannt"})
            if u.path == "/api/pegelbezug":
                # Bezugspegel des Pegelrechners (0 dB = x V) je Pruefling merken
                try:
                    v = float(body.get("v"))
                except (TypeError, ValueError):
                    return self._send(400, {"error": "Bezugspegel fehlt"})
                if not (0.001 <= v <= 100):
                    return self._send(400, {"error": "Bezugspegel 0,001 bis 100 V"})
                st = load_settings()
                je = st.get("pegelbezug") if isinstance(st.get("pegelbezug"), dict) else {}
                if app.pruefling:
                    je[report.ordnername(app.pruefling)] = v
                save_settings({"pegelbezug": je, "pegelbezug_letzt": v})
                return self._send(200, {"ok": True, "v": v})
            if u.path == "/api/papierkorb":
                # Messung/Protokoll in den Papierkorb des Geraeteordners verschieben bzw. zurueckholen
                pr = app.pruefling
                if not pr:
                    return self._send(400, {"error": "Kein Prüfling festgelegt"})
                if app.busy or app.fl_busy:
                    return self._send(409, {"error": "Während einer Messung oder Aufzeichnung nicht möglich"})
                zurueck = body.get("aktion") == "zurueck"
                try:
                    namen = protokoll.verschieben(report.ordner(pr), str(body.get("art", "")),
                                                  body.get("name"), zurueck)
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                app.log(("Aus dem Papierkorb zurückgeholt: " if zurueck else "In den Papierkorb verschoben: ")
                        + ", ".join(namen))
                return self._send(200, {"ok": True, "dateien": namen})
            if u.path == "/api/oeffnen":
                # nur Dateien im Geraeteordner bzw. der Ordner selbst; nur auf diesem Rechner
                pr = app.pruefling
                if not pr:
                    return self._send(400, {"error": "Kein Prüfling festgelegt"})
                ordner = report.ordner(pr)
                name = os.path.basename(str(body.get("datei", "")))
                ziel = os.path.join(ordner, name) if name else ordner
                if not os.path.exists(ziel):
                    return self._send(404, {"error": "Datei nicht gefunden"})
                ok, hinweis = oeffnen(ziel, drucken=bool(body.get("drucken")))
                return self._send(200 if ok else 400, {"ok": ok, "hinweis": hinweis, "error": None if ok else hinweis})
            if u.path == "/api/quit":
                grund = app.beenden_grund()
                if grund:
                    return self._send(409, {"error": grund})
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
            if u.path == "/api/menue":
                # Zurueck ins Menue (UPA-/Multimeter-Ansicht verlassen)
                grund = app.menue_grund()
                if grund:
                    return self._send(409, {"error": grund})
                return self._send(200, {"ok": True})
            if u.path == "/api/einstellungen":
                if app.beschaeftigt:
                    return self._send(409, {"error": "Während einer Messung nicht änderbar"})
                try:
                    neu = validate_einstellungen(body, app)
                    if "ablage" in body:
                        app.set_ablage(body.get("ablage") or "")
                except (ValueError, TypeError) as e:
                    return self._send(400, {"error": str(e)})
                if neu:
                    save_settings(neu)
                    if "port" in neu:
                        app.port = neu["port"]
                    if "addr" in neu:
                        app.addr = neu["addr"]
                    if "fluke_port" in neu:
                        app.fl_port = neu["fluke_port"]
                    if neu.get("mm2_port"):
                        app.m2_port = neu["mm2_port"]
                    app.log("Einstellungen gespeichert: " + ", ".join(sorted(neu)))
                return self._send(200, {"ok": True})
            if u.path == "/api/ordnerwahl":
                # Ordner im Windows-Dialog auswaehlen (nur im Programmfenster)
                if not app.ordner_waehlen:
                    return self._send(501, {"error": "Ordnerauswahl nur im Programmfenster"})
                start = str(body.get("start") or "") or paths.mess_dir()
                try:
                    pfad = app.ordner_waehlen(start)
                except Exception as e:
                    return self._send(500, {"error": f"Ordnerauswahl nicht möglich: {e}"})
                return self._send(200, {"ok": True, "pfad": pfad or ""})
            if u.path == "/api/link":
                # nur die Release-Seite des Projekts im Standardbrowser oeffnen
                ziel = (app.update or {}).get("url") or (REPO_URL + "/releases")
                if not ziel.startswith(REPO_URL):
                    return self._send(400, {"error": "Link nicht erlaubt"})
                webbrowser.open(ziel)
                return self._send(200, {"ok": True})
            if u.path == "/api/fluke/suchen":
                try:
                    port, info = app.fluke_suchen()
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                return self._send(200, {"ok": True, "port": port, "ident": info})
            if u.path == "/api/mm2/suchen":
                try:
                    port, info = app.mm2_suchen()
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                return self._send(200, {"ok": True, "port": port, "ident": info})
            if u.path == "/api/fluke/start":
                try:
                    p = validate_fluke(body)
                except (ValueError, TypeError) as e:
                    return self._send(400, {"error": str(e)})
                if not app.fluke_start(p):
                    return self._send(409, {"error": "Fluke-Messung läuft bereits"})
                return self._send(200, {"ok": True})
            if u.path == "/api/fluke/stop":
                app.fl_stop = True
                return self._send(200, {"ok": True})
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
        print("Selbsttest Protokoll:", protokoll.selbsttest(paths.data("selbsttest", "protokoll")))
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
        srv = None
        if fenster:
            app.log(f"Start: Port {a.http} belegt.")
            if window.vorhandenes_fenster_zeigen():
                app.log("Laufendes Programmfenster nach vorne geholt - kein zweiter Start.")
                return 0
            if window.frage("Die UPA-Software läuft noch im Hintergrund, aber ohne sichtbares Fenster.\n\n"
                            "Diese Instanz beenden und neu starten?"):
                app.log("Hängende Instanz ohne Fenster wird beendet.")
                window.andere_instanzen_beenden()
                for _ in range(20):                 # Port wird nach dem Beenden frei
                    time.sleep(0.25)
                    try:
                        srv = Server((a.listen, a.http), make_handler(app))
                        break
                    except OSError:
                        pass
            if srv is None:
                window.message_box("Die UPA-Software läuft bereits.\n\n"
                                   f"(Port {a.http} ist belegt. Im Task-Manager unter „Details“ "
                                   "kann „UPA-Analyzer-Control.exe“ beendet werden.)")
                return 0
        else:
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
    app.update_pruefen()          # im Hintergrund, ohne Internet einfach kein Hinweis
    if fenster:
        # Server im Hintergrund, Programmfenster im Hauptthread (so verlangt es pywebview)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        app.log("Oberflaeche im Programmfenster.")
        if window.run(app, url, f"{window.TITEL_ANFANG}  v{__version__}", paths.cache_dir("webview")):
            # Fenster zu (X oder QUIT) -> Software beenden
            app.aufraeumen()
            srv.shutdown()
            srv.server_close()
            app.log("Software beendet.")
            print("  UPA-Software beendet.")
            try:
                sys.stdout and sys.stdout.flush()
            except Exception:
                pass
            # Hart beenden: Reste des Fenster-Unterbaus (WebView2/.NET) duerfen den
            # Prozess nicht unsichtbar am Leben halten (sonst "Port belegt" beim naechsten Start).
            os._exit(0)
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
    app.aufraeumen()
    srv.server_close()
    app.log("Software beendet.")
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
