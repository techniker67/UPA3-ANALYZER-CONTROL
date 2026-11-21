"""Geraeteordner, Messungs-Zusammenfassung und Diagramme (PNG).

Ist ein Pruefling festgelegt (Hersteller, Typ, Seriennummer), landen alle
Messungen in einem eigenen Ordner:

  <Datenordner>/Messungen/<Hersteller>_<Typ>_<Seriennr>/
      geraet.json                     Pruefling
      messungen.json                  Liste aller Messungen mit Kernergebnissen
      upa_<prog>_<Zeit>.csv           Messwerte (wie bisher)
      upa_<prog>_<Zeit>.png           Diagramm (helle Druckdarstellung)

Aus diesem Ordner entstehen spaeter das Pruefprotokoll (PDF/DOCX) und die
Uebernahme in einen Reparaturbericht. Diagramme brauchen matplotlib; fehlt es,
werden nur CSV und Zusammenfassung geschrieben.
"""
import json
import math
import os
import re
from datetime import datetime

import upa_paths as paths

try:
    import matplotlib
    matplotlib.use("Agg")                     # ohne Bildschirm/Tk
    import matplotlib.pyplot as plt
    import logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    # Hausschrift Calibri (Windows), sonst Carlito / DejaVu Sans
    plt.rcParams["font.family"] = ["Calibri", "Carlito", "DejaVu Sans"]
    from matplotlib.ticker import FuncFormatter, NullFormatter, LogLocator
except Exception:
    plt = None

# Aufloesung der Diagramme. Nicht unter 300 dpi gehen: Calibri enthaelt
# eingebettete Pixelschriften fuer 12-19 Pixel Schrifthoehe, die matplotlib
# leer zeichnet. Bei 150 dpi fielen Achsenzahlen, Legende und Zeitmarken-
# Texte (7,5-8 pt) genau in diesen Bereich; ab 300 dpi liegt jede Schrift
# ab 4,6 pt darueber.
DPI = 300

FELDER = (("hersteller", "Hersteller"), ("typ", "Typ"), ("seriennr", "Seriennummer"))
FARBE = {"L": "#2E5A88", "R": "#C0504D", "L→R": "#2E5A88", "R→L": "#C0504D"}   # Hausfarben


# ---------------------------------------------------------------------------
# Pruefling / Ordner
def pruefling_pruefen(d):
    """Eingabe bereinigen. Liefert dict oder None (= kein Pruefling)."""
    if not d:
        return None
    pr = {k: re.sub(r"\s+", " ", str(d.get(k, "") or "")).strip()[:60] for k, _ in FELDER}
    auftrag = re.sub(r"\s+", "", str(d.get("auftrag", "") or ""))[:40]
    if not any(pr.values()) and not auftrag:
        return None
    fehlt = [n for k, n in FELDER if not pr[k]]
    if fehlt:
        raise ValueError("Bitte ausfüllen: " + ", ".join(fehlt))
    if auftrag:
        if re.search(r'[\\/:*?"<>|]', auftrag):
            raise ValueError('Auftragsnummer darf keine Zeichen \\ / : * ? " < > | enthalten')
        pr["auftrag"] = auftrag
    return pr


def _sicher(s):
    s = re.sub(r'[\\/:*?"<>|]+', "-", s).strip(" .")
    return re.sub(r"\s+", " ", s) or "unbekannt"


def geraetename(pr):
    """Hersteller_Typ_Seriennr – Grundlage der Dateinamen."""
    return "_".join(_sicher(pr[k]) for k, _ in FELDER)


def ordnername(pr):
    """Ordnername: Auftragsnummer (falls angegeben), sonst Hersteller_Typ_Seriennr."""
    return _sicher(pr["auftrag"]) if pr.get("auftrag") else geraetename(pr)


WARNUNG = ""          # letzte Meldung, falls die Ablage nicht erreichbar war


def ordner(pr):
    """Messordner im Ablageordner: Geraete-/Auftragsordner oder (ohne Pruefling)
    die Ablage direkt. Ist die Ablage (z. B. NAS) nicht erreichbar, wird lokal
    unter <Datenordner>/Messungen gespeichert."""
    global WARNUNG
    WARNUNG = ""
    basis = paths.mess_dir()
    d = os.path.join(basis, ordnername(pr)) if pr else basis
    try:
        os.makedirs(d, exist_ok=True)
    except OSError as e:
        if basis == paths.mess_dir_lokal():
            raise
        WARNUNG = f"Ablage {basis} nicht erreichbar ({e.strerror or e}) – lokal gespeichert."
        lokal = paths.mess_dir_lokal()
        d = os.path.join(lokal, ordnername(pr)) if pr else lokal
        os.makedirs(d, exist_ok=True)
    if pr:
        gj = os.path.join(d, "geraet.json")
        try:
            with open(gj, encoding="utf-8") as fh:
                alt = json.load(fh)
        except Exception:
            alt = {}
        neu = dict(pr, angelegt=alt.get("angelegt") or datetime.now().isoformat(timespec="seconds"))
        if {k: v for k, v in alt.items()} != neu:
            with open(gj, "w", encoding="utf-8") as fh:
                json.dump(neu, fh, ensure_ascii=False, indent=1)
    return d


def bezeichnung(pr):
    if not pr:
        return ""
    t = f"{pr['hersteller']} {pr['typ']} · SN {pr['seriennr']}"
    return f"{t} · {pr['auftrag']}" if pr.get("auftrag") else t


# ---------------------------------------------------------------------------
# Kernergebnisse
def _ok(pts, key):
    return [p for p in pts if p.get(key) is not None and not p.get("abbruch")]


def _kanaele(pts):
    seen = []
    for p in pts:
        c = p.get("dir") or p.get("ch")
        if c not in seen:
            seen.append(c)
    return seen


def _ref_1k(pts):
    """Pegel des Punktes am naechsten an 1 kHz (Bezug fuer Frequenzgang)."""
    return min(pts, key=lambda p: abs(math.log10(max(p.get("f") or p["x"], 1) / 1000)))


def zusammenfassung(prog_id, points):
    """Kernergebnisse je Kanal als Liste von {kanal, werte:[(Name, Text)]}."""
    out = []
    for c in _kanaele(points):
        pts = [p for p in points if (p.get("dir") or p.get("ch")) == c]
        w = []
        if prog_id == "fr":
            ok = _ok(pts, "u_true")
            if ok:
                ref = _ref_1k(ok)["u_true"]
                db = [20 * math.log10(p["u_true"] / ref) for p in ok if p["u_true"] > 0]
                fs = [p.get("f") or p["x"] for p in ok]
                w = [("Pegel bei 1 kHz", f"{ref:.4g} V"),
                     ("Abweichung", f"{min(db):+.2f} / {max(db):+.2f} dB"),
                     ("Bereich", f"{_fmt_f(min(fs))} – {_fmt_f(max(fs))}")]
        elif prog_id == "gain":
            ok = _ok(pts, "u_true")
            for p in ok:
                w = [("Ausgangspegel", f"{p['u_true']:.4g} V")]
                if p.get("gain_db") is not None:
                    w.append(("Verstärkung", f"{p['gain_db']:+.2f} dB ({p['gain']:.3g}-fach)"))
                if p.get("p_w") is not None:
                    w.append(("Leistung", f"{p['p_w']:.3g} W"))
        elif prog_id == "thdf":
            ok = _ok(pts, "fnct")
            if ok:
                mx = max(ok, key=lambda p: p["fnct"])
                mn = min(ok, key=lambda p: p["fnct"])
                w = [("THD+N max.", f"{mx['fnct']:.4g} % bei {_fmt_f(mx['x'])}"),
                     ("THD+N min.", f"{mn['fnct']:.4g} % bei {_fmt_f(mn['x'])}")]
        elif prog_id == "thdl":
            ok = _ok(pts, "fnct")
            if ok:
                mn = min(ok, key=lambda p: p["fnct"])
                last = ok[-1]
                w = [("THD+N min.", f"{mn['fnct']:.4g} % bei {_fmt_u(mn.get('u_true'))}"),
                     ("Höchster Pegel", f"{_fmt_u(last.get('u_true'))}: {last['fnct']:.4g} %")]
        elif prog_id == "sn":
            ok = _ok(pts, "sn_db")
            for p in ok:
                w = [("Störabstand", f"{p['sn_db']:.1f} dB"),
                     ("Bezugspegel", _fmt_u(p.get("ref_u"))),
                     ("Rauschen", _fmt_u(p.get("noise_u")))]
        elif prog_id == "xt":
            ok = _ok(pts, "xt_db")
            if ok:
                mx = max(ok, key=lambda p: p["xt_db"])
                w = [("Übersprechen schlechtester Wert", f"{mx['xt_db']:.1f} dB bei {_fmt_f(mx['x'])}")]
        if any(p.get("abbruch") for p in pts):
            w.append(("Hinweis", "Messung abgebrochen"))
        out.append({"kanal": c, "werte": [(n, _komma(v)) for n, v in w]})
    return out


def _komma(t):
    """Dezimalpunkt -> Komma (deutsche Schreibweise wie im Reparaturbericht)."""
    return re.sub(r"(?<=\d)\.(?=\d)", ",", t)


def _fmt_f(f):
    if f is None:
        return "–"
    return f"{f/1000:g} kHz" if f >= 1000 else f"{f:g} Hz"


def _fmt_u(u):
    if u is None:
        return "–"
    return f"{u*1e6:.3g} µV" if u < 1e-3 else f"{u*1e3:.4g} mV" if u < 1 else f"{u:.4g} V"


# ---------------------------------------------------------------------------
# Diagramm
def _logfmt_f(v, _):
    return _komma(f"{v/1000:g}k" if v >= 1000 else f"{v:g}")


def _zahl(v, _):
    return _komma(f"{v:g}")


def _dekaden(ax, werte):
    """Log-Achse auf ganze Dekaden setzen (mindestens eine), nur Hauptstriche beschriften."""
    werte = [w for w in werte if w and w > 0]
    if not werte:
        return
    lo = 10 ** math.floor(math.log10(min(werte)))
    hi = 10 ** math.ceil(math.log10(max(werte)))
    if hi <= lo:
        hi = lo * 10
    return lo, hi


def diagramm(prog_id, titel, points, pfad):
    """PNG fuer Programme mit Kurve. Liefert True, wenn geschrieben."""
    if plt is None or prog_id not in ("fr", "thdf", "thdl", "xt"):
        return False
    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=DPI)
    alle_x, alle_y = [], []
    try:
        for c in _kanaele(points):
            pts = [p for p in points if (p.get("dir") or p.get("ch")) == c and not p.get("abbruch")]
            if prog_id == "fr":
                pts = _ok(pts, "u_true")
                if not pts:
                    continue
                ref = _ref_1k(pts)["u_true"]
                xs = [p.get("f") or p["x"] for p in pts]
                ys = [20 * math.log10(p["u_true"] / ref) for p in pts]
            elif prog_id in ("thdf", "thdl"):
                pts = _ok(pts, "fnct")
                if prog_id == "thdl":
                    pts = [p for p in pts if p.get("u_true")]
                xs = [p["x"] if prog_id == "thdf" else p["u_true"] for p in pts]
                ys = [p["fnct"] for p in pts]
            else:
                pts = _ok(pts, "xt_db")
                xs = [p["x"] for p in pts]
                ys = [p["xt_db"] for p in pts]
            if xs:
                alle_x += xs
                alle_y += ys
                ax.plot(xs, ys, marker="o", ms=3.5, lw=1.6, color=FARBE.get(c), label=f"Kanal {c}")
        ax.set_xscale("log")
        if prog_id == "thdl":
            ax.set_xlabel("Ausgangspegel (V)")
            d = _dekaden(ax, alle_x)
            if d:
                ax.set_xlim(*d)
            ax.xaxis.set_major_formatter(FuncFormatter(_zahl))
            ax.xaxis.set_minor_formatter(NullFormatter())
        else:
            ax.set_xlabel("Frequenz (Hz)")
            ax.xaxis.set_major_formatter(FuncFormatter(_logfmt_f))
        if prog_id == "fr":
            ax.set_ylabel("Pegel re 1 kHz (dB)")
            lo, hi = ax.get_ylim()
            ax.set_ylim(min(lo, -1.0), max(hi, 1.0))
        elif prog_id in ("thdf", "thdl"):
            ax.set_yscale("log")
            ax.set_ylabel("THD+N (%)")
            d = _dekaden(ax, alle_y)
            if d:
                ax.set_ylim(*d)
            ax.yaxis.set_major_locator(LogLocator(base=10))
            ax.yaxis.set_major_formatter(FuncFormatter(_zahl))
            ax.yaxis.set_minor_formatter(NullFormatter())
        else:
            ax.set_ylabel("Übersprechen (dB)")
        if prog_id in ("fr", "xt"):
            ax.yaxis.set_major_formatter(FuncFormatter(_zahl))
        ax.grid(True, which="major", color="#c9ced6", lw=0.7)
        ax.grid(True, which="minor", color="#e6e9ee", lw=0.5)
        ax.set_title(titel, fontsize=10.5, loc="left", color="#2E5A88", fontweight="bold")
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=8, frameon=False)
        fig.tight_layout()
        fig.savefig(pfad, facecolor="white")
        return True
    finally:
        plt.close(fig)


def ruhe_wert(v, ok, ol=False):
    """Text fuer einen Ruhestrom-/Offsetwert mit Bewertung."""
    if v is None:
        return "OL" + (" ✗ Überlauf" if ok is False else "") if ol else "–"
    t = _komma(f"{v:.3f} mV")
    return t + ("" if ok is None else (" ✓" if ok else " ✗ außerhalb Toleranz"))


def _ol_luecken(punkte):
    try:
        from upa_fluke import luecken
    except Exception:
        return []
    return luecken(punkte)


def diagramm_ruhe(titel, punkte, soll, tol, marken, pfad):
    """Verlauf Ruhestrom/Offset ueber der Zeit (mV ueber Minuten) mit Toleranzband."""
    if plt is None:
        return False
    xs = [t / 60.0 for t, v, _ in punkte if v is not None]
    ys = [v for t, v, _ in punkte if v is not None]
    if not xs:
        return False
    # Linie an Messluecken (OL, kein Wert) unterbrechen statt sie zu ueberbruecken
    lx = [t / 60.0 for t, v, _ in punkte]
    ly = [float("nan") if v is None else v for t, v, _ in punkte]
    ol_ab = _ol_luecken(punkte)
    fig, ax = plt.subplots(figsize=(8, 3.9), dpi=DPI)
    try:
        if soll is not None and tol:
            ax.axhspan(soll - tol, soll + tol, color="#2E8B57", alpha=0.12, lw=0, label="Toleranzband")
            ax.axhline(soll, color="#2E8B57", lw=1.0, ls="--", label=_komma(f"Soll {soll:g} mV"))
        ax.plot(lx, ly, color=FARBE["L"], lw=1.4, label="Messwert")
        for i, (a, b, art) in enumerate(ol_ab):
            ax.axvspan(a / 60.0, b / 60.0, color="#C0504D", alpha=0.13, lw=0,
                       label=("Überlauf (OL)" if art == "OL" else "kein Messwert") if i == 0 else None)
        x_max = max(punkte[-1][0] / 60.0, 0.5)
        for m in marken or []:
            ax.axvline(m["t"] / 60.0, color="#7F7F7F", lw=0.8, ls=":")
            if m.get("wert") is not None:
                rechts = m["t"] / 60.0 > 0.85 * x_max          # am rechten Rand nach links schreiben
                ax.annotate(_komma(f"{m['minute']:g} min: {m['wert']:.2f} mV"), (m["t"] / 60.0, m["wert"]),
                            textcoords="offset points", xytext=(-4 if rechts else 4, 6),
                            ha="right" if rechts else "left", fontsize=7.5, color="#333333")
        # Spannungsachse auf Sollband und Werte ab der ersten Zeitmarke ausrichten;
        # Anklemm-/Abgleichspitzen davor duerfen die Skalierung nicht bestimmen.
        ab_t = marken[0]["t"] if marken else 0.0
        fokus = [v for t, v, _ in punkte if v is not None and t >= ab_t] or ys
        lo, hi = min(fokus), max(fokus)
        if soll is not None and tol:
            lo, hi = min(lo, soll - tol), max(hi, soll + tol)
        rand = max((hi - lo) * 0.3, 0.05)
        y_lo, y_hi = lo - rand, hi + rand
        ax.set_ylim(y_lo, y_hi)
        ax.set_xlim(0, x_max)
        if min(ys) < y_lo or max(ys) > y_hi:
            fig.text(0.01, 0.02, _komma(f"Achse ab {marken[0]['minute']:g} min skaliert, "
                                        "Spitzen davor abgeschnitten"),
                     fontsize=7.5, color="#7F7F7F")
        ax.set_xlabel("Zeit (min)")
        ax.set_ylabel("Spannung (mV)")
        ax.xaxis.set_major_formatter(FuncFormatter(_zahl))
        ax.yaxis.set_major_formatter(FuncFormatter(_zahl))
        ax.grid(True, color="#c9ced6", lw=0.7)
        ax.set_title(titel, fontsize=10.5, loc="left", color="#2E5A88", fontweight="bold")
        ax.tick_params(labelsize=8)
        # Legende unter dem Diagramm (rechts), damit sie keine Messwerte verdeckt;
        # links daneben ggf. der Hinweis zur abgeschnittenen Achse
        h, l = ax.get_legend_handles_labels()
        fig.legend(h, l, fontsize=8, frameon=False, loc="lower right", bbox_to_anchor=(0.995, 0.0),
                   ncol=len(h), handlelength=1.8, columnspacing=1.4)
        fig.tight_layout(rect=(0, 0.07, 1, 1))
        fig.savefig(pfad, facecolor="white")
        return True
    finally:
        plt.close(fig)


# ---------------------------------------------------------------------------
# Liste der Messungen
def eintrag_speichern(ordner_, eintrag):
    pj = os.path.join(ordner_, "messungen.json")
    try:
        with open(pj, encoding="utf-8") as fh:
            liste = json.load(fh)
    except Exception:
        liste = []
    liste.append(eintrag)
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump(liste, fh, ensure_ascii=False, indent=1)


def _schrift_sichtbar(pt):
    """Zeichnet Ziffern in der Diagrammschrift und prueft, ob Pixel gesetzt wurden
    (Schutz gegen leere Pixelschrift-Groessen der Calibri, siehe DPI)."""
    import io
    fig = plt.figure(figsize=(2, 0.5), dpi=DPI)
    try:
        fig.text(0.05, 0.3, "0123456789 mV", fontsize=pt)
        buf = io.BytesIO()
        fig.savefig(buf, format="rgba", facecolor="white")
    finally:
        plt.close(fig)
    return any(b < 128 for b in buf.getvalue()[0::4])


def selbsttest(ziel_ordner):
    """Diagramm aus Beispieldaten erzeugen (Pruefung der installierten Version).
    Liefert den Pfad der PNG oder wirft eine Ausnahme."""
    if plt is None:
        raise RuntimeError("matplotlib fehlt")
    fs = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    pts = [{"ch": c, "x": f, "f": f, "u_true": 0.5 * (1 - 0.004 * (f / 20000) ** 2)}
           for c in ("L", "R") for f in fs]
    for pt in (7.5, 8, 10.5):
        if not _schrift_sichtbar(pt):
            raise RuntimeError(f"Diagrammschrift {pt} pt wird bei {DPI} dpi nicht gezeichnet")
    os.makedirs(ziel_ordner, exist_ok=True)
    pfad = os.path.join(ziel_ordner, "selbsttest_frequenzgang.png")
    if not diagramm("fr", "Selbsttest Frequenzgang", pts, pfad) or os.path.getsize(pfad) < 5000:
        raise RuntimeError("Diagramm nicht erzeugt")
    zusammenfassung("fr", pts)
    return pfad
