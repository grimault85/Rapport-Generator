"""
La Carte — Générateur PDF Rapport de Suivi Mensuel
6 pages max : Tableau de bord / Alertes / Focus / Recommandations / Annexes
"""

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

BG       = (0.082, 0.122, 0.165)
BG_BAND  = (0.102, 0.145, 0.208)
GOLD     = (0.788, 0.659, 0.298)
GOLD_DIM = (0.620, 0.522, 0.251)
TEXT     = (0.933, 0.902, 0.788)
MUTED    = (0.722, 0.667, 0.541)
RED      = (0.75, 0.25, 0.25)
ORANGE   = (0.80, 0.55, 0.10)
GREEN    = (0.25, 0.60, 0.30)

W, H = A4
ML   = 18*mm
MR   = W - 18*mm
MTOP = H - 14*mm

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
    if not text or text == "—": return y
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

def draw_header(c, page_num, total_pages, section_title=""):
    fill(c, BG_BAND); c.rect(0, H-22*mm, W, 22*mm, fill=1, stroke=0)
    fill(c, GOLD);    c.rect(0, H-23*mm, W, 0.7*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 11); fill(c, GOLD)
    c.drawString(ML, H-13*mm, "LA CARTE")
    c.setFont("Helvetica", 7); fill(c, MUTED)
    c.drawString(ML, H-17*mm, "CONSEIL & STRATÉGIE CHR")
    if section_title:
        c.setFont("Helvetica-Bold", 9); fill(c, TEXT)
        c.drawCentredString(W/2, H-14*mm, section_title.upper())
    c.setFont("Helvetica", 8); fill(c, MUTED)
    c.drawRightString(MR, H-14*mm, f"{page_num} / {total_pages}")

def draw_footer(c, restaurant="", mois=""):
    fill(c, GOLD);    c.rect(0, 11*mm, W, 0.5*mm, fill=1, stroke=0)
    fill(c, BG_BAND); c.rect(0, 0, W, 11*mm, fill=1, stroke=0)
    c.setFont("Helvetica", 7); fill(c, MUTED)
    c.drawString(ML, 4*mm, f"Suivi Mensuel — {restaurant} — {mois}")
    c.drawCentredString(W/2, 4*mm, "Document confidentiel — La Carte")
    c.drawRightString(MR, 4*mm, "lacarte-conseil.fr")

def new_page(c, pn, tp, section, restaurant, mois):
    c.showPage()
    fill(c, BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    draw_header(c, pn, tp, section)
    draw_footer(c, restaurant, mois)
    return MTOP - 28*mm

def sec_title(c, y, number, title, subtitle=""):
    fill(c, GOLD); c.rect(ML, y-5*mm, 1.2*mm, 12*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 15); fill(c, GOLD)
    c.drawString(ML+5*mm, y+4*mm, f"{number}.")
    c.setFont("Helvetica-Bold", 13); fill(c, TEXT)
    c.drawString(ML+15*mm, y+4*mm, title.upper())
    if subtitle:
        c.setFont("Helvetica", 8); fill(c, MUTED)
        c.drawString(ML+15*mm, y-1*mm, subtitle)
    return y - 14*mm

def sub(c, y, text):
    fill(c, BG_BAND); c.rect(ML, y-1*mm, MR-ML, 7*mm, fill=1, stroke=0)
    fill(c, GOLD_DIM); c.rect(ML, y-1*mm, 0.8*mm, 7*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9); fill(c, GOLD)
    c.drawString(ML+4*mm, y+3*mm, text.upper())
    return y - 10*mm

def divider(c, y):
    stk(c, GOLD_DIM); c.setLineWidth(0.4)
    c.line(ML, y, MR, y); return y - 4*mm

def alerte_color(niveau):
    if "🔴" in str(niveau): return RED
    if "🟡" in str(niveau): return ORANGE
    if "🟢" in str(niveau): return GREEN
    return MUTED

def status_icon(val):
    """Retourne 🔴/🟡/🟢 selon la valeur du statut saisi."""
    if not val or val == "—": return "—"
    v_lower = str(val).lower()
    if any(x in v_lower for x in ["rouge","🔴","urgent","critique"]): return "🔴"
    if any(x in v_lower for x in ["orange","🟡","jaune","surveiller"]): return "🟡"
    if any(x in v_lower for x in ["vert","🟢","ok","positif","atteint"]): return "🟢"
    return val


# ─── PAGE COUVERTURE ──────────────────────────────────────────────────────────
def page_cover(c, d):
    restaurant = v(d,"infos","restaurant")
    mois       = v(d,"infos","mois")
    auditeur   = v(d,"infos","auditeur")

    fill(c, BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    fill(c, GOLD); c.rect(0, 0, 4*mm, H, fill=1, stroke=0)

    cy = H * 0.65
    c.setFont("Helvetica", 9); fill(c, GOLD_DIM)
    c.drawCentredString(W/2, cy+22*mm, "LA CARTE")
    fill(c, GOLD); c.rect(W/2-25*mm, cy+19*mm, 50*mm, 0.6*mm, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 24); fill(c, TEXT)
    c.drawCentredString(W/2, cy+6*mm, "RAPPORT DE SUIVI")
    c.setFont("Helvetica-Bold", 18); fill(c, GOLD)
    c.drawCentredString(W/2, cy-5*mm, "MENSUEL")
    fill(c, GOLD_DIM); c.rect(W/2-30*mm, cy-10*mm, 60*mm, 0.4*mm, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 14); fill(c, TEXT)
    c.drawCentredString(W/2, cy-20*mm, restaurant)
    c.setFont("Helvetica-Bold", 11); fill(c, GOLD)
    c.drawCentredString(W/2, cy-28*mm, mois)

    info_y = 38*mm
    for label, val in [("Client", restaurant), ("Période", mois), ("Auditeur", auditeur), ("Confidentialité", "Document strictement confidentiel")]:
        if val and val != "—":
            c.setFont("Helvetica-Bold", 8); fill(c, GOLD_DIM)
            c.drawString(ML+10*mm, info_y, label.upper())
            c.setFont("Helvetica", 8); fill(c, TEXT)
            c.drawString(ML+50*mm, info_y, val)
            info_y -= 6*mm

    fill(c, GOLD); c.rect(0, 0, W, 1*mm, fill=1, stroke=0)
    c.setFont("Helvetica", 7); fill(c, MUTED)
    c.drawCentredString(W/2, 5*mm, "www.lacarte-conseil.fr — lacarte.advisory@gmail.com")


# ─── PAGE 1 : TABLEAU DE BORD ─────────────────────────────────────────────────
def page_tableau_bord(c, pn, tp, d):
    restaurant = v(d,"infos","restaurant"); mois = v(d,"infos","mois")
    y = new_page(c, pn, tp, "TABLEAU DE BORD", restaurant, mois)
    y = sec_title(c, y, "01", "Tableau de Bord", f"{mois} — 5 indicateurs clés")

    kpis = d.get("kpis", [])

    # Tableau KPIs
    headers = ["INDICATEUR", "VALEUR DU MOIS", "VS MOIS PRÉC.", "VS OBJECTIF", "STATUT"]
    col_widths = [50*mm, 32*mm, 32*mm, 32*mm, 27*mm]
    total_w = sum(col_widths)
    x0 = ML

    # Header
    fill(c, GOLD_DIM); c.rect(x0, y-8*mm, total_w, 8*mm, fill=1, stroke=0)
    cx = x0
    for i, h in enumerate(headers):
        c.setFont("Helvetica-Bold", 7.5); fill(c, BG)
        c.drawString(cx+2*mm, y-5.5*mm, h); cx += col_widths[i]
    y -= 8*mm

    for ri, kpi in enumerate(kpis):
        indicateur   = v(kpi,"indicateur")
        valeur       = v(kpi,"valeur")
        vs_precedent = v(kpi,"vs_precedent")
        vs_objectif  = v(kpi,"vs_objectif")
        statut       = v(kpi,"statut")
        col_s        = alerte_color(statut)

        bg = BG_BAND if ri % 2 == 0 else BG
        fill(c, bg); c.rect(x0, y-8*mm, total_w, 8*mm, fill=1, stroke=0)
        # Barre couleur statut à gauche
        fill(c, col_s); c.rect(x0, y-8*mm, 2*mm, 8*mm, fill=1, stroke=0)
        stk(c, GOLD_DIM); c.setLineWidth(0.2)
        c.line(x0, y-8*mm, x0+total_w, y-8*mm)

        data_row = [indicateur, valeur, vs_precedent, vs_objectif, status_icon(statut)]
        cx = x0
        for ci, cell in enumerate(data_row):
            c.setFont("Helvetica-Bold" if ci==0 else "Helvetica", 8)
            fill(c, GOLD if ci==1 else TEXT)
            txt = truncate(c, cell, col_widths[ci]-4*mm)
            c.drawString(cx+2*mm, y-5.5*mm, txt)
            cx += col_widths[ci]
        y -= 8*mm

    stk(c, GOLD); c.setLineWidth(0.5)
    c.rect(x0, y, total_w, 8*mm*(len(kpis)+1), fill=0, stroke=1)
    y -= 8*mm

    y = divider(c, y)

    # Bloc CA & Ticket moyen détaillé
    ca = d.get("ca_ticket", {})
    y = sub(c, y, "CA & Ticket Moyen — Détail")

    details = [
        ("CA du mois",            v(ca,"ca_mois")),
        ("Nombre de couverts",    v(ca,"couverts")),
        ("Ticket moyen global",   v(ca,"ticket_global")),
        ("Ticket moyen midi",     v(ca,"ticket_midi")),
        ("Ticket moyen soir",     v(ca,"ticket_soir")),
        ("Vs mois précédent",     v(ca,"vs_precedent")),
        ("Vs même mois N-1",      v(ca,"vs_n_moins_1")),
    ]
    col1_x = ML + 2*mm
    col2_x = ML + 65*mm
    for i, (label, val) in enumerate(details):
        if val == "—": continue
        bg = BG_BAND if i%2==0 else BG
        fill(c, bg); c.rect(ML, y-6*mm, MR-ML, 6*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8); fill(c, MUTED)
        c.drawString(col1_x, y-4*mm, label)
        c.setFont("Helvetica", 9); fill(c, TEXT)
        c.drawString(col2_x, y-4*mm, val)
        y -= 6.5*mm

    analyse_ca = v(ca, "analyse")
    if analyse_ca != "—":
        y -= 2*mm
        c.setFont("Helvetica-Oblique", 8); fill(c, MUTED)
        y = wrap_text(c, f"Analyse : {analyse_ca}", ML+2*mm, y, MR-ML-4*mm, font="Helvetica-Oblique", max_lines=3)


# ─── PAGE 2 : ALERTES & FAITS MARQUANTS ──────────────────────────────────────
def page_alertes(c, pn, tp, d):
    restaurant = v(d,"infos","restaurant"); mois = v(d,"infos","mois")
    y = new_page(c, pn, tp, "ALERTES & FAITS MARQUANTS", restaurant, mois)
    y = sec_title(c, y, "02", "Faits Marquants & Alertes", "Mois en bref + signaux à traiter")

    # Faits marquants
    faits = [f for f in d.get("faits_marquants", []) if f.get("fait")]
    if faits:
        y = sub(c, y, "Faits marquants du mois")
        for i, fait in enumerate(faits):
            texte = v(fait,"fait"); impact = v(fait,"impact")
            col = alerte_color(v(fait,"niveau","🟢 Positif"))
            fill(c, BG_BAND); c.rect(ML, y-8*mm, MR-ML, 8*mm, fill=1, stroke=0)
            fill(c, col);     c.rect(ML, y-8*mm, 2*mm, 8*mm, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 8); fill(c, TEXT)
            c.drawString(ML+5*mm, y-3.5*mm, truncate(c, texte, MR-ML-70*mm))
            if impact != "—":
                c.setFont("Helvetica-Bold", 8); fill(c, GOLD)
                c.drawRightString(MR-3*mm, y-3.5*mm, impact)
            c.setFont("Helvetica", 7.5); fill(c, MUTED)
            c.drawString(ML+5*mm, y-7*mm, v(fait,"contexte"))
            y -= 9.5*mm
        y -= 3*mm

    # Alertes
    alertes = [a for a in d.get("alertes", []) if a.get("description")]
    if alertes:
        y = sub(c, y, "Alertes — Action requise")
        for alerte in alertes:
            niveau      = v(alerte,"niveau","🟡 À surveiller")
            description = v(alerte,"description")
            action      = v(alerte,"action")
            responsable = v(alerte,"responsable")
            delai       = v(alerte,"delai")
            col = alerte_color(niveau)

            fill(c, BG_BAND); c.roundRect(ML, y-16*mm, MR-ML, 16*mm, 1.5*mm, fill=1, stroke=0)
            fill(c, col);     c.rect(ML, y-16*mm, 2*mm, 16*mm, fill=1, stroke=0)

            # Niveau badge
            niveau_txt = niveau.split(" ",1)[-1] if " " in niveau else niveau
            c.setFont("Helvetica-Bold", 8); fill(c, col)
            c.drawString(ML+5*mm, y-4*mm, niveau_txt.upper())

            c.setFont("Helvetica-Bold", 8); fill(c, TEXT)
            c.drawString(ML+5*mm, y-8.5*mm, truncate(c, description, MR-ML-10*mm))

            if action != "—":
                c.setFont("Helvetica", 7.5); fill(c, MUTED)
                c.drawString(ML+5*mm, y-12.5*mm, f"→ {truncate(c, action, 80*mm)}")

            if responsable != "—" or delai != "—":
                c.setFont("Helvetica", 7.5); fill(c, GOLD_DIM)
                c.drawRightString(MR-3*mm, y-8.5*mm, f"{responsable} · {delai}")

            y -= 18.5*mm

    # CMV détail
    cmv = d.get("cmv", {})
    y -= 2*mm
    y = sub(c, y, "CMV du mois")
    cmv_details = [
        ("CMV Global",         v(cmv,"cmv_global")),
        ("CMV Food",           v(cmv,"cmv_food")),
        ("CMV Boissons",       v(cmv,"cmv_boissons")),
        ("Vs mois précédent",  v(cmv,"vs_precedent")),
        ("Tendance",           v(cmv,"tendance")),
    ]
    for i,(label,val) in enumerate(cmv_details):
        if val == "—": continue
        bg = BG_BAND if i%2==0 else BG
        fill(c, bg); c.rect(ML, y-6*mm, MR-ML, 6*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8); fill(c, MUTED)
        c.drawString(ML+3*mm, y-4*mm, label)
        c.setFont("Helvetica", 9); fill(c, TEXT)
        c.drawString(ML+65*mm, y-4*mm, val)
        y -= 6.5*mm

    commentaire_cmv = v(cmv,"commentaire")
    if commentaire_cmv != "—":
        y -= 2*mm
        c.setFont("Helvetica-Oblique", 8); fill(c, MUTED)
        y = wrap_text(c, commentaire_cmv, ML+3*mm, y, MR-ML-6*mm, font="Helvetica-Oblique", max_lines=3)


# ─── PAGE 3 : FOCUS DU MOIS ───────────────────────────────────────────────────
def page_focus(c, pn, tp, d):
    restaurant = v(d,"infos","restaurant"); mois = v(d,"infos","mois")
    y = new_page(c, pn, tp, "FOCUS DU MOIS", restaurant, mois)
    y = sec_title(c, y, "03", "Focus du Mois", "1 question business — réponse chiffrée — 2 décisions")

    focus = d.get("focus", {})
    question  = v(focus,"question")
    reponse   = v(focus,"reponse")
    chiffres  = focus.get("chiffres_cles", [])
    decisions = [dec for dec in focus.get("decisions", []) if dec.get("decision")]

    # Bloc question
    fill(c, BG_BAND); c.roundRect(ML, y-16*mm, MR-ML, 16*mm, 2*mm, fill=1, stroke=0)
    stk(c, GOLD); c.setLineWidth(0.5)
    c.roundRect(ML, y-16*mm, MR-ML, 16*mm, 2*mm, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8); fill(c, GOLD_DIM)
    c.drawString(ML+5*mm, y-4*mm, "QUESTION DU MOIS")
    c.setFont("Helvetica-Bold", 10); fill(c, TEXT)
    y_q = y - 8*mm
    y_q = wrap_text(c, question, ML+5*mm, y_q, MR-ML-10*mm, font="Helvetica-Bold", size=10, max_lines=2)
    y -= 19*mm

    y -= 2*mm
    y = sub(c, y, "Réponse chiffrée")

    # Chiffres clés
    if chiffres:
        kw = (MR - ML - (len(chiffres)-1)*3*mm) / max(len(chiffres),1)
        kx = ML
        for item in chiffres[:4]:
            fill(c, BG_BAND); c.roundRect(kx, y-18*mm, kw, 18*mm, 2*mm, fill=1, stroke=0)
            stk(c, GOLD_DIM); c.setLineWidth(0.4)
            c.roundRect(kx, y-18*mm, kw, 18*mm, 2*mm, fill=0, stroke=1)
            label_k = v(item,"label"); val_k = v(item,"valeur")
            c.setFont("Helvetica-Bold", 7); fill(c, MUTED)
            for li, ln in enumerate(label_k.split("\n")[:2]):
                c.drawCentredString(kx+kw/2, y-5*mm-li*4*mm, ln)
            c.setFont("Helvetica-Bold", 13); fill(c, GOLD)
            c.drawCentredString(kx+kw/2, y-15*mm, val_k)
            kx += kw + 3*mm
        y -= 22*mm

    # Analyse textuelle
    if reponse and reponse != "—":
        y -= 2*mm
        fill(c, BG_BAND); c.rect(ML, y-2*mm, MR-ML, 2*mm, fill=1, stroke=0)
        c.setFont("Helvetica", 9); fill(c, TEXT)
        y -= 4*mm
        y = wrap_text(c, reponse, ML+3*mm, y, MR-ML-6*mm, size=9, line_h=5.5*mm, max_lines=5)

    y -= 4*mm
    y = divider(c, y)
    y = sub(c, y, "2 Décisions concrètes")

    dec_colors = [GOLD, GOLD_DIM]
    for i, dec in enumerate(decisions[:2]):
        decision = v(dec,"decision"); impact_d = v(dec,"impact"); resp_d = v(dec,"responsable"); delai_d = v(dec,"delai")
        fill(c, BG_BAND); c.roundRect(ML, y-14*mm, MR-ML, 14*mm, 1.5*mm, fill=1, stroke=0)
        col = dec_colors[i%2]
        fill(c, col); c.circle(ML+6*mm, y-7*mm, 3.5*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9); fill(c, BG)
        c.drawCentredString(ML+6*mm, y-8.5*mm, str(i+1))
        c.setFont("Helvetica-Bold", 9); fill(c, col)
        c.drawString(ML+13*mm, y-4*mm, truncate(c, decision, 100*mm))
        if impact_d != "—":
            c.setFont("Helvetica-Bold", 8); fill(c, GOLD)
            c.drawRightString(MR-3*mm, y-4*mm, impact_d)
        c.setFont("Helvetica", 8); fill(c, MUTED)
        resp_str = f"{resp_d} · {delai_d}" if resp_d != "—" and delai_d != "—" else (resp_d if resp_d != "—" else delai_d)
        c.drawString(ML+13*mm, y-9*mm, resp_str if resp_str != "—" else "")
        y -= 17*mm


# ─── PAGE 4 : RECOMMANDATIONS ─────────────────────────────────────────────────
def page_recommandations(c, pn, tp, d):
    restaurant = v(d,"infos","restaurant"); mois = v(d,"infos","mois")
    y = new_page(c, pn, tp, "RECOMMANDATIONS", restaurant, mois)
    y = sec_title(c, y, "04", "Recommandations", "2–3 actions prioritaires avec impact chiffré")

    recos = [r for r in d.get("recommandations", []) if r.get("description")]
    reco_colors = [GOLD, GOLD_DIM, MUTED]

    for i, reco in enumerate(recos[:3]):
        description = v(reco,"description"); impact = v(reco,"impact")
        responsable = v(reco,"responsable"); delai = v(reco,"delai"); priorite = v(reco,"priorite")
        col = reco_colors[i%3]
        col_p = alerte_color(priorite)

        # Bloc reco
        fill(c, BG_BAND); c.roundRect(ML, y-32*mm, MR-ML, 32*mm, 2*mm, fill=1, stroke=0)
        fill(c, col);     c.rect(ML, y-32*mm, 3*mm, 32*mm, fill=1, stroke=0)

        # Numéro
        c.setFont("Helvetica-Bold", 11); fill(c, col)
        c.drawString(ML+6*mm, y-6*mm, f"RECOMMANDATION {i+1}")

        # Priorité badge
        if priorite != "—":
            prio_txt = priorite.split(" ",1)[-1] if " " in priorite else priorite
            c.setFont("Helvetica-Bold", 7); fill(c, col_p)
            c.drawRightString(MR-3*mm, y-6*mm, f"● {prio_txt.upper()}")

        c.setFont("Helvetica", 9); fill(c, TEXT)
        y2 = y - 10*mm
        y2 = wrap_text(c, description, ML+6*mm, y2, MR-ML-12*mm, size=9, line_h=5*mm, max_lines=3)

        # Impact
        if impact != "—":
            fill(c, BG_BAND)
            c.setFont("Helvetica-Bold", 8); fill(c, GOLD)
            c.drawString(ML+6*mm, y-24*mm, "Impact attendu :")
            c.setFont("Helvetica-Bold", 10); fill(c, GOLD)
            c.drawString(ML+36*mm, y-24*mm, impact)

        # Responsable / délai
        c.setFont("Helvetica", 8); fill(c, MUTED)
        resp_str = []
        if responsable != "—": resp_str.append(f"Responsable : {responsable}")
        if delai != "—":       resp_str.append(f"Délai : {delai}")
        c.drawString(ML+6*mm, y-29*mm, "  ·  ".join(resp_str) if resp_str else "")

        y -= 36*mm

    # Seuil de rentabilité & marge de sécurité
    seuil = d.get("seuil", {})
    if any(v(seuil, k) != "—" for k in ["ca_mois","seuil_mois","marge_securite"]):
        y = divider(c, y)
        y = sub(c, y, "Seuil de Rentabilité du Mois")
        col_ms = RED if "rouge" in str(v(seuil,"statut_ms","")).lower() or "🔴" in str(v(seuil,"statut_ms","")) else GOLD

        details_s = [
            ("CA du mois",                  v(seuil,"ca_mois")),
            ("Seuil de rentabilité (mois)",  v(seuil,"seuil_mois")),
            ("Marge de sécurité",            v(seuil,"marge_securite")),
            ("Charges fixes (changement ?)", v(seuil,"changement_cf")),
        ]
        for i,(label,val) in enumerate(details_s):
            if val == "—": continue
            bg = BG_BAND if i%2==0 else BG
            fill(c, bg); c.rect(ML, y-6*mm, MR-ML, 6*mm, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 8); fill(c, MUTED)
            c.drawString(ML+3*mm, y-4*mm, label)
            c.setFont("Helvetica", 9)
            fill(c, col_ms if "marge" in label.lower() else TEXT)
            c.drawString(ML+75*mm, y-4*mm, val)
            y -= 6.5*mm


# ─── PAGE 5 (OPTIONNELLE) : MENU ENGINEERING ─────────────────────────────────
def page_menu_engineering(c, pn, tp, d):
    restaurant = v(d,"infos","restaurant"); mois = v(d,"infos","mois")
    y = new_page(c, pn, tp, "MENU ENGINEERING — SUIVI", restaurant, mois)
    y = sec_title(c, y, "05", "Suivi Menu Engineering", "Variations de popularité & changements de quadrant")

    me = d.get("menu_engineering", {})
    carte_changee = v(me,"carte_changee","Non")

    fill(c, BG_BAND); c.roundRect(ML, y-10*mm, MR-ML, 10*mm, 1.5*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9); fill(c, GOLD)
    c.drawString(ML+5*mm, y-4*mm, "CARTE MODIFIÉE CE MOIS :")
    col_carte = GOLD if carte_changee.lower() in ("oui","yes") else MUTED
    c.setFont("Helvetica-Bold", 9); fill(c, col_carte)
    c.drawString(ML+65*mm, y-4*mm, carte_changee.upper())
    y -= 13*mm

    # Variations de popularité
    variations = [v2 for v2 in me.get("variations", []) if v2.get("plat")]
    if variations:
        y = sub(c, y, "Variations de popularité ≥ ±30% vs mois précédent")
        headers = ["PLAT","CATÉG.","POP. MOIS PRÉC.","POP. CE MOIS","VARIATION","CHANGEMENT QUADRANT"]
        col_widths = [42*mm,20*mm,22*mm,22*mm,18*mm,49*mm]
        total_w = sum(col_widths); x0 = ML

        fill(c, GOLD_DIM); c.rect(x0, y-7*mm, total_w, 7*mm, fill=1, stroke=0)
        cx = x0
        for i,h in enumerate(headers):
            c.setFont("Helvetica-Bold",7); fill(c,BG)
            c.drawString(cx+2*mm, y-4.5*mm, h); cx += col_widths[i]
        y -= 7*mm

        for ri, var in enumerate(variations):
            fill(c, BG_BAND if ri%2==0 else BG)
            c.rect(x0, y-7*mm, total_w, 7*mm, fill=1, stroke=0)
            stk(c, GOLD_DIM); c.setLineWidth(0.2)
            c.line(x0, y-7*mm, x0+total_w, y-7*mm)
            row = [v(var,"plat"),v(var,"categorie"),v(var,"pop_precedent"),v(var,"pop_mois"),v(var,"variation"),v(var,"changement_quadrant")]
            cx = x0
            for ci, cell in enumerate(row):
                c.setFont("Helvetica",7.5); fill(c,TEXT)
                c.drawString(cx+2*mm, y-4.5*mm, truncate(c,cell,col_widths[ci]-4*mm))
                cx += col_widths[ci]
            y -= 7*mm
        stk(c,GOLD); c.setLineWidth(0.5)
        c.rect(x0, y, total_w, 7*mm*(len(variations)+1), fill=0, stroke=1)
        y -= 5*mm

    # Nouveaux plats
    nouveaux = [np for np in me.get("nouveaux_plats", []) if np.get("nom")]
    if nouveaux:
        y = sub(c, y, "Nouveaux plats — données 1er mois (pas encore représentatives)")
        for np_item in nouveaux:
            fill(c, BG_BAND); c.roundRect(ML, y-10*mm, MR-ML, 10*mm, 1.5*mm, fill=1, stroke=0)
            fill(c, GOLD_DIM); c.rect(ML, y-10*mm, 2*mm, 10*mm, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 8); fill(c, TEXT)
            c.drawString(ML+5*mm, y-4.5*mm, v(np_item,"nom"))
            c.setFont("Helvetica", 7.5); fill(c, MUTED)
            c.drawString(ML+5*mm, y-8.5*mm, f"Prix : {v(np_item,'prix')} · Marge : {v(np_item,'marge')} · Observations : {v(np_item,'observations')}")
            y -= 12*mm

    # Observations générales
    obs = v(me, "observations")
    if obs != "—":
        y -= 2*mm
        c.setFont("Helvetica-Oblique", 8); fill(c, MUTED)
        y = wrap_text(c, obs, ML+3*mm, y, MR-ML-6*mm, font="Helvetica-Oblique", max_lines=4)


# ─── ENTRÉE PRINCIPALE ────────────────────────────────────────────────────────
def generate_pdf_suivi(data: dict) -> bytes:
    buffer   = io.BytesIO()
    restaurant = v(data,"infos","restaurant", default="Suivi Mensuel")
    mois       = v(data,"infos","mois", default="")

    me = data.get("menu_engineering", {})
    has_me = bool(me.get("variations") or me.get("nouveaux_plats") or me.get("observations"))
    TOTAL = 6 if has_me else 5

    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Rapport Suivi Mensuel — {restaurant} — {mois}")
    c.setAuthor("La Carte")

    # P1 : Couverture
    fill(c, BG); c.rect(0,0,W,H,fill=1,stroke=0)
    page_cover(c, data)

    # P2 : Tableau de bord
    page_tableau_bord(c, 2, TOTAL, data)

    # P3 : Alertes & faits marquants
    page_alertes(c, 3, TOTAL, data)

    # P4 : Focus du mois
    page_focus(c, 4, TOTAL, data)

    # P5 : Recommandations
    page_recommandations(c, 5, TOTAL, data)

    # P6 (optionnelle) : Menu Engineering
    if has_me:
        page_menu_engineering(c, 6, TOTAL, data)

    c.save(); buffer.seek(0)
    return buffer.read()


if __name__ == "__main__":
    sample = {
        "infos": {"restaurant":"Le Bistrot du Port","mois":"Avril 2025","auditeur":"Anthony Grimault"},
        "kpis": [
            {"indicateur":"CA du mois","valeur":"21 400 €","vs_precedent":"+4,2 %","vs_objectif":"✓ +200 €","statut":"🟢 Positif"},
            {"indicateur":"Ticket moyen","valeur":"29,20 €","vs_precedent":"+2,5 %","vs_objectif":"✓ Objectif atteint","statut":"🟢 Positif"},
            {"indicateur":"CMV Global","valeur":"33 %","vs_precedent":"+2 pts","vs_objectif":"⚠ +3 pts vs cible","statut":"🔴 Urgent"},
            {"indicateur":"Marge de sécurité","valeur":"17 %","vs_precedent":"+3 pts","vs_objectif":"🟡 Correct","statut":"🟡 À surveiller"},
            {"indicateur":"Nb de couverts","valeur":"733","vs_precedent":"+1,5 %","vs_objectif":"✓ Dans la cible","statut":"🟢 Positif"},
        ],
        "ca_ticket": {
            "ca_mois":"21 400 €","couverts":"733","ticket_global":"29,20 €",
            "ticket_midi":"23,50 €","ticket_soir":"35,80 €",
            "vs_precedent":"+4,2 % vs mars 2025","vs_n_moins_1":"+6,8 % vs avril 2024",
            "analyse":"Hausse portée par une meilleure pénétration des desserts (+0,80€/couvert vs mars).",
        },
        "cmv": {
            "cmv_global":"33 %","cmv_food":"35 %","cmv_boissons":"22 %",
            "vs_precedent":"+2 pts vs mars 2025",
            "tendance":"Hausse 2e mois consécutif — investigation requise",
            "commentaire":"Hypothèse principale : introduction de l'agneau pascal à coût matière élevé (CMV ~48%). Vérifier avec le chef si recette a été reformulée depuis.",
        },
        "faits_marquants": [
            {"fait":"Hausse du ticket moyen midi grâce à la formule déjeuner revisitée","impact":"+1,20€/couvert","niveau":"🟢 Positif","contexte":"Mise en place semaine 2"},
            {"fait":"CMV Food dépasse 35% pour le 2e mois consécutif","impact":"−700 €/mois","niveau":"🔴 Urgent","contexte":"Lié à l'agneau pascal — à confirmer"},
            {"fait":"Popularité entrecôte Bordelaise en hausse de +32%","impact":"+ commandes","niveau":"🟢 Positif","contexte":"Suite repositionnement en tête de carte"},
        ],
        "alertes": [
            {"niveau":"🔴 Urgent","description":"CMV Food > 35% — 2e mois consécutif","action":"Vérifier coût agneau pascal + reformuler ou retirer","responsable":"Chef + Patron","delai":"Semaine prochaine"},
            {"niveau":"🟡 À surveiller","description":"Marge de sécurité à 17% — en dessous de l'objectif 20%","action":"Surveiller les charges variables ce mois-ci","responsable":"Patron","delai":"Fin de mois"},
        ],
        "focus": {
            "question":"La formule déjeuner à 19,90€ améliore-t-elle réellement la rentabilité midi ?",
            "reponse":"Sur 412 couverts midi, 38% ont pris la formule (156 couverts). Le ticket moyen formule est 19,90€ vs 22,30€ en à la carte. La perte de ticket est compensée par une vitesse de rotation +18% (durée repas −12 min). Net : gain estimé de +340€ sur le mois.",
            "chiffres_cles": [
                {"label":"Couverts formule","valeur":"156"},
                {"label":"Ticket moyen formule","valeur":"19,90 €"},
                {"label":"Ticket moyen carte","valeur":"22,30 €"},
                {"label":"Gain net estimé","valeur":"+340 €"},
            ],
            "decisions": [
                {"decision":"Maintenir la formule déjeuner — rentabilité validée","impact":"+340 €/mois","responsable":"Patron","delai":"Immédiat"},
                {"decision":"Tester une formule soir 2j/semaine (mer-jeu) à 28€","impact":"À mesurer","responsable":"Patron + Chef","delai":"Mois prochain"},
            ],
        },
        "recommandations": [
            {"description":"Reformuler ou remplacer l'agneau pascal par un plat printanier à CMV ≤ 30%. Calculer le nouveau coût avec le chef avant mise en carte.","impact":"−2 pts CMV food","responsable":"Chef","delai":"2 semaines","priorite":"🔴 Urgent"},
            {"description":"Négocier le prix des viandes avec Metro — volumes Q1 suffisants pour une remise de 4–6%.","impact":"−500 €/an","responsable":"Patron","delai":"Ce mois","priorite":"🟡 À faire"},
            {"description":"Repositionner la crème brûlée en dessert recommandé par la salle — taux de pénétration desserts à 28%, objectif 35%.","impact":"+0,60 €/couvert","responsable":"Responsable salle","delai":"Immédiat","priorite":"🟡 À faire"},
        ],
        "seuil": {
            "ca_mois":"21 400 €","seuil_mois":"18 200 €","marge_securite":"17 %",
            "changement_cf":"Non","statut_ms":"🟡 À surveiller",
        },
        "menu_engineering": {
            "carte_changee":"Non",
            "variations": [
                {"plat":"Entrecôte Bordelaise","categorie":"Plats","pop_precedent":"14 %","pop_mois":"18,5 %","variation":"+32 %","changement_quadrant":"✓ Star confirmé"},
                {"plat":"Filet de bar","categorie":"Plats","pop_precedent":"8 %","pop_mois":"4 %","variation":"−50 %","changement_quadrant":"❗ Star → Énigme"},
            ],
            "nouveaux_plats": [],
            "observations":"Le filet de bar perd en popularité — possiblement lié à la concurrence de l'agneau pascal ce mois-ci. À surveiller mois prochain avant décision de retrait.",
        },
    }
    pdf = generate_pdf_suivi(sample)
    with open("/mnt/user-data/outputs/rapport_suivi_mensuel_test.pdf","wb") as f:
        f.write(pdf)
    print(f"✅ Suivi mensuel : {len(pdf)} bytes")
