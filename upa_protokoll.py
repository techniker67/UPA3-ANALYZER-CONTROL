"""Pruefprotokoll aus dem Geraeteordner: PDF (reportlab) und DOCX (python-docx).

Ablauf:  messungen.json + CSV + PNG  ->  Inhalt (Bloecke)  ->  PDF / DOCX
Beide Ausgaben entstehen aus derselben Blockliste und sind damit inhaltsgleich.

Bloecke:  ("titel", text) ("h1", text) ("h2", text) ("p", text) ("klein", text)
          ("kv", [(Name, Wert), ...])  ("tabelle", kopf, zeilen, spaltenanteile)
          ("bild", pfad)  ("unterschrift", None)  ("umbruch", None)
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
    from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
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
              "thdl": "THD+N über Pegel", "sn": "Störabstand (unbewertet)", "xt": "Kanaltrennung",
              "ruhe": "Ruhestrom / Offset"}


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


# ---------------------------------------------------------------------------
# Papierkorb: Messungen und Protokolle nicht loeschen, sondern in den Unterordner
# "Papierkorb" des Geraeteordners verschieben (wiederherstellbar; endgueltig
# loescht der Anwender den Ordner selbst im Explorer).
PAPIERKORB = "Papierkorb"


def _liste(ordner):
    try:
        with open(os.path.join(ordner, "messungen.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


def protokolle(ordner, im_korb=False):
    """Erstellte Protokolle, neueste zuerst: [{"basis", "pdf", "docx"}]."""
    o = os.path.join(ordner, PAPIERKORB) if im_korb else ordner
    try:
        namen = os.listdir(o)
    except OSError:
        return []
    basen = {}
    for n in namen:
        b, ext = os.path.splitext(n)
        if n.startswith("Pruefprotokoll_") and ext.lower() in (".pdf", ".docx"):
            basen.setdefault(b, {"basis": b, "pdf": None, "docx": None})[ext.lower()[1:]] = n
    return sorted(basen.values(), key=lambda e: e["basis"], reverse=True)


def im_papierkorb(ordner):
    """Messungen (Eintraege aus messungen.json, deren CSV im Papierkorb liegt) und Protokolle."""
    korb = os.path.join(ordner, PAPIERKORB)
    ms = [e for e in _liste(ordner)
          if e.get("csv") and not os.path.exists(os.path.join(ordner, e["csv"]))
          and os.path.exists(os.path.join(korb, e["csv"]))]
    return ms, protokolle(ordner, True)


def _dateien(ordner, art, name):
    """Dateinamen, die zu einer Messung (CSV-Name) bzw. einem Protokoll (Basisname) gehoeren."""
    name = os.path.basename(str(name or ""))
    if not name:
        raise ValueError("Kein Eintrag angegeben")
    if art == "messung":
        e = next((e for e in _liste(ordner) if e.get("csv") == name), None)
        if not e:
            raise ValueError("Messung nicht gefunden")
        return [n for n in (e.get("csv"), e.get("png")) if n]
    if art == "protokoll":
        if not name.startswith("Pruefprotokoll_"):
            raise ValueError("Kein Prüfprotokoll")
        return [name + ext for ext in (".pdf", ".docx")]
    raise ValueError("Unbekannte Art")


def verschieben(ordner, art, name, zurueck=False):
    """Messung/Protokoll in den Papierkorb (zurueck=False) oder zurueck in den Geraeteordner.
    Verschiebt nur vorhandene Dateien, ueberschreibt nie. Liefert die verschobenen Namen."""
    korb = os.path.join(ordner, PAPIERKORB)
    von, nach = (korb, ordner) if zurueck else (ordner, korb)
    dateien = [n for n in _dateien(ordner, art, name) if os.path.isfile(os.path.join(von, os.path.basename(n)))]
    if not dateien:
        raise ValueError("Nichts zu verschieben – Datei nicht gefunden")
    for n in dateien:
        if os.path.exists(os.path.join(nach, os.path.basename(n))):
            raise ValueError(f"{os.path.basename(n)} gibt es am Ziel schon – nichts verschoben")
    os.makedirs(nach, exist_ok=True)
    fertig = []
    try:
        for n in dateien:
            n = os.path.basename(n)
            os.replace(os.path.join(von, n), os.path.join(nach, n))
            fertig.append(n)
    except OSError as e:
        for n in fertig:               # halb verschoben -> rueckgaengig
            try:
                os.replace(os.path.join(nach, n), os.path.join(von, n))
            except OSError:
                pass
        raise ValueError(f"Verschieben nicht möglich: {e}")
    return fertig


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
    if e["programm"] == "ruhe":
        t = [f"Multimeter {e.get('adapter') or 'Fluke'}"]
        if p.get("soll") is not None:
            t.append(f"Sollwert {k(p['soll'], '{:g}')} mV ± {k(p['tol'], '{:g}')} mV")
        t.append("Dauer " + (_dauer(p["dauer_s"]) if p.get("dauer_s") else "bis Stop"))
        t.append(f"Intervall {k(p.get('intervall') or 1, '{:g}')} s")
        return " · ".join(t)
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


def _dauer(s):
    s = int(round(s or 0))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d} h" if s >= 3600 else f"{s // 60} min"


def _mmss(s):
    """Laufzeit wie in der Ergebnisuebersicht: m:ss bzw. h:mm:ss."""
    s = int(round(s or 0))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def ruhe_tabelle(e):
    """Zeitmarken + Endwert eines Ruhestrom-/Offset-Laufs."""
    p = e.get("parameter", {})
    soll = p.get("soll")
    soll_txt = f"{k(soll, '{:g}')} ± {k(p.get('tol'), '{:g}')}" if soll is not None else "–"

    def bew(ok, ol=False):
        if ol and ok is False:
            return "✗ Überlauf"
        return "–" if ok is None else ("✓ i. O." if ok else "✗ außerhalb")

    def wert(v, ol):
        return "OL" if v is None and ol else k(v, "{:.3f}")
    z = [[f"nach {k(m['minute'], '{:g}')} min", wert(m.get("wert"), m.get("ol")), soll_txt,
          bew(m.get("ok"), m.get("ol"))] for m in e.get("marken", [])]
    ende, ende_ol = e.get("ende_wert"), e.get("ende_ol", False)
    if ende is None:
        ok = False if ende_ol and soll is not None else None
    else:
        ok = None if soll is None else abs(ende - soll) <= p.get("tol", 0)
    z.append([f"Endwert ({_mmss(e.get('ende_t'))})", wert(ende, ende_ol), soll_txt, bew(ok, ende_ol)])
    st = e.get("statistik") or {}
    if st:
        ab = st.get("ab_t")
        mk = e.get("marken") or []
        name = (f"Min / Max ab {k(mk[0]['minute'], '{:g}')} min" if ab and mk else
                "Minimum / Maximum")
        z.append([name, f"{k(st['min'], '{:.3f}')} / {k(st['max'], '{:.3f}')}", "", ""])
    return ["Zeitpunkt", "Wert (mV)", "Soll (mV)", "Bewertung"], z, [2.2, 1.6, 1.6, 1.8]


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
    adapter = next((e.get("adapter") for e in reversed(ms) if e.get("adapter") and e["programm"] != "ruhe"), "–")
    multimeter = next((e.get("adapter") for e in reversed(ms) if e["programm"] == "ruhe" and e.get("adapter")), "")
    hat_upa = any(e["programm"] != "ruhe" for e in ms)
    software = ms[-1].get("software", "")
    tage = sorted({_datum(e.get("start"))[:10] for e in ms})
    b = [("titel", "PRÜFPROTOKOLL"),
         ("untertitel", f"{g['hersteller'].upper()} {g['typ']} · Audiomessung"),
         ("grau", f"Seriennummer {g['seriennr']} · Messsystem "
                  + " + ".join(([("R&S UPA Audioanalysator")] if hat_upa else []) + (["Fluke 287"] if multimeter else []))),
         ("datum", f"Protokolldatum: {datetime.now().strftime('%d.%m.%Y')}"),
         ("h1", "1. Prüfling und Messsystem"),
         ("tabelle", ["Parameter", "Wert"],
          [["Hersteller", g["hersteller"]], ["Typ / Modell", g["typ"]],
           ["Seriennummer", g["seriennr"]]] + ([["Auftragsnummer", g["auftrag"]]] if g.get("auftrag") else []) + [
           ["Prüfdatum", ", ".join(tage)],
           ["Prüfer", firma or "–"],
           ] + ([["Messsystem", "R&S UPA Audioanalysator, AR488-GPIB-Adapter"],
                 ["Adapter-Firmware", adapter]] if hat_upa else []) + ([["Multimeter", multimeter]] if multimeter else []) + [
           ["Software", f"UPA-Analyzer-Control v{software}"]], [3000, 6638], True),
         ("h1", "2. Ergebnisübersicht")]
    z = []
    for e in ms:
        name = PROG_NAMEN.get(e["programm"], e.get("name"))
        erste = True
        for c in e.get("ergebnis", []):
            for i, (n, w) in enumerate(c["werte"]):
                z.append([name if erste else "", c["kanal"] if i == 0 else "", n, w])
                erste = False
    b.append(("tabelle", ["Messung", "Kanal", "Größe", "Ergebnis"], z, [2.2, 1.3, 2.1, 3.0], False))
    for n, e in enumerate(ms, 1):
        prog = e["programm"]
        pts = lese_csv(os.path.join(ordner, e["csv"]))
        b.append(("umbruch", None))          # jede Messung auf neuer Seite
        if n == 1:
            b.append(("h1", "3. Messergebnisse"))
        b.append(("h2", f"3.{n} {PROG_NAMEN.get(prog, e.get('name'))}"))
        zeile = f"{_datum(e.get('start'))} · {einstellungen(e)}"
        if e.get("bezeichnung"):
            zeile += f" · {e['bezeichnung']}"
        if e.get("abgebrochen"):
            zeile += " · ABGEBROCHEN"
        b.append(("grau", zeile))
        if e.get("png") and os.path.exists(os.path.join(ordner, e["png"])):
            b.append(("bild", os.path.join(ordner, e["png"])))
        kopf, zeilen, ant = ruhe_tabelle(e) if prog == "ruhe" else werte_tabelle(prog, pts)
        b.append(("tabelle", kopf, zeilen, ant, False))
        b.append(("klein", f"Messdatei: {e['csv']}"))
    if bemerkung.strip():
        b += [("h1", "4. Bemerkung"), ("p", bemerkung.strip())]
    b.append(("unterschrift", None))
    return g, b


def dateiname(g):
    return (f"Pruefprotokoll_{report.geraetename(g)}_"
            f"{datetime.now().strftime('%Y%m%d-%H%M')}")


def erstellen(ordner, auswahl=None, bemerkung="", firma="", version=""):
    """PDF und DOCX schreiben (soweit die Bibliotheken da sind). Liefert Dateinamen."""
    g, bl = inhalt(ordner, auswahl, bemerkung, firma)
    basis = os.path.join(ordner, dateiname(g))
    kopf = f"Prüfprotokoll  |  {g['hersteller'].upper()} {g['typ']}  |  SN {g['seriennr']}"
    if g.get("auftrag"):
        kopf += f"  |  {g['auftrag']}"
    fuss = "  |  ".join(t for t in (firma, f"Prüfprotokoll Audiomessung · UPA-Analyzer-Control v{version}") if t)
    out = []
    if A4 is not None:
        pdf(bl, basis + ".pdf", kopf, fuss)
        out.append(os.path.basename(basis + ".pdf"))
    if docx is not None:
        als_docx(bl, basis + ".docx", kopf, fuss)
        out.append(os.path.basename(basis + ".docx"))
    if not out:
        raise RuntimeError("Weder reportlab (PDF) noch python-docx (DOCX) installiert")
    return out


# ---------------------------------------------------------------------------
# Hausstil (wie die Reparaturberichte von Vintage Audio Repair Magdeburg)
AKZENT, ZEBRA, RAND, GRAU, FUSSGRAU = "#2E5A88", "#EAF0F6", "#BFC9D6", "#595959", "#7F7F7F"
GROESSE = {"titel": 20, "untertitel": 14, "h1": 14, "h2": 11.5, "p": 10.5, "grau": 10.5,
           "datum": 9.5, "tab": 9.5, "klein": 8.5, "kopf": 8.5, "fuss": 8.5}

# ---------------------------------------------------------------------------
# PDF
_FONT = None


def _schrift():
    """Calibri (Windows), sonst Carlito (gleiche Laufweite), sonst DejaVu Sans."""
    global _FONT
    if _FONT:
        return _FONT
    kandidaten = [
        (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "calibri.ttf"),
         os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "calibrib.ttf")),
        ("/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
         "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
    ]
    try:
        import matplotlib
        d = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
        kandidaten.append((os.path.join(d, "DejaVuSans.ttf"), os.path.join(d, "DejaVuSans-Bold.ttf")))
    except Exception:
        pass
    global _SYMBOL
    try:
        import matplotlib
        dj = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", "DejaVuSans.ttf")
        pdfmetrics.registerFont(TTFont("Symbole", dj))
        _SYMBOL = "Symbole"
    except Exception:
        _SYMBOL = None
    for normal, fett in kandidaten:
        if os.path.exists(normal) and os.path.exists(fett):
            try:
                pdfmetrics.registerFont(TTFont("Haus", normal))
                pdfmetrics.registerFont(TTFont("Haus-Bold", fett))
                _FONT = ("Haus", "Haus-Bold")
                return _FONT
            except Exception:
                continue
    _FONT = ("Helvetica", "Helvetica-Bold")
    return _FONT


_SYMBOL = None


def _esc(t):
    t = str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if _SYMBOL:            # Haken/Kreuz: Calibri/Carlito haben die Zeichen nicht
        for z in ("✓", "✗"):
            t = t.replace(z, f'<font name="{_SYMBOL}">{z}</font>')
    return t


def pdf(bl, pfad, kopfzeile, fuss):
    from reportlab.pdfgen import canvas as rl_canvas
    f, fb = _schrift()
    akz, grau = colors.HexColor(AKZENT), colors.HexColor(GRAU)
    G = GROESSE
    st = {
        "titel": ParagraphStyle("t", fontName=fb, fontSize=G["titel"], leading=G["titel"] * 1.2, textColor=akz, spaceAfter=2),
        "untertitel": ParagraphStyle("u", fontName=fb, fontSize=G["untertitel"], leading=G["untertitel"] * 1.25, spaceAfter=2),
        "grau": ParagraphStyle("g", fontName=f, fontSize=G["grau"], leading=G["grau"] * 1.3, textColor=grau, spaceAfter=3),
        "datum": ParagraphStyle("d", fontName=f, fontSize=G["datum"], leading=G["datum"] * 1.3, textColor=grau, spaceAfter=6),
        "h1": ParagraphStyle("h1", fontName=fb, fontSize=G["h1"], leading=G["h1"] * 1.25, textColor=akz, spaceBefore=14, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName=fb, fontSize=G["h2"], leading=G["h2"] * 1.25, textColor=akz, spaceBefore=10, spaceAfter=4),
        "p": ParagraphStyle("p", fontName=f, fontSize=G["p"], leading=G["p"] * 1.3, spaceAfter=4),
        "klein": ParagraphStyle("k", fontName=f, fontSize=G["klein"], leading=G["klein"] * 1.3, textColor=colors.HexColor(FUSSGRAU), spaceAfter=4),
        "zelle": ParagraphStyle("z", fontName=f, fontSize=G["tab"], leading=G["tab"] * 1.25, alignment=TA_LEFT),
        "zelle_fett": ParagraphStyle("zf", fontName=fb, fontSize=G["tab"], leading=G["tab"] * 1.25),
        "kopf": ParagraphStyle("zk", fontName=fb, fontSize=G["tab"], leading=G["tab"] * 1.25, textColor=colors.white),
    }
    rand = 20 * mm
    breite = A4[0] - 2 * rand
    story = []

    def tab(kopf, zeilen, ant, erste_fett=False):
        s = sum(ant)
        cw = [breite * a / s for a in ant]
        daten = [[Paragraph(_esc(h), st["kopf"]) for h in kopf]] + \
                [[Paragraph(_esc(c), st["zelle_fett"] if erste_fett and i == 0 else st["zelle"])
                  for i, c in enumerate(z)] for z in zeilen]
        t = Table(daten, colWidths=cw, repeatRows=1)
        cmds = [("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(RAND)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4.5), ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("BACKGROUND", (0, 0), (-1, 0), akz),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(ZEBRA)])]
        t.setStyle(TableStyle(cmds))
        return t

    halten, aktiv = [], [False]      # Ueberschrift + Zeile + Diagramm zusammenhalten

    def ablegen(x):
        (halten if aktiv[0] else story).append(x)

    def halten_ende():
        if aktiv[0]:
            story.append(KeepTogether(list(halten)))
            halten.clear()
            aktiv[0] = False

    for blk in bl:
        art = blk[0]
        if art in ("h1", "h2") and not (art == "h2" and aktiv[0]):
            halten_ende()
            aktiv[0] = True
        if art in ("tabelle", "umbruch"):
            halten_ende()
        if art == "umbruch":
            story.append(PageBreak())
        elif art in st:
            ablegen(Paragraph(_esc(blk[1]), st[art]))
        elif art == "tabelle":
            story.append(tab(blk[1], blk[2], blk[3], blk[4] if len(blk) > 4 else False))
            story.append(Spacer(1, 4))
        elif art == "bild":
            img = Image(blk[1])
            sk = breite / img.imageWidth
            img.drawWidth, img.drawHeight = breite, img.imageHeight * sk
            ablegen(img)
            halten_ende()
        elif art == "unterschrift":     # mit der Bemerkung zusammenhalten
            ablegen(Spacer(1, 26))
            ablegen(Paragraph(_esc("Datum: ________________________          "
                                   "Unterschrift: ________________________"), st["p"]))
            halten_ende()
    halten_ende()

    class SeitenCanvas(rl_canvas.Canvas):
        """Kopf- und Fusszeile mit 'Seite x von y' (zwei Durchlaeufe)."""
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._seiten = []

        def showPage(self):
            self._seiten.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            n = len(self._seiten)
            for zustand in self._seiten:
                self.__dict__.update(zustand)
                self._rahmen(n)
                super().showPage()
            super().save()

        def _rahmen(self, n):
            self.saveState()
            self.setFont(fb, G["kopf"])
            self.setFillColor(akz)
            y = A4[1] - 12.5 * mm
            self.drawString(rand, y, kopfzeile)
            self.setStrokeColor(akz)
            self.setLineWidth(0.75)
            self.line(rand, y - 2.2 * mm, A4[0] - rand, y - 2.2 * mm)
            self.setFont(f, G["fuss"])
            self.setFillColor(colors.HexColor(FUSSGRAU))
            self.drawCentredString(A4[0] / 2, 10 * mm, f"Seite {self._pageNumber} von {n}  |  {fuss}")
            self.restoreState()

    doc = SimpleDocTemplate(pfad, pagesize=A4, leftMargin=rand, rightMargin=rand,
                            topMargin=20 * mm, bottomMargin=18 * mm,
                            title="Prüfprotokoll", author="UPA-Analyzer-Control")
    doc.build(story, canvasmaker=SeitenCanvas)


# ---------------------------------------------------------------------------
# DOCX
def _schattierung(zelle, farbe):
    tcPr = zelle._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), farbe.lstrip("#"))
    tcPr.append(shd)


def _feld(absatz, instr, groesse, farbe):
    """Feld (PAGE/NUMPAGES) als komplexes Feld wie in Word."""
    def run_mit(kind, **attr):
        r = absatz.add_run()
        r.font.size, r.font.color.rgb = groesse, farbe
        el = OxmlElement(kind)
        for k_, v_ in attr.items():
            el.set(qn(k_), v_)
        r._r.append(el)
        return r
    run_mit("w:fldChar", **{"w:fldCharType": "begin"})
    r = absatz.add_run()
    r.font.size, r.font.color.rgb = groesse, farbe
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r._r.append(it)
    run_mit("w:fldChar", **{"w:fldCharType": "separate"})
    t = absatz.add_run("1")
    t.font.size, t.font.color.rgb = groesse, farbe
    run_mit("w:fldChar", **{"w:fldCharType": "end"})


def _calibri(stil, groesse=None, fett=None, farbe=None):
    """Schrift eines Formats fest auf Calibri setzen (Design-Schriften entfernen)."""
    stil.font.name = "Calibri"
    rpr = stil.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), "Calibri")
    if groesse:
        stil.font.size = Pt(groesse)
    if fett is not None:
        stil.font.bold = fett
    stil.font.italic = False
    if farbe:
        stil.font.color.rgb = farbe


def _rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def als_docx(bl, pfad, kopfzeile, fuss):
    G = GROESSE
    d = docx.Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.0)
    breite = sec.page_width - sec.left_margin - sec.right_margin
    akz = _rgb(AKZENT)
    _calibri(d.styles["Normal"], G["p"])
    for name, gr, vor, nach in (("Heading 1", G["h1"], 14, 6), ("Heading 2", G["h2"], 10, 4)):
        s_ = d.styles[name]
        _calibri(s_, gr, True, akz)
        s_.paragraph_format.space_before, s_.paragraph_format.space_after = Pt(vor), Pt(nach)
        s_.paragraph_format.keep_with_next = True

    # Kopfzeile (Unterstrich in Akzentfarbe) und Fusszeile "Seite x von y | ..."
    hp = sec.header.paragraphs[0]
    r = hp.add_run(kopfzeile)
    r.bold, r.font.size, r.font.color.rgb = True, Pt(G["kopf"]), akz
    pPr = hp._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    unten = OxmlElement("w:bottom")
    for k_, v_ in (("w:val", "single"), ("w:sz", "6"), ("w:space", "4"), ("w:color", AKZENT.lstrip("#"))):
        unten.set(qn(k_), v_)
    bdr.append(unten)
    pPr.append(bdr)
    fp = sec.footer.paragraphs[0]
    fp.alignment = 1
    gr_, fg = Pt(G["fuss"]), _rgb(FUSSGRAU)
    for teil in ("Seite ", "PAGE", " von ", "NUMPAGES", f"  |  {fuss}"):
        if teil in ("PAGE", "NUMPAGES"):
            _feld(fp, teil, gr_, fg)
        else:
            rr = fp.add_run(teil)
            rr.font.size, rr.font.color.rgb = gr_, fg

    def tabelle(kopf, zeilen, ant, erste_fett=False):
        t = d.add_table(rows=0, cols=len(kopf))
        tblPr = t._tbl.tblPr
        rb = OxmlElement("w:tblBorders")
        for seite in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{seite}")
            for k_, v_ in (("w:val", "single"), ("w:sz", "4"), ("w:space", "0"), ("w:color", RAND.lstrip("#"))):
                el.set(qn(k_), v_)
            rb.append(el)
        tblPr.append(rb)
        mar = OxmlElement("w:tblCellMar")
        for seite, w in (("top", 50), ("left", 90), ("bottom", 50), ("right", 90)):
            el = OxmlElement(f"w:{seite}")
            el.set(qn("w:w"), str(w))
            el.set(qn("w:type"), "dxa")
            mar.append(el)
        tblPr.append(mar)
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        s = sum(ant)

        def zeile(werte, art, j=0):
            zs = t.add_row()
            if art == "kopf":       # Kopfzeile auf jeder Seite wiederholen
                trPr = zs._tr.get_or_add_trPr()
                trPr.append(OxmlElement("w:tblHeader"))
            for i, c in enumerate(werte):
                zelle = zs.cells[i]
                zelle.width = int(breite * ant[i] / s)
                p_ = zelle.paragraphs[0]
                p_.paragraph_format.space_after = Pt(0)
                p_.paragraph_format.line_spacing = 1.0
                run = p_.add_run(str(c))
                run.font.size = Pt(G["tab"])
                if art == "kopf":
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    _schattierung(zelle, AKZENT)
                else:
                    if erste_fett and i == 0:
                        run.bold = True
                    if j % 2 == 1:
                        _schattierung(zelle, ZEBRA)
        zeile(kopf, "kopf")
        for j, z in enumerate(zeilen):
            zeile(z, "daten", j)
        # feste Spaltenbreiten (sonst verteilt Word/LibreOffice gleichmaessig)
        t.autofit = False
        for i, gc in enumerate(t._tbl.tblGrid.gridCol_lst):
            gc.w = int(breite * ant[i] / s)
        tw = OxmlElement("w:tblW")
        tw.set(qn("w:w"), str(int(breite) // 635))   # EMU -> Twips
        tw.set(qn("w:type"), "dxa")
        alt = tblPr.find(qn("w:tblW"))
        if alt is not None:
            tblPr.remove(alt)
        tblPr.append(tw)
        d.add_paragraph().paragraph_format.space_after = Pt(2)

    def absatz(text, groesse, fett=False, farbe=None, nach=4):
        p_ = d.add_paragraph()
        p_.paragraph_format.space_after = Pt(nach)
        run = p_.add_run(text)
        run.font.size, run.bold = Pt(groesse), fett
        if farbe:
            run.font.color.rgb = farbe
        return p_

    for blk in bl:
        art = blk[0]
        if art == "umbruch":
            d.add_page_break()
        elif art == "titel":
            absatz(blk[1], G["titel"], True, akz, 2)
        elif art == "untertitel":
            absatz(blk[1], G["untertitel"], True, None, 2)
        elif art == "grau":
            absatz(blk[1], G["grau"], False, _rgb(GRAU), 3)
        elif art == "datum":
            absatz(blk[1], G["datum"], False, _rgb(GRAU), 6)
        elif art == "h1":
            d.add_paragraph(blk[1], style="Heading 1")
        elif art == "h2":
            d.add_paragraph(blk[1], style="Heading 2")
        elif art == "p":
            absatz(blk[1], G["p"])
        elif art == "klein":
            absatz(blk[1], G["klein"], False, _rgb(FUSSGRAU))
        elif art == "tabelle":
            tabelle(blk[1], blk[2], blk[3], blk[4] if len(blk) > 4 else False)
        elif art == "bild":
            d.add_picture(blk[1], width=breite)
        elif art == "unterschrift":
            d.add_paragraph()
            absatz("Datum: ________________________          Unterschrift: ________________________", G["p"])
    d.core_properties.title = "Prüfprotokoll"
    d.core_properties.author = "UPA-Analyzer-Control"
    d.save(pfad)


# ---------------------------------------------------------------------------
def selbsttest(ziel):
    """Beispiel-Geraeteordner + Protokoll (Pruefung der installierten Version)."""
    pr = {"hersteller": "Selbsttest", "typ": "Loopback", "seriennr": "0001"}
    os.makedirs(ziel, exist_ok=True)
    import shutil
    shutil.rmtree(os.path.join(ziel, PAPIERKORB), ignore_errors=True)   # nur im Selbsttest-Ordner
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
    dateien = erstellen(ziel, bemerkung="Selbsttest µ Ω → äöü", firma="Selbsttest", version="test")
    # Papierkorb: Messung + Protokoll hin und zurueck
    basis = protokolle(ziel)[0]["basis"]
    verschieben(ziel, "messung", "upa_fr_selbsttest.csv")
    verschieben(ziel, "protokoll", basis)
    ms, pk = im_papierkorb(ziel)
    if messungen(ziel) or len(ms) != 1 or len(pk) != 1:
        raise RuntimeError("Papierkorb-Selbsttest fehlgeschlagen")
    verschieben(ziel, "messung", "upa_fr_selbsttest.csv", zurueck=True)
    verschieben(ziel, "protokoll", basis, zurueck=True)
    if len(messungen(ziel)) != 1 or any(im_papierkorb(ziel)):
        raise RuntimeError("Papierkorb-Selbsttest: Zurückholen fehlgeschlagen")
    return dateien
