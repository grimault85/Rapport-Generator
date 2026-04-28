"""
La Carte — Générateur PDF Audit Menu
Accepte un dict Python issu du formulaire JSON
"""

import io
from reportlab.pdfgen import canvas
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

W, H   = A4
ML     = 18*mm
MR     = W - 18*mm
MTOP   = H - 14*mm


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def rgb(t):    return colors.Color(*t)
def fill(c,t): c.setFillColor(rgb(t))
def stk(c,t):  c.setStrokeColor(rgb(t))
def v(d, *keys, default="—"):
    """Navigation sécurisée dans un dict imbriqué."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, None)
        elif isinstance(cur, list) and isinstance(k, int):
            cur = cur[k] if k < len(cur) else None
        else:
            cur = None
        if cur is None:
            return default
    return cur if cur not in (None, "") else default


# ─── HEADER / FOOTER ──────────────────────────────────────────────────────────
def draw_header(c, page_num, total_pages, section_title=""):
    fill(c, BG_BAND)
    c.rect(0, H - 22*mm, W, 22*mm, fill=1, stroke=0)
    fill(c, GOLD)
    c.rect(0, H - 23*mm, W, 0.7*mm, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 11)
    fill(c, GOLD)
    c.drawString(ML, H - 13*mm, "LA CARTE")

    c.setFont("Helvetica", 7)
    fill(c, MUTED)
    c.drawString(ML, H - 17*mm, "CONSEIL & STRATÉGIE CHR")

    if section_title:
        c.setFont("Helvetica-Bold", 9)
        fill(c, TEXT)
        c.drawCentredString(W/2, H - 14*mm, section_title.upper())

    c.setFont("Helvetica", 8)
    fill(c, MUTED)
    c.drawRightString(MR, H - 14*mm, f"{page_num} / {total_pages}")


def draw_footer(c, restaurant="", date=""):
    fill(c, GOLD)
    c.rect(0, 11*mm, W, 0.5*mm, fill=1, stroke=0)
    fill(c, BG_BAND)
    c.rect(0, 0, W, 11*mm, fill=1, stroke=0)
    c.setFont("Helvetica", 7)
    fill(c, MUTED)
    c.drawString(ML, 4*mm, f"Audit Menu — {restaurant} — {date}")
    c.drawCentredString(W/2, 4*mm, "Document confidentiel — La Carte Advisory")
    c.drawRightString(MR, 4*mm, "lacarte-advisory.fr")


# ─── UI PRIMITIVES ────────────────────────────────────────────────────────────
def section_title(c, y, number, title, subtitle=""):
    fill(c, GOLD)
    c.rect(ML, y - 5*mm, 1.2*mm, 12*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 15)
    fill(c, GOLD)
    c.drawString(ML + 5*mm, y + 4*mm, f"{number}.")
    c.setFont("Helvetica-Bold", 13)
    fill(c, TEXT)
    c.drawString(ML + 15*mm, y + 4*mm, title.upper())
    if subtitle:
        c.setFont("Helvetica", 8)
        fill(c, MUTED)
        c.drawString(ML + 15*mm, y - 1*mm, subtitle)
    return y - 14*mm


def sub_title(c, y, text):
    fill(c, BG_BAND)
    c.rect(ML, y - 1*mm, MR - ML, 7*mm, fill=1, stroke=0)
    fill(c, GOLD_DIM)
    c.rect(ML, y - 1*mm, 0.8*mm, 7*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9)
    fill(c, GOLD)
    c.drawString(ML + 4*mm, y + 3*mm, text.upper())
    return y - 10*mm


def divider(c, y):
    stk(c, GOLD_DIM)
    c.setLineWidth(0.4)
    c.line(ML, y, MR, y)
    return y - 4*mm


def label_value(c, y, label, value, value_color=None):
    if value_color is None:
        value_color = TEXT
    c.setFont("Helvetica-Bold", 8)
    fill(c, MUTED)
    c.drawString(ML + 2*mm, y, label)
    c.setFont("Helvetica", 9)
    fill(c, value_color)
    c.drawString(ML + 52*mm, y, value)
    return y - 6*mm


def draw_table(c, y, headers, rows, col_widths, row_height=7*mm):
    total_w = sum(col_widths)
    x0 = ML

    # Header
    fill(c, GOLD_DIM)
    c.rect(x0, y - row_height, total_w, row_height, fill=1, stroke=0)
    cx = x0
    for i, h in enumerate(headers):
        c.setFont("Helvetica-Bold", 7.5)
        fill(c, BG)
        c.drawString(cx + 2*mm, y - row_height + 2.2*mm, str(h))
        cx += col_widths[i]
    y -= row_height

    # Rows
    for ri, row in enumerate(rows):
        bg = BG_BAND if ri % 2 == 0 else BG
        fill(c, bg)
        c.rect(x0, y - row_height, total_w, row_height, fill=1, stroke=0)
        stk(c, GOLD_DIM)
        c.setLineWidth(0.2)
        c.line(x0, y - row_height, x0 + total_w, y - row_height)
        cx = x0
        for ci, cell in enumerate(row):
            c.setFont("Helvetica", 7.5)
            fill(c, TEXT)
            txt = str(cell)
            # Truncate if too long for column
            max_w = col_widths[ci] - 4*mm
            while c.stringWidth(txt, "Helvetica", 7.5) > max_w and len(txt) > 3:
                txt = txt[:-2] + "…"
            c.drawString(cx + 2*mm, y - row_height + 2.2*mm, txt)
            cx += col_widths[ci]
        y -= row_height

    # Border
    stk(c, GOLD)
    c.setLineWidth(0.5)
    c.rect(x0, y, total_w, row_height * (len(rows) + 1), fill=0, stroke=1)
    return y - 4*mm


def new_page(c, page_num, total_pages, section="", restaurant="", date=""):
    c.showPage()
    fill(c, BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    draw_header(c, page_num, total_pages, section)
    draw_footer(c, restaurant, date)
    return MTOP - 28*mm


def badge(c, x, y, text, bg=GOLD, fg=BG):
    c.setFont("Helvetica-Bold", 8)
    tw = c.stringWidth(text, "Helvetica-Bold", 8)
    pad = 3*mm
    fill(c, bg)
    c.roundRect(x, y - 1.5*mm, tw + pad*2, 5.5*mm, 1.5*mm, fill=1, stroke=0)
    fill(c, fg)
    c.drawString(x + pad, y + 1.5*mm, text)
    return x + tw + pad*2 + 3*mm


# ─── PAGES ────────────────────────────────────────────────────────────────────

def page_cover(c, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    auditeur   = v(d, "infos", "auditeur")
    ville      = v(d, "infos", "ville")

    fill(c, BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    fill(c, GOLD)
    c.rect(0, 0, 4*mm, H, fill=1, stroke=0)

    cy = H * 0.65
    c.setFont("Helvetica", 9)
    fill(c, GOLD_DIM)
    c.drawCentredString(W/2, cy + 22*mm, "LA CARTE ADVISORY")
    fill(c, GOLD)
    c.rect(W/2 - 25*mm, cy + 19*mm, 50*mm, 0.6*mm, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 26)
    fill(c, TEXT)
    c.drawCentredString(W/2, cy + 6*mm, "RAPPORT D'AUDIT")
    c.setFont("Helvetica-Bold", 20)
    fill(c, GOLD)
    c.drawCentredString(W/2, cy - 6*mm, "MENU & INGÉNIERIE TARIFAIRE")

    fill(c, GOLD_DIM)
    c.rect(W/2 - 30*mm, cy - 11*mm, 60*mm, 0.4*mm, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 14)
    fill(c, TEXT)
    c.drawCentredString(W/2, cy - 21*mm, restaurant)
    if ville and ville != "—":
        c.setFont("Helvetica", 10)
        fill(c, MUTED)
        c.drawCentredString(W/2, cy - 28*mm, ville)

    info_y = 38*mm
    for label, val in [("Client", restaurant), ("Ville", ville), ("Auditeur", auditeur), ("Date", date), ("Confidentialité", "Document strictement confidentiel")]:
        if val and val != "—":
            c.setFont("Helvetica-Bold", 8)
            fill(c, GOLD_DIM)
            c.drawString(ML + 10*mm, info_y, label.upper())
            c.setFont("Helvetica", 8)
            fill(c, TEXT)
            c.drawString(ML + 50*mm, info_y, val)
            info_y -= 6*mm

    fill(c, GOLD)
    c.rect(0, 0, W, 1*mm, fill=1, stroke=0)
    c.setFont("Helvetica", 7)
    fill(c, MUTED)
    c.drawCentredString(W/2, 5*mm, "lacarte-advisory.fr — conseil@lacarte-advisory.fr")


def page_synthese(c, page_num, total_pages, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    y = new_page(c, page_num, total_pages, "SYNTHÈSE EXÉCUTIVE", restaurant, date)
    y = section_title(c, y, "01", "Synthèse Exécutive", "3 décisions clés + impact estimé")

    # KPIs
    kpi_items = [
        ("MARGE BRUTE\nACTUELLE", v(d, "kpis", "marge_actuelle"), MUTED),
        ("MARGE BRUTE\nCIBLE",    v(d, "kpis", "marge_cible"), GOLD),
        ("GAIN MENSUEL\nESTIMÉ",  v(d, "kpis", "gain_mensuel"), GOLD),
    ]
    kpi_w = (MR - ML - 6*mm) / 3
    kx = ML
    for title_k, val_k, col in kpi_items:
        fill(c, BG_BAND)
        c.roundRect(kx, y - 18*mm, kpi_w, 18*mm, 2*mm, fill=1, stroke=0)
        stk(c, GOLD_DIM)
        c.setLineWidth(0.4)
        c.roundRect(kx, y - 18*mm, kpi_w, 18*mm, 2*mm, fill=0, stroke=1)
        lines = title_k.split("\n")
        c.setFont("Helvetica-Bold", 7)
        fill(c, MUTED)
        c.drawCentredString(kx + kpi_w/2, y - 5*mm, lines[0])
        c.drawCentredString(kx + kpi_w/2, y - 9*mm, lines[1])
        c.setFont("Helvetica-Bold", 14)
        fill(c, col)
        c.drawCentredString(kx + kpi_w/2, y - 15*mm, val_k)
        kx += kpi_w + 3*mm
    y -= 24*mm
    y = divider(c, y)

    # 3 décisions
    y = sub_title(c, y, "3 Décisions clés")
    decisions = d.get("decisions", [])
    dec_colors = [GOLD, GOLD_DIM, MUTED]
    for i, dec in enumerate(decisions[:3]):
        titre = v(dec, "titre")
        desc  = v(dec, "description")
        imp   = v(dec, "impact")
        if titre == "—" and desc == "—":
            continue
        fill(c, BG_BAND)
        c.roundRect(ML, y - 14*mm, MR - ML, 14*mm, 1.5*mm, fill=1, stroke=0)
        fill(c, dec_colors[i % 3])
        c.circle(ML + 6*mm, y - 7*mm, 3.5*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9)
        fill(c, BG)
        c.drawCentredString(ML + 6*mm, y - 8.5*mm, str(i + 1))
        c.setFont("Helvetica-Bold", 9)
        fill(c, GOLD)
        c.drawString(ML + 13*mm, y - 4*mm, titre.upper() if titre != "—" else f"DÉCISION {i+1}")
        c.setFont("Helvetica", 8)
        fill(c, TEXT)
        c.drawString(ML + 13*mm, y - 9*mm, desc if desc != "—" else "")
        if imp != "—":
            c.setFont("Helvetica-Bold", 8)
            fill(c, GOLD)
            c.drawRightString(MR - 3*mm, y - 4*mm, imp)
        y -= 17*mm

    y = divider(c, y)

    # Tableau indicateurs synthèse
    y = sub_title(c, y, "Indicateurs Synthèse")
    plats = d.get("plats", [])
    nb_refs = v(d, "inventaire", "nb_references")
    nb_refs_apres = str(len([p for p in plats if p.get("decision", "") != "Suppression"])) if plats else "—"
    stars  = len([p for p in plats if p.get("classe") == "⭐ Star"])
    morts  = len([p for p in plats if p.get("classe") == "💀 Poids mort"])
    headers = ["INDICATEUR", "SITUATION ACTUELLE", "APRÈS RECOMMANDATIONS", "ÉCART"]
    rows = [
        ["Nb de références",    nb_refs,                              nb_refs_apres,                          "—"],
        ["Taux de marge moyen", v(d, "kpis", "marge_actuelle"),       v(d, "kpis", "marge_cible"),            "—"],
        ["Nb de Stars",         str(stars),                           str(stars),                             "—"],
        ["Nb de Poids Morts",   str(morts),                           str(max(0, morts - 1)),                 "—"],
        ["Gain mensuel estimé", "—",                                  v(d, "kpis", "gain_mensuel"),           v(d, "impact", "amelioration_marge")],
    ]
    col_widths = [52*mm, 42*mm, 52*mm, 27*mm]
    draw_table(c, y, headers, rows, col_widths)


def page_inventaire(c, page_num, total_pages, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    y = new_page(c, page_num, total_pages, "INVENTAIRE & ARCHITECTURE", restaurant, date)
    y = section_title(c, y, "02", "Inventaire & Architecture de Carte",
                      "Structure, lisibilité, cohérence positionnement")

    y = sub_title(c, y, "Données générales")
    y = label_value(c, y, "Nombre total de références", v(d, "inventaire", "nb_references"))
    y = label_value(c, y, "Nombre de catégories",       v(d, "inventaire", "nb_categories"))
    y = label_value(c, y, "Doublons identifiés",        v(d, "inventaire", "doublons"))
    y = label_value(c, y, "Lisibilité < 90s",           v(d, "inventaire", "lisibilite"))
    y = label_value(c, y, "Cohérence positionnement",   v(d, "inventaire", "coherence"))
    y -= 4*mm

    # Tableau catégories
    categories = d.get("inventaire", {}).get("categories", [])
    if categories:
        y = sub_title(c, y, "Architecture des catégories")
        headers = ["CATÉGORIE", "NB RÉFS", "PRIX MIN", "PRIX MAX", "OBSERVATION"]
        rows = []
        for cat in categories:
            rows.append([
                v(cat, "nom"), v(cat, "nb_refs"), v(cat, "prix_min"),
                v(cat, "prix_max"), v(cat, "observation")
            ])
        col_widths = [42*mm, 20*mm, 22*mm, 22*mm, 67*mm]
        y = draw_table(c, y, headers, rows, col_widths)
        y -= 2*mm

    # Signaux d'alerte
    alertes = d.get("inventaire", {}).get("alertes", [])
    if alertes:
        y = sub_title(c, y, "Signaux d'alerte")
        alerte_colors = {"🔴": (0.8, 0.2, 0.2), "🟡": (0.8, 0.65, 0.1), "🟢": (0.2, 0.65, 0.2)}
        for alerte in alertes:
            niveau = v(alerte, "niveau", default="🟡 Attention")
            label  = v(alerte, "label", default="")
            detail = v(alerte, "detail", default="")
            # Couleur selon niveau
            col = MUTED
            for k, col_v in alerte_colors.items():
                if k in niveau:
                    col = col_v
                    break
            fill(c, BG_BAND)
            c.rect(ML, y - 6*mm, MR - ML, 6*mm, fill=1, stroke=0)
            fill(c, col)
            c.rect(ML, y - 6*mm, 2*mm, 6*mm, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 8)
            fill(c, TEXT)
            c.drawString(ML + 5*mm, y - 4*mm, niveau.split(" ", 1)[-1] if " " in niveau else niveau)
            c.setFont("Helvetica", 8)
            fill(c, TEXT)
            c.drawString(ML + 35*mm, y - 4*mm, label if label != "—" else "")
            if detail and detail != "—":
                c.setFont("Helvetica", 7.5)
                fill(c, MUTED)
                c.drawRightString(MR - 3*mm, y - 4*mm, detail)
            y -= 7.5*mm


def page_menu_engineering(c, page_num, total_pages, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    y = new_page(c, page_num, total_pages, "MATRICE MENU ENGINEERING", restaurant, date)
    y = section_title(c, y, "03", "Matrice Menu Engineering",
                      "Classification Stars / Vaches à lait / Énigmes / Poids morts")

    plats = d.get("plats", [])
    counts = {
        "⭐ Star":        len([p for p in plats if p.get("classe") == "⭐ Star"]),
        "❓ Énigme":      len([p for p in plats if p.get("classe") == "❓ Énigme"]),
        "🐄 Vache à lait": len([p for p in plats if p.get("classe") == "🐄 Vache à lait"]),
        "💀 Poids mort":  len([p for p in plats if p.get("classe") == "💀 Poids mort"]),
    }

    mat_w = (MR - ML - 4*mm) / 2
    mat_h = 38*mm
    quadrants = [
        (0, 1, "⭐ STARS",         "Popularité haute\nMarge haute",  GOLD,     BG),
        (1, 1, "ÉNIGMES",          "Popularité basse\nMarge haute",  BG_BAND,  GOLD),
        (0, 0, "VACHES À LAIT",    "Popularité haute\nMarge basse",  BG_BAND,  TEXT),
        (1, 0, "POIDS MORTS",      "Popularité basse\nMarge basse",  BG_BAND,  MUTED),
    ]
    classe_keys = ["⭐ Star", "❓ Énigme", "🐄 Vache à lait", "💀 Poids mort"]

    mat_x0 = ML
    mat_y0 = y - mat_h * 2 - 4*mm

    for idx, (col, row, title_q, desc, bg, fg) in enumerate(quadrants):
        qx = mat_x0 + col * (mat_w + 4*mm)
        qy = mat_y0 + row * (mat_h + 4*mm)
        fill(c, bg)
        c.roundRect(qx, qy, mat_w, mat_h, 2*mm, fill=1, stroke=0)
        stk(c, GOLD_DIM)
        c.setLineWidth(0.4)
        c.roundRect(qx, qy, mat_w, mat_h, 2*mm, fill=0, stroke=1)

        text_color = BG if bg == GOLD else fg
        c.setFont("Helvetica-Bold", 9)
        fill(c, text_color)
        c.drawCentredString(qx + mat_w/2, qy + mat_h - 7*mm, title_q)
        lines = desc.split("\n")
        c.setFont("Helvetica", 7.5)
        fill(c, MUTED if bg != GOLD else BG)
        c.drawCentredString(qx + mat_w/2, qy + mat_h - 14*mm, lines[0])
        c.drawCentredString(qx + mat_w/2, qy + mat_h - 19*mm, lines[1])

        count = counts.get(classe_keys[idx], 0)
        c.setFont("Helvetica-Bold", 22)
        fill(c, text_color)
        c.drawCentredString(qx + mat_w/2, qy + 6*mm, str(count))
        c.setFont("Helvetica", 7)
        fill(c, MUTED if bg != GOLD else BG)
        c.drawCentredString(qx + mat_w/2, qy + 2.5*mm, "référence(s)")

    c.setFont("Helvetica", 7)
    fill(c, MUTED)
    c.drawCentredString(mat_x0 + mat_w, mat_y0 - 4*mm, "◄ POPULARITÉ ►")
    c.saveState()
    c.translate(mat_x0 - 5*mm, mat_y0 + mat_h)
    c.rotate(90)
    c.drawCentredString(0, 0, "◄ MARGE ►")
    c.restoreState()

    y = mat_y0 - 10*mm
    y = divider(c, y)

    # Tableau classement
    if plats:
        y = sub_title(c, y, "Tableau de classification")
        headers = ["PLAT", "CAT.", "PRIX TTC", "COÛT MAT.", "MARGE %", "% VENTES", "CLASSE"]
        rows = []
        for p in plats:
            rows.append([
                v(p, "nom"), v(p, "categorie"), v(p, "prix_ttc"),
                v(p, "cout_matiere"), v(p, "marge_pct"), v(p, "pct_ventes"),
                v(p, "classe"),
            ])
        col_widths = [42*mm, 18*mm, 18*mm, 18*mm, 16*mm, 16*mm, 45*mm]
        y = draw_table(c, y, headers, rows, col_widths)

    y -= 3*mm
    c.setFont("Helvetica-Oblique", 7.5)
    fill(c, MUTED)
    c.drawString(ML, y, "Seuil popularité = popularité moyenne théorique × 70%  |  Marge brute = Prix HT − Coût matière")


def page_repricing(c, page_num, total_pages, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    y = new_page(c, page_num, total_pages, "RE-PRICING & RATIONALISATION", restaurant, date)
    y = section_title(c, y, "04", "Analyse Plat par Plat — Re-pricing",
                      "Recommandations tarifaires justifiées")

    plats = d.get("plats", [])
    decision_colors = {
        "Maintien":    MUTED,
        "Hausse":      GOLD,
        "Baisse":      (0.8, 0.4, 0.3),
        "Suppression": (0.7, 0.3, 0.3),
    }

    for plat in plats:
        nom     = v(plat, "nom")
        cat     = v(plat, "categorie")
        prix    = v(plat, "prix_ttc")
        prix_r  = v(plat, "prix_recommande")
        dec     = v(plat, "decision", default="Maintien")
        m_av    = v(plat, "marge_pct")
        just    = v(plat, "justification")
        impact  = v(plat, "impact_estime")

        # Saut de page si pas assez d'espace
        if y < 60*mm:
            y = new_page(c, page_num, total_pages, "RE-PRICING & RATIONALISATION", restaurant, date)

        dc = decision_colors.get(dec, MUTED)

        fill(c, BG_BAND)
        c.roundRect(ML, y - 10*mm, MR - ML, 10*mm, 1.5*mm, fill=1, stroke=0)
        fill(c, dc)
        c.roundRect(ML, y - 10*mm, 3*mm, 10*mm, 1.5*mm, fill=1, stroke=0)

        c.setFont("Helvetica-Bold", 10)
        fill(c, TEXT)
        c.drawString(ML + 7*mm, y - 4*mm, nom)
        c.setFont("Helvetica", 8)
        fill(c, MUTED)
        c.drawString(ML + 7*mm, y - 8*mm, cat)
        badge(c, MR - 38*mm, y - 8.5*mm, dec.upper(), dc, BG)
        y -= 13*mm

        # Métriques
        c1, c2, c3 = ML + 2*mm, ML + 55*mm, ML + 110*mm
        c.setFont("Helvetica-Bold", 7.5)
        fill(c, MUTED)
        c.drawString(c1, y, "PRIX ACTUEL")
        c.drawString(c2, y, "PRIX RECOMMANDÉ")
        c.drawString(c3, y, "MARGE ACTUELLE")
        y -= 5*mm

        c.setFont("Helvetica-Bold", 10)
        fill(c, TEXT)
        c.drawString(c1, y, prix)
        fill(c, GOLD)
        c.drawString(c2, y, prix_r)
        c.setFont("Helvetica", 9)
        fill(c, GOLD)
        c.drawString(c3, y, m_av)
        y -= 7*mm

        if just and just != "—":
            c.setFont("Helvetica-Bold", 7.5)
            fill(c, MUTED)
            c.drawString(ML + 2*mm, y, "JUSTIFICATION")
            y -= 4.5*mm
            c.setFont("Helvetica", 8)
            fill(c, TEXT)
            # Wrap text basique
            words = just.split()
            line, lines_out = [], []
            for w in words:
                test = " ".join(line + [w])
                if c.stringWidth(test, "Helvetica", 8) > (MR - ML - 4*mm):
                    lines_out.append(" ".join(line))
                    line = [w]
                else:
                    line.append(w)
            if line:
                lines_out.append(" ".join(line))
            for ln in lines_out[:2]:
                c.drawString(ML + 2*mm, y, ln)
                y -= 4.5*mm

        if impact and impact != "—":
            c.setFont("Helvetica-Bold", 7.5)
            fill(c, GOLD_DIM)
            c.drawString(ML + 2*mm, y, f"Impact estimé : {impact}")
            y -= 4*mm

        y = divider(c, y)
        y -= 2*mm


def page_positionnement(c, page_num, total_pages, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    y = new_page(c, page_num, total_pages, "POSITIONNEMENT TARIFAIRE", restaurant, date)
    y = section_title(c, y, "05", "Positionnement Tarifaire & Concurrence",
                      "Benchmark local + verdict global")

    # Tableau concurrents
    concurrents = d.get("concurrents", [])
    if concurrents:
        y = sub_title(c, y, "Comparatif concurrence directe")
        headers = ["CONCURRENT", "TICKET MOY.", "FOURCHETTE", "POSITIONNEMENT", "SOURCE"]
        rows = []
        for con in concurrents:
            rows.append([
                v(con, "nom"), v(con, "ticket_moyen"), v(con, "fourchette"),
                v(con, "positionnement"), v(con, "source")
            ])
        # Ligne du restaurant client
        rows.append([restaurant, "—", "—", v(d, "verdict", "global"), "—"])
        col_widths = [42*mm, 22*mm, 24*mm, 48*mm, 37*mm]
        y = draw_table(c, y, headers, rows, col_widths)
        y -= 4*mm

    # Verdict
    verdict_global = v(d, "verdict", "global")
    commentaire    = v(d, "verdict", "commentaire")
    y = sub_title(c, y, "Verdict de positionnement global")

    verdict_map = {
        "Sous-tarifé":               ("🔴", (0.8, 0.2, 0.2)),
        "Correctement positionné":   ("🟢", (0.2, 0.65, 0.2)),
        "Au-dessus du marché perçu": ("🟡", (0.8, 0.65, 0.1)),
    }
    icon, col = verdict_map.get(verdict_global, ("🟡", MUTED))

    fill(c, BG_BAND)
    c.roundRect(ML, y - 18*mm, MR - ML, 18*mm, 1.5*mm, fill=1, stroke=0)
    fill(c, col)
    c.rect(ML, y - 18*mm, 2*mm, 18*mm, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 11)
    fill(c, TEXT)
    c.drawString(ML + 7*mm, y - 6*mm, verdict_global)
    if commentaire and commentaire != "—":
        c.setFont("Helvetica", 8)
        fill(c, MUTED)
        # Wrap commentaire
        words = commentaire.split()
        line, out = [], []
        for w in words:
            test = " ".join(line + [w])
            if c.stringWidth(test, "Helvetica", 8) > (MR - ML - 12*mm):
                out.append(" ".join(line))
                line = [w]
            else:
                line.append(w)
        if line:
            out.append(" ".join(line))
        ly = y - 11*mm
        for ln in out[:2]:
            c.drawString(ML + 7*mm, ly, ln)
            ly -= 4.5*mm
    y -= 22*mm

    # Impact global
    y = sub_title(c, y, "Impact global estimé")
    kpi_items = [
        ("AMÉLIORATION\nMARGE BRUTE", v(d, "impact", "amelioration_marge")),
        ("GAIN MENSUEL\nESTIMÉ",      v(d, "impact", "gain_mensuel")),
        ("GAIN ANNUEL\nESTIMÉ",       v(d, "impact", "gain_annuel")),
    ]
    kpi_w = (MR - ML - 6*mm) / 3
    kx = ML
    for title_k, val_k in kpi_items:
        fill(c, BG_BAND)
        c.roundRect(kx, y - 18*mm, kpi_w, 18*mm, 2*mm, fill=1, stroke=0)
        stk(c, GOLD_DIM)
        c.setLineWidth(0.4)
        c.roundRect(kx, y - 18*mm, kpi_w, 18*mm, 2*mm, fill=0, stroke=1)
        lines = title_k.split("\n")
        c.setFont("Helvetica-Bold", 7)
        fill(c, MUTED)
        c.drawCentredString(kx + kpi_w/2, y - 5*mm, lines[0])
        c.drawCentredString(kx + kpi_w/2, y - 9*mm, lines[1])
        c.setFont("Helvetica-Bold", 14)
        fill(c, GOLD)
        c.drawCentredString(kx + kpi_w/2, y - 15*mm, val_k)
        kx += kpi_w + 3*mm


def page_plan_action(c, page_num, total_pages, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    y = new_page(c, page_num, total_pages, "PLAN D'ACTION", restaurant, date)
    y = section_title(c, y, "06", "Plan d'Action",
                      "Priorités S1 / M1 / M2-3 + objectifs chiffrés")

    plan = d.get("plan_action", {})
    phases = [
        ("S1",   "Semaine 1 — Actions immédiates",   GOLD),
        ("M1",   "Mois 1 — Consolidation",           GOLD_DIM),
        ("M2_3", "Mois 2–3 — Optimisation continue", MUTED),
    ]

    for key, label_p, color in phases:
        actions = plan.get(key, [])
        actions = [a for a in actions if a and a.strip()]
        if not actions:
            continue

        fill(c, BG_BAND)
        c.roundRect(ML, y - 8*mm, MR - ML, 8*mm, 1.5*mm, fill=1, stroke=0)
        stk(c, color)
        c.setLineWidth(0.6)
        c.roundRect(ML, y - 8*mm, MR - ML, 8*mm, 1.5*mm, fill=0, stroke=1)
        fill(c, color)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(ML + 4*mm, y - 5.5*mm, key)
        fill(c, TEXT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(ML + 18*mm, y - 5.5*mm, label_p)
        y -= 10*mm

        for action in actions:
            if y < 50*mm:
                y = new_page(c, page_num, total_pages, "PLAN D'ACTION", restaurant, date)
            fill(c, color)
            c.circle(ML + 7*mm, y - 2.5*mm, 1.2*mm, fill=1, stroke=0)
            c.setFont("Helvetica", 8.5)
            fill(c, TEXT)
            c.drawString(ML + 12*mm, y - 4*mm, action[:100])
            y -= 6.5*mm

        y -= 3*mm

    y = divider(c, y)
    y -= 2*mm

    # Objectifs chiffrés
    objectifs = d.get("objectifs", [])
    objectifs = [o for o in objectifs if o.get("objectif", "").strip()]
    if objectifs:
        y = sub_title(c, y, "Tableau Objectifs Chiffrés")
        headers = ["OBJECTIF", "VALEUR ACTUELLE", "CIBLE", "ÉCHÉANCE", "INDICATEUR"]
        rows = [[v(o,"objectif"), v(o,"valeur_actuelle"), v(o,"cible"), v(o,"echeance"), v(o,"indicateur")]
                for o in objectifs]
        col_widths = [48*mm, 28*mm, 22*mm, 22*mm, 53*mm]
        draw_table(c, y, headers, rows, col_widths)


# ─── ENTRÉE PRINCIPALE ────────────────────────────────────────────────────────
def generate_pdf(data: dict) -> bytes:
    """
    Génère le rapport PDF à partir du dict data.
    Retourne les bytes du PDF.
    """
    buffer = io.BytesIO()
    restaurant = v(data, "infos", "restaurant", default="Audit Menu")
    date       = v(data, "infos", "date", default="")

    TOTAL = 7
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Rapport Audit Menu — {restaurant}")
    c.setAuthor("La Carte Advisory")

    # Page 1 : Couverture
    fill(c, BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    page_cover(c, data)

    # Page 2 : Synthèse
    page_synthese(c, 2, TOTAL, data)

    # Page 3 : Inventaire
    page_inventaire(c, 3, TOTAL, data)

    # Page 4 : Menu Engineering
    page_menu_engineering(c, 4, TOTAL, data)

    # Page 5 : Re-pricing
    page_repricing(c, 5, TOTAL, data)

    # Page 6 : Positionnement
    page_positionnement(c, 6, TOTAL, data)

    # Page 7 : Plan d'action
    page_plan_action(c, 7, TOTAL, data)

    c.save()
    buffer.seek(0)
    return buffer.read()


if __name__ == "__main__":
    # Test local avec données fictives
    import json
    sample = {
        "infos": {"restaurant": "Le Bistrot du Port", "date": "Mai 2025", "auditeur": "Anthony Grimault", "ville": "Nantes"},
        "kpis": {"marge_actuelle": "52 %", "marge_cible": "67 %", "gain_mensuel": "+1 200 €"},
        "decisions": [
            {"titre": "Re-pricing", "description": "Hausse tarifaire sur 6 plats sous-évalués", "impact": "+800 €/mois"},
            {"titre": "Rationalisation", "description": "Suppression de 4 poids morts", "impact": "−15 % coûts cuisine"},
            {"titre": "Architecture", "description": "Repositionnement des Stars en zone A de lecture", "impact": "+12 % conversion"},
        ],
        "inventaire": {
            "nb_references": "38", "nb_categories": "5", "doublons": "3",
            "lisibilite": "Partielle", "coherence": "Bistrot traditionnel",
            "categories": [
                {"nom": "Entrées", "nb_refs": "8", "prix_min": "8,50 €", "prix_max": "14,00 €", "observation": "Cohérente"},
                {"nom": "Plats", "nb_refs": "16", "prix_min": "16,00 €", "prix_max": "28,00 €", "observation": "Trop large"},
                {"nom": "Desserts", "nb_refs": "7", "prix_min": "7,00 €", "prix_max": "11,00 €", "observation": "OK"},
            ],
            "alertes": [
                {"niveau": "🔴 Critique", "label": "Carte illisible en moins de 90 secondes", "detail": "38 refs trop nombreuses"},
                {"niveau": "🟡 Attention", "label": "Plats stratégiques en zone faible", "detail": "Entrecôte en bas de page"},
                {"niveau": "🟢 OK", "label": "Cohérence avec le positionnement bistrot", "detail": ""},
            ],
        },
        "plats": [
            {"nom": "Entrecôte Bordelaise", "categorie": "Plats", "prix_ttc": "24,00 €", "cout_matiere": "8,50 €", "marge_pct": "64 %", "pct_ventes": "18 %", "classe": "⭐ Star", "prix_recommande": "26,00 €", "decision": "Hausse", "justification": "Plat star sous-évalué vs concurrence directe. +2€ absorbable sans résistance.", "impact_estime": "+240 €/mois"},
            {"nom": "Carpaccio de bœuf", "categorie": "Entrées", "prix_ttc": "12,00 €", "cout_matiere": "5,20 €", "marge_pct": "56 %", "pct_ventes": "4 %", "classe": "❓ Énigme", "prix_recommande": "12,00 €", "decision": "Maintien", "justification": "Marge correcte mais faible rotation. Nécessite mise en avant.", "impact_estime": "Neutre"},
            {"nom": "Crème brûlée maison", "categorie": "Desserts", "prix_ttc": "7,50 €", "cout_matiere": "1,80 €", "marge_pct": "76 %", "pct_ventes": "22 %", "classe": "⭐ Star", "prix_recommande": "8,50 €", "decision": "Hausse", "justification": "Meilleure marge du menu. Hausse de +1€ totalement absorbable.", "impact_estime": "+180 €/mois"},
            {"nom": "Filet de poisson du jour", "categorie": "Plats", "prix_ttc": "19,00 €", "cout_matiere": "9,00 €", "marge_pct": "52 %", "pct_ventes": "3 %", "classe": "💀 Poids mort", "prix_recommande": "—", "decision": "Suppression", "justification": "Faible popularité et coût opérationnel élevé (préparation complexe).", "impact_estime": "Simplification opérationnelle"},
        ],
        "concurrents": [
            {"nom": "La Brasserie du Port", "ticket_moyen": "29 €", "fourchette": "18–38 €", "positionnement": "Correctement positionné", "source": "Google Maps"},
            {"nom": "Chez Marcel", "ticket_moyen": "22 €", "fourchette": "14–28 €", "positionnement": "Sous-tarifé", "source": "Site web"},
        ],
        "verdict": {"global": "Sous-tarifé", "commentaire": "Le restaurant pratique des prix inférieurs de 15 à 20% par rapport à la concurrence directe pour une qualité identique voire supérieure."},
        "impact": {"amelioration_marge": "+12 pts", "gain_mensuel": "+1 200 €", "gain_annuel": "+14 400 €"},
        "plan_action": {
            "S1": ["Supprimer 4 références poids morts", "Appliquer les hausses tarifaires validées", "Repositionner l'Entrecôte Bordelaise en tête de carte"],
            "M1": ["Refonte de la mise en page de la carte", "Briefing équipe de salle sur les plats à pousser"],
            "M2_3": ["Analyse des résultats post-refonte", "Ajustements fins selon retours clients"],
        },
        "objectifs": [
            {"objectif": "Taux de marge moyen", "valeur_actuelle": "52 %", "cible": "67 %", "echeance": "M1", "indicateur": "Fiches recettes + caisse"},
            {"objectif": "Nb de références", "valeur_actuelle": "38", "cible": "30", "echeance": "S1", "indicateur": "Carte imprimée"},
        ],
    }
    pdf_bytes = generate_pdf(sample)
    with open("/mnt/user-data/outputs/rapport_audit_test.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"✅ Test PDF : {len(pdf_bytes)} bytes")
