"""
Formulaire d'embauche — version cloud (Streamlit Community Cloud)
Envoie les données et documents par email à natacha@ralyconseils.com
Pas de stockage local (filesystem éphémère sur le cloud).
"""
import streamlit as st
import json
import uuid
import smtplib
import mimetypes
import requests
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path
import base64

ASANA_PROJECT_GID = "1213986643545923"
ASANA_API_URL     = "https://app.asana.com/api/1.0/tasks"


def get_asana_token() -> str:
    try:
        return st.secrets["asana_token"]
    except Exception:
        return ""


def create_asana_task(data: dict) -> tuple[bool, str]:
    token = get_asana_token()
    if not token:
        return False, "Token Asana manquant"

    def v(k): return str(data.get(k, "") or "—")

    horaires_txt = ""
    for jour, h in (data.get("horaires") or {}).items():
        horaires_txt += f"\n  {jour} : {h.get('de1','')}–{h.get('a1','')} / {h.get('de2','')}–{h.get('a2','')}"

    notes = f"""📋 Référence : {v('id')} — reçu le {v('soumis_le')}

🏢 ENTREPRISE
• Entreprise : {v('entreprise')}
• SIRET : {v('siret')}
• DPAE à établir : {v('dpae')}
• Contrat à établir : {v('contrat_a_etablir')}

👤 SALARIÉ
• Nom : {v('prenom')} {v('nom')}
• Nom de naissance : {v('nom_naissance')}
• Date de naissance : {v('date_naissance')}
• Lieu de naissance : {v('lieu_naissance')} ({v('pays_naissance')})
• Nationalité : {v('nationalite')}
• N° SS : {v('nss')}
• Titre de séjour : {v('titre_sejour')}
• Situation familiale : {v('situation_familiale')}
• Email : {v('email')}
• Adresse : {v('adresse_numero')} {v('adresse_complement')}, {v('code_postal')} {v('ville')}

📅 CONTRAT
• Date d'embauche : {v('date_embauche')} {v('heure_embauche')}
• Type : {v('type_contrat')}
• Date fin CDD : {v('date_fin_cdd')}
• Motif CDD : {v('motif_cdd')}
• Salarié remplacé : {v('salarie_remplace')}
• Heures/semaine : {v('nb_heures')}{horaires_txt}

💼 POSTE & RÉMUNÉRATION
• Emploi : {v('emploi')} ({v('categorie')})
• Convention collective : {v('convention')}
• Coefficient : {v('coefficient')}
• Salaire brut : {v('salaire')} €
• Autres rémunérations : {v('autres_remun')}
• Clauses : {v('clauses')}

🏥 AVANTAGES
• Mutuelle : {v('mutuelle')} — Option : {v('option_mutuelle')}
• Transport : {v('transport')}

---JSON---
""" + json.dumps(data, ensure_ascii=False)

    payload = {
        "data": {
            "name": f"Embauche — {v('prenom')} {v('nom')} ({v('entreprise')}) · {v('date_embauche')}",
            "notes": notes,
            "projects": [ASANA_PROJECT_GID],
        }
    }

    try:
        r = requests.post(
            ASANA_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code != 201:
            return False, r.text
        task_gid = r.json()["data"]["gid"]
        return True, task_gid
    except Exception as e:
        return False, str(e)


def upload_attachment(token: str, task_gid: str, filename: str, content: bytes) -> str:
    """Envoie un fichier comme pièce jointe sur la tâche Asana. Retourne "" si ok, sinon le message d'erreur."""
    try:
        r = requests.post(
            "https://app.asana.com/api/1.0/attachments",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "parent": (None, task_gid),
                "file":   (filename, content),
            },
            timeout=30,
        )
        if r.status_code == 200 or r.status_code == 201:
            return ""
        return f"{filename}: {r.status_code} {r.text[:200]}"
    except Exception as e:
        return f"{filename}: {e}"

LOGO_PATH = Path(__file__).parent / "logo.png"

st.set_page_config(
    page_title="Formulaire d'embauche — Raly Conseils",
    page_icon="📋",
    layout="centered",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root { --vert:#789F90; --gris:#3F4443; --orange:#F67728; }
.stApp { background-color:#F8F9F8; }
[data-testid="stSidebar"] { display:none; }
h1, h2, h3 { color:#3F4443 !important; }
h1 { border-bottom:3px solid #789F90; padding-bottom:10px; }
.stButton > button[kind="primary"] {
    background-color:#789F90 !important; border:none !important;
    color:white !important; font-weight:600 !important;
}
.stButton > button[kind="primary"]:hover { background-color:#5d8577 !important; }
hr { border-color:#789F90 !important; }
[data-testid="stAlert"] { border-left:4px solid #789F90; }
</style>
""", unsafe_allow_html=True)

# ── Logo ───────────────────────────────────────────────────────────────────────
if LOGO_PATH.exists():
    b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
    st.markdown(f"""
    <div style="text-align:center;padding:24px 0 8px;">
        <div style="display:inline-block;background:white;border-radius:8px;padding:12px 24px;">
            <img src="data:image/png;base64,{b64}" style="height:60px;">
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;padding:8px 0 16px;">
    <div style="font-size:1.5rem;font-weight:700;color:#3F4443;">Fiche d'identification d'un nouveau salarié</div>
    <div style="color:#789F90;font-size:1rem;margin-top:4px;">Raly Conseils</div>
</div>
""", unsafe_allow_html=True)
st.divider()


def get_smtp_password() -> str:
    """Récupère le mot de passe SMTP depuis st.secrets (cloud) ou config.json (local)."""
    try:
        return st.secrets["smtp_password"]
    except Exception:
        pass
    try:
        cfg = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
        return cfg.get("smtp_password", "")
    except Exception:
        return ""


def send_email(data: dict, fichiers_uploades: dict) -> tuple[bool, str]:
    """Envoie l'email de notification avec pièces jointes."""
    smtp_password = get_smtp_password()
    if not smtp_password:
        return False, "Mot de passe email non configuré"

    SMTP_HOST = "smtp.office365.com"
    SMTP_PORT = 587
    SMTP_USER = "natacha@ralyconseils.com"

    def v(k): return str(data.get(k, "") or "—")

    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#3F4443;">
    <div style="background:#789F90;padding:16px 24px;border-radius:8px 8px 0 0;">
        <h2 style="color:white;margin:0;">Nouvelle fiche d'embauche reçue</h2>
        <p style="color:#e0ede8;margin:4px 0 0;">Référence : <strong>{v('id')}</strong> &nbsp;·&nbsp; {v('soumis_le')}</p>
    </div>
    <div style="padding:16px 24px;background:#f8f9f8;border:1px solid #ddd;border-radius:0 0 8px 8px;">

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;">🏢 Entreprise</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Entreprise</td><td>{v('entreprise')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">SIRET</td><td>{v('siret')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">DPAE à établir</td><td>{v('dpae')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Contrat à établir</td><td>{v('contrat_a_etablir')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">👤 Salarié</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Nom</td><td>{v('prenom')} {v('nom')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Nom de naissance</td><td>{v('nom_naissance')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Date de naissance</td><td>{v('date_naissance')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Lieu de naissance</td><td>{v('lieu_naissance')} ({v('pays_naissance')})</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Nationalité</td><td>{v('nationalite')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">N° Sécurité Sociale</td><td>{v('nss')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Situation familiale</td><td>{v('situation_familiale')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Email</td><td>{v('email')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Adresse</td><td>{v('adresse_numero')} {v('adresse_complement')}, {v('code_postal')} {v('ville')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Titre de séjour</td><td>{v('titre_sejour')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">📅 Contrat</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Date d'embauche</td><td>{v('date_embauche')} {v('heure_embauche')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Type de contrat</td><td>{v('type_contrat')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Date fin CDD</td><td>{v('date_fin_cdd')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Motif CDD</td><td>{v('motif_cdd')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Salarié remplacé</td><td>{v('salarie_remplace')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Heures / semaine</td><td>{v('nb_heures')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">💼 Poste & Rémunération</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Emploi</td><td>{v('emploi')} ({v('categorie')})</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Convention collective</td><td>{v('convention')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Coefficient</td><td>{v('coefficient')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Salaire brut mensuel</td><td>{v('salaire')} €</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Autres rémunérations</td><td>{v('autres_remun')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Clauses spéciales</td><td>{v('clauses')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">🏥 Avantages</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Mutuelle</td><td>{v('mutuelle')} — Option : {v('option_mutuelle')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Transport</td><td>{v('transport')}</td></tr>
    </table>

    <p style="margin-top:24px;font-size:0.85rem;color:#789F90;">
        Message généré automatiquement par l'outil Raly Conseils.
    </p>
    </div></body></html>
    """

    msg = EmailMessage()
    msg["Subject"] = f"[Embauche] {v('prenom')} {v('nom')} — {v('entreprise')} ({v('date_embauche')})"
    msg["From"]    = SMTP_USER
    msg["To"]      = SMTP_USER
    msg.set_content("Veuillez consulter cet email dans un client compatible HTML.")
    msg.add_alternative(html, subtype="html")

    # Pièces jointes
    for label, fichiers in fichiers_uploades.items():
        for f in (fichiers or []):
            f.seek(0)
            contenu = f.read()
            mime_type, _ = mimetypes.guess_type(f.name)
            maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
            nom_pj = f"{label}_{f.name}"
            msg.add_attachment(contenu, maintype=maintype, subtype=subtype, filename=nom_pj)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USER, smtp_password)
            server.send_message(msg)
        return True, "ok"
    except Exception as e:
        return False, str(e)


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
        date_naiss  = st.date_input("Date de naissance *", value=None, format="DD/MM/YYYY",
                                    min_value=datetime(1900, 1, 1).date(), max_value=datetime.now().date())
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
    cols[0].markdown("**Jour**"); cols[1].markdown("**De**"); cols[2].markdown("**À**")
    cols[3].markdown("**De**");   cols[4].markdown("**À**")
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
                                  placeholder="Variable, non concurrence, télétravail, véhicule, etc.")

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
    st.markdown("Déposez les documents du salarié *(PDF, JPG, PNG)*")
    col1, col2 = st.columns(2)
    with col1:
        f_identite  = st.file_uploader("Pièce d'identité",               type=["pdf","jpg","jpeg","png"], accept_multiple_files=True)
        f_ss        = st.file_uploader("Attestation sécurité sociale",    type=["pdf","jpg","jpeg","png"], accept_multiple_files=True)
        f_rib       = st.file_uploader("RIB",                             type=["pdf","jpg","jpeg","png"], accept_multiple_files=True)
        f_sejour    = st.file_uploader("Titre de séjour *(si étranger)*", type=["pdf","jpg","jpeg","png"], accept_multiple_files=True)
    with col2:
        f_mutuelle  = st.file_uploader("Justificatif mutuelle",           type=["pdf","jpg","jpeg","png"], accept_multiple_files=True)
        f_transport = st.file_uploader("Justificatif transport",          type=["pdf","jpg","jpeg","png"], accept_multiple_files=True)
        f_autres    = st.file_uploader("Autres documents",                type=["pdf","jpg","jpeg","png"], accept_multiple_files=True)

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

# ── Traitement ─────────────────────────────────────────────────────────────────
if submitted:
    errors = []
    if not entreprise.strip():  errors.append("Entreprise")
    if not nom.strip():         errors.append("Nom")
    if not prenom.strip():      errors.append("Prénom")
    if not date_naiss:          errors.append("Date de naissance")
    if not date_embauche:       errors.append("Date d'embauche")
    if not nb_heures.strip():   errors.append("Nombre d'heures par semaine")
    if not emploi.strip():      errors.append("Emploi occupé")
    if not convention.strip():  errors.append("Convention collective")
    if not salaire.strip():     errors.append("Salaire brut mensuel")

    if errors:
        st.error("⚠️ Merci de remplir les champs obligatoires suivants : **" + "**, **".join(errors) + "**")
    else:
        ref = str(uuid.uuid4())[:8].upper()
        data = {
            "id":                ref,
            "soumis_le":         datetime.now().strftime("%d/%m/%Y %H:%M"),
            "entreprise":        entreprise,
            "siret":             siret,
            "dpae":              dpae,
            "contrat_a_etablir": contrat,
            "nom":               nom,
            "prenom":            prenom,
            "nom_naissance":     nom_naiss,
            "nss":               nss,
            "date_naissance":    date_naiss.strftime("%d/%m/%Y") if date_naiss else "",
            "lieu_naissance":    lieu_naiss,
            "pays_naissance":    pays_naiss,
            "nationalite":       nationalite,
            "titre_sejour":      titre_sejour,
            "situation_familiale": situation,
            "adresse_numero":    adresse_num,
            "adresse_complement":adresse_comp,
            "ville":             ville,
            "code_postal":       code_postal,
            "region":            region,
            "email":             email,
            "date_embauche":     date_embauche.strftime("%d/%m/%Y") if date_embauche else "",
            "heure_embauche":    str(heure_embauche) if heure_embauche else "",
            "type_contrat":      type_contrat,
            "motif_cdd":         motif_cdd,
            "date_fin_cdd":      date_fin_cdd.strftime("%d/%m/%Y") if date_fin_cdd else "",
            "salarie_remplace":  remplace,
            "nb_heures":         nb_heures,
            "horaires":          horaires,
            "categorie":         categorie,
            "emploi":            emploi,
            "convention":        convention,
            "coefficient":       coefficient,
            "salaire":           salaire,
            "autres_remun":      autres_remun,
            "clauses":           clauses,
            "mutuelle":          mutuelle,
            "option_mutuelle":   option_mut,
            "transport":         transport,
        }

        fichiers_uploades = {
            "piece_identite":  f_identite,
            "attestation_ss":  f_ss,
            "rib":             f_rib,
            "titre_sejour":    f_sejour,
            "mutuelle":        f_mutuelle,
            "transport":       f_transport,
            "autres":          f_autres,
        }

        with st.spinner("Envoi en cours..."):
            ok, task_gid = create_asana_task(data)
            upload_errors = []
            if ok:
                token = get_asana_token()
                for label, fichiers in fichiers_uploades.items():
                    for f in (fichiers or []):
                        contenu = f.read()
                        err = upload_attachment(token, task_gid, f"{label}_{f.name}", contenu)
                        if err:
                            upload_errors.append(err)

        if ok:
            if upload_errors:
                st.warning("Documents : " + " | ".join(upload_errors))
            st.balloons()
            st.markdown("""
            <div style="background:#e8f5e9;border:2px solid #789F90;border-radius:10px;padding:24px;text-align:center;margin-top:16px;">
                <div style="font-size:2rem;">✅</div>
                <div style="font-size:1.3rem;font-weight:700;color:#3F4443;margin:8px 0;">Formulaire envoyé avec succès !</div>
                <div style="color:#789F90;font-size:1rem;">Référence : <strong>{ref}</strong></div>
                <div style="color:#555;margin-top:12px;">Raly Conseils a bien reçu votre fiche.<br>Votre gestionnaire prendra en charge l'embauche dans les meilleurs délais.</div>
            </div>
            """.replace("{ref}", ref), unsafe_allow_html=True)
        else:
            st.error(f"Erreur lors de l'envoi : {msg}")
            st.warning("Merci de contacter Raly Conseils directement : natacha@ralyconseils.com")
