"""Versionsnummer der UPA-Software (einzige Stelle, an der sie gepflegt wird).

Schema MAJOR.MINOR.PATCH (Semantic Versioning):
  PATCH  +1  Fehlerkorrektur / kleine Anzeige-Aenderung, keine neue Funktion
  MINOR  +1  neue Funktion oder neues Messprogramm (PATCH zurueck auf 0)
  MAJOR  1   erste oeffentliche GitHub-Version (Messungen + DOCX-Protokoll komplett)
Aenderungen stehen in CHANGELOG.md.
"""
__version__ = "1.3.1"
DATUM = "2026-11-21"

# Adapter-Firmware, mit der alle Messprogramme am Geraet getestet wurden.
# Andere Versionen laufen, erzeugen aber einen Hinweis im Protokoll.
GETESTETE_FIRMWARE = ["0.53.26 (JW)"]
