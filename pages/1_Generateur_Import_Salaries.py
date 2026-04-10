"""
Outil de génération d'import Silae
Génère automatiquement un fichier Excel d'import salarié pour Silae
à partir de documents (contrat, pièce d'identité, email, etc.)
"""

import streamlit as st
import anthropic
import xlwt
import io
import json
import base64
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import CSS, logo_html, load_config, save_config


# ── CSS Raly Conseils ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Palette Raly Conseils */
:root {
    --vert:   #789F90;
    --gris:   #3F4443;
    --orange: #F67728;
}

/* Fond général */
.stApp { background-color: #F8F9F8; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #3F4443 !important;
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] input { color: #3F4443 !important; }
[data-testid="stSidebar"] .stSuccess { color: #789F90 !important; }

/* Titre principal */
h1 { color: #3F4443 !important; border-bottom: 3px solid #789F90; padding-bottom: 10px; }

/* Sous-titres */
h2, h3 { color: #3F4443 !important; }

/* Bouton primaire */
.stButton > button[kind="primary"] {
    background-color: #789F90 !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #5d8577 !important;
}

/* Bouton secondaire / download */
.stDownloadButton > button {
    background-color: #F67728 !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
}
.stDownloadButton > button:hover {
    background-color: #d4601a !important;
}

/* Expanders */
[data-testid="stExpander"] summary {
    background-color: #789F90 !important;
    color: white !important;
    border-radius: 6px;
    font-weight: 600;
}

/* Séparateur */
hr { border-color: #789F90 !important; }

/* Bandeau info/success/warning */
[data-testid="stAlert"] { border-left: 4px solid #789F90; }
</style>
""", unsafe_allow_html=True)

# ── Clé API ────────────────────────────────────────────────────────────────────
_config = load_config()
api_key = _config.get("api_key", "")


# ── Définition des champs Silae (noms exacts du fichier entêtes Silae) ─────────
FIELDS = {
    "Identification": {
        "Matricule":                  {"label": "Matricule *",               "help": "Identifiant unique (obligatoire)"},
        "Civilité":                   {"label": "Civilité",                   "help": "1=Monsieur · 2=Madame · 3=Mademoiselle"},
        "Sexe":                       {"label": "Sexe",                       "help": "1=Masculin · 2=Féminin"},
        "Nom de naissance":           {"label": "Nom de naissance",           "help": "Obligatoire pour créer un salarié"},
        "Nom usuel":                  {"label": "Nom usuel"},
        "Nom marital":                {"label": "Nom marital"},
        "Prénom (salarié)":           {"label": "Prénom(s)"},
        "Date de naissance (salarié)":{"label": "Date de naissance",          "help": "Format JJ/MM/AAAA"},
        "Numéro de sécurité sociale": {"label": "N° Sécurité Sociale",        "help": "15 chiffres sans espace"},
        "Clé numéro sécurité sociale":{"label": "Clé N° SS",                  "help": "2 derniers chiffres"},
        "Département de naissance":   {"label": "Département de naissance",   "help": "Ex: 75 · 99 si né à l'étranger"},
        "Commune de naissance":       {"label": "Commune de naissance"},
        "Etranger ?":                 {"label": "Etranger ?",                 "help": "Oui / Non"},
        "Code pays de naissance":     {"label": "Code pays de naissance",     "help": "Ex: FR, MA..."},
        "Code pays nationalité":      {"label": "Code pays nationalité",      "help": "Ex: FR"},
        "Situation familiale":        {"label": "Situation familiale",        "help": "10=Célibataire · 20=Vie maritale · 30=Pacsé · 40=Marié · 60=Divorcé · 70=Veuf"},
        "Date d'entrée dans l'entreprise": {"label": "Date d'entrée",         "help": "Format JJ/MM/AAAA"},
        "Date de sortie de l'entreprise":  {"label": "Date de sortie",        "help": "Format JJ/MM/AAAA"},
    },
    "Coordonnées": {
        "Numéro de la voie":  {"label": "N° de voie"},
        "BTQ":                {"label": "BTQ"},
        "Nom de la voie":     {"label": "Nom de la voie"},
        "Complément d'adresse":{"label": "Complément d'adresse"},
        "Code postal":        {"label": "Code postal"},
        "Ville":              {"label": "Ville"},
        "Code pays":          {"label": "Code pays résidence",   "help": "Ex: FR"},
        "Téléphone domicile": {"label": "Téléphone domicile"},
        "Téléphone portable": {"label": "Téléphone portable"},
        "E-mail":             {"label": "Email personnel"},
        "E-mail pro":         {"label": "Email professionnel"},
    },
    "Contrat & Emploi": {
        "Code contrat":       {"label": "Code contrat",          "help": "01=CDI · 02=CDD"},
        "Emploi":             {"label": "Intitulé du poste"},
        "CSP":                {"label": "Code CSP"},
        "CCN":                {"label": "Code convention collective"},
        "Date début":         {"label": "Date début emploi",     "help": "Format JJ/MM/AAAA"},
        "Date fin":           {"label": "Date fin emploi",       "help": "Format JJ/MM/AAAA · CDD uniquement"},
        "Motif du CDD":       {"label": "Motif CDD",             "help": "Code motif (voir fiche Salarié Silae)"},
        "Date signature contrat": {"label": "Date signature contrat", "help": "Format JJ/MM/AAAA"},
        "Date début contrat": {"label": "Date début contrat",    "help": "Format JJ/MM/AAAA"},
    },
    "Rémunération & Horaires": {
        "Code salaire":        {"label": "Type de salaire",            "help": "Mensuel ou Horaire"},
        "Salaire de base (emploi)": {"label": "Salaire de base (€)"},
        "Nb heures":           {"label": "Heures mensuelles normales", "help": "Ex: 151.67 pour 35h/semaine"},
        "Nb heures majorées":  {"label": "Heures majorées"},
        "Grille horaire":      {"label": "Code grille horaire"},
        "Ticket restaurant":   {"label": "Tickets restaurant",         "help": "0=Non · 1=Auto · 2=Saisi · 3=Repris mois préc."},
    },
    "Informations bancaires": {
        "IBAN":              {"label": "IBAN"},
        "BIC":               {"label": "BIC / SWIFT"},
        "Mode de paiement":  {"label": "Mode de paiement",  "help": "Virement ou Espèces"},
    },
}

# ── Prompt d'extraction ────────────────────────────────────────────────────────
EXTRACTION_PROMPT = """Tu es un expert RH qui extrait des informations de salariés depuis des documents pour les importer dans le logiciel de paie Silae.

Analyse le(s) document(s) fourni(s) et extrait toutes les informations disponibles.

RÈGLES D'EXTRACTION :
- Matricule : si non fourni explicitement, laisse la valeur vide ""
- Civilité : 1=Monsieur/M., 2=Madame/Mme, 3=Mademoiselle/Mlle
- Dates : toujours au format JJ/MM/AAAA
- Code Contrat : 01=CDI, 02=CDD (à compléter)
- Code Salaire : "Mensuel" si salaire mensuel fixe, "Horaire" si taux horaire
- Code pays : code ISO 2 lettres (FR pour France, BE pour Belgique, MA pour Maroc, etc.)
- Situation familiale : 10=Célibataire, 20=Vie maritale, 30=Pacsé, 40=Marié, 60=Divorcé, 70=Veuf
- "Numéro de sécurité sociale" : 13 premiers chiffres (sans la clé), sans espace ni tiret
- "Clé numéro sécurité sociale" : les 2 derniers chiffres du N° SS (14e et 15e)
- IBAN : format international complet (FR76...)
- Sexe : 1=Masculin (chiffre 1 du N° SS), 2=Féminin (chiffre 2 du N° SS)
- "Etranger ?" : "Oui" si né à l'étranger (dept=99), "Non" sinon

EXTRACTION DU DÉPARTEMENT DE NAISSANCE depuis le N° de Sécurité Sociale :
Le numéro INSEE a la structure suivante (15 chiffres) :
  [1] Sexe · [2-3] Année naissance · [4-5] Mois naissance · [6-7] Département · [8-10] Commune · [11-13] Ordre · [14-15] Clé
- "Département de naissance" = chiffres 6 et 7 du numéro SS complet 15 chiffres (ex: "99" si né à l'étranger)
- Si département = "99" → la personne est née à l'étranger :
    · "Code pays de naissance" = déduire du code commune (chiffres 8-10) via les codes INSEE pays :
      099 ou 100=Allemagne, 101=Autriche, 109=Belgique, 117=Espagne, 127=Grande-Bretagne,
      131=Grèce, 135=Italie, 144=Luxembourg, 168=Pays-Bas, 212=Algérie, 216=Maroc (→ MA),
      220=Tunisie, 302=Sénégal, 304=Côte d'Ivoire, 306=Mali, 328=Cameroun,
      351=Congo, 400=États-Unis, 404=Canada, 501=Brésil, 601=Chine, 603=Inde,
      607=Japon, 612=Philippines, 628=Turquie, 629=Vietnam
    · Pour tout code non listé, utiliser le code ISO 2 lettres du pays correspondant
    · "Commune de naissance" = laisser vide (non applicable pour naissance à l'étranger)
- Si département ≠ "99" → naissance en France, "Code pays de naissance" = "FR"

- Si une information n'est pas présente dans le document, NE PAS l'inclure dans le JSON
- Ne jamais inventer une information qui n'est pas dans le document

DOCUMENT(S) :
{text}

Réponds UNIQUEMENT avec un objet JSON valide de la forme {{"clé": "valeur", ...}}.
Pas de tableau, pas de texte autour. Uniquement les champs trouvés dans le document.

Les clés JSON doivent être EXACTEMENT ces noms de champs Silae :
- Matricule
- Civilité
- Sexe
- Nom de naissance
- Nom usuel
- Nom marital
- Prénom (salarié)
- Date de naissance (salarié)
- Numéro de sécurité sociale
- Clé numéro sécurité sociale
- Département de naissance
- Commune de naissance
- Etranger ?
- Code pays de naissance
- Code pays nationalité
- Situation familiale
- Date d'entrée dans l'entreprise
- Date de sortie de l'entreprise
- Numéro de la voie
- BTQ
- Nom de la voie
- Complément d'adresse
- Code postal
- Ville
- Code pays
- Téléphone domicile
- Téléphone portable
- E-mail
- E-mail pro
- Code contrat
- Emploi
- CSP
- CCN
- Date début
- Date fin
- Motif du CDD
- Date signature contrat
- Date début contrat
- Code salaire
- Salaire de base (emploi)
- Nb heures
- Nb heures majorées
- Grille horaire
- Ticket restaurant
- IBAN
- BIC
- Mode de paiement
"""


# ── Extraction via Claude ──────────────────────────────────────────────────────
def extract_with_claude(text: str, files_data: list, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    content = []

    # Ajouter les fichiers (images ou PDF)
    for f in files_data:
        if f["media_type"].startswith("image/"):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": f["media_type"],
                    "data": f["data"],
                },
            })
        elif f["media_type"] == "application/pdf":
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": f["data"],
                },
            })

    # Ajouter le texte + prompt
    content.append({
        "type": "text",
        "text": EXTRACTION_PROMPT.format(text=text or "(voir les documents joints)"),
    })

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()

    # Nettoyer les blocs de code éventuels
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    return json.loads(raw)


# ── Génération du fichier XLS ──────────────────────────────────────────────────
def generate_xls(data: dict) -> bytes:
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Import Salariés")

    # Style entête
    hdr_style = xlwt.easyxf(
        "font: bold true, colour white; "
        "pattern: pattern solid, fore_colour dark_red; "
        "alignment: horizontal centre;"
    )
    val_style = xlwt.easyxf("alignment: horizontal left;")

    for col_idx, (key, val) in enumerate(data.items()):
        ws.write(0, col_idx, key, hdr_style)
        ws.write(1, col_idx, str(val) if val is not None else "", val_style)
        # Largeur approximative
        width = max(len(str(key)), len(str(val or ""))) * 300 + 500
        ws.col(col_idx).width = min(width, 15000)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Interface Streamlit ────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:16px; margin-bottom:8px;">
    <div style="background:#789F90; width:6px; height:48px; border-radius:3px;"></div>
    <div>
        <div style="font-size:1.8rem; font-weight:700; color:#3F4443; line-height:1.1;">Générateur d'import Salariés</div>
        <div style="font-size:1rem; color:#789F90; font-weight:500;">Silae · Raly Conseils</div>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown(
    "Collez les informations du salarié (contrat, pièce d'identité, email...) "
    "et générez automatiquement le fichier `.xls` d'import pour Silae."
)

# Session state
if "form_data" not in st.session_state:
    st.session_state.form_data = {}
if "last_extraction_ok" not in st.session_state:
    st.session_state.last_extraction_ok = False

# ── Étape 1 : Saisie ──────────────────────────────────────────────────────────
st.subheader("1️⃣  Renseigner les informations du salarié")

col_txt, col_files = st.columns([3, 2])

with col_txt:
    text_input = st.text_area(
        "Coller le texte (contrat, email, notes RH...)",
        height=220,
        placeholder=(
            "Exemples :\n"
            "Nom : MARTIN  Prénom : Sophie  Née le : 15/03/1990 à Paris\n"
            "Adresse : 12 Rue de la Paix, 75001 Paris\n"
            "Entrée : 01/04/2026 · CDI · Comptable\n"
            "Salaire brut mensuel : 2 800 €  · 35h/semaine\n"
            "IBAN : FR76 3000 1007 9412 3456 7890 185\n"
            "N° SS : 2 90 03 75 XXX XXX XX"
        ),
    )

with col_files:
    uploaded_files = st.file_uploader(
        "Joindre des documents (optionnel)",
        accept_multiple_files=True,
        type=["pdf", "jpg", "jpeg", "png"],
        help="Contrat de travail, carte d'identité, RIB, email scanné…",
    )
    if uploaded_files:
        for f in uploaded_files:
            st.caption(f"📎 {f.name}")

btn_extract = st.button(
    "🔍  Extraire les informations avec Claude AI",
    type="primary",
    use_container_width=True,
)

if btn_extract:
    if not api_key:
        st.error("Clé API manquante. Allez dans ⚙️ Paramètres pour la configurer.")
    elif not text_input and not uploaded_files:
        st.error("Veuillez saisir du texte ou joindre au moins un document.")
    else:
        with st.spinner("Analyse en cours…"):
            try:
                files_data = []
                if uploaded_files:
                    for f in uploaded_files:
                        raw_bytes = f.read()
                        files_data.append({
                            "media_type": f.type or "application/octet-stream",
                            "data": base64.standard_b64encode(raw_bytes).decode("utf-8"),
                        })

                extracted = extract_with_claude(text_input, files_data, api_key)
                if not isinstance(extracted, dict):
                    raise ValueError(f"Réponse inattendue (type {type(extracted).__name__}) — réessayez.")
                st.session_state.form_data = extracted
                st.session_state.last_extraction_ok = True
                st.success(f"✅ {len(extracted)} champ(s) extrait(s) avec succès.")
            except json.JSONDecodeError as e:
                st.error(f"Impossible de parser la réponse JSON : {e}")
            except anthropic.AuthenticationError:
                st.error("Clé API Anthropic invalide. Vérifiez la variable d'environnement ANTHROPIC_API_KEY.")
            except Exception as e:
                st.error(f"Erreur : {e}")

# ── Étape 2 : Formulaire de vérification ──────────────────────────────────────
if st.session_state.form_data or st.session_state.last_extraction_ok:
    st.divider()
    st.subheader("2️⃣  Vérifier et compléter les informations")
    st.info(
        "Les champs sont pré-remplis avec les informations extraites. "
        "Corrigez ou complétez avant de générer le fichier."
    )

    form_data = st.session_state.form_data

    for section, fields in FIELDS.items():
        with st.expander(
            f"📁 {section}",
            expanded=(section in ("Identification", "Contrat & Emploi")),
        ):
            cols = st.columns(2)
            for i, (field_key, meta) in enumerate(fields.items()):
                with cols[i % 2]:
                    current_val = form_data.get(field_key, "")
                    new_val = st.text_input(
                        meta["label"],
                        value=str(current_val) if current_val else "",
                        key=f"field__{field_key}",
                        help=meta.get("help", ""),
                    )
                    form_data[field_key] = new_val

    # Données nettoyées (champs non vides uniquement)
    clean_data = {k: v for k, v in form_data.items() if v and str(v).strip()}

    # ── Étape 3 : Génération ──────────────────────────────────────────────────
    st.divider()
    st.subheader("3️⃣  Générer le fichier d'import Silae")

    col_btn, col_tip = st.columns([1, 2])

    with col_btn:
        if st.button("💾  Générer le fichier XLS", type="primary", use_container_width=True):
            if not clean_data.get("Matricule", "").strip():
                st.warning(
                    "⚠️ Le **Matricule** est vide. "
                    "Silae en a besoin pour identifier le salarié."
                )

            if not clean_data:
                st.error("Aucune donnée à exporter.")
            else:
                try:
                    xls_bytes = generate_xls(clean_data)
                    nom = clean_data.get("Nom", "salarie").upper()
                    prenom = clean_data.get("Prénom", "").capitalize()
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"import_silae_{nom}_{prenom}_{ts}.xls"

                    st.download_button(
                        label="📥  Télécharger le fichier XLS",
                        data=xls_bytes,
                        file_name=filename,
                        mime="application/vnd.ms-excel",
                        use_container_width=True,
                    )
                    st.success(f"Fichier **{filename}** prêt.")
                except Exception as e:
                    st.error(f"Erreur lors de la génération : {e}")

    with col_tip:
        st.info(
            "**Rappel — Import dans Silae :**\n\n"
            "1. Menu **Outils › Import Excel d'informations salariés**\n"
            "2. Cliquer sur **Ouvrir un fichier** et sélectionner le `.xls`\n"
            "3. La 1ʳᵉ ligne doit contenir les entêtes (format Option 2)\n"
            "4. Cliquer sur **Contrôler** puis **Importer**\n\n"
            "☑️ Cocher *Mettre à jour les salariés existants seulement* "
            "si vous ne souhaitez pas créer de nouveaux salariés."
        )

    # Aperçu
    if clean_data:
        with st.expander("🔎 Aperçu des données exportées", expanded=False):
            preview_items = list(clean_data.items())
            nb_cols = 3
            cols = st.columns(nb_cols)
            for i, (k, v) in enumerate(preview_items):
                with cols[i % nb_cols]:
                    st.metric(label=k, value=v)

else:
    st.info(
        "Saisissez les informations du salarié ci-dessus puis cliquez sur "
        "**Extraire les informations** pour commencer."
    )

# ── Pied de page ──────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Outil basé sur la notice officielle Silae — "
    "*Importer des informations Salariés (via Excel)* — mise à jour 24/02/2026"
)
