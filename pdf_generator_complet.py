"""
La Carte — Générateur PDF Audit Complet
12 sections : Menu Engineering + CMV + Ticket moyen + Seuil rentabilité + Fournisseurs
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
RED      = (0.75, 0.25, 0.25)
GREEN    = (0.25, 0.60, 0.30)

W, H   = A4
ML     = 18*mm
MR     = W - 18*mm
MTOP   = H - 14*mm

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def rgb(t):    return colors.Color(*t)
def fill(c,t): c.setFillColor(rgb(t))
def stk(c,t):  c.setStrokeColor(rgb(t))

def v(d, *keys, default="—"):
    cur = d
    for k in keys:
        if isinstance(cur, dict):   cur = cur.get(k, None)
        elif isinstance(cur, list): cur = cur[k] if isinstance(k,int) and k < len(cur) else None
        else: cur = None
        if cur is None: return default
    return cur if cur not in (None, "") else default

def wrap_text(c, text, x, y, max_w, font="Helvetica", size=8, line_h=4.5*mm, max_lines=3):
    if text in (None, "—", ""): return y
    c.setFont(font, size)
    words = str(text).split()
    line, lines = [], []
    for w in words:
        test = " ".join(line + [w])
        if c.stringWidth(test, font, size) > max_w:
            if line: lines.append(" ".join(line))
            line = [w]
        else: line.append(w)
    if line: lines.append(" ".join(line))
    for ln in lines[:max_lines]:
        c.drawString(x, y, ln)
        y -= line_h
    return y

def truncate(c, text, max_w, font="Helvetica", size=8):
    txt = str(text)
    while c.stringWidth(txt, font, size) > max_w and len(txt) > 3:
        txt = txt[:-2] + "…"
    return txt

# ─── HEADER / FOOTER ──────────────────────────────────────────────────────────
def draw_header(c, page_num, total_pages, section_title=""):
    fill(c, BG_BAND)
    c.rect(0, H - 22*mm, W, 22*mm, fill=1, stroke=0)
    fill(c, GOLD)
    c.rect(0, H - 23*mm, W, 0.7*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 11); fill(c, GOLD)
    c.drawString(ML, H - 13*mm, "LA CARTE")
    c.setFont("Helvetica", 7); fill(c, MUTED)
    c.drawString(ML, H - 17*mm, "CONSEIL & STRATÉGIE CHR")
    if section_title:
        c.setFont("Helvetica-Bold", 9); fill(c, TEXT)
        c.drawCentredString(W/2, H - 14*mm, section_title.upper())
    c.setFont("Helvetica", 8); fill(c, MUTED)
    c.drawRightString(MR, H - 14*mm, f"{page_num} / {total_pages}")

def draw_footer(c, restaurant="", date=""):
    fill(c, GOLD); c.rect(0, 11*mm, W, 0.5*mm, fill=1, stroke=0)
    fill(c, BG_BAND); c.rect(0, 0, W, 11*mm, fill=1, stroke=0)
    c.setFont("Helvetica", 7); fill(c, MUTED)
    c.drawString(ML, 4*mm, f"Audit Complet — {restaurant} — {date}")
    c.drawCentredString(W/2, 4*mm, "Document confidentiel — La Carte")
    c.drawRightString(MR, 4*mm, "lacarte-conseil.fr")

def new_page(c, pn, tp, section, restaurant, date):
    c.showPage()
    fill(c, BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    draw_header(c, pn, tp, section)
    draw_footer(c, restaurant, date)
    return MTOP - 28*mm

# ─── UI PRIMITIVES ────────────────────────────────────────────────────────────
def sec_title(c, y, number, title, subtitle=""):
    fill(c, GOLD); c.rect(ML, y - 5*mm, 1.2*mm, 12*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 15); fill(c, GOLD)
    c.drawString(ML + 5*mm, y + 4*mm, f"{number}.")
    c.setFont("Helvetica-Bold", 13); fill(c, TEXT)
    c.drawString(ML + 15*mm, y + 4*mm, title.upper())
    if subtitle:
        c.setFont("Helvetica", 8); fill(c, MUTED)
        c.drawString(ML + 15*mm, y - 1*mm, subtitle)
    return y - 14*mm

def sub(c, y, text):
    fill(c, BG_BAND); c.rect(ML, y - 1*mm, MR - ML, 7*mm, fill=1, stroke=0)
    fill(c, GOLD_DIM); c.rect(ML, y - 1*mm, 0.8*mm, 7*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9); fill(c, GOLD)
    c.drawString(ML + 4*mm, y + 3*mm, text.upper())
    return y - 10*mm

def divider(c, y):
    stk(c, GOLD_DIM); c.setLineWidth(0.4)
    c.line(ML, y, MR, y); return y - 4*mm

def lv(c, y, label, value, vc=None):
    if vc is None: vc = TEXT
    c.setFont("Helvetica-Bold", 8); fill(c, MUTED)
    c.drawString(ML + 2*mm, y, label)
    c.setFont("Helvetica", 9); fill(c, vc)
    c.drawString(ML + 55*mm, y, str(value))
    return y - 6*mm

def kpi_row(c, y, items):
    """items = list of (label, value, color)"""
    kw = (MR - ML - (len(items)-1)*3*mm) / len(items)
    kx = ML
    for label, val, col in items:
        fill(c, BG_BAND); c.roundRect(kx, y - 18*mm, kw, 18*mm, 2*mm, fill=1, stroke=0)
        stk(c, GOLD_DIM); c.setLineWidth(0.4)
        c.roundRect(kx, y - 18*mm, kw, 18*mm, 2*mm, fill=0, stroke=1)
        lines = label.split("\n")
        c.setFont("Helvetica-Bold", 7); fill(c, MUTED)
        for li, ln in enumerate(lines):
            c.drawCentredString(kx + kw/2, y - 5*mm - li*4*mm, ln)
        c.setFont("Helvetica-Bold", 13); fill(c, col)
        c.drawCentredString(kx + kw/2, y - 15*mm, str(val))
        kx += kw + 3*mm
    return y - 22*mm

def table(c, y, headers, rows, col_widths, row_h=7*mm):
    total_w = sum(col_widths); x0 = ML
    fill(c, GOLD_DIM); c.rect(x0, y - row_h, total_w, row_h, fill=1, stroke=0)
    cx = x0
    for i, h in enumerate(headers):
        c.setFont("Helvetica-Bold", 7.5); fill(c, BG)
        c.drawString(cx + 2*mm, y - row_h + 2.2*mm, str(h)); cx += col_widths[i]
    y -= row_h
    for ri, row in enumerate(rows):
        fill(c, BG_BAND if ri % 2 == 0 else BG)
        c.rect(x0, y - row_h, total_w, row_h, fill=1, stroke=0)
        stk(c, GOLD_DIM); c.setLineWidth(0.2)
        c.line(x0, y - row_h, x0 + total_w, y - row_h)
        cx = x0
        for ci, cell in enumerate(row):
            c.setFont("Helvetica", 7.5); fill(c, TEXT)
            txt = truncate(c, cell, col_widths[ci] - 4*mm)
            c.drawString(cx + 2*mm, y - row_h + 2.2*mm, txt); cx += col_widths[ci]
        y -= row_h
    stk(c, GOLD); c.setLineWidth(0.5)
    c.rect(x0, y, total_w, row_h * (len(rows)+1), fill=0, stroke=1)
    return y - 4*mm

def alert_box(c, y, level, text, detail=""):
    """level: 'rouge' | 'orange' | 'vert'"""
    cols = {"rouge": RED, "orange": (0.8, 0.55, 0.1), "vert": GREEN}
    col = cols.get(level, MUTED)
    fill(c, BG_BAND); c.rect(ML, y - 7*mm, MR - ML, 7*mm, fill=1, stroke=0)
    fill(c, col); c.rect(ML, y - 7*mm, 2*mm, 7*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8); fill(c, TEXT)
    c.drawString(ML + 5*mm, y - 4.5*mm, text[:80])
    if detail and detail != "—":
        c.setFont("Helvetica", 7.5); fill(c, MUTED)
        c.drawRightString(MR - 3*mm, y - 4.5*mm, truncate(c, detail, 60*mm, size=7.5))
    return y - 8.5*mm

# ─── PAGE COUVERTURE ──────────────────────────────────────────────────────────
def page_cover(c, d):
    restaurant = v(d, "infos", "restaurant")
    date       = v(d, "infos", "date")
    auditeur   = v(d, "infos", "auditeur")
    ville      = v(d, "infos", "ville")
    fill(c, BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    fill(c, GOLD); c.rect(0, 0, 4*mm, H, fill=1, stroke=0)
    cy = H * 0.65
    c.setFont("Helvetica", 9); fill(c, GOLD_DIM)
    c.drawCentredString(W/2, cy + 22*mm, "LA CARTE")
    fill(c, GOLD); c.rect(W/2 - 25*mm, cy + 19*mm, 50*mm, 0.6*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 26); fill(c, TEXT)
    c.drawCentredString(W/2, cy + 6*mm, "RAPPORT D'AUDIT")
    c.setFont("Helvetica-Bold", 18); fill(c, GOLD)
    c.drawCentredString(W/2, cy - 5*mm, "COMPLET")
    fill(c, GOLD_DIM); c.rect(W/2 - 30*mm, cy - 10*mm, 60*mm, 0.4*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 14); fill(c, TEXT)
    c.drawCentredString(W/2, cy - 20*mm, restaurant)
    if ville and ville != "—":
        c.setFont("Helvetica", 10); fill(c, MUTED)
        c.drawCentredString(W/2, cy - 27*mm, ville)
    info_y = 38*mm
    for label, val in [("Client", restaurant), ("Ville", ville), ("Auditeur", auditeur), ("Date", date), ("Confidentialité", "Document strictement confidentiel")]:
        if val and val != "—":
            c.setFont("Helvetica-Bold", 8); fill(c, GOLD_DIM)
            c.drawString(ML + 10*mm, info_y, label.upper())
            c.setFont("Helvetica", 8); fill(c, TEXT)
            c.drawString(ML + 50*mm, info_y, val)
            info_y -= 6*mm
    fill(c, GOLD); c.rect(0, 0, W, 1*mm, fill=1, stroke=0)
    c.setFont("Helvetica", 7); fill(c, MUTED)
    c.drawCentredString(W/2, 5*mm, "www.lacarte-conseil.fr — lacarte.advisory@gmail.com")

# ─── PAGE SOMMAIRE ────────────────────────────────────────────────────────────
def page_sommaire(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "SOMMAIRE", restaurant, date)
    c.setFont("Helvetica-Bold", 16); fill(c, GOLD)
    c.drawString(ML, y, "SOMMAIRE")
    y -= 3*mm; fill(c, GOLD)
    c.rect(ML, y, MR - ML, 0.5*mm, fill=1, stroke=0); y -= 10*mm
    sections = [
        ("01", "Données utilisées", "3"),
        ("02", "Synthèse Exécutive", "4"),
        ("03", "Architecture & Lisibilité de la Carte", "5"),
        ("04", "Matrice Menu Engineering", "6"),
        ("05", "Re-pricing & Rationalisation", "7–8"),
        ("06", "Analyse CMV Global", "9"),
        ("07", "Analyse CMV par Catégorie", "10"),
        ("08", "Analyse Ticket Moyen", "11"),
        ("09", "Seuil de Rentabilité", "12"),
        ("10", "Analyse Fournisseurs", "13"),
        ("11", "Plan d'Action & Objectifs", "14"),
    ]
    for num, title, pg in sections:
        fill(c, BG_BAND); c.rect(ML, y - 2*mm, MR - ML, 9*mm, fill=1, stroke=0)
        fill(c, GOLD); c.rect(ML, y - 2*mm, 1*mm, 9*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9); fill(c, GOLD_DIM)
        c.drawString(ML + 4*mm, y + 2.5*mm, num)
        c.setFont("Helvetica-Bold", 9); fill(c, TEXT)
        c.drawString(ML + 16*mm, y + 2.5*mm, title.upper())
        c.setFont("Helvetica", 8); fill(c, MUTED)
        c.drawRightString(MR - 4*mm, y + 2.5*mm, f"p. {pg}")
        y -= 12*mm

# ─── PAGE DONNÉES UTILISÉES ───────────────────────────────────────────────────
def page_donnees(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "DONNÉES UTILISÉES", restaurant, date)
    y = sec_title(c, y, "01", "Données Utilisées", "Traçabilité — documents reçus, manquants et impact sur l'analyse")
    docs_recus    = d.get("donnees", {}).get("recus", [])
    docs_manquants = d.get("donnees", {}).get("manquants", [])
    periode       = v(d, "donnees", "periode")
    commentaire   = v(d, "donnees", "commentaire")

    y = sub(c, y, "Documents reçus")
    for doc in docs_recus:
        if not doc.get("nom"): continue
        fill(c, BG_BAND); c.rect(ML, y - 6*mm, MR - ML, 6*mm, fill=1, stroke=0)
        fill(c, GREEN); c.rect(ML, y - 6*mm, 2*mm, 6*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8); fill(c, TEXT)
        c.drawString(ML + 5*mm, y - 4*mm, v(doc, "nom"))
        c.setFont("Helvetica", 7.5); fill(c, MUTED)
        c.drawRightString(MR - 3*mm, y - 4*mm, v(doc, "detail"))
        y -= 7.5*mm

    y -= 3*mm
    y = sub(c, y, "Documents manquants & impact")
    for doc in docs_manquants:
        if not doc.get("nom"): continue
        fill(c, BG_BAND); c.rect(ML, y - 6*mm, MR - ML, 6*mm, fill=1, stroke=0)
        fill(c, (0.7, 0.4, 0.1)); c.rect(ML, y - 6*mm, 2*mm, 6*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8); fill(c, TEXT)
        c.drawString(ML + 5*mm, y - 4*mm, v(doc, "nom"))
        c.setFont("Helvetica", 7.5); fill(c, MUTED)
        c.drawRightString(MR - 3*mm, y - 4*mm, v(doc, "impact"))
        y -= 7.5*mm

    if periode != "—":
        y -= 3*mm; y = divider(c, y)
        y = lv(c, y, "Période analysée", periode)
    if commentaire != "—":
        y -= 2*mm
        c.setFont("Helvetica-Oblique", 8); fill(c, MUTED)
        y = wrap_text(c, commentaire, ML + 2*mm, y, MR - ML - 4*mm, font="Helvetica-Oblique", size=8)

# ─── PAGE SYNTHÈSE EXÉCUTIVE ──────────────────────────────────────────────────
def page_synthese(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "SYNTHÈSE EXÉCUTIVE", restaurant, date)
    y = sec_title(c, y, "02", "Synthèse Exécutive", "5 indicateurs clés + 3 décisions prioritaires")

    # 5 KPIs sur 2 lignes
    kpis = d.get("kpis", {})
    y = kpi_row(c, y, [
        ("MARGE\nMENU", v(kpis, "marge_menu"), MUTED),
        ("CMV\nGLOBAL", v(kpis, "cmv_global"), MUTED),
        ("TICKET\nMOYEN", v(kpis, "ticket_moyen"), GOLD),
    ])
    y -= 2*mm
    y = kpi_row(c, y, [
        ("SEUIL\nRENTABILITÉ", v(kpis, "seuil"), GOLD),
        ("MARGE\nSÉCURITÉ", v(kpis, "marge_securite"), GOLD),
    ])
    y -= 4*mm; y = divider(c, y)

    # 3 décisions
    y = sub(c, y, "3 Décisions Prioritaires")
    decisions = d.get("decisions", [])
    dec_colors = [GOLD, GOLD_DIM, MUTED]
    for i, dec in enumerate(decisions[:3]):
        titre = v(dec, "titre"); desc = v(dec, "description"); imp = v(dec, "impact")
        if titre == "—": continue
        fill(c, BG_BAND); c.roundRect(ML, y - 14*mm, MR - ML, 14*mm, 1.5*mm, fill=1, stroke=0)
        fill(c, dec_colors[i]); c.circle(ML + 6*mm, y - 7*mm, 3.5*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9); fill(c, BG)
        c.drawCentredString(ML + 6*mm, y - 8.5*mm, str(i+1))
        c.setFont("Helvetica-Bold", 9); fill(c, GOLD)
        c.drawString(ML + 13*mm, y - 4*mm, titre.upper())
        c.setFont("Helvetica", 8); fill(c, TEXT)
        c.drawString(ML + 13*mm, y - 9*mm, desc if desc != "—" else "")
        if imp != "—":
            c.setFont("Helvetica-Bold", 8); fill(c, GOLD)
            c.drawRightString(MR - 3*mm, y - 4*mm, imp)
        y -= 17*mm

    y = divider(c, y)
    # Tableau indicateurs synthèse
    y = sub(c, y, "Indicateurs avant / après recommandations")
    headers = ["INDICATEUR", "SITUATION ACTUELLE", "APRÈS RECOMMANDATIONS", "ÉCART"]
    rows_data = d.get("synthese_tableau", [])
    if not rows_data:
        rows_data = [
            ["Taux de marge menu",    v(kpis,"marge_menu"),    "—", "—"],
            ["CMV global",            v(kpis,"cmv_global"),    "—", "—"],
            ["Ticket moyen",          v(kpis,"ticket_moyen"),  "—", "—"],
            ["Marge de sécurité",     v(kpis,"marge_securite"),"—", "—"],
        ]
    table(c, y, headers, rows_data, [52*mm, 42*mm, 52*mm, 27*mm])

# ─── PAGE ARCHITECTURE & LISIBILITÉ ──────────────────────────────────────────
def page_inventaire(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "ARCHITECTURE & LISIBILITÉ", restaurant, date)
    y = sec_title(c, y, "03", "Architecture & Lisibilité de la Carte", "Structure, cohérence, positionnement")
    inv = d.get("inventaire", {})
    y = sub(c, y, "Données générales")
    y = lv(c, y, "Nombre total de références", v(inv, "nb_references"))
    y = lv(c, y, "Nombre de catégories",       v(inv, "nb_categories"))
    y = lv(c, y, "Doublons identifiés",        v(inv, "doublons"))
    y = lv(c, y, "Lisibilité < 90s",           v(inv, "lisibilite"))
    y = lv(c, y, "Cohérence positionnement",   v(inv, "coherence"))
    y -= 4*mm
    categories = inv.get("categories", [])
    if categories:
        y = sub(c, y, "Architecture des catégories")
        rows = [[v(cat,"nom"),v(cat,"nb_refs"),v(cat,"prix_min"),v(cat,"prix_max"),v(cat,"observation")] for cat in categories]
        y = table(c, y, ["CATÉGORIE","NB RÉFS","PRIX MIN","PRIX MAX","OBSERVATION"], rows, [42*mm,20*mm,22*mm,22*mm,67*mm])
        y -= 2*mm
    alertes = inv.get("alertes", [])
    if alertes:
        y = sub(c, y, "Signaux d'alerte")
        alerte_map = {"🔴 Critique": "rouge", "🟡 Attention": "orange", "🟢 OK": "vert"}
        for a in alertes:
            niveau = v(a, "niveau", default="🟡 Attention")
            level  = alerte_map.get(niveau, "orange")
            y = alert_box(c, y, level, v(a,"label"), v(a,"detail"))

# ─── PAGE MENU ENGINEERING ────────────────────────────────────────────────────
def page_menu_engineering(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "MATRICE MENU ENGINEERING", restaurant, date)
    y = sec_title(c, y, "04", "Matrice Menu Engineering", "Stars / Vaches à lait / Énigmes / Poids morts")
    plats = d.get("plats", [])
    counts = {k: len([p for p in plats if p.get("classe") == k]) for k in ["⭐ Star","❓ Énigme","🐄 Vache à lait","💀 Poids mort"]}
    mat_w = (MR - ML - 4*mm) / 2; mat_h = 35*mm
    quadrants = [(0,1,"⭐ STARS","Popularité haute\nMarge haute",GOLD,BG),(1,1,"ÉNIGMES","Popularité basse\nMarge haute",BG_BAND,GOLD),(0,0,"VACHES À LAIT","Popularité haute\nMarge basse",BG_BAND,TEXT),(1,0,"POIDS MORTS","Popularité basse\nMarge basse",BG_BAND,MUTED)]
    classe_keys = ["⭐ Star","❓ Énigme","🐄 Vache à lait","💀 Poids mort"]
    mat_x0 = ML; mat_y0 = y - mat_h * 2 - 4*mm
    for idx,(col,row,tq,desc,bg,fg) in enumerate(quadrants):
        qx = mat_x0 + col*(mat_w+4*mm); qy = mat_y0 + row*(mat_h+4*mm)
        fill(c,bg); c.roundRect(qx,qy,mat_w,mat_h,2*mm,fill=1,stroke=0)
        stk(c,GOLD_DIM); c.setLineWidth(0.4); c.roundRect(qx,qy,mat_w,mat_h,2*mm,fill=0,stroke=1)
        tc = BG if bg==GOLD else fg
        c.setFont("Helvetica-Bold",9); fill(c,tc); c.drawCentredString(qx+mat_w/2,qy+mat_h-7*mm,tq)
        lines=desc.split("\n"); c.setFont("Helvetica",7); fill(c,MUTED if bg!=GOLD else BG)
        c.drawCentredString(qx+mat_w/2,qy+mat_h-13*mm,lines[0]); c.drawCentredString(qx+mat_w/2,qy+mat_h-17*mm,lines[1])
        c.setFont("Helvetica-Bold",20); fill(c,tc)
        c.drawCentredString(qx+mat_w/2,qy+6*mm,str(counts.get(classe_keys[idx],0)))
        c.setFont("Helvetica",7); fill(c,MUTED if bg!=GOLD else BG)
        c.drawCentredString(qx+mat_w/2,qy+2*mm,"référence(s)")
    c.setFont("Helvetica",7); fill(c,MUTED)
    c.drawCentredString(mat_x0+mat_w,mat_y0-4*mm,"◄ POPULARITÉ ►")
    y = mat_y0 - 10*mm; y = divider(c, y)
    if plats:
        y = sub(c, y, "Tableau de classification")
        rows = [[v(p,"nom"),v(p,"categorie"),v(p,"prix_ttc"),v(p,"cout_matiere"),v(p,"marge_pct"),v(p,"pct_ventes"),v(p,"classe")] for p in plats]
        y = table(c, y, ["PLAT","CAT.","PRIX TTC","COÛT MAT.","MARGE %","% VENTES","CLASSE"], rows, [40*mm,18*mm,18*mm,18*mm,15*mm,15*mm,49*mm])
    c.setFont("Helvetica-Oblique",7); fill(c,MUTED)
    c.drawString(ML, y-3*mm, "Seuil popularité = popularité moyenne théorique × 70%  |  Marge brute = Prix HT − Coût matière")

# ─── PAGE RE-PRICING ──────────────────────────────────────────────────────────
def page_repricing(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "RE-PRICING & RATIONALISATION", restaurant, date)
    y = sec_title(c, y, "05", "Re-pricing & Rationalisation", "Recommandations tarifaires plat par plat")
    plats = d.get("plats", [])
    dec_colors = {"Maintien":MUTED,"Hausse":GOLD,"Baisse":(0.8,0.4,0.3),"Suppression":(0.7,0.3,0.3)}
    for plat in plats:
        if y < 55*mm: y = new_page(c, pn, tp, "RE-PRICING & RATIONALISATION", restaurant, date)
        dec = v(plat,"decision",default="Maintien"); dc = dec_colors.get(dec, MUTED)
        fill(c,BG_BAND); c.roundRect(ML,y-10*mm,MR-ML,10*mm,1.5*mm,fill=1,stroke=0)
        fill(c,dc); c.roundRect(ML,y-10*mm,3*mm,10*mm,1.5*mm,fill=1,stroke=0)
        c.setFont("Helvetica-Bold",10); fill(c,TEXT); c.drawString(ML+7*mm,y-4*mm,v(plat,"nom"))
        c.setFont("Helvetica",8); fill(c,MUTED); c.drawString(ML+7*mm,y-8*mm,v(plat,"categorie"))
        c.setFont("Helvetica-Bold",8); fill(c,dc)
        c.drawRightString(MR-3*mm,y-4*mm,dec.upper()); y -= 13*mm
        c1,c2,c3 = ML+2*mm,ML+55*mm,ML+110*mm
        c.setFont("Helvetica-Bold",7); fill(c,MUTED)
        c.drawString(c1,y,"PRIX ACTUEL"); c.drawString(c2,y,"PRIX RECOMMANDÉ"); c.drawString(c3,y,"MARGE ACTUELLE")
        y -= 5*mm
        c.setFont("Helvetica-Bold",10); fill(c,TEXT); c.drawString(c1,y,v(plat,"prix_ttc"))
        fill(c,GOLD); c.drawString(c2,y,v(plat,"prix_recommande"))
        c.setFont("Helvetica",9); fill(c,GOLD); c.drawString(c3,y,v(plat,"marge_pct"))
        y -= 7*mm
        just = v(plat,"justification")
        if just != "—":
            c.setFont("Helvetica-Bold",7); fill(c,MUTED); c.drawString(ML+2*mm,y,"JUSTIFICATION"); y -= 4*mm
            fill(c,TEXT); y = wrap_text(c,just,ML+2*mm,y,MR-ML-4*mm)
        imp = v(plat,"impact_estime")
        if imp != "—":
            c.setFont("Helvetica-Bold",7.5); fill(c,GOLD_DIM)
            c.drawString(ML+2*mm,y,f"Impact estimé : {imp}"); y -= 4*mm
        y = divider(c, y); y -= 2*mm

# ─── PAGE CMV GLOBAL ──────────────────────────────────────────────────────────
def page_cmv_global(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "ANALYSE CMV GLOBAL", restaurant, date)
    y = sec_title(c, y, "06", "Analyse CMV Global", "Coût Matière Variable — food + boissons")
    cmv = d.get("cmv", {})

    y = kpi_row(c, y, [
        ("CMV\nGLOBAL", v(cmv,"cmv_global"), GOLD),
        ("CMV\nFOOD", v(cmv,"cmv_food"), MUTED),
        ("CMV\nBOISSONS", v(cmv,"cmv_boissons"), MUTED),
    ])
    y -= 4*mm

    y = sub(c, y, "Comparaison aux benchmarks secteur")
    benchmarks = [
        ("CMV Food", v(cmv,"cmv_food"), "28–32 %", v(cmv,"verdict_food")),
        ("CMV Boissons", v(cmv,"cmv_boissons"), "20–25 %", v(cmv,"verdict_boissons")),
        ("CMV Global", v(cmv,"cmv_global"), "28–35 %", v(cmv,"verdict_global")),
    ]
    headers = ["INDICATEUR", "VALEUR RÉELLE", "BENCHMARK", "VERDICT"]
    rows = [[ind, val, bench, vert] for ind, val, bench, vert in benchmarks]
    y = table(c, y, headers, rows, [50*mm, 35*mm, 35*mm, 53*mm])
    y -= 4*mm

    ecart = v(cmv, "ecart_theorique_reel")
    fuite = v(cmv, "fuite_euros")
    if ecart != "—" or fuite != "—":
        y = sub(c, y, "Écart CMV théorique / réel")
        y = lv(c, y, "CMV théorique (fiches recettes)", v(cmv,"cmv_theorique"))
        y = lv(c, y, "CMV réel (achats / CA)",           v(cmv,"cmv_global"))
        y = lv(c, y, "Écart",                             ecart, RED if ecart != "—" else TEXT)
        y = lv(c, y, "Fuite estimée (€/an)",              fuite, RED if fuite != "—" else TEXT)
        y -= 3*mm
        commentaire = v(cmv, "commentaire")
        if commentaire != "—":
            c.setFont("Helvetica-Oblique", 8); fill(c, MUTED)
            y = wrap_text(c, commentaire, ML+2*mm, y, MR-ML-4*mm, font="Helvetica-Oblique", max_lines=4)

    alertes_cmv = cmv.get("alertes", [])
    if alertes_cmv:
        y -= 3*mm; y = sub(c, y, "Signaux d'alerte CMV")
        for a in alertes_cmv:
            if not a.get("texte"): continue
            level = "rouge" if ">" in a.get("texte","") or "élevé" in a.get("texte","").lower() else "orange"
            y = alert_box(c, y, level, v(a,"texte"), v(a,"detail"))

# ─── PAGE CMV PAR CATÉGORIE ───────────────────────────────────────────────────
def page_cmv_categories(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "CMV PAR CATÉGORIE", restaurant, date)
    y = sec_title(c, y, "07", "Analyse CMV par Catégorie", "Décomposition food / boissons / familles")
    cmv_cats = d.get("cmv_categories", {})
    cats = cmv_cats.get("categories", [])
    if cats:
        y = sub(c, y, "CMV par famille de produits")
        headers = ["FAMILLE", "CA (PÉRIODE)", "ACHATS", "CMV %", "BENCHMARK", "ÉCART", "ACTION"]
        rows = [[v(cat,"famille"),v(cat,"ca"),v(cat,"achats"),v(cat,"cmv_pct"),v(cat,"benchmark"),v(cat,"ecart"),v(cat,"action")] for cat in cats]
        y = table(c, y, headers, rows, [30*mm,22*mm,22*mm,18*mm,22*mm,18*mm,41*mm])
        y -= 4*mm
    croisement = cmv_cats.get("croisement_engineering", [])
    if croisement:
        y = sub(c, y, "Croisement familles à CMV élevé × Matrice Engineering")
        for item in croisement:
            if not item.get("famille"): continue
            fill(c, BG_BAND); c.roundRect(ML, y-12*mm, MR-ML, 12*mm, 1.5*mm, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 9); fill(c, GOLD)
            c.drawString(ML+5*mm, y-4*mm, v(item,"famille").upper())
            c.setFont("Helvetica", 8); fill(c, TEXT)
            c.drawString(ML+5*mm, y-9*mm, f"CMV : {v(item,'cmv_pct')}  ·  Classe : {v(item,'classe_engineering')}  ·  {v(item,'recommandation')}")
            y -= 14*mm
    y -= 3*mm
    y = sub(c, y, "Calcul CMV théorique vs réel (si fiches recettes disponibles)")
    fiches = cmv_cats.get("fiches_recettes", {})
    dispo = v(fiches, "disponibles")
    y = lv(c, y, "Fiches recettes disponibles", dispo)
    if dispo not in ("—", "Non", "0"):
        y = lv(c, y, "CMV théorique calculé",  v(fiches,"cmv_theorique"))
        y = lv(c, y, "CMV réel constaté",      v(fiches,"cmv_reel"))
        y = lv(c, y, "Écart",                  v(fiches,"ecart"), RED)
        y = lv(c, y, "Fuite annuelle estimée",  v(fiches,"fuite_annuelle"), RED)
        note = v(fiches, "note")
        if note != "—":
            y -= 2*mm; c.setFont("Helvetica-Oblique", 8); fill(c, MUTED)
            y = wrap_text(c, note, ML+2*mm, y, MR-ML-4*mm, font="Helvetica-Oblique", max_lines=3)

# ─── PAGE TICKET MOYEN ────────────────────────────────────────────────────────
def page_ticket_moyen(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "ANALYSE TICKET MOYEN", restaurant, date)
    y = sec_title(c, y, "08", "Analyse Ticket Moyen", "Évolution, segmentation, leviers d'amélioration")
    tm = d.get("ticket_moyen", {})

    y = kpi_row(c, y, [
        ("TICKET MOYEN\nGLOBAL", v(tm,"ticket_global"), GOLD),
        ("TICKET\nDÉJEUNER", v(tm,"ticket_dejeuner"), MUTED),
        ("TICKET\nDÎNER", v(tm,"ticket_diner"), MUTED),
    ])
    y -= 4*mm

    evolution = tm.get("evolution", [])
    if evolution:
        y = sub(c, y, "Évolution mensuelle")
        headers = ["MOIS", "CA", "COUVERTS", "TICKET MOY.", "VARIATION", "ÉVÉNEMENT / COMMENTAIRE"]
        rows = [[v(m,"mois"),v(m,"ca"),v(m,"couverts"),v(m,"ticket"),v(m,"variation"),v(m,"evenement")] for m in evolution]
        y = table(c, y, headers, rows, [20*mm,22*mm,22*mm,22*mm,18*mm,69*mm])
        y -= 4*mm

    y = sub(c, y, "Leviers d'amélioration identifiés")
    leviers = tm.get("leviers", [])
    for levier in leviers:
        if not levier.get("levier"): continue
        fill(c, BG_BAND); c.rect(ML, y-7*mm, MR-ML, 7*mm, fill=1, stroke=0)
        fill(c, GOLD); c.rect(ML, y-7*mm, 2*mm, 7*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8); fill(c, TEXT)
        c.drawString(ML+5*mm, y-4.5*mm, v(levier,"levier"))
        c.setFont("Helvetica-Bold", 8); fill(c, GOLD)
        c.drawRightString(MR-3*mm, y-4.5*mm, v(levier,"impact"))
        y -= 8.5*mm
    y -= 3*mm
    impact_1eu = v(tm, "impact_1euro")
    if impact_1eu != "—":
        fill(c, BG_BAND); c.roundRect(ML, y-12*mm, MR-ML, 12*mm, 2*mm, fill=1, stroke=0)
        stk(c, GOLD); c.setLineWidth(0.5)
        c.roundRect(ML, y-12*mm, MR-ML, 12*mm, 2*mm, fill=0, stroke=1)
        c.setFont("Helvetica-Bold", 9); fill(c, GOLD)
        c.drawString(ML+5*mm, y-4*mm, "Impact d'une hausse de +1 € de ticket moyen")
        c.setFont("Helvetica-Bold", 12); fill(c, GOLD)
        c.drawRightString(MR-5*mm, y-4*mm, impact_1eu)
        c.setFont("Helvetica", 8); fill(c, MUTED)
        c.drawString(ML+5*mm, y-9*mm, "Gain annuel estimé sur CA")

# ─── PAGE SEUIL DE RENTABILITÉ ────────────────────────────────────────────────
def page_seuil(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "SEUIL DE RENTABILITÉ", restaurant, date)
    y = sec_title(c, y, "09", "Seuil de Rentabilité", "Charges fixes, taux de charges variables, marge de sécurité")
    seuil = d.get("seuil", {})

    marge_sec = v(seuil, "marge_securite")
    col_ms = RED if any(x in str(marge_sec) for x in ["1%","2%","3%","4%","5%","6%","7%","8%","9%","0%"]) else GOLD
    y = kpi_row(c, y, [
        ("SEUIL\nRENTABILITÉ (€/mois)", v(seuil,"seuil_euros"), GOLD),
        ("SEUIL EN\nCOUVERTS/JOUR", v(seuil,"seuil_couverts"), GOLD),
        ("MARGE DE\nSÉCURITÉ", marge_sec, col_ms),
    ])
    y -= 4*mm

    y = sub(c, y, "Charges fixes mensuelles")
    charges_fixes = seuil.get("charges_fixes", [])
    if charges_fixes:
        headers = ["POSTE DE CHARGE", "MONTANT MENSUEL", "OBSERVATION"]
        rows = [[v(ch,"poste"),v(ch,"montant"),v(ch,"observation")] for ch in charges_fixes]
        y = table(c, y, headers, rows, [75*mm, 45*mm, 53*mm])
        y = lv(c, y+4*mm, "TOTAL CHARGES FIXES", v(seuil,"total_charges_fixes"), GOLD)
        y -= 4*mm

    y = sub(c, y, "Calcul du seuil")
    y = lv(c, y, "Total charges fixes (CF)",          v(seuil,"total_charges_fixes"))
    y = lv(c, y, "Taux charges variables (%)",         v(seuil,"taux_charges_variables"))
    y = lv(c, y, "Seuil = CF ÷ (1 − taux CV)",        v(seuil,"seuil_euros"), GOLD)
    y = lv(c, y, "Ticket moyen utilisé",               v(seuil,"ticket_moyen_utilise"))
    y = lv(c, y, "Seuil en couverts / jour",           v(seuil,"seuil_couverts"), GOLD)
    y = lv(c, y, "CA actuel",                           v(seuil,"ca_actuel"))
    y = lv(c, y, "Marge de sécurité = (CA − seuil)/CA", marge_sec,
           RED if "%" in str(marge_sec) else GOLD)
    y -= 4*mm

    commentaire = v(seuil, "commentaire")
    alerte_ms = v(seuil, "alerte_marge_securite")
    if alerte_ms not in ("—", "Non", ""):
        y = alert_box(c, y, "rouge", f"⚠ Marge de sécurité < 10% — {alerte_ms}")
    if commentaire != "—":
        y -= 2*mm; c.setFont("Helvetica-Oblique", 8); fill(c, MUTED)
        y = wrap_text(c, commentaire, ML+2*mm, y, MR-ML-4*mm, font="Helvetica-Oblique", max_lines=4)

# ─── PAGE FOURNISSEURS ────────────────────────────────────────────────────────
def page_fournisseurs(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "ANALYSE FOURNISSEURS", restaurant, date)
    y = sec_title(c, y, "10", "Analyse Fournisseurs", "Cartographie, dépendances, leviers de renégociation")
    fournisseurs = d.get("fournisseurs", {})
    liste = fournisseurs.get("liste", [])

    if liste:
        y = sub(c, y, "Cartographie des fournisseurs actifs")
        headers = ["FOURNISSEUR","CATÉGORIE","ACHATS (PÉRIODE)","FRÉQUENCE","DÉPENDANCE","STATUT"]
        rows = [[v(f,"nom"),v(f,"categorie"),v(f,"montant"),v(f,"frequence"),v(f,"dependance"),v(f,"statut")] for f in liste]
        y = table(c, y, headers, rows, [38*mm,25*mm,28*mm,22*mm,22*mm,38*mm])
        y -= 4*mm

    alertes_f = fournisseurs.get("alertes", [])
    if alertes_f:
        y = sub(c, y, "Signaux d'alerte & dépendances")
        for a in alertes_f:
            if not a.get("texte"): continue
            level = "rouge" if v(a,"niveau") == "🔴 Critique" else "orange" if v(a,"niveau") == "🟡 Attention" else "vert"
            y = alert_box(c, y, level, v(a,"texte"), v(a,"detail"))
        y -= 3*mm

    recommandations = fournisseurs.get("recommandations", [])
    if recommandations:
        y = sub(c, y, "Recommandations de renégociation")
        for reco in recommandations:
            if not reco.get("fournisseur"): continue
            if y < 45*mm: y = new_page(c, pn, tp, "ANALYSE FOURNISSEURS", restaurant, date)
            fill(c, BG_BAND); c.roundRect(ML, y-14*mm, MR-ML, 14*mm, 1.5*mm, fill=1, stroke=0)
            statut = v(reco,"statut")
            col_s = GREEN if "différenciant" in statut.lower() else GOLD
            c.setFont("Helvetica-Bold", 9); fill(c, col_s)
            c.drawString(ML+5*mm, y-4*mm, v(reco,"fournisseur").upper())
            c.setFont("Helvetica", 8); fill(c, TEXT)
            c.drawString(ML+5*mm, y-9*mm, v(reco,"recommandation"))
            c.setFont("Helvetica-Bold", 8); fill(c, GOLD)
            c.drawRightString(MR-3*mm, y-4*mm, v(reco,"gain_potentiel"))
            c.setFont("Helvetica", 7.5); fill(c, MUTED)
            c.drawRightString(MR-3*mm, y-9*mm, statut)
            y -= 17*mm

# ─── PAGE PLAN D'ACTION ───────────────────────────────────────────────────────
def page_plan_action(c, pn, tp, d):
    restaurant = v(d, "infos", "restaurant"); date = v(d, "infos", "date")
    y = new_page(c, pn, tp, "PLAN D'ACTION & OBJECTIFS", restaurant, date)
    y = sec_title(c, y, "11", "Plan d'Action", "S1 / M1 / M2-3 + tableau de bord des objectifs chiffrés")
    plan = d.get("plan_action", {})
    phases = [("S1","Semaine 1 — Actions immédiates",GOLD),("M1","Mois 1 — Consolidation",GOLD_DIM),("M2_3","Mois 2–3 — Optimisation continue",MUTED)]
    for key, label_p, color in phases:
        actions = [a for a in plan.get(key, []) if a and str(a).strip()]
        if not actions: continue
        fill(c, BG_BAND); c.roundRect(ML, y-8*mm, MR-ML, 8*mm, 1.5*mm, fill=1, stroke=0)
        stk(c, color); c.setLineWidth(0.6); c.roundRect(ML, y-8*mm, MR-ML, 8*mm, 1.5*mm, fill=0, stroke=1)
        fill(c, color); c.setFont("Helvetica-Bold", 10)
        c.drawString(ML+4*mm, y-5.5*mm, key)
        fill(c, TEXT); c.setFont("Helvetica-Bold", 9)
        c.drawString(ML+18*mm, y-5.5*mm, label_p); y -= 10*mm
        for action in actions:
            if y < 50*mm: y = new_page(c, pn, tp, "PLAN D'ACTION & OBJECTIFS", restaurant, date)
            fill(c, color); c.circle(ML+7*mm, y-2.5*mm, 1.2*mm, fill=1, stroke=0)
            c.setFont("Helvetica", 8.5); fill(c, TEXT)
            c.drawString(ML+12*mm, y-4*mm, str(action)[:100]); y -= 6.5*mm
        y -= 3*mm
    y = divider(c, y); y -= 2*mm
    objectifs = [o for o in d.get("objectifs", []) if o.get("objectif","").strip()]
    if objectifs:
        y = sub(c, y, "Tableau de Bord des Objectifs Chiffrés")
        headers = ["OBJECTIF","VALEUR ACTUELLE","CIBLE","ÉCHÉANCE","INDICATEUR DE SUIVI"]
        rows = [[v(o,"objectif"),v(o,"valeur_actuelle"),v(o,"cible"),v(o,"echeance"),v(o,"indicateur")] for o in objectifs]
        table(c, y, headers, rows, [50*mm,28*mm,22*mm,20*mm,53*mm])

# ─── ENTRÉE PRINCIPALE ────────────────────────────────────────────────────────
def generate_pdf_complet(data: dict) -> bytes:
    buffer = io.BytesIO()
    restaurant = v(data, "infos", "restaurant", default="Audit Complet")
    date       = v(data, "infos", "date", default="")
    TOTAL = 13
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Rapport Audit Complet — {restaurant}")
    c.setAuthor("La Carte")

    # P1 : Couverture
    fill(c, BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    page_cover(c, data)

    # P2 : Sommaire
    page_sommaire(c, 2, TOTAL, data)

    # P3 : Données utilisées
    page_donnees(c, 3, TOTAL, data)

    # P4 : Synthèse exécutive
    page_synthese(c, 4, TOTAL, data)

    # P5 : Architecture & lisibilité
    page_inventaire(c, 5, TOTAL, data)

    # P6 : Menu Engineering
    page_menu_engineering(c, 6, TOTAL, data)

    # P7-8 : Re-pricing
    page_repricing(c, 7, TOTAL, data)

    # P9 : CMV Global
    page_cmv_global(c, 9, TOTAL, data)

    # P10 : CMV par catégorie
    page_cmv_categories(c, 10, TOTAL, data)

    # P11 : Ticket moyen
    page_ticket_moyen(c, 11, TOTAL, data)

    # P12 : Seuil de rentabilité
    page_seuil(c, 12, TOTAL, data)

    # P13 : Fournisseurs
    page_fournisseurs(c, 13, TOTAL, data)

    # P14 : Plan d'action
    page_plan_action(c, 14, TOTAL, data)

    c.save(); buffer.seek(0)
    return buffer.read()


if __name__ == "__main__":
    sample = {
        "infos": {"restaurant":"Le Bistrot du Port","date":"Mai 2025","auditeur":"Anthony Grimault","ville":"Nantes"},
        "kpis": {"marge_menu":"64 %","cmv_global":"31 %","ticket_moyen":"28,50 €","seuil":"18 200 €/mois","marge_securite":"14 %"},
        "decisions": [
            {"titre":"Re-pricing menu","description":"Hausse tarifaire sur 6 plats sous-évalués","impact":"+800 €/mois"},
            {"titre":"Réduction CMV","description":"Renégociation 2 fournisseurs + suppression 4 références","impact":"−3 pts CMV"},
            {"titre":"Hausse ticket moyen","description":"Développement ventes additionnelles","impact":"+1 200 €/mois CA"},
        ],
        "donnees": {
            "recus": [{"nom":"Carte PDF","detail":"Version avril 2025"},{"nom":"Tickets Z — 6 mois","detail":"Oct 2024 – Mar 2025"},{"nom":"Factures fournisseurs","detail":"3 fournisseurs principaux"}],
            "manquants": [{"nom":"Fiches recettes","impact":"CMV théorique non calculable — estimation utilisée"},{"nom":"Données couverts dîner","impact":"Segmentation déjeuner/dîner partielle"}],
            "periode":"Octobre 2024 – Mars 2025 (6 mois)",
            "commentaire":"Toutes les recommandations chiffrées sont basées sur les données reçues. Les sections sans données suffisantes ont été exclues.",
        },
        "inventaire": {
            "nb_references":"38","nb_categories":"5","doublons":"3","lisibilite":"Partielle","coherence":"Bistrot traditionnel",
            "categories":[{"nom":"Entrées","nb_refs":"8","prix_min":"8,50 €","prix_max":"14,00 €","observation":"OK"},{"nom":"Plats","nb_refs":"16","prix_min":"16,00 €","prix_max":"28,00 €","observation":"Trop large"}],
            "alertes":[{"niveau":"🔴 Critique","label":"38 références — illisible en moins de 90s","detail":""},{"niveau":"🟢 OK","label":"Cohérence bistrot traditionnel","detail":""}],
        },
        "plats": [
            {"nom":"Entrecôte Bordelaise","categorie":"Plats","prix_ttc":"24,00 €","cout_matiere":"8,50 €","marge_pct":"64 %","pct_ventes":"18 %","classe":"⭐ Star","prix_recommande":"26,00 €","decision":"Hausse","justification":"Sous-évalué vs concurrence. +2€ absorbable.","impact_estime":"+240 €/mois"},
            {"nom":"Filet de poisson","categorie":"Plats","prix_ttc":"19,00 €","cout_matiere":"9,00 €","marge_pct":"52 %","pct_ventes":"3 %","classe":"💀 Poids mort","prix_recommande":"—","decision":"Suppression","justification":"Faible popularité, coût opérationnel élevé.","impact_estime":"Simplification"},
        ],
        "cmv": {
            "cmv_global":"31 %","cmv_food":"33 %","cmv_boissons":"22 %",
            "verdict_food":"⚠ Au-dessus du benchmark","verdict_boissons":"✓ Dans la cible","verdict_global":"⚠ Limite haute",
            "cmv_theorique":"28 %","ecart_theorique_reel":"3 pts","fuite_euros":"8 400 €/an",
            "commentaire":"Un écart de 3 points entre CMV théorique et réel suggère des pertes ou un manque de rigueur sur les grammages.",
            "alertes":[{"texte":"CMV Food > 32% — dépasse le benchmark","detail":"Croiser avec les familles à CMV élevé"}],
        },
        "cmv_categories": {
            "categories":[
                {"famille":"Viandes","ca":"12 400 €","achats":"4 340 €","cmv_pct":"35 %","benchmark":"28–32 %","ecart":"+3 pts","action":"Renégocier ou reformuler"},
                {"famille":"Poissons","ca":"3 200 €","achats":"1 440 €","cmv_pct":"45 %","benchmark":"30–35 %","ecart":"+10 pts","action":"Réduire ou supprimer"},
                {"famille":"Boissons","ca":"6 800 €","achats":"1 496 €","cmv_pct":"22 %","benchmark":"20–25 %","ecart":"OK","action":"Maintien"},
            ],
            "croisement_engineering":[{"famille":"Poissons","cmv_pct":"45 %","classe_engineering":"💀 Poids mort","recommandation":"Suppression prioritaire — double impact"}],
            "fiches_recettes":{"disponibles":"Partielle (12/38)","cmv_theorique":"28 %","cmv_reel":"31 %","ecart":"3 pts","fuite_annuelle":"8 400 €","note":"Écart formulé sans accusation — peut relever d'erreurs de grammage ou de pertes cuisine."},
        },
        "ticket_moyen": {
            "ticket_global":"28,50 €","ticket_dejeuner":"22,00 €","ticket_diner":"34,00 €",
            "evolution":[
                {"mois":"Oct 2024","ca":"18 200 €","couverts":"638","ticket":"28,52 €","variation":"—","evenement":"—"},
                {"mois":"Nov 2024","ca":"16 400 €","couverts":"590","ticket":"27,80 €","variation":"−2,5 %","evenement":"Baisse saisonnière"},
                {"mois":"Mar 2025","ca":"19 800 €","couverts":"670","ticket":"29,55 €","variation":"+6,3 %","evenement":"Hausse de 3 prix"},
            ],
            "leviers":[{"levier":"Développer les ventes de desserts (+0,80€/couvert potentiel)","impact":"+6 100 €/an"},{"levier":"Proposition systématique de vin au verre","impact":"+4 200 €/an"}],
            "impact_1euro":"+7 640 €/an",
        },
        "seuil": {
            "seuil_euros":"18 200 €/mois","seuil_couverts":"21 couverts/jour","marge_securite":"14 %",
            "total_charges_fixes":"9 800 €","taux_charges_variables":"46 %","ticket_moyen_utilise":"28,50 €","ca_actuel":"21 200 €/mois",
            "alerte_marge_securite":"",
            "charges_fixes":[{"poste":"Loyer","montant":"3 200 €","observation":"Bail commercial"},{"poste":"Salaires fixes","montant":"4 800 €","observation":"2 ETP"},{"poste":"Assurances + abonnements","montant":"680 €","observation":"—"},{"poste":"Expert-comptable","montant":"320 €","observation":"Mensuel"},{"poste":"Amortissements","montant":"800 €","observation":"Matériel cuisine"}],
            "commentaire":"La marge de sécurité de 14% est correcte mais fragile. Une baisse de fréquentation de 15% suffirait à passer sous le seuil.",
        },
        "fournisseurs": {
            "liste":[
                {"nom":"Metro Cash","categorie":"Épicerie / produits frais","montant":"4 200 €","frequence":"2×/sem","dependance":"42 %","statut":"À renégocier"},
                {"nom":"Boucherie Lebreton","categorie":"Viandes","montant":"2 800 €","frequence":"3×/sem","dependance":"100 %","statut":"Différenciant — à conserver"},
                {"nom":"Pomona","categorie":"Fruits & Légumes","montant":"1 100 €","frequence":"1×/sem","dependance":"100 %","statut":"Comparer Transgourmet"},
            ],
            "alertes":[{"niveau":"🔴 Critique","texte":"Pomona — fournisseur unique F&L, prix +12% vs marché","detail":"Comparer Transgourmet ou local"},{"niveau":"🟡 Attention","texte":"Metro > 30% des achats globaux — dépendance","detail":"Diversifier sur 2–3 postes"}],
            "recommandations":[
                {"fournisseur":"Pomona","recommandation":"Obtenir devis Transgourmet — économie estimée sur F&L","gain_potentiel":"−1 400 €/an","statut":"À challenger"},
                {"fournisseur":"Metro","recommandation":"Renégocier compte fidélité — volumes suffisants pour remise","gain_potentiel":"−800 €/an","statut":"À renégocier"},
                {"fournisseur":"Boucherie Lebreton","recommandation":"Ne pas changer — qualité différenciante pour les plats stars","gain_potentiel":"—","statut":"Fournisseur différenciant"},
            ],
        },
        "plan_action": {
            "S1":["Supprimer 4 références poids morts","Appliquer hausses tarifaires validées","Contacter Pomona + Transgourmet pour devis comparatif"],
            "M1":["Refonte mise en page carte","Renégocier contrat Metro","Briefing équipe sur plats à pousser"],
            "M2_3":["Analyse résultats post-refonte","Ajustements fins CMV","Bilan fournisseurs"],
        },
        "objectifs":[
            {"objectif":"Taux de marge menu","valeur_actuelle":"64 %","cible":"70 %","echeance":"M1","indicateur":"Fiches recettes + caisse"},
            {"objectif":"CMV Global","valeur_actuelle":"31 %","cible":"28 %","echeance":"M2","indicateur":"Factures fournisseurs / CA"},
            {"objectif":"Ticket moyen","valeur_actuelle":"28,50 €","cible":"30,00 €","echeance":"M3","indicateur":"Z quotidien"},
            {"objectif":"Seuil couverts/jour","valeur_actuelle":"21","cible":"18","echeance":"M2","indicateur":"Baisse charges + hausse ticket"},
        ],
    }
    pdf_bytes = generate_pdf_complet(sample)
    with open("/mnt/user-data/outputs/rapport_audit_complet_test.pdf","wb") as f:
        f.write(pdf_bytes)
    print(f"✅ Audit Complet : {len(pdf_bytes)} bytes")
