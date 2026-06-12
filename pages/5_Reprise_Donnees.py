"""
Reprise de données — Import Silae
Génère les fichiers d'import pour les prémontages mensuels et l'initialisation des congés payés
lors de la reprise d'un dossier client.
"""

import streamlit as st
import anthropic
import xlwt
import io
import json
import base64
import re
from datetime import datetime, date
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_config

# ── CSS Raly Conseils ──────────────────────────────────────────────────────────
st.markdown("""
<style>
:root { --vert: #789F90; --gris: #3F4443; --orange: #F67728; }
.stApp { background-color: #F8F9F8; }
[data-testid="stSidebar"] { background-color: #3F4443 !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] input { color: #3F4443 !important; }
h1 { color: #3F4443 !important; border-bottom: 3px solid #789F90; padding-bottom: 10px; }
h2, h3 { color: #3F4443 !important; }
.stButton > button[kind="primary"] {
    background-color: #789F90 !important; border: none !important;
    color: white !important; font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover { background-color: #5d8577 !important; }
.stDownloadButton > button {
    background-color: #F67728 !important; border: none !important;
    color: white !important; font-weight: 600 !important;
}
[data-testid="stExpander"] summary {
    background-color: #789F90 !important; color: white !important;
    border-radius: 6px; font-weight: 600;
}
hr { border-color: #789F90 !important; }
[data-testid="stAlert"] { border-left: 4px solid #789F90; }
</style>
""", unsafe_allow_html=True)

_config = load_config()
api_key = _config.get("api_key", "")

# ── En-tête ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:16px; margin-bottom:8px;">
    <div style="background:#789F90; width:6px; height:48px; border-radius:3px;"></div>
    <div>
        <div style="font-size:1.8rem; font-weight:700; color:#3F4443; line-height:1.1;">Reprise de données client</div>
        <div style="font-size:1rem; color:#789F90; font-weight:500;">Silae · Prémontages & Congés payés</div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📅 Prémontages mensuels", "🏖️ Initialisation congés payés"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRÉMONTAGES MENSUELS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(
        "Extrait depuis les **bulletins de salaire PDF** les données mensuelles par salarié "
        "(brut, charges patronales, total versé, heures/jours travaillés) "
        "pour initialiser les prémontages dans Silae."
    )

    # ── Prompt d'extraction prémontages ───────────────────────────────────────
    PROMPT_PREMONTAGES = """Tu es un expert en paie qui extrait des données depuis des bulletins de salaire.

Analyse les bulletins de salaire fournis et extrait pour CHAQUE salarié ET CHAQUE mois :

DONNÉES À EXTRAIRE PAR SALARIÉ PAR MOIS :
- matricule : le matricule du salarié (respecte exactement les zéros en tête, ex: "0042")
- nom_prenom : Nom et prénom du salarié (NOM Prénom)
- periode : période du bulletin au format MM/AAAA (ex: "03/2025")
- brut : salaire brut total du bulletin (en euros, nombre décimal, ex: 2850.00)
- charges_patronales : total des charges patronales / cotisations employeur (en euros)
- total_verse : total versé = brut + charges patronales (si non indiqué, calcule-le)
- heures_normales : heures normales travaillées (nombre décimal, ex: 151.67)
- heures_majorees : heures majorées ou supplémentaires (0 si aucune)
- jours_travailles : nombre de jours travaillés dans le mois (entier ou décimal)

RÈGLES :
- Si le matricule n'est pas visible, laisse une chaîne vide ""
- "Charges patronales" = total cotisations à la charge de l'employeur (souvent libellé "Total charges patronales", "Cotisations patronales", "Part employeur")
- "Total versé" = Brut + Charges patronales (= coût total employeur)
- Si plusieurs bulletins dans un seul PDF, extrait TOUS les salariés
- Format périodes toujours MM/AAAA
- Ne jamais inventer de données absentes

Réponds UNIQUEMENT avec un tableau JSON valide :
[
  {"matricule": "...", "nom_prenom": "...", "periode": "MM/AAAA", "brut": 0.00, "charges_patronales": 0.00, "total_verse": 0.00, "heures_normales": 0.00, "heures_majorees": 0.00, "jours_travailles": 0},
  ...
]
"""

    def extract_premontages(files_data: list, api_key: str) -> list:
        client = anthropic.Anthropic(api_key=api_key)
        content = []
        for f in files_data:
            if f["media_type"].startswith("image/"):
                content.append({"type": "image", "source": {"type": "base64", "media_type": f["media_type"], "data": f["data"]}})
            elif f["media_type"] == "application/pdf":
                content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": f["data"]}})
        content.append({"type": "text", "text": PROMPT_PREMONTAGES})
        has_pdfs = any(f["media_type"] == "application/pdf" for f in files_data)
        if has_pdfs:
            resp = client.beta.messages.create(
                model="claude-fable-5", max_tokens=4000,
                messages=[{"role": "user", "content": content}],
                betas=["pdfs-2024-09-25"],
            )
        else:
            resp = client.messages.create(
                model="claude-fable-5", max_tokens=4000,
                messages=[{"role": "user", "content": content}],
            )
        raw = resp.content[0].text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)

    def generate_premontages_xls(rows: list) -> bytes:
        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("Données")
        hdr = xlwt.easyxf("font: bold true, colour white; pattern: pattern solid, fore_colour dark_red; alignment: horizontal centre;")
        val = xlwt.easyxf("alignment: horizontal left;")
        num = xlwt.easyxf("alignment: horizontal right;", num_format_str="0.00")

        # Colonnes Silae exactes pour prémontages
        COLS = [
            ("Matricule", "matricule", False),
            ("Période (bulletins fictifs)", "periode", False),
            ("Brut (bulletins fictifs)", "brut", True),
            ("Heures normales travaillées", "heures_normales", True),
            ("Heures majorées travaillées", "heures_majorees", True),
            ("Jours travaillés", "jours_travailles", True),
            ("Cumul Ch. patronales (bulletins fictifs)", "charges_patronales", True),
            ("Total versé (bulletins fictifs)", "total_verse", True),
        ]
        for ci, (header, _, _) in enumerate(COLS):
            ws.write(0, ci, header, hdr)
        for ri, row in enumerate(rows, start=1):
            for ci, (_, key, is_num) in enumerate(COLS):
                v = row.get(key, "")
                if is_num and v != "":
                    try:
                        ws.write(ri, ci, float(v), num)
                    except (ValueError, TypeError):
                        ws.write(ri, ci, str(v), val)
                else:
                    ws.write(ri, ci, str(v) if v is not None else "", val)
        for ci, (h, _, _) in enumerate(COLS):
            ws.col(ci).width = max(len(h) * 300 + 500, 3000)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # ── Interface prémontages ──────────────────────────────────────────────────
    st.subheader("1️⃣  Charger les bulletins de salaire")
    uploaded_bulletins = st.file_uploader(
        "Bulletins de salaire (PDF ou images)",
        accept_multiple_files=True,
        type=["pdf", "jpg", "jpeg", "png"],
        key="bulletins_up",
        help="Un ou plusieurs PDF. Si plusieurs salariés ou plusieurs mois, vous pouvez tout mettre en une fois.",
    )
    if uploaded_bulletins:
        st.caption(f"📎 {len(uploaded_bulletins)} fichier(s) chargé(s)")

    btn_extract_prem = st.button("🔍  Extraire les données avec Claude AI", type="primary", key="btn_prem", use_container_width=True)

    if "prem_data" not in st.session_state:
        st.session_state.prem_data = []

    if btn_extract_prem:
        if not api_key:
            st.error("Clé API manquante. Allez dans ⚙️ Paramètres.")
        elif not uploaded_bulletins:
            st.error("Veuillez charger au moins un bulletin.")
        else:
            with st.spinner("Analyse des bulletins en cours…"):
                try:
                    files_data = []
                    for f in uploaded_bulletins:
                        raw = f.read()
                        files_data.append({"media_type": f.type or "application/pdf", "data": base64.standard_b64encode(raw).decode("utf-8")})
                    extracted = extract_premontages(files_data, api_key)
                    if not isinstance(extracted, list):
                        raise ValueError("Réponse inattendue, réessayez.")
                    st.session_state.prem_data = extracted
                    st.success(f"✅ {len(extracted)} ligne(s) extraite(s).")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # ── Tableau éditable ───────────────────────────────────────────────────────
    if st.session_state.prem_data:
        st.divider()
        st.subheader("2️⃣  Vérifier et corriger les données")
        st.info("Corrigez les valeurs si besoin (double-clic pour éditer une cellule).")

        import pandas as pd
        df = pd.DataFrame(st.session_state.prem_data, columns=[
            "matricule", "nom_prenom", "periode", "brut",
            "charges_patronales", "total_verse",
            "heures_normales", "heures_majorees", "jours_travailles"
        ])
        df.columns = ["Matricule", "Nom Prénom", "Période (MM/AAAA)", "Brut (€)",
                      "Charges patronales (€)", "Total versé (€)",
                      "Heures normales", "Heures majorées", "Jours travaillés"]

        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="prem_editor")

        # ── Génération XLS ─────────────────────────────────────────────────────
        st.divider()
        st.subheader("3️⃣  Générer le fichier d'import Silae")

        col_btn, col_tip = st.columns([1, 2])
        with col_btn:
            if st.button("💾  Générer le fichier XLS", type="primary", key="gen_prem", use_container_width=True):
                rows_out = []
                for _, row in edited_df.iterrows():
                    rows_out.append({
                        "matricule": str(row["Matricule"]),
                        "periode": str(row["Période (MM/AAAA)"]),
                        "brut": row["Brut (€)"],
                        "charges_patronales": row["Charges patronales (€)"],
                        "total_verse": row["Total versé (€)"],
                        "heures_normales": row["Heures normales"],
                        "heures_majorees": row["Heures majorées"],
                        "jours_travailles": row["Jours travaillés"],
                    })
                xls_bytes = generate_premontages_xls(rows_out)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "📥  Télécharger le fichier XLS prémontages",
                    data=xls_bytes,
                    file_name=f"premontages_silae_{ts}.xls",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                )
        with col_tip:
            st.info(
                "**Import dans Silae :**\n\n"
                "Menu **Outils › Gestion des cumuls › Import Excel bulletins fictifs**\n\n"
                "1. Ouvrir le fichier `.xls`\n"
                "2. Contrôler puis Importer\n\n"
                "⚠️ Le matricule doit correspondre exactement (zéros en tête inclus)."
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — INITIALISATION CONGÉS PAYÉS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(
        "Extrait depuis les **bulletins ou provisions de congés payés PDF** les compteurs CP "
        "et RTT/repos pour initialiser les soldes dans Silae lors d'une reprise."
    )

    # ── Configuration des périodes CP ─────────────────────────────────────────
    st.subheader("1️⃣  Définir les périodes de congés")
    col_per1, col_per2 = st.columns(2)
    current_year = datetime.now().year
    # La période CP va de juin N à mai N+1
    # N-1 = période close, N = période en cours
    annee_n1_debut = current_year - 2 if datetime.now().month < 6 else current_year - 1
    annee_n_debut  = current_year - 1 if datetime.now().month < 6 else current_year

    with col_per1:
        n1_debut = st.number_input("Année début période N-1", value=annee_n1_debut, min_value=2015, max_value=2030, key="n1d")
        st.caption(f"Période N-1 : 06/{n1_debut} → 05/{n1_debut+1}")
    with col_per2:
        n_debut = st.number_input("Année début période N (en cours)", value=annee_n_debut, min_value=2015, max_value=2030, key="nd")
        st.caption(f"Période N : 06/{n_debut} → 05/{n_debut+1}")

    periode_n1 = f"06/{n1_debut} - 05/{n1_debut+1}"
    periode_n  = f"06/{n_debut} - 05/{n_debut+1}"

    # ── Prompt extraction CP ──────────────────────────────────────────────────
    PROMPT_CP = f"""Tu es un expert en paie qui extrait les compteurs de congés payés depuis des bulletins de salaire ou des états de provision congés payés.

PÉRIODES DE RÉFÉRENCE :
- Période N-1 (close) : {periode_n1}
- Période N (en cours) : {periode_n}

Pour CHAQUE salarié, extrait :

CONGÉS PAYÉS :
- matricule : matricule (respecte les zéros en tête)
- nom_prenom : NOM Prénom
- cp_n1_acquis : jours CP acquis sur la période N-1
- cp_n1_pris : jours CP pris sur la période N-1
- cp_n1_provision_acquise : provision (montant €) acquise sur N-1
- cp_n1_provision_consommee : provision (montant €) consommée sur N-1
- cp_n1_solde_jours : solde de jours CP restants N-1
- cp_n_acquis : jours CP acquis sur la période N (depuis juin {n_debut})
- cp_n_pris : jours CP pris sur la période N
- cp_n_provision_acquise : provision (montant €) acquise sur N
- cp_n_provision_consommee : provision (montant €) consommée sur N
- cp_n_solde_jours : solde de jours CP restants N

AUTRES COMPTEURS (si présents dans le document) :
- rtt_acquis : jours RTT acquis (0 si non applicable)
- rtt_pris : jours RTT pris
- rtt_solde : solde RTT restant
- repos_acquis : jours de repos compensateur acquis (0 si non applicable)
- repos_pris : jours repos pris
- repos_solde : solde repos restant
- recup_acquis : jours de récupération acquis (0 si non applicable)
- recup_pris : jours récup pris
- recup_solde : solde récup restant

RÈGLES :
- Mets 0 pour tout compteur absent du document
- Si document de provision CP : les montants de provision y sont explicitement indiqués
- Si simple bulletin : la provision peut ne pas y figurer (mettre 0)
- N'invente jamais de valeurs

Réponds UNIQUEMENT avec un tableau JSON :
[
  {{"matricule": "...", "nom_prenom": "...",
    "cp_n1_acquis": 0, "cp_n1_pris": 0, "cp_n1_provision_acquise": 0.0, "cp_n1_provision_consommee": 0.0, "cp_n1_solde_jours": 0,
    "cp_n_acquis": 0, "cp_n_pris": 0, "cp_n_provision_acquise": 0.0, "cp_n_provision_consommee": 0.0, "cp_n_solde_jours": 0,
    "rtt_acquis": 0, "rtt_pris": 0, "rtt_solde": 0,
    "repos_acquis": 0, "repos_pris": 0, "repos_solde": 0,
    "recup_acquis": 0, "recup_pris": 0, "recup_solde": 0}},
  ...
]
"""

    def extract_cp(files_data: list, api_key: str, prompt: str) -> list:
        client = anthropic.Anthropic(api_key=api_key)
        content = []
        for f in files_data:
            if f["media_type"].startswith("image/"):
                content.append({"type": "image", "source": {"type": "base64", "media_type": f["media_type"], "data": f["data"]}})
            elif f["media_type"] == "application/pdf":
                content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": f["data"]}})
        content.append({"type": "text", "text": prompt})
        has_pdfs = any(f["media_type"] == "application/pdf" for f in files_data)
        if has_pdfs:
            resp = client.beta.messages.create(
                model="claude-fable-5", max_tokens=4000,
                messages=[{"role": "user", "content": content}],
                betas=["pdfs-2024-09-25"],
            )
        else:
            resp = client.messages.create(
                model="claude-fable-5", max_tokens=4000,
                messages=[{"role": "user", "content": content}],
            )
        raw = resp.content[0].text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)

    def generate_cp_xls(rows: list, periode_n1: str, periode_n: str) -> bytes:
        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("Données CP")
        hdr  = xlwt.easyxf("font: bold true, colour white; pattern: pattern solid, fore_colour dark_red; alignment: horizontal centre, wrap true;")
        val  = xlwt.easyxf("alignment: horizontal left;")
        num  = xlwt.easyxf("alignment: horizontal right;", num_format_str="0.00")
        numi = xlwt.easyxf("alignment: horizontal right;", num_format_str="0")

        # Colonnes correspondant au format initialisation des congés payés.xml
        COLS = [
            (f"Matricule",                               "matricule",               False, False),
            (f"Salarié",                                 "nom_prenom",              False, False),
            (f"Jours acquis\n{periode_n1}",              "cp_n1_acquis",            True,  True),
            (f"Jours pris\n{periode_n1}",                "cp_n1_pris",              True,  True),
            (f"Provision acquise\n{periode_n1}",         "cp_n1_provision_acquise", True,  False),
            (f"Provision consommée\n{periode_n1}",       "cp_n1_provision_consommee","True",False),
            (f"Solde jours\n{periode_n1}",               "cp_n1_solde_jours",       True,  True),
            (f"Jours acquis\n{periode_n}",               "cp_n_acquis",             True,  True),
            (f"Jours pris\n{periode_n}",                 "cp_n_pris",               True,  True),
            (f"Provision acquise\n{periode_n}",          "cp_n_provision_acquise",  True,  False),
            (f"Provision consommée\n{periode_n}",        "cp_n_provision_consommee",True,  False),
            (f"Solde jours\n{periode_n}",                "cp_n_solde_jours",        True,  True),
            ("RTT acquis",     "rtt_acquis",   True, True),
            ("RTT pris",       "rtt_pris",     True, True),
            ("RTT solde",      "rtt_solde",    True, True),
            ("Repos acquis",   "repos_acquis", True, True),
            ("Repos pris",     "repos_pris",   True, True),
            ("Repos solde",    "repos_solde",  True, True),
            ("Récup acquis",   "recup_acquis", True, True),
            ("Récup pris",     "recup_pris",   True, True),
            ("Récup solde",    "recup_solde",  True, True),
        ]
        ws.row(0).height_mismatch = True
        ws.row(0).height = 1000
        for ci, (header, _, is_num, is_int) in enumerate(COLS):
            ws.write(0, ci, header, hdr)
        for ri, row in enumerate(rows, start=1):
            for ci, (_, key, is_num, is_int) in enumerate(COLS):
                v = row.get(key, "")
                if is_num and v != "":
                    try:
                        fv = float(v)
                        ws.write(ri, ci, int(fv) if is_int else fv, numi if is_int else num)
                    except (ValueError, TypeError):
                        ws.write(ri, ci, str(v), val)
                else:
                    ws.write(ri, ci, str(v) if v is not None else "", val)
        for ci, (h, _, _, _) in enumerate(COLS):
            ws.col(ci).width = max(len(h.split("\n")[0]) * 280 + 400, 2800)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # ── Interface CP ───────────────────────────────────────────────────────────
    st.subheader("2️⃣  Charger les documents")
    uploaded_cp = st.file_uploader(
        "Bulletins de salaire ou états de provision congés payés (PDF ou images)",
        accept_multiple_files=True,
        type=["pdf", "jpg", "jpeg", "png"],
        key="cp_up",
        help="Bulletins du dernier mois de chaque période, ou état de provision CP annuel.",
    )
    if uploaded_cp:
        st.caption(f"📎 {len(uploaded_cp)} fichier(s) chargé(s)")

    btn_extract_cp = st.button("🔍  Extraire les compteurs CP avec Claude AI", type="primary", key="btn_cp", use_container_width=True)

    if "cp_data" not in st.session_state:
        st.session_state.cp_data = []

    if btn_extract_cp:
        if not api_key:
            st.error("Clé API manquante. Allez dans ⚙️ Paramètres.")
        elif not uploaded_cp:
            st.error("Veuillez charger au moins un document.")
        else:
            with st.spinner("Analyse des documents CP en cours…"):
                try:
                    files_data = []
                    for f in uploaded_cp:
                        raw = f.read()
                        files_data.append({"media_type": f.type or "application/pdf", "data": base64.standard_b64encode(raw).decode("utf-8")})
                    extracted = extract_cp(files_data, api_key, PROMPT_CP)
                    if not isinstance(extracted, list):
                        raise ValueError("Réponse inattendue, réessayez.")
                    st.session_state.cp_data = extracted
                    st.success(f"✅ {len(extracted)} salarié(s) extrait(s).")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # ── Tableau éditable CP ────────────────────────────────────────────────────
    if st.session_state.cp_data:
        st.divider()
        st.subheader("3️⃣  Vérifier et corriger les compteurs")

        import pandas as pd
        cp_cols_map = {
            "matricule":               "Matricule",
            "nom_prenom":              "Salarié",
            "cp_n1_acquis":            f"CP acquis N-1",
            "cp_n1_pris":              f"CP pris N-1",
            "cp_n1_provision_acquise": f"Prov. acquise N-1 (€)",
            "cp_n1_provision_consommee":f"Prov. conso. N-1 (€)",
            "cp_n1_solde_jours":       f"Solde jours N-1",
            "cp_n_acquis":             f"CP acquis N",
            "cp_n_pris":               f"CP pris N",
            "cp_n_provision_acquise":  f"Prov. acquise N (€)",
            "cp_n_provision_consommee":f"Prov. conso. N (€)",
            "cp_n_solde_jours":        f"Solde jours N",
            "rtt_acquis": "RTT acquis", "rtt_pris": "RTT pris", "rtt_solde": "RTT solde",
            "repos_acquis": "Repos acquis", "repos_pris": "Repos pris", "repos_solde": "Repos solde",
            "recup_acquis": "Récup acquis", "recup_pris": "Récup pris", "recup_solde": "Récup solde",
        }
        df_cp = pd.DataFrame(st.session_state.cp_data)
        for col in cp_cols_map:
            if col not in df_cp.columns:
                df_cp[col] = 0
        df_cp = df_cp[list(cp_cols_map.keys())]
        df_cp.columns = list(cp_cols_map.values())

        edited_cp = st.data_editor(df_cp, use_container_width=True, num_rows="dynamic", key="cp_editor")

        # ── Génération XLS CP ──────────────────────────────────────────────────
        st.divider()
        st.subheader("4️⃣  Générer le fichier d'import Silae")
        col_btn2, col_tip2 = st.columns([1, 2])
        with col_btn2:
            if st.button("💾  Générer le fichier XLS congés payés", type="primary", key="gen_cp", use_container_width=True):
                # Reconstituer les clés internes
                inv_map = {v: k for k, v in cp_cols_map.items()}
                rows_out = []
                for _, row in edited_cp.iterrows():
                    r = {}
                    for display_col, internal_key in inv_map.items():
                        r[internal_key] = row.get(display_col, 0)
                    rows_out.append(r)
                xls_bytes = generate_cp_xls(rows_out, periode_n1, periode_n)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "📥  Télécharger le fichier XLS congés payés",
                    data=xls_bytes,
                    file_name=f"initialisation_CP_silae_{ts}.xls",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                )
        with col_tip2:
            st.info(
                "**Import dans Silae :**\n\n"
                "Menu **Outils › Initialisation des compteurs CP (montage)**\n\n"
                "1. Ouvrir le fichier `.xls`\n"
                "2. Sélectionner la période concernée\n"
                "3. Contrôler puis Importer\n\n"
                "⚠️ Le matricule doit correspondre exactement à Silae (zéros en tête inclus)."
            )

# ── Pied de page ───────────────────────────────────────────────────────────────
st.divider()
st.caption("Outil basé sur les notices officielles Silae — Prémontages & Initialisation CP — Raly Conseils")
