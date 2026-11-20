"""Pruefprotokoll aus dem Geraeteordner: PDF (reportlab) und DOCX (python-docx).

Ablauf:  messungen.json + CSV + PNG  ->  Inhalt (Bloecke)  ->  PDF / DOCX
Beide Ausgaben entstehen aus derselben Blockliste und sind damit inhaltsgleich.

Bloecke:  ("titel", text) ("h1", text) ("h2", text) ("p", text) ("klein", text)
          ("kv", [(Name, Wert), ...])  ("tabelle", kopf, zeilen, spaltenanteile)
          ("bild", pfad)  ("unterschrift", None)
"""
import csv
import json
import math
import os
from datetime import datetime

import upa_report as report

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)
except Exception:
    A4 = None

try:
    import docx
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
except Exception:
    docx = None

PROG_NAMEN = {"fr": "Frequenzgang", "gain": "Pegel / Verstärkung", "thdf": "THD+N über Frequenz",
              "thdl": "THD+N über Pegel", "sn": "Störabstand (unbewertet)", "xt": "Kanaltrennung"}
AKZENT = "#1f5fbf"


def verfuegbar():
    return {"pdf": A4 is not None, "docx": docx is not None}


# ---------------------------------------------------------------------------
# Daten lesen
def _zahl(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except ValueError:
        return v


def lese_csv(pfad):
    with open(pfad, encoding="utf-8") as fh:
        zeilen = [z for z in fh if not z.startswith("#")]
    return [{k: _zahl(v) for k, v in r.items()} for r in csv.DictReader(zeilen, delimiter=";")]


def messungen(ordner):
    """Eintraege aus messungen.json, deren CSV noch vorhanden ist (aelteste zuerst)."""
    try:
        with open(os.path.join(ordner, "messungen.json"), encoding="utf-8") as fh:
            liste = json.load(fh)
    except Exception:
        return []
    return [e for e in liste if os.path.exists(os.path.join(ordner, e.get("csv", "")))]


def geraet(ordner):
    with open(os.path.join(ordner, "geraet.json"), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Formatierung (deutsch)
def k(v, fmt="{:.4g}"):
    if v is None or v == "":
        return "–"
    if isinstance(v, str):
        return v
    return report._komma(fmt.format(v))


def f_hz(f):
    """Frequenz auf 4 Stellen (gemessene Werte wie 49,999 Hz -> 50 Hz)."""
    if not f:
        return "–"
    f = float(f"{f:.4g}")
    return report._komma(report._fmt_f(f))


def db(v, fmt="{:+.2f}"):
    """dB-Wert ohne '-0,00'."""
    if v is None:
        return "–"
    return k(round(v, 2) + 0.0, fmt)


def u_v(u):
    return report._komma(report._fmt_u(u)) if u is not None else "–"


def _datum(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso or "–"


def einstellungen(e):
    p = e.get("parameter", {})
    teile = []
    if e["programm"] == "thdl":
        lv = p.get("levels") or []
        if lv:
            teile.append(f"Generator {u_v(lv[0])} … {u_v(lv[-1])}, {len(lv)} Stufen, {f_hz(p.get('fixfreq'))}")
    elif e["programm"] in ("gain", "sn"):
        teile.append(f"Generator {u_v(p.get('level'))}, {f_hz(p.get('fixfreq'))}")
    else:
        teile.append(f"Generator {u_v(p.get('level'))}")
    filt = [n for key, n in (("lp22", "TP 22 kHz"), ("hp22", "HP 22 Hz")) if p.get(key)]
    teile.append("Filter " + (" + ".join(filt) if filt else "aus"))
    teile.append(f"Bereich {p.get('rng', 'AUTO')}")
    att = p.get("atten")
    teile.append("Abschwächer P78 (kalibriert)" if att == "p78" else
                 f"Abschwächer {k(att, '{:g}')}:1" if att not in (None, 1, 1.0) else "ohne Abschwächer")
    if p.get("load"):
        teile.append(f"Last {k(p['load'], '{:g}')} Ω")
    return " · ".join(teile)


def werte_tabelle(prog, pts):
    """Kopf, Zeilen, Spaltenanteile fuer die Messwert-Tabelle."""
    pts = [p for p in pts if not p.get("abbruch")]
    kan = lambda p: p.get("dir") or p.get("ch")
    if prog == "fr":
        ref = {}
        for c in {kan(p) for p in pts}:
            ok = [p for p in pts if kan(p) == c and p.get("u_true")]
            if ok:
                ref[c] = report._ref_1k(ok)["u_true"]
        z = [[kan(p), f_hz(p.get("f") or p.get("x")), u_v(p.get("u_true")),
              db(20 * math.log10(p["u_true"] / ref[kan(p)])) if p.get("u_true") and kan(p) in ref else "–"]
             for p in pts]
        return ["Kanal", "Frequenz", "Pegel", "re 1 kHz (dB)"], z, [1, 2, 2, 2]
    if prog == "gain":
        z = [[kan(p), f_hz(p.get("f") or p.get("x")), u_v(p.get("u_soll")), u_v(p.get("u_true")),
              db(p.get("gain_db")), k(p.get("p_w"), "{:.3g}")] for p in pts]
        return ["Kanal", "Frequenz", "Generator", "Ausgang", "Verstärkung (dB)", "Leistung (W)"], z, [1, 1.5, 1.5, 1.5, 2, 1.7]
    if prog == "thdf":
        z = [[kan(p), f_hz(p.get("x")), u_v(p.get("u_true")), k(p.get("fnct")),
              k(20 * math.log10(p["fnct"] / 100), "{:.1f}") if p.get("fnct") else "–"] for p in pts]
        return ["Kanal", "Frequenz", "Pegel", "THD+N (%)", "THD+N (dB)"], z, [1, 1.6, 1.6, 1.6, 1.6]
    if prog == "thdl":
        z = [[kan(p), u_v(p.get("x")), u_v(p.get("u_true")), k(p.get("fnct")),
              k(p.get("p_w"), "{:.3g}")] for p in pts]
        return ["Kanal", "Generator", "Ausgang", "THD+N (%)", "Leistung (W)"], z, [1, 1.6, 1.6, 1.6, 1.6]
    if prog == "sn":
        z = [[kan(p), u_v(p.get("ref_u")), u_v(p.get("noise_u")), k(p.get("sn_db"), "{:.1f}")] for p in pts]
        return ["Kanal", "Bezugspegel", "Rauschen", "Störabstand (dB)"], z, [1, 2, 2, 2]
    if prog == "xt":
        z = [[kan(p), f_hz(p.get("x")), u_v(p.get("ref_u")), u_v(p.get("xt_u")), k(p.get("xt_db"), "{:.1f}")]
             for p in pts]
        return ["Richtung", "Frequenz", "Bezugspegel", "Übersprechen", "dB"], z, [1.3, 1.5, 1.7, 1.7, 1.2]
    return ["Kanal", "x", "Wert"], [[kan(p), k(p.get("x")), u_v(p.get("u_true"))] for p in pts], [1, 2, 2]


# ---------------------------------------------------------------------------
# Inhalt
def inhalt(ordner, auswahl=None, bemerkung="", firma=""):
    g = geraet(ordner)
    alle = messungen(ordner)
    ms = [e for e in alle if not auswahl or e["csv"] in auswahl]
    if not ms:
        raise ValueError("Keine Messungen ausgewählt")
    adapter = next((e.get("adapter") for e in reversed(ms) if e.get("adapter")), "–")
    software = ms[-1].get("software", "")
    tage = sorted({_datum(e.get("start"))[:10] for e in ms})
    b = [("titel", "Prüfprotokoll Audiomessung"),
         ("p", f"{g['hersteller']} {g['typ']} · Seriennummer {g['seriennr']}"),
         ("h1", "Prüfling und Messsystem"),
         ("kv", [("Hersteller", g["hersteller"]), ("Typ / Modell", g["typ"]),
                 ("Seriennummer", g["seriennr"]), ("Prüfdatum", ", ".join(tage)),
                 ("Prüfer", firma or "–"),
                 ("Messsystem", "R&S UPA Audioanalysator, AR488-GPIB-Adapter"),
                 ("Adapter-Firmware", adapter),
                 ("Software", f"UPA-Analyzer-Control v{software}")]),
         ("h1", "Ergebnisübersicht")]
    z = []
    for e in ms:
        name = PROG_NAMEN.get(e["programm"], e.get("name"))
        erste = True
        for c in e.get("ergebnis", []):
            for i, (n, w) in enumerate(c["werte"]):
                z.append([name if erste else "", c["kanal"] if i == 0 else "", n, w])
                erste = False
    b.append(("tabelle", ["Messung", "Kanal", "Größe", "Ergebnis"], z, [2.4, 0.9, 2.2, 3.2]))
    for n, e in enumerate(ms, 1):
        prog = e["programm"]
        pts = lese_csv(os.path.join(ordner, e["csv"]))
        b.append(("h1", f"{n}. {PROG_NAMEN.get(prog, e.get('name'))}"))
        zeile = f"{_datum(e.get('start'))} · {einstellungen(e)}"
        if e.get("bezeichnung"):
            zeile += f" · {e['bezeichnung']}"
        if e.get("abgebrochen"):
            zeile += " · ABGEBROCHEN"
        b.append(("klein", zeile))
        if e.get("png") and os.path.exists(os.path.join(ordner, e["png"])):
            b.append(("bild", os.path.join(ordner, e["png"])))
        kopf, zeilen, ant = werte_tabelle(prog, pts)
        b.append(("tabelle", kopf, zeilen, ant))
        b.append(("klein", f"Messdatei: {e['csv']}"))
    if bemerkung.strip():
        b += [("h1", "Bemerkung"), ("p", bemerkung.strip())]
    b.append(("unterschrift", None))
    return g, b


def dateiname(g):
    return (f"Pruefprotokoll_{report.ordnername(g)}_"
            f"{datetime.now().strftime('%Y%m%d-%H%M')}")


def erstellen(ordner, auswahl=None, bemerkung="", firma="", version=""):
    """PDF und DOCX schreiben (soweit die Bibliotheken da sind). Liefert Dateinamen."""
    g, bl = inhalt(ordner, auswahl, bemerkung, firma)
    basis = os.path.join(ordner, dateiname(g))
    fuss = f"{firma + ' · ' if firma else ''}Prüfprotokoll {g['hersteller']} {g['typ']} SN {g['seriennr']} · UPA-Analyzer-Control v{version}"
    out = []
    if A4 is not None:
        pdf(bl, basis + ".pdf", fuss)
        out.append(os.path.basename(basis + ".pdf"))
    if docx is not None:
        als_docx(bl, basis + ".docx", fuss)
        out.append(os.path.basename(basis + ".docx"))
    if not out:
        raise RuntimeError("Weder reportlab (PDF) noch python-docx (DOCX) installiert")
    return out


# ---------------------------------------------------------------------------
# PDF
_FONT = None


def _schrift():
    """DejaVu Sans (liegt matplotlib bei) – kann µ, Ω, →, – usw."""
    global _FONT
    if _FONT:
        return _FONT
    try:
        import matplotlib
        d = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
        pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(d, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(d, "DejaVuSans-Bold.ttf")))
        _FONT = ("DejaVu", "DejaVu-Bold")
    except Exception:
        _FONT = ("Helvetica", "Helvetica-Bold")
    return _FONT


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pdf(bl, pfad, fuss):
    f, fb = _schrift()
    akz = colors.HexColor(AKZENT)
    st = {
        "titel": ParagraphStyle("t", fontName=fb, fontSize=18, leading=22, textColor=akz, spaceAfter=2),
        "h1": ParagraphStyle("h1", fontName=fb, fontSize=12.5, leading=16, textColor=akz, spaceBefore=12, spaceAfter=5),
        "p": ParagraphStyle("p", fontName=f, fontSize=10, leading=13.5, spaceAfter=4),
        "klein": ParagraphStyle("k", fontName=f, fontSize=8, leading=10.5, textColor=colors.HexColor("#555b66"), spaceAfter=4),
        "zelle": ParagraphStyle("z", fontName=f, fontSize=8.6, leading=10.8, alignment=TA_LEFT),
        "kopf": ParagraphStyle("zk", fontName=fb, fontSize=8.6, leading=10.8, textColor=colors.white),
    }
    breite = A4[0] - 36 * mm
    story = []

    def tab(kopf, zeilen, ant, kv=False):
        s = sum(ant)
        cw = [breite * a / s for a in ant]
        daten = ([[Paragraph(_esc(h), st["kopf"]) for h in kopf]] if kopf else []) + \
                [[Paragraph(_esc(c), st["zelle"]) for c in z] for z in zeilen]
        t = Table(daten, colWidths=cw, repeatRows=1 if kopf else 0)
        cmds = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9ced6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
        if kopf:
            cmds.append(("BACKGROUND", (0, 0), (-1, 0), akz))
            cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f9")]))
        if kv:
            cmds.append(("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")))
        t.setStyle(TableStyle(cmds))
        return t

    halten = []          # Ueberschrift + Zeile + Diagramm zusammenhalten

    def ablegen(x):
        if halten is not None and halten_aktiv[0]:
            halten.append(x)
        else:
            story.append(x)

    halten_aktiv = [False]

    def halten_ende():
        if halten_aktiv[0]:
            story.append(KeepTogether(list(halten)))
            halten.clear()
            halten_aktiv[0] = False

    for blk in bl:
        art = blk[0]
        if art == "h1":
            halten_ende()
            halten_aktiv[0] = True
        if art in ("tabelle", "kv"):
            halten_ende()
        if art in ("titel", "h1", "p", "klein"):
            ablegen(Paragraph(_esc(blk[1]), st[art]))
            continue
        elif art == "kv":
            story.append(tab(None, [[n, w] for n, w in blk[1]], [1, 2.6], kv=True))
        elif art == "tabelle":
            story.append(tab(blk[1], blk[2], blk[3]))
            story.append(Spacer(1, 3))
        elif art == "bild":
            img = Image(blk[1])
            sk = breite / img.imageWidth
            img.drawWidth, img.drawHeight = breite, img.imageHeight * sk
            ablegen(img)
            halten_ende()
        elif art == "unterschrift":     # mit der Bemerkung zusammenhalten
            ablegen(Spacer(1, 22))
            ablegen(tab(None, [["Datum: ______________________",
                                "Unterschrift: ______________________"]], [1, 1.4]))
            halten_ende()

    halten_ende()

    def seite(c, d):
        c.saveState()
        c.setFont(f, 7.5)
        c.setFillColor(colors.HexColor("#555b66"))
        c.drawString(18 * mm, 10 * mm, fuss)
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Seite {d.page}")
        c.setStrokeColor(akz)
        c.setLineWidth(0.6)
        c.line(18 * mm, 13.5 * mm, A4[0] - 18 * mm, 13.5 * mm)
        c.restoreState()

    doc = SimpleDocTemplate(pfad, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=20 * mm,
                            title=bl[0][1], author="UPA-Analyzer-Control")
    doc.build(story, onFirstPage=seite, onLaterPages=seite)


# ---------------------------------------------------------------------------
# DOCX
def _schattierung(zelle, farbe):
    tcPr = zelle._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), farbe.lstrip("#"))
    tcPr.append(shd)


def _seitenzahl(absatz):
    run = absatz.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.append(fld)


def als_docx(bl, pfad, fuss):
    d = docx.Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin, sec.bottom_margin = Cm(1.6), Cm(1.8)
    breite = sec.page_width - sec.left_margin - sec.right_margin
    norm = d.styles["Normal"]
    norm.font.name = "Calibri"
    norm.font.size = Pt(10)
    blau = RGBColor(0x1F, 0x5F, 0xBF)

    fp = sec.footer.paragraphs[0]
    r = fp.add_run(fuss + " · Seite ")
    r.font.size = Pt(7.5)
    _seitenzahl(fp)

    def tabelle(kopf, zeilen, ant, kv=False):
        n = len(kopf) if kopf else len(zeilen[0])
        t = d.add_table(rows=0, cols=n)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        s = sum(ant)
        if kopf:
            zs = t.add_row().cells
            for i, h in enumerate(kopf):
                zs[i].text = ""
                run = zs[i].paragraphs[0].add_run(str(h))
                run.bold = True
                run.font.size = Pt(8.5)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                _schattierung(zs[i], AKZENT)
        for j, z in enumerate(zeilen):
            zs = t.add_row().cells
            for i, c in enumerate(z):
                zs[i].text = ""
                run = zs[i].paragraphs[0].add_run(str(c))
                run.font.size = Pt(8.5)
                if kv and i == 0:
                    _schattierung(zs[i], "#eef2f7")
                elif kopf and j % 2 == 1:
                    _schattierung(zs[i], "#f2f5f9")
        for zeile in t.rows:
            for i, zelle in enumerate(zeile.cells):
                zelle.width = int(breite * ant[i] / s)
        d.add_paragraph()

    for blk in bl:
        art = blk[0]
        if art == "titel":
            p = d.add_paragraph()
            run = p.add_run(blk[1])
            run.bold = True
            run.font.size = Pt(18)
            run.font.color.rgb = blau
        elif art == "h1":
            p = d.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            run = p.add_run(blk[1])
            run.bold = True
            run.font.size = Pt(12.5)
            run.font.color.rgb = blau
        elif art == "p":
            d.add_paragraph(blk[1])
        elif art == "klein":
            run = d.add_paragraph().add_run(blk[1])
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(0x55, 0x5B, 0x66)
        elif art == "kv":
            tabelle(None, [[n, w] for n, w in blk[1]], [1, 2.6], kv=True)
        elif art == "tabelle":
            tabelle(blk[1], blk[2], blk[3])
        elif art == "bild":
            d.add_picture(blk[1], width=breite)
        elif art == "unterschrift":
            d.add_paragraph()
            d.add_paragraph("Datum: ______________________          Unterschrift: ______________________")
    d.core_properties.title = bl[0][1]
    d.core_properties.author = "UPA-Analyzer-Control"
    d.save(pfad)


# ---------------------------------------------------------------------------
def selbsttest(ziel):
    """Beispiel-Geraeteordner + Protokoll (Pruefung der installierten Version)."""
    pr = {"hersteller": "Selbsttest", "typ": "Loopback", "seriennr": "0001"}
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "geraet.json"), "w", encoding="utf-8") as fh:
        json.dump(pr, fh)
    fs = [20, 100, 1000, 10000, 20000]
    pts = [{"i": i, "ch": c, "x": f, "f": f, "u_soll": 0.5, "u_true": 0.496 - 0.001 * (f / 20000)}
           for c in ("L", "R") for i, f in enumerate(fs)]
    with open(os.path.join(ziel, "upa_fr_selbsttest.csv"), "w", encoding="utf-8") as fh:
        fh.write("# Selbsttest\n" + ";".join(["i", "ch", "x", "f", "u_soll", "u_true"]) + "\n")
        for p in pts:
            fh.write(";".join(str(p[c]) for c in ["i", "ch", "x", "f", "u_soll", "u_true"]) + "\n")
    report.diagramm("fr", "Selbsttest Frequenzgang", pts, os.path.join(ziel, "upa_fr_selbsttest.png"))
    with open(os.path.join(ziel, "messungen.json"), "w", encoding="utf-8") as fh:
        json.dump([{"programm": "fr", "name": "Frequenzgang", "start": datetime.now().isoformat(timespec="seconds"),
                    "csv": "upa_fr_selbsttest.csv", "png": "upa_fr_selbsttest.png", "adapter": "Selbsttest",
                    "software": "test", "parameter": {"level": 0.5, "rng": "AUTO", "atten": 1.0},
                    "ergebnis": report.zusammenfassung("fr", pts), "abgebrochen": False}], fh, ensure_ascii=False)
    return erstellen(ziel, bemerkung="Selbsttest µ Ω → äöü", firma="Selbsttest", version="test")
