"""Eigenes Programmfenster fuer die Oberflaeche (pywebview).

Unter Windows nutzt pywebview den eingebauten Edge-WebView2 - dieselbe Technik
wie der Edge-Browser, nur ohne Adressleiste und Tabs. Ist pywebview nicht
installiert oder startet das Fenster nicht, laeuft die Software wie bisher im
Browser weiter (siehe upa_server.main).

Fenster: startet maximiert in der Bildschirmaufloesung, frei veraenderbar,
Zoom mit Strg + Mausrad bzw. Strg +/-/0. Schliessen (X) waehrend einer
Messung bzw. Fluke-Aufzeichnung wird abgelehnt - erst Stop.
"""
import os
import sys
import threading

try:
    import webview
except Exception:          # nicht installiert oder Plattform ohne Unterbau
    webview = None


def available():
    return webview is not None


def message_box(text, title="UPA-Analyzer-Control"):
    """Meldung auch ohne Konsole sichtbar machen (installierte Fenster-Version)."""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(text), title, 0x40)   # MB_ICONINFORMATION
            return
        except Exception:
            pass
    print(text)


def frage(text, title="UPA-Analyzer-Control"):
    """Ja/Nein-Frage ohne Konsole. Liefert True bei Ja (ausserhalb Windows: False)."""
    if os.name == "nt":
        try:
            import ctypes
            return ctypes.windll.user32.MessageBoxW(None, str(text), title, 0x24) == 6  # YESNO|QUESTION
        except Exception:
            pass
    print(text)
    return False


TITEL_ANFANG = "UPA·3 // Analyzer Control"      # Fenstertitel ohne Versionsnummer
MM_TITEL = "UPA·3 // Multimeter – Ruhestrom · Offset"


def vorhandenes_fenster_zeigen(titel_anfang=TITEL_ANFANG):
    """Laeuft die Software schon mit sichtbarem Fenster, dieses nach vorne holen.
    Liefert True, wenn ein Fenster gefunden wurde."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        gefunden = []
        PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def pruefen(hwnd, _):
            n = u32.GetWindowTextLengthW(hwnd)
            if n and u32.IsWindowVisible(hwnd):
                buf = ctypes.create_unicode_buffer(n + 1)
                u32.GetWindowTextW(hwnd, buf, n + 1)
                if buf.value.startswith(titel_anfang):
                    gefunden.append(hwnd)
                    return False
            return True
        u32.EnumWindows(PROC(pruefen), 0)
        if not gefunden:
            return False
        hwnd = gefunden[0]
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, 9)                 # SW_RESTORE
        u32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def andere_instanzen_beenden():
    """Haengende Instanz ohne Fenster beenden: alle Prozesse mit demselben
    Programmnamen ausser diesem. Nur in der installierten Version."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return False
    try:
        import subprocess
        exe = os.path.basename(sys.executable)
        r = subprocess.run(["taskkill", "/F", "/IM", exe, "/FI", f"PID ne {os.getpid()}"],
                           capture_output=True, timeout=10, creationflags=0x08000000)   # CREATE_NO_WINDOW
        return r.returncode == 0
    except Exception:
        return False


APP_ID = "VintageAudioRepair.UPAAnalyzerControl"   # gleich wie in packaging/installer.iss


def _app_id():
    """Windows: eigene AppUserModelID - die Taskleiste ordnet das Fenster dann der
    Startmenue-Verknuepfung (mit unserem Icon) zu statt python.exe/pythonw.exe."""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass


def _icon_setzen(title):
    """Windows: Fenster-Icon (Titelleiste, Taskleiste, Alt+Tab) direkt aus
    assets/icon.ico setzen - pywebview setzt sonst sein eigenes/Standard-Icon."""
    if os.name != "nt":
        return
    try:
        import ctypes
        import upa_paths as paths
        ico = os.path.join(paths.RES_DIR, "assets", "icon.ico")
        if not os.path.exists(ico):
            return
        u32 = ctypes.windll.user32
        u32.FindWindowW.restype = ctypes.c_void_p
        u32.LoadImageW.restype = ctypes.c_void_p
        u32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        hwnd = None
        for _ in range(50):                 # Fenster kann einen Moment brauchen
            hwnd = u32.FindWindowW(None, title)
            if hwnd:
                break
            import time
            time.sleep(0.1)
        if not hwnd:
            return
        WM_SETICON, ICON_SMALL, ICON_BIG, IMAGE_ICON, LR_LOADFROMFILE = 0x80, 0, 1, 1, 0x10
        GCLP_HICON, GCLP_HICONSM = -14, -34
        setclass = getattr(u32, "SetClassLongPtrW", None) or u32.SetClassLongW
        setclass.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        import time
        for durchgang in range(3):          # nochmals, falls der Unterbau sein Icon spaeter setzt
            for art, klasse, metrik in ((ICON_BIG, GCLP_HICON, (11, 12)),        # SM_CXICON
                                        (ICON_SMALL, GCLP_HICONSM, (49, 50))):   # SM_CXSMICON
                cx, cy = u32.GetSystemMetrics(metrik[0]), u32.GetSystemMetrics(metrik[1])
                if art == ICON_BIG:
                    cx, cy = max(cx, 48), max(cy, 48)      # Taskleiste bei hoher Skalierung
                h = u32.LoadImageW(None, ico, IMAGE_ICON, cx, cy, LR_LOADFROMFILE)
                if h:
                    u32.SendMessageW(hwnd, WM_SETICON, art, h)
                    setclass(hwnd, klasse, h)
            time.sleep(1.0)
    except Exception:
        pass


def run(app, url, title, storage_dir):
    """Fenster oeffnen und blockieren, bis es geschlossen ist.
    Liefert True, wenn das Fenster lief; False, wenn es nicht startete
    (dann soll der Aufrufer auf den Browser ausweichen)."""
    if webview is None:
        return False
    _app_id()
    win = webview.create_window(
        title, url,
        width=1600, height=900, min_size=(1100, 700),
        maximized=True, resizable=True, zoomable=True, text_select=True,
        background_color="#01050a")

    def on_closing():
        grund = app.beenden_grund()
        if grund:
            # Hinweis im Fenster anzeigen (nicht aus dem GUI-Thread heraus warten)
            import json
            threading.Thread(target=lambda: win.evaluate_js(f"alert({json.dumps(grund)})"),
                             daemon=True).start()
            return False          # Schliessen abbrechen
        app.log("Programmfenster wird geschlossen.")
        return True

    def on_shown():
        app.log("Programmfenster angezeigt.")
        threading.Thread(target=_icon_setzen, args=(title,), daemon=True).start()

    # Multimeter-Fenster (hoechstens eines). "versteckt": Hauptfenster ist im
    # Nur-Multimeter-Betrieb ausgeblendet; "ende": Software wird beendet.
    mm = {"win": None, "versteckt": False, "ende": False}

    def haupt_zeigen():
        """Hauptfenster (wieder) anzeigen und nach vorne holen."""
        if mm["ende"]:
            return
        if mm["versteckt"]:
            mm["versteckt"] = False
            try:
                win.show()
            except Exception:
                pass
            app.log("Hauptfenster wieder angezeigt.")
        try:
            win.restore()
        except Exception:
            pass
        import time
        time.sleep(0.2)
        vorhandenes_fenster_zeigen(TITEL_ANFANG)

    def mm_oeffnen(haupt_verbergen=False):
        w = mm["win"]
        if w is not None:            # schon offen -> nach vorne holen
            try:
                w.restore()
            except Exception:
                pass
            vorhandenes_fenster_zeigen(MM_TITEL)
            if haupt_verbergen and not mm["versteckt"]:
                mm["versteckt"] = True
                win.hide()
            return
        w = webview.create_window(
            MM_TITEL, url.rstrip("/") + "/?ansicht=multimeter",
            width=1100, height=820, min_size=(640, 560),
            resizable=True, zoomable=True, text_select=True, background_color="#01050a")

        def mm_closing():
            grund = app.mm_schliessen_grund()
            if grund:
                import json
                threading.Thread(target=lambda: w.evaluate_js(f"alert({json.dumps(grund)})"),
                                 daemon=True).start()
                return False
            app.mm_beenden()
            return True

        def mm_closed():
            mm["win"] = None
            app.log("Multimeter-Fenster geschlossen.")
            # Sicherheitsnetz: ein ausgeblendetes Hauptfenster kommt immer zurueck,
            # damit nie ein Prozess ohne sichtbares Fenster uebrig bleibt
            threading.Thread(target=haupt_zeigen, daemon=True).start()

        def mm_shown():
            app.log("Multimeter-Fenster angezeigt.")
            threading.Thread(target=_icon_setzen, args=(MM_TITEL,), daemon=True).start()
        w.events.closing += mm_closing
        w.events.closed += mm_closed
        w.events.shown += mm_shown
        mm["win"] = w
        if haupt_verbergen:          # Nur-Multimeter-Betrieb: Hauptfenster ausblenden
            mm["versteckt"] = True
            app.log("Nur-Multimeter-Betrieb: Hauptfenster ausgeblendet.")
            win.hide()

    def uebersicht():
        """ÜBERSICHT im Multimeter-Fenster: Hauptfenster zeigen; Multimeter-Fenster
        schliessen, ausser waehrend einer Aufzeichnung (dann bleibt es offen)."""
        if app.mm_schliessen_grund():
            haupt_zeigen()
            return False
        app.mm_beenden()
        if mm["win"] is not None:
            mm["win"].destroy()      # mm_closed holt das Hauptfenster zurueck
        else:
            haupt_zeigen()
        return True

    def mm_zu():
        w = mm["win"]
        if w is not None:
            w.destroy()

    def alles_zu():                  # QUIT: Multimeter-Fenster und Hauptfenster
        mm["ende"] = True
        mm_zu()
        win.destroy()

    def on_closed():                 # Hauptfenster zu -> Multimeter-Fenster mit schliessen
        mm["ende"] = True
        threading.Thread(target=mm_zu, daemon=True).start()

    win.events.closing += on_closing
    win.events.closed += on_closed
    win.events.shown += on_shown
    app.on_quit = alles_zu        # QUIT in der Oberflaeche schliesst alle Fenster
    app.fenster_oeffnen = mm_oeffnen
    app.fenster_schliessen = mm_zu
    app.fenster_uebersicht = uebersicht

    gui = "edgechromium" if os.name == "nt" else None   # unter Windows nie den alten IE-Unterbau
    try:
        os.makedirs(storage_dir, exist_ok=True)
        webview.start(gui=gui, private_mode=False, storage_path=storage_dir)
    except Exception as e:
        app.on_quit = app.fenster_oeffnen = app.fenster_schliessen = app.fenster_uebersicht = None
        app.log(f"Programmfenster nicht verfuegbar ({e}) - Oberflaeche im Browser.")
        return False
    return True
