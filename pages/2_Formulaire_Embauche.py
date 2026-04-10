"""
Page 2 — Formulaire d'embauche
À envoyer aux clients via le lien : http://localhost:8502/Formulaire_Embauche
"""
import streamlit as st
import json
import uuid
from datetime import datetime
from pathlib import Path

# Importer utils depuis le dossier parent
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import CSS, logo_html, SOUMISSIONS_DIR


st.markdown(CSS, unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.info("Remplissez ce formulaire et cliquez sur **Soumettre**.\n\nVos informations seront transmises à Raly Conseils.")

# ── Encart lien client ─────────────────────────────────────────────────────────
LIEN_CLIENT = "https://raly-embauche-2bkvn2ahjmqlxvybxhg3aq.streamlit.app/"
TEXTE_EMAIL = f"""Bonjour,

Afin de préparer l'embauche de votre nouveau salarié, merci de bien vouloir compléter le formulaire en ligne via le lien ci-dessous :

{LIEN_CLIENT}

⚠️ Si la page affiche un message de mise en veille, cliquez sur le bouton pour la réactiver — elle sera prête en 30 secondes.

N'hésitez pas à nous contacter pour toute question.

Cordialement,
Raly Conseils"""

st.markdown("### 📨 Lien formulaire client")
st.caption("Copiez ce texte et collez-le directement dans votre email.")
st.code(TEXTE_EMAIL, language=None)
st.divider()

# ── En-tête ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:24px 0 8px;">
    <div style="font-size:1.6rem;font-weight:700;color:#3F4443;">Fiche d'identification d'un nouveau salarié</div>
    <div style="color:#789F90;font-size:1rem;margin-top:4px;">Raly Conseils</div>
</div>
""", unsafe_allow_html=True)
st.divider()

SOUMISSIONS_DIR.mkdir(exist_ok=True)

# ── Formulaire ─────────────────────────────────────────────────────────────────
with st.form("formulaire_embauche", clear_on_submit=True):

    # — Entreprise —
    st.markdown("#### 🏢 Entreprise")
    entreprise   = st.text_input("Entreprise *")
    siret        = st.text_input("SIRET de l'établissement d'embauche")
    col1, col2 = st.columns(2)
    with col1:
        dpae     = st.radio("Devons-nous établir la DPAE ?*", ["Oui", "Non"], horizontal=True)
    with col2:
        contrat  = st.radio("Devons-nous établir le contrat ?*", ["Oui", "Non"], horizontal=True)

    st.divider()

    # — Identité —
    st.markdown("#### 👤 Identité du salarié")
    col1, col2 = st.columns(2)
    with col1:
        nom         = st.text_input("Nom *")
        nom_naiss   = st.text_input("Nom de naissance", help="Obligatoire pour la sécurité sociale")
        date_naiss  = st.date_input("Date de naissance *", value=None, format="DD/MM/YYYY")
        pays_naiss  = st.text_input("Pays de naissance", placeholder="France")
        nationalite = st.text_input("Nationalité", placeholder="Française")
    with col2:
        prenom      = st.text_input("Prénom *")
        nss         = st.text_input("Numéro de Sécurité Sociale", placeholder="ex: 1 85 03 75 XXX XXX XX")
        lieu_naiss  = st.text_input("Lieu de naissance (commune)")
        titre_sejour= st.text_input("Si étranger, n° du titre de séjour")
        situation   = st.selectbox("Situation familiale", [
            "", "Célibataire", "Marié(e)", "Pacsé(e)", "Vie maritale", "Divorcé(e)", "Veuf/Veuve"
        ])

    st.divider()

    # — Adresse —
    st.markdown("#### 🏠 Adresse")
    col1, col2 = st.columns(2)
    with col1:
        adresse_num  = st.text_input("Numéro et rue")
        ville        = st.text_input("Ville")
        code_postal  = st.text_input("Code Postal")
    with col2:
        adresse_comp = st.text_input("Complément d'adresse")
        region       = st.text_input("État / Région")
        email        = st.text_input("Email du salarié", placeholder="exemple@exemple.com")

    st.divider()

    # — Embauche —
    st.markdown("#### 📅 Conditions d'embauche")
    col1, col2 = st.columns(2)
    with col1:
        date_embauche   = st.date_input("Date d'embauche *", value=None, format="DD/MM/YYYY")
        type_contrat    = st.radio("Type de contrat *", ["CDI", "CDD"], horizontal=True)
    with col2:
        heure_embauche  = st.time_input("Heure d'embauche", value=None)

    # CDD uniquement
    st.markdown("**Si CDD :**")
    col1, col2, col3 = st.columns(3)
    with col1:
        motif_cdd   = st.selectbox("Motif du CDD", [
            "", "Accroissement temporaire d'activité", "Remplacement d'un salarié absent",
            "Emploi saisonnier", "Contrat d'usage", "Autre"
        ])
    with col2:
        date_fin_cdd = st.date_input("Date de fin de contrat", value=None, format="DD/MM/YYYY")
    with col3:
        remplace     = st.text_input("Nom du salarié remplacé (si remplacement)")

    st.divider()

    # — Horaires —
    st.markdown("#### ⏰ Horaires")
    nb_heures = st.text_input("Nombre d'heures par semaine ou forfait *", placeholder="ex: 35h ou Forfait 218 jours")

    st.markdown("**Répartition des heures sur la semaine** *(à remplir si moins de 35h)*")
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    horaires = {}
    cols = st.columns([2, 1, 1, 1, 1])
    cols[0].markdown("**Jour**")
    cols[1].markdown("**De**")
    cols[2].markdown("**À**")
    cols[3].markdown("**De**")
    cols[4].markdown("**À**")
    for j in jours:
        cols = st.columns([2, 1, 1, 1, 1])
        cols[0].markdown(j)
        h1 = cols[1].text_input("", key=f"h_{j}_1", placeholder="08:00", label_visibility="collapsed")
        h2 = cols[2].text_input("", key=f"h_{j}_2", placeholder="12:00", label_visibility="collapsed")
        h3 = cols[3].text_input("", key=f"h_{j}_3", placeholder="13:00", label_visibility="collapsed")
        h4 = cols[4].text_input("", key=f"h_{j}_4", placeholder="17:00", label_visibility="collapsed")
        if any([h1, h2, h3, h4]):
            horaires[j] = {"de1": h1, "a1": h2, "de2": h3, "a2": h4}

    st.divider()

    # — Poste —
    st.markdown("#### 💼 Poste & Rémunération")
    col1, col2 = st.columns(2)
    with col1:
        categorie    = st.radio("Catégorie *", ["Cadre", "Non Cadre", "Apprenti"], horizontal=True)
        emploi       = st.text_input("Emploi Occupé *")
        convention   = st.text_input("Convention collective de l'entreprise *")
    with col2:
        coefficient  = st.text_input("Coefficient / Niveau conventionnel")
        salaire      = st.text_input("Salaire Brut Mensuel *", placeholder="ex: 2500")

    autres_remun  = st.text_area("Autres infos de rémunération")
    clauses       = st.text_area("Clauses supplémentaires à prévoir dans le contrat",
                                  placeholder="Variable, non concurrence, télétravail, véhicule, vidéosurveillance, mobilité, etc.")

    st.divider()

    # — Avantages —
    st.markdown("#### 🏥 Avantages sociaux")
    col1, col2 = st.columns(2)
    with col1:
        mutuelle     = st.radio("Affiliation à la mutuelle de l'entreprise *", ["Oui", "Non (fournir justificatif)"], horizontal=False)
        option_mut   = st.text_input("Si Oui, sous quelle option ?", placeholder="ex: isolé, famille...")
    with col2:
        transport    = st.radio("Prise en charge abonnement transport *", ["Oui (fournir justificatif)", "Non"], horizontal=False)

    st.divider()

    # — Documents —
    st.markdown("#### 📎 Documents")
    st.info("Merci de transmettre par email à votre gestionnaire : pièce d'identité, attestation SS, RIB, etc.")
    docs_envoyes = st.multiselect("Documents qui seront transmis :", [
        "Pièce d'identité", "Attestation de sécurité sociale",
        "RIB", "Titre de séjour", "Justificatif mutuelle", "Justificatif transport", "Autre"
    ])

    # — Informations importantes —
    st.divider()
    st.markdown("""
    <div style="background:#fff8f5;border-left:4px solid #F67728;padding:12px 16px;border-radius:4px;font-size:0.85rem;color:#3F4443;">
    <strong>ℹ️ Informations importantes :</strong><br>
    La déclaration d'embauche (DPAE) est obligatoire <strong>avant l'arrivée</strong> du salarié dans l'entreprise.
    Pensez à enregistrer le salarié auprès de votre service de santé du travail pour son rendez-vous initial.
    Pour les salariés étrangers, une autorisation préalable à l'embauche est obligatoire avec un délai de
    <strong>2 jours ouvrables</strong> pour les titulaires d'un titre de séjour en cours de validité et un délai de
    <strong>2 mois</strong> pour les demandes d'autorisations de travail sans titre de séjour ou de nationalité algérienne.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    submitted = st.form_submit_button("✅  Soumettre", type="primary", use_container_width=True)

# ── Traitement de la soumission ────────────────────────────────────────────────
if submitted:
    errors = []
    if not entreprise.strip(): errors.append("Entreprise")
    if not nom.strip():        errors.append("Nom")
    if not prenom.strip():     errors.append("Prénom")
    if not date_embauche:      errors.append("Date d'embauche")

    if errors:
        st.error(f"Champs obligatoires manquants : {', '.join(errors)}")
    else:
        data = {
            "id":           str(uuid.uuid4())[:8],
            "soumis_le":    datetime.now().strftime("%d/%m/%Y %H:%M"),
            "entreprise":   entreprise,
            "siret":        siret,
            "dpae":         dpae,
            "contrat_a_etablir": contrat,
            "nom":          nom,
            "prenom":       prenom,
            "nom_naissance":nom_naiss,
            "nss":          nss,
            "date_naissance": date_naiss.strftime("%d/%m/%Y") if date_naiss else "",
            "lieu_naissance": lieu_naiss,
            "pays_naissance": pays_naiss,
            "nationalite":  nationalite,
            "titre_sejour": titre_sejour,
            "situation_familiale": situation,
            "adresse_numero": adresse_num,
            "adresse_complement": adresse_comp,
            "ville":        ville,
            "code_postal":  code_postal,
            "region":       region,
            "email":        email,
            "date_embauche": date_embauche.strftime("%d/%m/%Y") if date_embauche else "",
            "heure_embauche": str(heure_embauche) if heure_embauche else "",
            "type_contrat": type_contrat,
            "motif_cdd":    motif_cdd,
            "date_fin_cdd": date_fin_cdd.strftime("%d/%m/%Y") if date_fin_cdd else "",
            "salarie_remplace": remplace,
            "nb_heures":    nb_heures,
            "horaires":     horaires,
            "categorie":    categorie,
            "emploi":       emploi,
            "convention":   convention,
            "coefficient":  coefficient,
            "salaire":      salaire,
            "autres_remun": autres_remun,
            "clauses":      clauses,
            "mutuelle":     mutuelle,
            "option_mutuelle": option_mut,
            "transport":    transport,
            "docs_envoyes": docs_envoyes,
        }

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nom_fichier = f"{ts}_{entreprise[:20].replace(' ','_')}_{nom.upper()}.json"
        fichier = SOUMISSIONS_DIR / nom_fichier
        fichier.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        st.success(f"✅ Formulaire soumis avec succès ! Référence : **{data['id']}**")
        st.balloons()
        st.info("Raly Conseils a bien reçu votre fiche. Votre gestionnaire prendra en charge l'embauche.")
