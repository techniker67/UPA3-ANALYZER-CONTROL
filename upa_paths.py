"""Speicherorte der UPA-Software.

Programmdateien (Code, index.html) und Benutzerdaten liegen getrennt, damit ein
Update oder eine Neuinstallation keine Einstellungen, Kalibrierungen oder
Messungen ueberschreibt.

  Programmordner  PROG_DIR   Code, index.html (bei der .exe: entpackte Ressourcen)
  Datenordner     DATA_DIR   upa_einstellungen.json, p78_kalibrierung.json,
                             upa_log.txt, Messungen/, eigene MP3

Datenordner (in dieser Reihenfolge):
  1. Startoption  --data <Ordner>
  2. Umgebungsvariable  UPA_DATA
  3. Datei "portable" im Programmordner  -> Programmordner selbst (USB-Stick)
  4. Standard: <Dokumente>/UPA-Analyzer-Control
"""
import os
import shutil
import sys

APP_NAME = "UPA-Analyzer-Control"

# Programmordner; bei einer mit PyInstaller gebauten .exe liegen die
# mitgelieferten Dateien (index.html) im Entpackordner sys._MEIPASS.
PROG_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, "frozen", False) else __file__))
RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

# Dateien, die beim ersten Start aus dem alten Programmordner uebernommen werden
UEBERNAHME = ["upa_einstellungen.json", "p78_kalibrierung.json"]


def documents_dir():
    """Dokumente-Ordner des Benutzers (Windows: auch wenn nach OneDrive umgeleitet)."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_PERSONAL = 5 (Eigene Dokumente), SHGFP_TYPE_CURRENT = 0
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
                return buf.value
        except Exception:
            pass
    for name in ("Documents", "Dokumente"):
        p = os.path.join(os.path.expanduser("~"), name)
        if os.path.isdir(p):
            return p
    return os.path.expanduser("~")


def default_data_dir():
    if os.environ.get("UPA_DATA"):
        return os.environ["UPA_DATA"]
    if os.path.exists(os.path.join(PROG_DIR, "portable")):
        return PROG_DIR
    return os.path.join(documents_dir(), APP_NAME)


DATA_DIR = default_data_dir()


def set_data_dir(path):
    """Datenordner festlegen (Startoption --data)."""
    global DATA_DIR
    DATA_DIR = os.path.abspath(os.path.expanduser(path))


def data(*teile):
    """Pfad im Datenordner."""
    return os.path.join(DATA_DIR, *teile)


def cache_dir(name):
    """Interne Zwischenspeicher (z. B. Programmfenster) - nicht im Datenordner,
    damit dort nur Dateien des Benutzers liegen. Windows: %LOCALAPPDATA%."""
    basis = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and basis and DATA_DIR != PROG_DIR:
        return os.path.join(basis, APP_NAME, name)
    return data(name)


def mess_dir():
    return data("Messungen")


def prepare():
    """Datenordner anlegen und beim ersten Start Einstellungen/Kalibrierung aus
    dem Programmordner KOPIEREN (Originale bleiben unveraendert liegen).
    Liefert eine Liste von Meldungen fuer das Protokoll."""
    meldungen = []
    os.makedirs(mess_dir(), exist_ok=True)
    if os.path.normcase(os.path.abspath(DATA_DIR)) == os.path.normcase(os.path.abspath(PROG_DIR)):
        return meldungen
    for name in UEBERNAHME:
        alt, neu = os.path.join(PROG_DIR, name), data(name)
        if os.path.isfile(alt) and not os.path.exists(neu):
            shutil.copy2(alt, neu)
            meldungen.append(f"Uebernommen: {name} -> {DATA_DIR}")
    return meldungen
