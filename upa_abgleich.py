"""Abgleichliste eines Geraets (aus dem Service-Manual, z. B. im Chat erstellt).

Die Liste ist eine JSON-Datei. Beim Laden wird sie geprueft und in den
Geraeteordner des Prueflings kopiert (also auch auf das NAS, wenn dort die
Ablage liegt). Ist-Werte je Schritt werden in derselben Datei unter
"ergebnisse" gespeichert. Daraus entsteht das PDF-Abgleichblatt.

Format (Version 1):
{
  "format": "upa-abgleich", "version": 1,
  "geraet": {"hersteller": "Sony", "typ": "TC-K770ES"},
  "quelle": "Service Manual S. 13-16",
  "bezug_v": 0.775,                       # 0 dB im Manual = x V
  "schritte": [
    {"nr": "3", "titel": "Wiedergabepegel", "einsteller": "RV101 (L), RV201 (R)",
     "band": "P-4-L300 (315 Hz, 0 dB)", "anschluss": "LINE OUT, 47 kOhm",
     "generator": null,                   # oder {"f": 315, "v": 0.245}
     "messung": "pegel",                  # pegel | frequenz | info
     "soll_v": 0.44, "min_v": 0.42, "max_v": 0.46,    # optional
     "soll_f": 3000, "min_f": 2985, "max_f": 3015,    # bei "frequenz"
     "soll_text": "0,42-0,46 V, L/R < 0,5 dB", "hinweis": "..."}
  ]
}
"""

import json
import math
import os
import re
from datetime import datetime

import upa_protokoll as protokoll

FORMAT = "upa-abgleich"
MESSUNGEN = ("pegel", "frequenz", "info")
MAX_SCHRITTE = 200


def _txt(v, n=200):
    return " ".join(str(v or "").split())[:n]


def _zahl(v, lo, hi, name):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: keine Zahl ({v!r})")
    if not (lo <= x <= hi) or math.isnan(x):
        raise ValueError(f"{name}: {x} ausserhalb {lo}..{hi}")
    return x


def pruefen(d):
    """Liste pruefen und bereinigen. Wirft ValueError mit verstaendlichem Text."""
    if not isinstance(d, dict) or d.get("format") != FORMAT:
        raise ValueError('Keine Abgleichliste (Feld "format": "upa-abgleich" fehlt)')
    g = d.get("geraet") or {}
    out = {"format": FORMAT, "version": 1,
           "geraet": {"hersteller": _txt(g.get("hersteller"), 60), "typ": _txt(g.get("typ"), 60)},
           "quelle": _txt(d.get("quelle"), 200),
           "bezug_v": _zahl(d.get("bezug_v", 0.775), 0.001, 100, "bezug_v") or 0.775,
           "schritte": [], "ergebnisse": {}}
    sch = d.get("schritte")
    if not isinstance(sch, list) or not sch:
        raise ValueError("Die Liste enthält keine Schritte")
    if len(sch) > MAX_SCHRITTE:
        raise ValueError(f"Höchstens {MAX_SCHRITTE} Schritte")
    nrs = set()
    for i, s in enumerate(sch, 1):
        if not isinstance(s, dict):
            raise ValueError(f"Schritt {i}: kein Objekt")
        wo = f"Schritt {s.get('nr', i)}"
        nr = _txt(s.get("nr", i), 12) or str(i)
        if nr in nrs:
            nr = f"{nr}.{i}"
        nrs.add(nr)
        m = s.get("messung", "info")
        if m not in MESSUNGEN:
            raise ValueError(f"{wo}: messung muss pegel, frequenz oder info sein")
        gen = s.get("generator")
        if gen:
            gen = {"f": _zahl(gen.get("f"), 10, 100000, wo + " Generator f"),
                   "v": _zahl(gen.get("v"), 0.001, 5, wo + " Generator V")}
            if gen["f"] is None or gen["v"] is None:
                raise ValueError(f"{wo}: Generator braucht f und v")
        e = {"nr": nr, "titel": _txt(s.get("titel"), 80) or wo, "einsteller": _txt(s.get("einsteller"), 80),
             "band": _txt(s.get("band"), 80), "anschluss": _txt(s.get("anschluss"), 80),
             "generator": gen or None, "messung": m,
             "soll_v": _zahl(s.get("soll_v"), 1e-7, 100, wo + " soll_v"),
             "min_v": _zahl(s.get("min_v"), 1e-7, 100, wo + " min_v"),
             "max_v": _zahl(s.get("max_v"), 1e-7, 100, wo + " max_v"),
             "soll_f": _zahl(s.get("soll_f"), 1, 100000, wo + " soll_f"),
             "min_f": _zahl(s.get("min_f"), 1, 100000, wo + " min_f"),
             "max_f": _zahl(s.get("max_f"), 1, 100000, wo + " max_f"),
             "soll_text": _txt(s.get("soll_text"), 120), "hinweis": _txt(s.get("hinweis"), 400)}
        if e["min_v"] and e["max_v"] and e["min_v"] > e["max_v"]:
            raise ValueError(f"{wo}: min_v größer als max_v")
        if e["min_f"] and e["max_f"] and e["min_f"] > e["max_f"]:
            raise ValueError(f"{wo}: min_f größer als max_f")
        out["schritte"].append(e)
    erg = d.get("ergebnisse")
    if isinstance(erg, dict):
        for k, v in erg.items():
            if k in nrs and isinstance(v, dict):
                out["ergebnisse"][k] = {kk: v.get(kk) for kk in ("l", "r", "f", "ok", "zeit", "notiz")}
    return out


def dateiname(liste):
    g = liste["geraet"]
    roh = f"Abgleichliste_{g['hersteller']}_{g['typ']}".strip("_")
    return re.sub(r'[\\/:*?"<>|\s]+', "_", roh) + ".json"


def finden(ordner):
    """Pfad der Abgleichliste im Geraeteordner (neueste), sonst None."""
    try:
        namen = sorted(n for n in os.listdir(ordner) if n.startswith("Abgleichliste_") and n.endswith(".json"))
    except OSError:
        return None
    if not namen:
        return None
    return max((os.path.join(ordner, n) for n in namen), key=os.path.getmtime)


def laden(ordner):
    p = finden(ordner)
    if not p:
        return None, None
    with open(p, encoding="utf-8") as fh:
        return pruefen(json.load(fh)), p


def speichern(ordner, liste, pfad=None):
    pfad = pfad or os.path.join(ordner, dateiname(liste))
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(liste, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, pfad)
    return pfad


def ergebnis(ordner, nr, werte):
    """Ist-Werte eines Schritts speichern (l/r in V, f in Hz, ok, notiz)."""
    liste, pfad = laden(ordner)
    if not liste:
        raise ValueError("Keine Abgleichliste im Geräteordner")
    s = next((s for s in liste["schritte"] if s["nr"] == str(nr)), None)
    if not s:
        raise ValueError("Schritt nicht gefunden")
    e = {"zeit": datetime.now().strftime("%d.%m.%Y %H:%M")}
    for k in ("l", "r", "f"):
        v = werte.get(k)
        e[k] = float(v) if isinstance(v, (int, float)) and math.isfinite(v) else None
    e["ok"] = werte.get("ok") if werte.get("ok") in (True, False) else bewerten(s, e)
    e["notiz"] = _txt(werte.get("notiz"), 200)
    if werte.get("loeschen"):
        liste["ergebnisse"].pop(s["nr"], None)
    else:
        liste["ergebnisse"][s["nr"]] = e
    speichern(ordner, liste, pfad)
    return liste


def bewerten(s, e):
    """True/False, wenn Soll-Grenzen bekannt sind, sonst None."""
    ok = None
    if s["messung"] == "pegel" and (s["min_v"] or s["max_v"]):
        ws = [w for w in (e.get("l"), e.get("r")) if w]
        if ws:
            ok = all((not s["min_v"] or w >= s["min_v"]) and (not s["max_v"] or w <= s["max_v"]) for w in ws)
    if s["messung"] == "frequenz" and (s["min_f"] or s["max_f"]) and e.get("f"):
        f = e["f"]
        ok = (not s["min_f"] or f >= s["min_f"]) and (not s["max_f"] or f <= s["max_f"])
    return ok


# ---------------------------------------------------------------------------
def _v(x):
    if not x:
        return ""
    a = abs(x)
    if a >= 1:
        return f"{x:.3f} V".replace(".", ",")
    if a >= 1e-3:
        return f"{x * 1e3:.4g} mV".replace(".", ",")
    return f"{x * 1e6:.4g} µV".replace(".", ",")


def _f(x):
    if not x:
        return ""
    return (f"{x / 1000:g} kHz" if x >= 1000 else f"{x:g} Hz").replace(".", ",")


def soll(s):
    if s["soll_text"]:
        return s["soll_text"]
    if s["messung"] == "pegel":
        if s["min_v"] and s["max_v"]:
            return f"{_v(s['min_v'])} – {_v(s['max_v'])}"
        return _v(s["soll_v"])
    if s["messung"] == "frequenz":
        if s["min_f"] and s["max_f"]:
            return f"{_f(s['min_f'])} – {_f(s['max_f'])}"
        return _f(s["soll_f"])
    return ""


def generator(s):
    g = s["generator"]
    return f"{_f(g['f'])} · {_v(g['v'])}" if g else (s["band"] or "–")


def abgleichblatt(ordner, firma="", version=""):
    """PDF-Abgleichblatt im Hausstil in den Geraeteordner. Liefert den Dateinamen."""
    liste, _ = laden(ordner)
    if not liste:
        raise ValueError("Keine Abgleichliste im Geräteordner")
    if protokoll.A4 is None:
        raise RuntimeError("reportlab fehlt – PDF nicht möglich")
    g = liste["geraet"]
    try:
        gr = protokoll.geraet(ordner)
    except Exception:
        gr = {}
    sn = gr.get("seriennr") or ""
    erg = liste["ergebnisse"]
    zeilen = []
    for s in liste["schritte"]:
        e = erg.get(s["nr"]) or {}
        ist = " / ".join(x for x in (_v(e.get("l")) and "L " + _v(e.get("l")),
                                       _v(e.get("r")) and "R " + _v(e.get("r")),
                                       e.get("f") and _f(round(e["f"], 1))) if x)
        ok = {True: "✓", False: "✗"}.get(e.get("ok"), "")
        zeilen.append([s["nr"], s["titel"] + (f" ({s['einsteller']})" if s["einsteller"] else ""),
                       generator(s), soll(s), ist or "", ok])
    bl = [("titel", "ABGLEICHBLATT"),
          ("untertitel", f"{g['hersteller'].upper()} {g['typ']}"),
          ("grau", " · ".join(x for x in (f"Seriennummer {sn}" if sn else "", liste["quelle"],
                                           f"0 dB im Manual = {_v(liste['bezug_v'])}") if x)),
          ("datum", f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')}"),
          ("h1", "1. Abgleichschritte"),
          ("tabelle", ["Nr.", "Schritt (Einsteller)", "Generator / Band", "Soll", "Ist", "OK"],
           zeilen, [0.6, 3.2, 2.0, 2.2, 2.4, 0.6], False)]
    hinw = [s for s in liste["schritte"] if s["hinweis"] or s["anschluss"]]
    if hinw:
        bl.append(("h1", "2. Hinweise je Schritt"))
        bl.append(("tabelle", ["Nr.", "Anschluss", "Hinweis"],
                   [[s["nr"], s["anschluss"], s["hinweis"]] for s in hinw], [0.6, 2.6, 7.0], False))
    notizen = [(s["nr"], erg[s["nr"]].get("notiz")) for s in liste["schritte"]
               if s["nr"] in erg and erg[s["nr"]].get("notiz")]
    if notizen:
        bl.append(("h1", "3. Notizen"))
        bl.append(("tabelle", ["Nr.", "Notiz"], [[n, t] for n, t in notizen], [0.6, 9.6], False))
    bl.append(("unterschrift", None))
    name = f"Abgleichblatt_{dateiname(liste)[len('Abgleichliste_'):-5]}_{datetime.now().strftime('%Y%m%d-%H%M')}.pdf"
    kopf = f"Abgleichblatt  |  {g['hersteller'].upper()} {g['typ']}" + (f"  |  SN {sn}" if sn else "")
    fuss = "  |  ".join(t for t in (firma, f"Abgleichblatt · UPA-Analyzer-Control v{version}") if t)
    protokoll.pdf(bl, os.path.join(ordner, name), kopf, fuss)
    return name
