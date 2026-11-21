# Third-party notices

UPA-Analyzer-Control itself is licensed under the [MIT License](LICENSE).
The Windows setup additionally contains the following open-source components, distributed unmodified. Their licenses apply to the respective component.

| Component | Purpose | License |
|---|---|---|
| [Python](https://www.python.org/) runtime | program runtime | Python Software Foundation License 2.0 |
| [pyserial](https://github.com/pyserial/pyserial) | serial port (GPIB adapter) | BSD-3-Clause |
| [pywebview](https://github.com/r0x0r/pywebview) | program window | BSD-3-Clause |
| [pythonnet](https://github.com/pythonnet/pythonnet), [clr-loader](https://github.com/pythonnet/clr-loader) | Windows window toolkit for pywebview | MIT |
| [matplotlib](https://matplotlib.org/) | charts | Matplotlib License (PSF-based) |
| [NumPy](https://numpy.org/) | numerics for matplotlib | BSD-3-Clause |
| [Pillow](https://python-pillow.org/) | images | MIT-CMU (HPND) |
| [reportlab](https://www.reportlab.com/opensource/) | PDF test report | BSD-3-Clause |
| [python-docx](https://github.com/python-openxml/python-docx) | DOCX test report | MIT |
| [lxml](https://lxml.de/) | XML for python-docx | BSD-3-Clause |
| [contourpy](https://github.com/contourpy/contourpy), [cycler](https://github.com/matplotlib/cycler), [fonttools](https://github.com/fonttools/fonttools), [kiwisolver](https://github.com/nucleic/kiwi), [packaging](https://github.com/pypa/packaging), [pyparsing](https://github.com/pyparsing/pyparsing), [python-dateutil](https://github.com/dateutil/dateutil), [six](https://github.com/benjaminp/six) | dependencies of matplotlib | BSD-3-Clause / MIT / Apache-2.0 / BSD |
| [DejaVu fonts](https://dejavu-fonts.github.io/) (via matplotlib) | fallback font | Bitstream Vera / DejaVu License |
| [PyInstaller](https://pyinstaller.org/) bootloader | program start | GPL-2.0 with bootloader exception |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | installer | Inno Setup License |

Not included, but used at runtime if present: Microsoft Edge WebView2 Runtime (part of Windows) and the Calibri font (part of Windows/Office).
