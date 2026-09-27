"""
La Carte — Générateur PDF Audit Complet

Principes de mise en page :
  - Une section sans aucune donnée n'est pas générée (et disparaît du sommaire).
  - Dans une section, chaque bloc vide (tableau, liste, KPI, ligne) est omis.
  - Tous les textes passent à la ligne au lieu de déborder ; les blocs trop
    longs continuent sur une nouvelle page (en-têtes de tableau répétés).
  - Numéros de section, pagination « n / total » et sommaire calculés
    automatiquement (rendu en deux passes).
"""

import io
import re
import unicodedata

from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

# ─── PALETTE ──────────────────────────────────────────────────────────────────
BG       = (0.082, 0.122, 0.165)
BG_BAND  = (0.102, 0.145, 0.208)
GOLD     = (0.788, 0.659, 0.298)
GOLD_DIM = (0.620, 0.522, 0.251)
TEXT     = (0.933, 0.902, 0.788)
MUTED    = (0.722, 0.667, 0.541)
RED      = (0.75, 0.25, 0.25)
ORANGE   = (0.80, 0.55, 0.10)
GREEN    = (0.25, 0.60, 0.30)

W, H    = A4
ML      = 18*mm
MR      = W - 18*mm
CW      = MR - ML                 # largeur utile
TOP     = H - 35*mm               # haut de la zone de contenu
BOTTOM  = 20*mm                   # bas de la zone de contenu (au-dessus du pied de page)

# ─── TEXTE : NETTOYAGE & DÉTECTION DU VIDE ────────────────────────────────────
_REPL = {
    "−": "-", "‐": "-", "‑": "-",
    " ": " ", " ": " ", " ": " ", " ": " ",
    "⚠": "!", "✓": "", "✔": "", "✅": "", "❌": "",
    "◄": "", "►": "", "→": "->", "←": "<-",
    "≤": "<=", "≥": ">=", "≈": "~",
    "\t": " ", "\r": "",
}

def clean(s):
    """Texte affichable avec les polices standard (Helvetica / WinAnsi).
    Les emojis et symboles non supportés (qui s'affichaient en carrés) sont retirés."""
    if s is None:
        return ""
    s = str(s)
    for a, b in _REPL.items():
        s = s.replace(a, b)
    out = []
    for ch in s:
        if ch == "\n":
            out.append(ch); continue
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch).encode("cp1252", "ignore").decode("cp1252")
            out.append(base)
    s = "".join(out)
    s = re.sub(r"[ ]{2,}", " ", s)
    return "\n".join(line.strip() for line in s.split("\n")).strip()

def is_empty(x):
    if x is None:
        return True
    if isinstance(x, str):
        return clean(x).strip() in ("", "—", "-", "–", "N/A", "n/a")
    if isinstance(x, (int, float)):
        return False
    if isinstance(x, dict):
        return all(is_empty(v_) for v_ in x.values())
    if isinstance(x, (list, tuple)):
        return all(is_empty(v_) for v_ in x)
    return False

def filled(x):
    return not is_empty(x)

def g(d, *keys):
    """Valeur imbriquée nettoyée, ou '' si absente / vide."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        elif isinstance(cur, list) and isinstance(k, int) and k < len(cur):
            cur = cur[k]
        else:
            return ""
    return "" if is_empty(cur) else clean(cur)

def lst(d, *keys):
    cur = d
    for k in keys:
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur if isinstance(cur, list) else []

def dash(x):
    return x if filled(x) else "—"

def pct_value(s):
    """Extrait un nombre d'une chaîne type '-1.9%', '8,5 %'. None si absent."""
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(s or ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None

def strip_class(s):
    """'⭐ Star' -> 'Star'"""
    return clean(s).strip()

def alert_level(niveau, default="orange"):
    n = str(niveau or "").lower()
    if "critique" in n or "rouge" in n or "\U0001f534" in n:
        return "rouge"
    if "attention" in n or "orange" in n or "\U0001f7e1" in n:
        return "orange"
    if "ok" in n or "vert" in n or "\U0001f7e2" in n:
        return "vert"
    return default

# ─── MOTEUR DE MISE EN PAGE ───────────────────────────────────────────────────
def rgb(t):
    return colors.Color(*t)

def wrap(text, width, font="Helvetica", size=8):
    """Découpe en lignes tenant dans `width`. Respecte les retours à la ligne,
    transforme les puces '- ' en '• ', coupe les mots trop longs."""
    lines = []
    for para in clean(text).split("\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("- ") or para.startswith("* "):
            para = "• " + para[2:].strip()
        line = ""
        for word in para.split(" "):
            test = f"{line} {word}".strip()
            if stringWidth(test, font, size) <= width:
                line = test
                continue
            if line:
                lines.append(line)
            while stringWidth(word, font, size) > width and len(word) > 1:
                cut = len(word)
                while cut > 1 and stringWidth(word[:cut], font, size) > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            line = word
        if line:
            lines.append(line)
    return lines

def fit_size(text, width, font, size, min_size=7):
    while size > min_size and stringWidth(text, font, size) > width:
        size -= 0.5
    return size


class Doc:
    def __init__(self, buf, data, total=None, toc=None):
        self.c = canvas.Canvas(buf, pagesize=A4)
        self.data = data
        self.restaurant = g(data, "infos", "restaurant") or "Audit Complet"
        self.date = g(data, "infos", "date")
        self.total = total
        self.toc_in = toc or []
        self.toc = []             # [(num, titre, page_debut, page_fin)]
        self.page = 1
        self.label = ""
        self.y = TOP
        self.sec_num = 0

    # ── couleurs / texte ─────────────────────────────────────────────────────
    def fill(self, t): self.c.setFillColor(rgb(t))
    def stroke(self, t): self.c.setStrokeColor(rgb(t))

    def text(self, x, y, s, font="Helvetica", size=8, col=TEXT, align="left"):
        self.c.setFont(font, size); self.fill(col)
        s = clean(s)
        if align == "right":
            self.c.drawRightString(x, y, s)
        elif align == "center":
            self.c.drawCentredString(x, y, s)
        else:
            self.c.drawString(x, y, s)

    # ── pages ────────────────────────────────────────────────────────────────
    def _header_footer(self):
        c = self.c
        self.fill(BG_BAND); c.rect(0, H - 22*mm, W, 22*mm, fill=1, stroke=0)
        self.fill(GOLD); c.rect(0, H - 23*mm, W, 0.7*mm, fill=1, stroke=0)
        self.text(ML, H - 13*mm, "LA CARTE", "Helvetica-Bold", 11, GOLD)
        self.text(ML, H - 17*mm, "CONSEIL & STRATÉGIE CHR", "Helvetica", 7, MUTED)
        if self.label:
            self.text(W/2, H - 14*mm, self.label.upper(), "Helvetica-Bold", 9, TEXT, "center")
        total = self.total if self.total else "…"
        self.text(MR, H - 14*mm, f"{self.page} / {total}", "Helvetica", 8, MUTED, "right")
        self.fill(GOLD); c.rect(0, 11*mm, W, 0.5*mm, fill=1, stroke=0)
        self.fill(BG_BAND); c.rect(0, 0, W, 11*mm, fill=1, stroke=0)
        left = f"Audit Complet — {self.restaurant}" + (f" — {self.date}" if self.date else "")
        self.text(ML, 4*mm, left, "Helvetica", 7, MUTED)
        self.text(MR, 4*mm, "Document confidentiel — lacarte-conseil.fr", "Helvetica", 7, MUTED, "right")

    def new_page(self, label=None):
        self.c.showPage()
        self.page += 1
        if label is not None:
            self.label = label
        self.fill(BG); self.c.rect(0, 0, W, H, fill=1, stroke=0)
        self._header_footer()
        self.y = TOP
        if self.toc:
            n, t, p0, _ = self.toc[-1]
            if self.label == t:
                self.toc[-1] = (n, t, p0, self.page)

    def room(self):
        return self.y - BOTTOM

    def need(self, h):
        """Garantit `h` de place ; sinon passe à la page suivante."""
        if self.y - h < BOTTOM:
            self.new_page()
            return True
        return False

    def gap(self, h=3*mm):
        self.y -= h

    # ── blocs ────────────────────────────────────────────────────────────────
    def section(self, title, subtitle="", header_label=None):
        self.sec_num += 1
        num = f"{self.sec_num:02d}"
        self.label = header_label or title
        self.new_page()
        self.toc.append((num, title, self.page, self.page))
        self.label = title
        c = self.c; y = self.y
        self.fill(GOLD); c.rect(ML, y - 11*mm, 1.2*mm, 13*mm, fill=1, stroke=0)
        self.text(ML + 5*mm, y - 3*mm, f"{num}.", "Helvetica-Bold", 15, GOLD)
        self.text(ML + 15*mm, y - 3*mm, title.upper(), "Helvetica-Bold", 13, TEXT)
        if subtitle:
            self.text(ML + 15*mm, y - 8.5*mm, subtitle, "Helvetica", 8, MUTED)
        self.y = y - 18*mm

    def sub(self, title, keep=12*mm):
        """Sous-titre ; `keep` = hauteur minimale du contenu qui doit le suivre."""
        self.need(9*mm + keep)
        c = self.c; y = self.y
        self.fill(BG_BAND); c.rect(ML, y - 7*mm, CW, 7*mm, fill=1, stroke=0)
        self.fill(GOLD_DIM); c.rect(ML, y - 7*mm, 0.8*mm, 7*mm, fill=1, stroke=0)
        self.text(ML + 4*mm, y - 4.6*mm, title.upper(), "Helvetica-Bold", 9, GOLD)
        self.y = y - 11*mm

    def para(self, s, font="Helvetica", size=8, col=TEXT, indent=2*mm, line_h=4.2*mm):
        for ln in wrap(s, CW - 2*indent, font, size):
            self.need(line_h)
            self.text(ML + indent, self.y - 3.2*mm, ln, font, size, col)
            self.y -= line_h
        self.y -= 3*mm

    def lv_rows(self, pairs):
        """Lignes label / valeur ; les valeurs vides sont omises."""
        pairs = [(l, v_, col) for l, v_, col in pairs if filled(v_)]
        vx = ML + 62*mm; vw = MR - vx
        for label, val, col in pairs:
            lines = wrap(val, vw, "Helvetica", 9)
            llines = wrap(label, 58*mm, "Helvetica-Bold", 8)
            h = max(len(lines), len(llines)) * 4.4*mm + 1.8*mm
            self.need(h)
            y = self.y - 3.6*mm
            for i, ln in enumerate(llines):
                self.text(ML + 2*mm, y - i*4.4*mm, ln, "Helvetica-Bold", 8, MUTED)
            for i, ln in enumerate(lines):
                self.text(vx, y - i*4.4*mm, ln, "Helvetica", 9, col or TEXT)
            self.y -= h
        if pairs:
            self.y -= 2*mm
        return bool(pairs)

    def kpis(self, items):
        """items = [(label, valeur, couleur)] — les KPIs vides sont omis."""
        items = [it for it in items if filled(it[1])]
        if not items:
            return False
        hk = 18*mm
        self.need(hk + 4*mm)
        n = len(items); gapx = 3*mm
        kw = (CW - (n - 1) * gapx) / n
        kx = ML; y = self.y
        for label, val, col in items:
            self.fill(BG_BAND); self.c.roundRect(kx, y - hk, kw, hk, 2*mm, fill=1, stroke=0)
            self.stroke(GOLD_DIM); self.c.setLineWidth(0.4)
            self.c.roundRect(kx, y - hk, kw, hk, 2*mm, fill=0, stroke=1)
            for li, ln in enumerate(label.split("\n")):
                self.text(kx + kw/2, y - 5*mm - li*3.6*mm, ln, "Helvetica-Bold", 7, MUTED, "center")
            val = clean(val)
            size = fit_size(val, kw - 6*mm, "Helvetica-Bold", 13)
            self.text(kx + kw/2, y - 14.5*mm, val, "Helvetica-Bold", size, col, "center")
            kx += kw + gapx
        self.y = y - hk - 4*mm
        return True

    def table(self, headers, rows, widths, col_colors=None):
        """Tableau à hauteur de ligne variable ; lignes vides omises ;
        en-tête répété en cas de changement de page."""
        rows = [[clean(c_) if filled(c_) else "—" for c_ in r] for r in rows if filled(list(r))]
        if not rows:
            return False
        scale = CW / sum(widths)
        widths = [w_ * scale for w_ in widths]
        fs = 7.5; lh = 3.5*mm; pad = 2*mm; hh = 7*mm

        def header():
            y = self.y
            self.fill(GOLD_DIM); self.c.rect(ML, y - hh, CW, hh, fill=1, stroke=0)
            x = ML
            for i, hd in enumerate(headers):
                hs = fit_size(clean(hd), widths[i] - 2*pad, "Helvetica-Bold", 7.5, 5.5)
                self.text(x + pad, y - hh + 2.4*mm, hd, "Helvetica-Bold", hs, BG)
                x += widths[i]
            self.y = y - hh
            return y

        def frame(top):
            self.stroke(GOLD); self.c.setLineWidth(0.5)
            self.c.rect(ML, self.y, CW, top - self.y, fill=0, stroke=1)

        cells = [[wrap(cell, widths[i] - 2*pad, "Helvetica", fs) or ["—"] for i, cell in enumerate(r)] for r in rows]
        first_h = max(len(x) for x in cells[0]) * lh + 3.4*mm
        self.need(hh + first_h + 2*mm)
        top = header()
        for ri, rc in enumerate(cells):
            rh = max(len(x) for x in rc) * lh + 3.4*mm
            if self.y - rh < BOTTOM:
                frame(top)
                self.new_page()
                top = header()
            y = self.y
            self.fill(BG_BAND if ri % 2 == 0 else BG)
            self.c.rect(ML, y - rh, CW, rh, fill=1, stroke=0)
            self.stroke(GOLD_DIM); self.c.setLineWidth(0.2)
            self.c.line(ML, y - rh, MR, y - rh)
            x = ML
            for ci, lines in enumerate(rc):
                col = (col_colors or {}).get(ci, TEXT)
                for li, ln in enumerate(lines):
                    self.text(x + pad, y - 2.9*mm - li*lh - 0.3*mm, ln, "Helvetica", fs, col)
                x += widths[ci]
            self.y = y - rh
        frame(top)
        self.y -= 5*mm
        return True

    def table_height(self, rows, widths):
        rows = [r for r in rows if filled(list(r))]
        scale = CW / sum(widths); ws = [w_ * scale for w_ in widths]
        h = 7*mm + 5*mm
        for r in rows:
            n = max(len(wrap(c_ if filled(c_) else "—", ws[i] - 4*mm, "Helvetica", 7.5) or [""]) for i, c_ in enumerate(r))
            h += n * 3.5*mm + 3.4*mm
        return h

    def sub_table(self, title, headers, rows, widths, col_colors=None):
        """Sous-titre + tableau ; un tableau court n'est jamais coupé de son titre ni scindé."""
        h = self.table_height(rows, widths)
        self.sub(title, keep=h if h < 90*mm else 20*mm)
        return self.table(headers, rows, widths, col_colors)

    def card(self, title, body="", right="", right2="", accent=GOLD, number=None,
             title_col=GOLD, rounded=True):
        """Carte à hauteur variable (titre + texte libre + valeurs à droite)."""
        left_x = ML + (13*mm if number is not None else 6*mm)
        right_w = 0
        for r_, f_ in ((right, "Helvetica-Bold"), (right2, "Helvetica")):
            if filled(r_):
                right_w = max(right_w, min(stringWidth(clean(r_), f_, 8), 60*mm) + 4*mm)
        tw = MR - 3*mm - right_w - left_x
        tlines = wrap(title.upper() if title else "", tw, "Helvetica-Bold", 9)
        rlines = wrap(right, 60*mm, "Helvetica-Bold", 8) if filled(right) else []
        r2lines = wrap(right2, 60*mm, "Helvetica", 7.5) if filled(right2) else []
        head_n = max(len(tlines), len(rlines) + len(r2lines), 1)
        blines = wrap(body, MR - 4*mm - left_x, "Helvetica", 8) if filled(body) else []
        h = 3.2*mm + head_n * 4.3*mm + len(blines) * 3.9*mm + 2.6*mm
        max_h = TOP - BOTTOM - 2*mm
        overflow = []
        if h > max_h:                       # carte plus haute qu'une page : le reste passe en paragraphe
            keep = int((max_h - 3.2*mm - head_n*4.3*mm - 2.6*mm) / (3.9*mm))
            overflow, blines = blines[keep:], blines[:keep]
            h = 3.2*mm + head_n * 4.3*mm + len(blines) * 3.9*mm + 2.6*mm
        self.need(h + 3*mm)
        c = self.c; y = self.y
        self.fill(BG_BAND)
        if rounded:
            c.roundRect(ML, y - h, CW, h, 1.5*mm, fill=1, stroke=0)
        else:
            c.rect(ML, y - h, CW, h, fill=1, stroke=0)
        if number is not None:
            self.fill(accent); c.circle(ML + 6*mm, y - 6.5*mm, 3.5*mm, fill=1, stroke=0)
            self.text(ML + 6*mm, y - 7.9*mm, str(number), "Helvetica-Bold", 9, BG, "center")
        else:
            self.fill(accent); c.rect(ML, y - h, 2*mm, h, fill=1, stroke=0)
        ty = y - 5.4*mm
        for i, ln in enumerate(tlines):
            self.text(left_x, ty - i*4.3*mm, ln, "Helvetica-Bold", 9, title_col)
        for i, ln in enumerate(rlines):
            self.text(MR - 3*mm, ty - i*4.3*mm, ln, "Helvetica-Bold", 8, GOLD, "right")
        for i, ln in enumerate(r2lines):
            self.text(MR - 3*mm, ty - (len(rlines) + i)*4.3*mm, ln, "Helvetica", 7.5, MUTED, "right")
        by = y - 3.2*mm - head_n*4.3*mm - 2.4*mm
        for i, ln in enumerate(blines):
            self.text(left_x, by - i*3.9*mm, ln, "Helvetica", 8, TEXT)
        self.y = y - h - 3*mm
        if overflow:
            self.para("\n".join(overflow), indent=left_x - ML)

    def alert(self, level, label, detail=""):
        col = {"rouge": RED, "orange": ORANGE, "vert": GREEN}.get(level, MUTED)
        self.card(label, detail, accent=col, title_col=TEXT, rounded=False)

    def bullets(self, items, col):
        for it in items:
            lines = wrap(it, CW - 14*mm, "Helvetica", 8.5)
            h = len(lines) * 4.3*mm + 2.2*mm
            self.need(h)
            y = self.y
            self.fill(col); self.c.circle(ML + 7*mm, y - 2.9*mm, 1.2*mm, fill=1, stroke=0)
            for i, ln in enumerate(lines):
                self.text(ML + 12*mm, y - 4*mm - i*4.3*mm, ln, "Helvetica", 8.5, TEXT)
            self.y = y - h


# ─── COUVERTURE ───────────────────────────────────────────────────────────────
def page_cover(doc, d):
    c = doc.c
    restaurant = doc.restaurant
    ville = g(d, "infos", "ville"); auditeur = g(d, "infos", "auditeur"); date = doc.date
    doc.fill(BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    doc.fill(GOLD); c.rect(0, 0, 4*mm, H, fill=1, stroke=0)
    cy = H * 0.65
    doc.text(W/2, cy + 22*mm, "LA CARTE", "Helvetica", 9, GOLD_DIM, "center")
    doc.fill(GOLD); c.rect(W/2 - 25*mm, cy + 19*mm, 50*mm, 0.6*mm, fill=1, stroke=0)
    doc.text(W/2, cy + 6*mm, "RAPPORT D'AUDIT", "Helvetica-Bold", 26, TEXT, "center")
    doc.text(W/2, cy - 5*mm, "COMPLET", "Helvetica-Bold", 18, GOLD, "center")
    doc.fill(GOLD_DIM); c.rect(W/2 - 30*mm, cy - 10*mm, 60*mm, 0.4*mm, fill=1, stroke=0)
    ty = cy - 20*mm
    for ln in wrap(restaurant, W - 60*mm, "Helvetica-Bold", 14):
        doc.text(W/2, ty, ln, "Helvetica-Bold", 14, TEXT, "center"); ty -= 6*mm
    if ville:
        doc.text(W/2, ty - 1*mm, ville, "Helvetica", 10, MUTED, "center")
    info_y = 38*mm
    for label, val in [("Client", restaurant), ("Ville", ville), ("Auditeur", auditeur),
                       ("Date", date), ("Confidentialité", "Document strictement confidentiel")]:
        if val:
            doc.text(ML + 10*mm, info_y, label.upper(), "Helvetica-Bold", 8, GOLD_DIM)
            doc.text(ML + 50*mm, info_y, val, "Helvetica", 8, TEXT)
            info_y -= 6*mm
    doc.fill(GOLD); c.rect(0, 0, W, 1*mm, fill=1, stroke=0)
    doc.text(W/2, 5*mm, "www.lacarte-conseil.fr — lacarte.advisory@gmail.com", "Helvetica", 7, MUTED, "center")


# ─── SOMMAIRE ─────────────────────────────────────────────────────────────────
def page_sommaire(doc):
    doc.label = "SOMMAIRE"
    doc.new_page()
    c = doc.c
    doc.text(ML, doc.y - 4*mm, "SOMMAIRE", "Helvetica-Bold", 16, GOLD)
    doc.fill(GOLD); c.rect(ML, doc.y - 7*mm, CW, 0.5*mm, fill=1, stroke=0)
    y = doc.y - 18*mm
    for num, title, p0, p1 in doc.toc_in:
        doc.fill(BG_BAND); c.rect(ML, y - 2*mm, CW, 9*mm, fill=1, stroke=0)
        doc.fill(GOLD); c.rect(ML, y - 2*mm, 1*mm, 9*mm, fill=1, stroke=0)
        doc.text(ML + 4*mm, y + 2.5*mm, num, "Helvetica-Bold", 9, GOLD_DIM)
        doc.text(ML + 16*mm, y + 2.5*mm, title.upper(), "Helvetica-Bold", 9, TEXT)
        pg = f"p. {p0}" if p0 == p1 else f"p. {p0}–{p1}"
        doc.text(MR - 4*mm, y + 2.5*mm, pg, "Helvetica", 8, MUTED, "right")
        y -= 12*mm


# ─── 01 DONNÉES UTILISÉES ─────────────────────────────────────────────────────
def sec_donnees(doc, d):
    recus = [x for x in lst(d, "donnees", "recus") if filled(x.get("nom") if isinstance(x, dict) else x)]
    manq = [x for x in lst(d, "donnees", "manquants") if filled(x.get("nom") if isinstance(x, dict) else x)]
    periode = g(d, "donnees", "periode"); comm = g(d, "donnees", "commentaire")
    if not (recus or manq or periode or comm):
        return
    doc.section("Données utilisées", "Traçabilité — documents reçus, manquants et impact sur l'analyse")
    if recus:
        doc.sub("Documents reçus")
        for x in recus:
            doc.card(g(x, "nom"), right2=g(x, "detail"), accent=GREEN, title_col=TEXT, rounded=False)
    if manq:
        doc.sub("Documents manquants & impact")
        for x in manq:
            doc.card(g(x, "nom"), g(x, "impact"), accent=ORANGE, title_col=TEXT, rounded=False)
    if periode or comm:
        doc.sub("Période & commentaire", keep=8*mm)
        doc.lv_rows([("Période analysée", periode, TEXT)])
        if comm:
            doc.para(comm, "Helvetica-Oblique", 8, MUTED)


# ─── 02 SYNTHÈSE EXÉCUTIVE ────────────────────────────────────────────────────
def marge_color(val):
    n = pct_value(val)
    return RED if n is not None and n < 10 else GOLD

def sec_synthese(doc, d):
    k = d.get("kpis", {}) or {}
    kp = [("MARGE\nMENU", g(k, "marge_menu"), GOLD), ("CMV\nGLOBAL", g(k, "cmv_global"), GOLD),
          ("TICKET\nMOYEN", g(k, "ticket_moyen"), GOLD), ("SEUIL\nRENTABILITÉ", g(k, "seuil"), GOLD),
          ("MARGE\nSÉCURITÉ", g(k, "marge_securite"), marge_color(g(k, "marge_securite")))]
    kp = [x for x in kp if x[1]]
    decisions = [x for x in (d.get("decisions") or [])[:3] if isinstance(x, dict) and filled(x.get("titre"))]
    rows = []
    for r in d.get("synthese_tableau") or []:
        if isinstance(r, dict):
            r = list(r.values())
        rows.append(list(r)[:4] + [""] * (4 - len(list(r)[:4])))
    rows = [r for r in rows if filled(r)]
    if not (kp or decisions or rows):
        return
    doc.section("Synthèse exécutive", "Indicateurs clés et décisions prioritaires")
    if kp:
        if len(kp) <= 3:
            doc.kpis(kp)
        else:                                   # 4 -> 2+2, 5 -> 3+2
            cut = (len(kp) + 1) // 2
            doc.kpis(kp[:cut]); doc.kpis(kp[cut:])
    if decisions:
        doc.sub(f"{len(decisions)} décision{'s' if len(decisions) > 1 else ''} prioritaire{'s' if len(decisions) > 1 else ''}")
        cols = [GOLD, GOLD_DIM, MUTED]
        for i, dec in enumerate(decisions):
            doc.card(g(dec, "titre"), g(dec, "description"), right=g(dec, "impact"),
                     accent=cols[i], number=i + 1)
    if rows:
        doc.sub_table("Indicateurs avant / après recommandations", ["INDICATEUR", "SITUATION ACTUELLE", "APRÈS RECOMMANDATIONS", "ÉCART"],
                  rows, [52, 42, 52, 28], col_colors={3: GOLD})


# ─── 03 ARCHITECTURE & LISIBILITÉ ─────────────────────────────────────────────
def sec_inventaire(doc, d):
    inv = d.get("inventaire", {}) or {}
    pairs = [("Nombre total de références", g(inv, "nb_references"), TEXT),
             ("Nombre de catégories", g(inv, "nb_categories"), TEXT),
             ("Doublons identifiés", g(inv, "doublons"), TEXT),
             ("Lisibilité < 90s", g(inv, "lisibilite"), TEXT),
             ("Cohérence positionnement", g(inv, "coherence"), TEXT)]
    cats = [[g(x, "nom"), g(x, "nb_refs"), g(x, "prix_min"), g(x, "prix_max"), g(x, "observation")]
            for x in inv.get("categories") or [] if isinstance(x, dict)]
    cats = [r for r in cats if filled(r)]
    alertes = [a for a in inv.get("alertes") or [] if isinstance(a, dict) and filled(a.get("label"))]
    if not (any(p[1] for p in pairs) or cats or alertes):
        return
    doc.section("Architecture & lisibilité de la carte", "Structure, cohérence, positionnement",
                header_label="Architecture & lisibilité")
    if any(p[1] for p in pairs):
        doc.sub("Données générales", keep=6*mm)
        doc.lv_rows(pairs)
    if cats:
        doc.sub_table("Architecture des catégories", ["CATÉGORIE", "NB RÉFS", "PRIX MIN", "PRIX MAX", "OBSERVATION"], cats, [42, 18, 22, 22, 70])
    if alertes:
        doc.sub("Signaux d'alerte")
        for a in alertes:
            doc.alert(alert_level(a.get("niveau")), g(a, "label"), g(a, "detail"))


# ─── 04 MENU ENGINEERING ──────────────────────────────────────────────────────
def plats_list(d):
    return [p for p in d.get("plats") or [] if isinstance(p, dict) and filled(p.get("nom"))]

def sec_menu_engineering(doc, d):
    plats = plats_list(d)
    if not plats:
        return
    doc.section("Matrice menu engineering", "Stars / Vaches à lait / Énigmes / Poids morts")
    def count(key):
        return len([p for p in plats if key in clean(p.get("classe", "")).lower()])
    counts = {"star": count("star"), "enigme": count("nigme"), "vache": count("vache"), "poids": count("poids")}
    c = doc.c
    mat_w = (CW - 4*mm) / 2; mat_h = 32*mm
    quads = [(0, 1, "STARS", "Popularité haute · Marge haute", "star", GOLD, BG),
             (1, 1, "ÉNIGMES", "Popularité basse · Marge haute", "enigme", BG_BAND, GOLD),
             (0, 0, "VACHES À LAIT", "Popularité haute · Marge basse", "vache", BG_BAND, TEXT),
             (1, 0, "POIDS MORTS", "Popularité basse · Marge basse", "poids", BG_BAND, MUTED)]
    doc.need(mat_h * 2 + 12*mm)
    y0 = doc.y - mat_h * 2 - 4*mm
    for col, row, title, desc, key, bg, fg in quads:
        qx = ML + col * (mat_w + 4*mm); qy = y0 + row * (mat_h + 4*mm)
        doc.fill(bg); c.roundRect(qx, qy, mat_w, mat_h, 2*mm, fill=1, stroke=0)
        doc.stroke(GOLD_DIM); c.setLineWidth(0.4); c.roundRect(qx, qy, mat_w, mat_h, 2*mm, fill=0, stroke=1)
        tc = BG if bg == GOLD else fg; sc = BG if bg == GOLD else MUTED
        doc.text(qx + mat_w/2, qy + mat_h - 7*mm, title, "Helvetica-Bold", 9, tc, "center")
        doc.text(qx + mat_w/2, qy + mat_h - 12*mm, desc, "Helvetica", 7, sc, "center")
        doc.text(qx + mat_w/2, qy + 7*mm, str(counts[key]), "Helvetica-Bold", 20, tc, "center")
        doc.text(qx + mat_w/2, qy + 3*mm, "référence(s)", "Helvetica", 7, sc, "center")
    doc.y = y0 - 8*mm
    doc.sub("Tableau de classification")
    rows = [[g(p, "nom"), g(p, "categorie"), g(p, "prix_ttc"), g(p, "cout_matiere"),
             g(p, "marge_pct"), g(p, "pct_ventes"), strip_class(p.get("classe", ""))] for p in plats]
    doc.table(["PLAT", "CAT.", "PRIX TTC", "COÛT MAT.", "MARGE %", "% VENTES", "CLASSE"],
              rows, [44, 22, 18, 20, 17, 18, 35], col_colors={6: GOLD})
    doc.para("Seuil popularité = popularité moyenne théorique × 70 %  |  Marge brute = Prix HT - Coût matière",
             "Helvetica-Oblique", 7, MUTED, indent=0)


# ─── 05 RE-PRICING ────────────────────────────────────────────────────────────
def sec_repricing(doc, d):
    plats = [p for p in plats_list(d) if filled([p.get("prix_recommande"), p.get("justification"),
                                                 p.get("impact_estime"), p.get("prix_ttc")])]
    if not plats:
        return
    doc.section("Re-pricing & rationalisation", "Recommandations tarifaires plat par plat")
    dec_cols = {"maintien": MUTED, "hausse": GOLD, "baisse": (0.8, 0.4, 0.3), "suppression": RED}
    for p in plats:
        dec = g(p, "decision") or "Maintien"
        dc = dec_cols.get(dec.lower(), MUTED)
        body = []
        prices = [("Prix actuel", g(p, "prix_ttc")), ("Prix recommandé", g(p, "prix_recommande")),
                  ("Marge actuelle", g(p, "marge_pct"))]
        prices = [f"{l} : {v_}" for l, v_ in prices if v_]
        if prices:
            body.append("   ·   ".join(prices))
        if g(p, "justification"):
            body.append(g(p, "justification"))
        if g(p, "impact_estime"):
            body.append(f"Impact estimé : {g(p, 'impact_estime')}")
        title = g(p, "nom") + (f"  —  {g(p, 'categorie')}" if g(p, "categorie") else "")
        doc.card(title, "\n".join(body), right=dec.upper(), accent=dc, title_col=TEXT)


# ─── 06 CMV GLOBAL ────────────────────────────────────────────────────────────
def sec_cmv_global(doc, d):
    cmv = d.get("cmv", {}) or {}
    kp = [("CMV\nGLOBAL", g(cmv, "cmv_global"), GOLD), ("CMV\nFOOD", g(cmv, "cmv_food"), GOLD),
          ("CMV\nBOISSONS", g(cmv, "cmv_boissons"), GOLD)]
    bench = [["CMV Food", g(cmv, "cmv_food"), "28–32 %", g(cmv, "verdict_food")],
             ["CMV Boissons", g(cmv, "cmv_boissons"), "20–25 %", g(cmv, "verdict_boissons")],
             ["CMV Global", g(cmv, "cmv_global"), "28–35 %", g(cmv, "verdict_global")]]
    bench = [r for r in bench if r[1] or r[3]]
    ecart_pairs = [("CMV théorique (fiches recettes)", g(cmv, "cmv_theorique"), TEXT),
                   ("CMV réel (achats / CA)", g(cmv, "cmv_global"), TEXT),
                   ("Écart", g(cmv, "ecart_theorique_reel"), RED),
                   ("Fuite estimée (€/an)", g(cmv, "fuite_euros"), RED)]
    has_ecart = bool(g(cmv, "ecart_theorique_reel") or g(cmv, "fuite_euros") or g(cmv, "cmv_theorique"))
    comm = g(cmv, "commentaire")
    alertes = [a for a in cmv.get("alertes") or [] if isinstance(a, dict) and filled(a.get("texte"))]
    if not (any(x[1] for x in kp) or bench or has_ecart or comm or alertes):
        return
    doc.section("Analyse CMV global", "Coût matière variable — food + boissons")
    doc.kpis(kp)
    if bench:
        doc.sub_table("Comparaison aux benchmarks secteur", ["INDICATEUR", "VALEUR RÉELLE", "BENCHMARK", "VERDICT"], bench, [45, 32, 32, 65])
    if has_ecart or comm:
        doc.sub("Écart CMV théorique / réel", keep=6*mm)
        if has_ecart:
            doc.lv_rows(ecart_pairs)
        if comm:
            doc.para(comm, "Helvetica-Oblique", 8, MUTED)
    if alertes:
        doc.sub("Signaux d'alerte CMV")
        for a in alertes:
            t = g(a, "texte")
            lvl = alert_level(a.get("niveau"), "rouge" if (">" in t or "élevé" in t.lower()) else "orange")
            doc.alert(lvl, t, g(a, "detail"))


# ─── 07 CMV PAR CATÉGORIE ─────────────────────────────────────────────────────
def sec_cmv_categories(doc, d):
    cc = d.get("cmv_categories", {}) or {}
    cats = [[g(x, "famille"), g(x, "ca"), g(x, "achats"), g(x, "cmv_pct"), g(x, "benchmark"),
             g(x, "ecart"), g(x, "action")] for x in cc.get("categories") or [] if isinstance(x, dict)]
    cats = [r for r in cats if filled(r)]
    crois = [x for x in cc.get("croisement_engineering") or [] if isinstance(x, dict) and filled(x.get("famille"))]
    f = cc.get("fiches_recettes", {}) or {}
    dispo = g(f, "disponibles")
    fiche_pairs = [("Fiches recettes disponibles", dispo, TEXT),
                   ("CMV théorique calculé", g(f, "cmv_theorique"), TEXT),
                   ("CMV réel constaté", g(f, "cmv_reel"), TEXT),
                   ("Écart", g(f, "ecart"), RED),
                   ("Fuite annuelle estimée", g(f, "fuite_annuelle"), RED)]
    # « Disponibles : Non » seul n'apporte rien : on n'affiche le bloc que s'il y a des chiffres
    has_fiches = any(p[1] for p in fiche_pairs[1:]) or filled(f.get("note"))
    if not (cats or crois or has_fiches):
        return
    doc.section("Analyse CMV par catégorie", "Décomposition food / boissons / familles",
                header_label="CMV par catégorie")
    if cats:
        doc.sub_table("CMV par famille de produits", ["FAMILLE", "CA (PÉRIODE)", "ACHATS", "CMV %", "BENCHMARK", "ÉCART", "ACTION"],
                  cats, [30, 22, 22, 17, 22, 17, 44])
    if crois:
        doc.sub("Croisement familles à CMV élevé × matrice engineering")
        for x in crois:
            parts = [f"CMV : {g(x, 'cmv_pct')}" if g(x, "cmv_pct") else "",
                     f"Classe : {strip_class(x.get('classe_engineering', ''))}" if g(x, "classe_engineering") else ""]
            parts = [p_ for p_ in parts if p_]
            body = "   ·   ".join(parts)
            if g(x, "recommandation"):
                body = (body + "\n" if body else "") + g(x, "recommandation")
            doc.card(g(x, "famille"), body, accent=GOLD)
    if has_fiches:
        doc.sub("CMV théorique vs réel (fiches recettes)", keep=6*mm)
        doc.lv_rows(fiche_pairs)
        if g(f, "note"):
            doc.para(g(f, "note"), "Helvetica-Oblique", 8, MUTED)


# ─── 08 TICKET MOYEN ──────────────────────────────────────────────────────────
def sec_ticket(doc, d):
    tm = d.get("ticket_moyen", {}) or {}
    kp = [("TICKET MOYEN\nGLOBAL", g(tm, "ticket_global"), GOLD), ("TICKET\nDÉJEUNER", g(tm, "ticket_dejeuner"), GOLD),
          ("TICKET\nDÎNER", g(tm, "ticket_diner"), GOLD)]
    evo = [[g(m, "mois"), g(m, "ca"), g(m, "couverts"), g(m, "ticket"), g(m, "variation"), g(m, "evenement")]
           for m in tm.get("evolution") or [] if isinstance(m, dict)]
    evo = [r for r in evo if filled(r)]
    leviers = [x for x in tm.get("leviers") or [] if isinstance(x, dict) and filled(x.get("levier"))]
    imp = g(tm, "impact_1euro")
    if not (any(x[1] for x in kp) or evo or leviers or imp):
        return
    doc.section("Analyse ticket moyen", "Évolution, segmentation, leviers d'amélioration")
    doc.kpis(kp)
    if evo:
        doc.sub_table("Évolution mensuelle", ["MOIS", "CA", "COUVERTS", "TICKET MOY.", "VARIATION", "ÉVÉNEMENT / COMMENTAIRE"],
                  evo, [20, 22, 20, 22, 19, 71])
    if leviers:
        doc.sub("Leviers d'amélioration identifiés")
        for x in leviers:
            doc.card(g(x, "levier"), right=g(x, "impact"), accent=GOLD, title_col=TEXT, rounded=False)
    if imp:
        doc.sub("Impact d'une hausse de +1 € du ticket moyen", keep=8*mm)
        doc.lv_rows([("Gain annuel estimé sur le CA", imp, GOLD)])


# ─── 09 SEUIL DE RENTABILITÉ ──────────────────────────────────────────────────
def sec_seuil(doc, d):
    s = d.get("seuil", {}) or {}
    ms = g(s, "marge_securite")
    kp = [("SEUIL\nRENTABILITÉ (€/mois)", g(s, "seuil_euros"), GOLD),
          ("SEUIL EN\nCOUVERTS/JOUR", g(s, "seuil_couverts"), GOLD),
          ("MARGE DE\nSÉCURITÉ", ms, marge_color(ms))]
    charges = [[g(x, "poste"), g(x, "montant"), g(x, "observation")]
               for x in s.get("charges_fixes") or [] if isinstance(x, dict)]
    charges = [r for r in charges if filled(r)]
    calc = [("Total charges fixes (CF)", g(s, "total_charges_fixes"), TEXT),
            ("Taux charges variables (%)", g(s, "taux_charges_variables"), TEXT),
            ("Seuil = CF ÷ (1 - taux CV)", g(s, "seuil_euros"), GOLD),
            ("Ticket moyen utilisé", g(s, "ticket_moyen_utilise"), TEXT),
            ("Seuil en couverts / jour", g(s, "seuil_couverts"), GOLD),
            ("CA actuel", g(s, "ca_actuel"), TEXT),
            ("Marge de sécurité = (CA - seuil) / CA", ms, marge_color(ms))]
    alerte = g(s, "alerte_marge_securite")
    if alerte.lower() in ("non", "no", "false"):
        alerte = ""
    comm = g(s, "commentaire")
    if not (any(x[1] for x in kp) or charges or any(x[1] for x in calc) or alerte or comm):
        return
    doc.section("Seuil de rentabilité", "Charges fixes, taux de charges variables, marge de sécurité")
    doc.kpis(kp)
    if charges:
        doc.sub_table("Charges fixes mensuelles", ["POSTE DE CHARGE", "MONTANT MENSUEL", "OBSERVATION"], charges, [70, 40, 64])
    if any(x[1] for x in calc):
        doc.sub("Calcul du seuil", keep=6*mm)
        doc.lv_rows(calc)
    if alerte or comm:
        if alerte:
            label = "Marge de sécurité < 10 %"
            if alerte.lower() not in ("oui", "yes", "true"):
                label += f" — {alerte}"
            doc.alert("rouge", label, comm)
        else:
            doc.sub("Commentaire", keep=6*mm)
            doc.para(comm, "Helvetica-Oblique", 8, MUTED)


# ─── 10 FOURNISSEURS ──────────────────────────────────────────────────────────
def sec_fournisseurs(doc, d):
    fo = d.get("fournisseurs", {}) or {}
    liste = [[g(x, "nom"), g(x, "categorie"), g(x, "montant"), g(x, "frequence"), g(x, "dependance"), g(x, "statut")]
             for x in fo.get("liste") or [] if isinstance(x, dict)]
    liste = [r for r in liste if filled(r)]
    alertes = [a for a in fo.get("alertes") or [] if isinstance(a, dict) and filled(a.get("texte"))]
    recos = [r for r in fo.get("recommandations") or [] if isinstance(r, dict) and filled(r.get("fournisseur"))]
    if not (liste or alertes or recos):
        return
    doc.section("Analyse fournisseurs", "Cartographie, dépendances, leviers de renégociation")
    if liste:
        doc.sub_table("Cartographie des fournisseurs actifs", ["FOURNISSEUR", "CATÉGORIE", "ACHATS (PÉRIODE)", "FRÉQUENCE", "DÉPENDANCE", "STATUT"],
                  liste, [36, 28, 27, 21, 21, 41])
    if alertes:
        doc.sub("Signaux d'alerte & dépendances")
        for a in alertes:
            doc.alert(alert_level(a.get("niveau"), "vert"), g(a, "texte"), g(a, "detail"))
    if recos:
        doc.sub("Recommandations de renégociation")
        for r in recos:
            st = g(r, "statut")
            col = GREEN if "différenciant" in st.lower() else GOLD
            doc.card(g(r, "fournisseur"), g(r, "recommandation"), right=g(r, "gain_potentiel"),
                     right2=st, accent=col, title_col=col)


# ─── 11 PLAN D'ACTION ─────────────────────────────────────────────────────────
def sec_plan(doc, d):
    plan = d.get("plan_action", {}) or {}
    phases = [("S1", "Semaine 1 — Actions immédiates", GOLD), ("M1", "Mois 1 — Consolidation", GOLD_DIM),
              ("M2_3", "Mois 2–3 — Optimisation continue", MUTED)]
    phases = [(k, l, c_, [clean(a) for a in plan.get(k) or [] if filled(a)]) for k, l, c_ in phases]
    phases = [p for p in phases if p[3]]
    obj = [[g(o, "objectif"), g(o, "valeur_actuelle"), g(o, "cible"), g(o, "echeance"), g(o, "indicateur")]
           for o in d.get("objectifs") or [] if isinstance(o, dict) and filled(o.get("objectif"))]
    if not (phases or obj):
        return
    doc.section("Plan d'action & objectifs", "Semaine 1 / Mois 1 / Mois 2–3 + objectifs chiffrés")
    c = doc.c
    for key, label, col, actions in phases:
        doc.need(10*mm + 7*mm)
        y = doc.y
        doc.fill(BG_BAND); c.roundRect(ML, y - 8*mm, CW, 8*mm, 1.5*mm, fill=1, stroke=0)
        doc.stroke(col); c.setLineWidth(0.6); c.roundRect(ML, y - 8*mm, CW, 8*mm, 1.5*mm, fill=0, stroke=1)
        doc.text(ML + 4*mm, y - 5.4*mm, key.replace("_", "–"), "Helvetica-Bold", 10, col)
        doc.text(ML + 20*mm, y - 5.4*mm, label, "Helvetica-Bold", 9, TEXT)
        doc.y = y - 11*mm
        doc.bullets(actions, col)
        doc.gap(3*mm)
    if obj:
        doc.sub_table("Tableau de bord des objectifs chiffrés", ["OBJECTIF", "VALEUR ACTUELLE", "CIBLE", "ÉCHÉANCE", "INDICATEUR DE SUIVI"],
                  obj, [50, 28, 22, 20, 54], col_colors={2: GOLD})


SECTIONS = [sec_donnees, sec_synthese, sec_inventaire, sec_menu_engineering, sec_repricing,
            sec_cmv_global, sec_cmv_categories, sec_ticket, sec_seuil, sec_fournisseurs, sec_plan]


# ─── ENTRÉE PRINCIPALE ────────────────────────────────────────────────────────
def _render(data, total=None, toc=None):
    buf = io.BytesIO()
    doc = Doc(buf, data, total, toc)
    doc.c.setTitle(f"Rapport Audit Complet — {doc.restaurant}")
    doc.c.setAuthor("La Carte")
    page_cover(doc, data)
    page_sommaire(doc)
    for fn in SECTIONS:
        fn(doc, data)
    doc.c.save()
    return buf.getvalue(), doc.page, doc.toc


def generate_pdf_complet(data: dict) -> bytes:
    data = data or {}
    # Passe 1 : calcule la pagination et le sommaire ; passe 2 : rendu final.
    _, pages, toc = _render(data)
    pdf, _, _ = _render(data, total=pages, toc=toc)
    return pdf


if __name__ == "__main__":
    import json, sys
    src = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else "rapport_audit_complet_test.pdf"
    data = json.load(open(src, encoding="utf-8")) if src else {"infos": {"restaurant": "Test"}}
    with open(out, "wb") as fh:
        fh.write(generate_pdf_complet(data))
    print(f"OK -> {out}")
