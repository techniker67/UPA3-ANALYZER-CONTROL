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


def ist_maximiert(titel):
    """Windows: True/False, ob das Fenster mit genau diesem Titel maximiert ist; None = unbekannt."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        import time
        u32 = ctypes.windll.user32
        u32.FindWindowW.restype = ctypes.c_void_p
        u32.IsZoomed.argtypes = [ctypes.c_void_p]
        for _ in range(30):
            hwnd = u32.FindWindowW(None, titel)
            if hwnd:
                return bool(u32.IsZoomed(hwnd))
            time.sleep(0.1)
    except Exception:
        pass
    return None


def _zustand_loggen(app, name, titel):
    import time
    time.sleep(1.0)
    z = ist_maximiert(titel)
    if z is not None:
        app.log(f"{name}: {'maximiert' if z else 'NICHT maximiert'}.")


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
        u32.ShowWindow(hwnd, 3)                     # SW_MAXIMIZE (auch aus der Taskleiste)
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

    zustand = {"ende": False}        # True: Beenden ist bestaetigt (QUIT im Menue)

    def on_closing():
        if zustand["ende"]:
            app.log("Programmfenster wird geschlossen.")
            return True
        import json
        grund = app.beenden_grund()
        # Nicht aus dem GUI-Thread heraus warten: Hinweis bzw. Rueckfrage im Fenster
        js = f"alert({json.dumps(grund)})" if grund else "xBeenden()"
        threading.Thread(target=lambda: win.evaluate_js(js), daemon=True).start()
        return False              # X schliesst nicht direkt - erst Rueckfrage im Fenster

    def on_shown():
        app.log("Programmfenster angezeigt.")
        threading.Thread(target=_icon_setzen, args=(title,), daemon=True).start()
        threading.Thread(target=_zustand_loggen, args=(app, "Hauptfenster", title), daemon=True).start()

    def beenden():                   # QUIT (Menue oder bestaetigtes X)
        zustand["ende"] = True
        win.destroy()

    win.events.closing += on_closing
    win.events.shown += on_shown
    app.on_quit = beenden

    gui = "edgechromium" if os.name == "nt" else None   # unter Windows nie den alten IE-Unterbau
    try:
        os.makedirs(storage_dir, exist_ok=True)
        webview.start(gui=gui, private_mode=False, storage_path=storage_dir)
    except Exception as e:
        app.on_quit = None
        app.log(f"Programmfenster nicht verfuegbar ({e}) - Oberflaeche im Browser.")
        return False
    return True
