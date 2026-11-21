# Neue Version veröffentlichen (für den Maintainer)

1. Änderung als Pull Request übernehmen. Darin sind `upa_version.py` (`__version__`, `DATUM`) und `CHANGELOG.md` bereits angepasst.
2. Auf GitHub: **Actions → Windows-Installer → Run workflow**
   - Branch: `main`
   - Haken bei **„Release mit Setup.exe veroeffentlichen"**
   - **Run workflow** klicken
3. Nach ca. 3 Minuten steht unter **Releases** die neue Version `v<Version>` mit der Setup.exe.

Der Bau wird vor der Veröffentlichung automatisch getestet (Start, Oberfläche, Version, QUIT). Schlägt ein Test fehl, entsteht kein Release.
Versionen 0.x waren als *Pre-release* markiert; ab 1.0.0 sind Releases reguläre Versionen.
