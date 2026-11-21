"""Erzeugt packaging/version_info.txt fuer PyInstaller (--version-file).
Damit traegt die .exe Produktname, Version und Herausgeber in den
Datei-Eigenschaften - Voraussetzung fuer signierte Releases (SignPath).
Aufruf im Workflow: python packaging/version_info.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from upa_version import __version__  # noqa: E402

teile = [int(x) for x in __version__.split(".")[:3]] + [0]
tup = tuple(teile[:4])
text = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040704b0', [
      StringStruct('CompanyName', 'Vintage Audio Repair Magdeburg'),
      StringStruct('FileDescription', 'UPA-Analyzer-Control'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', 'UPA-Analyzer-Control'),
      StringStruct('LegalCopyright', '(c) 2026 Vintage Audio Repair Magdeburg - MIT License'),
      StringStruct('OriginalFilename', 'UPA-Analyzer-Control.exe'),
      StringStruct('ProductName', 'UPA-Analyzer-Control'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [0x0407, 1200])])
  ]
)
"""
ziel = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_info.txt")
with open(ziel, "w", encoding="utf-8") as fh:
    fh.write(text)
print("version_info.txt:", __version__)
