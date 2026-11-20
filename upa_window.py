"""Eigenes Programmfenster fuer die Oberflaeche (pywebview).

Unter Windows nutzt pywebview den eingebauten Edge-WebView2 - dieselbe Technik
wie der Edge-Browser, nur ohne Adressleiste und Tabs. Ist pywebview nicht
installiert oder startet das Fenster nicht, laeuft die Software wie bisher im
Browser weiter (siehe upa_server.main).

Fenster: startet maximiert in der Bildschirmaufloesung, frei veraenderbar,
Zoom mit Strg + Mausrad bzw. Strg +/-/0. Schliessen (X) waehrend einer
Messung wird abgelehnt - erst Stop.
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


def run(app, url, title, storage_dir):
    """Fenster oeffnen und blockieren, bis es geschlossen ist.
    Liefert True, wenn das Fenster lief; False, wenn es nicht startete
    (dann soll der Aufrufer auf den Browser ausweichen)."""
    if webview is None:
        return False
    win = webview.create_window(
        title, url,
        width=1600, height=900, min_size=(1100, 700),
        maximized=True, resizable=True, zoomable=True, text_select=True,
        background_color="#01050a")

    def on_closing():
        if app.busy:
            # Hinweis im Fenster anzeigen (nicht aus dem GUI-Thread heraus warten)
            threading.Thread(target=lambda: win.evaluate_js(
                'alert("Bitte erst die laufende Messung stoppen.")'), daemon=True).start()
            return False          # Schliessen abbrechen
        return True

    win.events.closing += on_closing
    app.on_quit = win.destroy     # QUIT in der Oberflaeche schliesst das Fenster

    gui = "edgechromium" if os.name == "nt" else None   # unter Windows nie den alten IE-Unterbau
    try:
        os.makedirs(storage_dir, exist_ok=True)
        webview.start(gui=gui, private_mode=False, storage_path=storage_dir)
    except Exception as e:
        app.on_quit = None
        app.log(f"Programmfenster nicht verfuegbar ({e}) - Oberflaeche im Browser.")
        return False
    return True
