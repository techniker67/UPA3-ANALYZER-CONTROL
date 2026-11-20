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
    from matplotlib.ticker import FuncFormatter, NullFormatter, LogLocator
except Exception:
    plt = None

FELDER = (("hersteller", "Hersteller"), ("typ", "Typ"), ("seriennr", "Seriennummer"))
FARBE = {"L": "#1f5fbf", "R": "#c8323c", "L→R": "#1f5fbf", "R→L": "#c8323c"}


# ---------------------------------------------------------------------------
# Pruefling / Ordner
def pruefling_pruefen(d):
    """Eingabe bereinigen. Liefert dict oder None (= kein Pruefling)."""
    if not d:
        return None
    pr = {k: re.sub(r"\s+", " ", str(d.get(k, "") or "")).strip()[:60] for k, _ in FELDER}
    if not any(pr.values()):
        return None
    fehlt = [n for k, n in FELDER if not pr[k]]
    if fehlt:
        raise ValueError("Bitte ausfüllen: " + ", ".join(fehlt))
    return pr


def _sicher(s):
    s = re.sub(r'[\\/:*?"<>|]+', "-", s).strip(" .")
    return re.sub(r"\s+", " ", s) or "unbekannt"


def ordnername(pr):
    return "_".join(_sicher(pr[k]) for k, _ in FELDER)


def ordner(pr):
    """Messordner: Geraeteordner oder (ohne Pruefling) Messungen/ direkt."""
    d = os.path.join(paths.mess_dir(), ordnername(pr)) if pr else paths.mess_dir()
    os.makedirs(d, exist_ok=True)
    if pr:
        gj = os.path.join(d, "geraet.json")
        if not os.path.exists(gj):
            with open(gj, "w", encoding="utf-8") as fh:
                json.dump(dict(pr, angelegt=datetime.now().isoformat(timespec="seconds")),
                          fh, ensure_ascii=False, indent=1)
    return d


def bezeichnung(pr):
    return f"{pr['hersteller']} {pr['typ']} · SN {pr['seriennr']}" if pr else ""


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
    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
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
        ax.set_title(titel, fontsize=10, loc="left")
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=8, frameon=False)
        fig.tight_layout()
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


def selbsttest(ziel_ordner):
    """Diagramm aus Beispieldaten erzeugen (Pruefung der installierten Version).
    Liefert den Pfad der PNG oder wirft eine Ausnahme."""
    if plt is None:
        raise RuntimeError("matplotlib fehlt")
    fs = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    pts = [{"ch": c, "x": f, "f": f, "u_true": 0.5 * (1 - 0.004 * (f / 20000) ** 2)}
           for c in ("L", "R") for f in fs]
    os.makedirs(ziel_ordner, exist_ok=True)
    pfad = os.path.join(ziel_ordner, "selbsttest_frequenzgang.png")
    if not diagramm("fr", "Selbsttest Frequenzgang", pts, pfad) or os.path.getsize(pfad) < 5000:
        raise RuntimeError("Diagramm nicht erzeugt")
    zusammenfassung("fr", pts)
    return pfad
