"""Utilitaires partagés entre les pages."""
import json
import base64
import smtplib
import mimetypes
from email.message import EmailMessage
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
LOGO_PATH   = Path(__file__).parent / "logo.png"
SOUMISSIONS_DIR = Path(__file__).parent / "soumissions"


def load_config() -> dict:
    """Charge la config depuis config.json (local) et/ou st.secrets (cloud)."""
    cfg = {}
    # Local : config.json
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Cloud : st.secrets complète/remplace config.json
    try:
        import streamlit as st
        for key in ["api_key", "asana_token", "app_password", "smtp_password"]:
            if key in st.secrets:
                cfg[key] = st.secrets[key]
    except Exception:
        pass
    return cfg


def is_cloud() -> bool:
    """Retourne True si l'app tourne sur Streamlit Cloud (pas de config.json local)."""
    return not CONFIG_FILE.exists()


def save_config(data: dict):
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def logo_html() -> str:
    if LOGO_PATH.exists():
        b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        return f"""<div style="background:white;border-radius:8px;padding:12px 16px;margin-bottom:8px;">
            <img src="data:image/png;base64,{b64}" style="width:100%;display:block;">
        </div>"""
    return ""


def send_submission_email(data: dict, docs_folder: Path | None = None) -> tuple[bool, str]:
    """Envoie un email de notification à Raly Conseils lors d'une soumission."""
    cfg = load_config()
    smtp_password = cfg.get("smtp_password", "")
    if not smtp_password:
        return False, "Mot de passe SMTP non configuré"

    SMTP_HOST = "smtp.office365.com"
    SMTP_PORT = 587
    SMTP_USER = "natacha@ralyconseils.com"
    DEST      = "natacha@ralyconseils.com"

    def v(k): return str(data.get(k, "") or "—")

    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#3F4443;">
    <div style="background:#789F90;padding:16px 24px;border-radius:8px 8px 0 0;">
        <h2 style="color:white;margin:0;">Nouvelle fiche d'embauche reçue</h2>
        <p style="color:#e0ede8;margin:4px 0 0;">Référence : <strong>{v('id')}</strong> · {v('soumis_le')}</p>
    </div>
    <div style="padding:16px 24px;background:#f8f9f8;border:1px solid #ddd;border-radius:0 0 8px 8px;">

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;">🏢 Entreprise</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Entreprise</td><td style="padding:4px 8px;">{v('entreprise')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">SIRET</td><td style="padding:4px 8px;">{v('siret')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">DPAE à établir</td><td style="padding:4px 8px;">{v('dpae')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Contrat à établir</td><td style="padding:4px 8px;">{v('contrat_a_etablir')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">👤 Salarié</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Nom</td><td style="padding:4px 8px;">{v('prenom')} {v('nom')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Nom de naissance</td><td style="padding:4px 8px;">{v('nom_naissance')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Date de naissance</td><td style="padding:4px 8px;">{v('date_naissance')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Lieu de naissance</td><td style="padding:4px 8px;">{v('lieu_naissance')} ({v('pays_naissance')})</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Nationalité</td><td style="padding:4px 8px;">{v('nationalite')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">N° Sécurité Sociale</td><td style="padding:4px 8px;">{v('nss')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Situation familiale</td><td style="padding:4px 8px;">{v('situation_familiale')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Email</td><td style="padding:4px 8px;">{v('email')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Adresse</td><td style="padding:4px 8px;">{v('adresse_numero')} {v('adresse_complement')}, {v('code_postal')} {v('ville')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">📅 Contrat</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Date d'embauche</td><td style="padding:4px 8px;">{v('date_embauche')} {v('heure_embauche')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Type de contrat</td><td style="padding:4px 8px;">{v('type_contrat')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Date fin CDD</td><td style="padding:4px 8px;">{v('date_fin_cdd')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Motif CDD</td><td style="padding:4px 8px;">{v('motif_cdd')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Heures / semaine</td><td style="padding:4px 8px;">{v('nb_heures')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">💼 Poste & Rémunération</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Emploi</td><td style="padding:4px 8px;">{v('emploi')} ({v('categorie')})</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Convention collective</td><td style="padding:4px 8px;">{v('convention')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Coefficient</td><td style="padding:4px 8px;">{v('coefficient')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Salaire brut mensuel</td><td style="padding:4px 8px;">{v('salaire')} €</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Autres rémunérations</td><td style="padding:4px 8px;">{v('autres_remun')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Clauses spéciales</td><td style="padding:4px 8px;">{v('clauses')}</td></tr>
    </table>

    <h3 style="color:#789F90;border-bottom:2px solid #789F90;padding-bottom:4px;margin-top:16px;">🏥 Avantages</h3>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:4px 8px;font-weight:600;width:40%;">Mutuelle</td><td style="padding:4px 8px;">{v('mutuelle')} — Option : {v('option_mutuelle')}</td></tr>
      <tr><td style="padding:4px 8px;font-weight:600;">Transport</td><td style="padding:4px 8px;">{v('transport')}</td></tr>
    </table>

    <p style="margin-top:24px;font-size:0.85rem;color:#789F90;">
        Ce message a été généré automatiquement par l'outil Raly Conseils.
    </p>
    </div></body></html>
    """

    msg = EmailMessage()
    msg["Subject"] = f"[Raly Conseils] Nouvelle embauche — {v('prenom')} {v('nom')} ({v('entreprise')})"
    msg["From"]    = SMTP_USER
    msg["To"]      = DEST
    msg.set_content("Veuillez consulter cet email dans un client compatible HTML.")
    msg.add_alternative(html, subtype="html")

    # Joindre les documents uploadés
    if docs_folder and docs_folder.exists():
        for doc in sorted(docs_folder.iterdir()):
            mime_type, _ = mimetypes.guess_type(doc.name)
            maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
            msg.add_attachment(doc.read_bytes(), maintype=maintype, subtype=subtype, filename=doc.name)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, smtp_password)
            server.send_message(msg)
        return True, "Email envoyé"
    except Exception as e:
        return False, str(e)


CSS = """
<style>
:root { --vert:#789F90; --gris:#3F4443; --orange:#F67728; }
.stApp { background-color:#F8F9F8; }
[data-testid="stSidebar"] { background-color:#3F4443 !important; }
[data-testid="stSidebar"] * { color:#FFFFFF !important; }
[data-testid="stSidebar"] input { color:#3F4443 !important; }

/* Logo au-dessus de la navigation */
[data-testid="stSidebar"] > div:first-child {
    display: flex;
    flex-direction: column;
}
[data-testid="stSidebarUserContent"] { order: 1; }
[data-testid="stSidebarNav"]         { order: 2; }

h1 { color:#3F4443 !important; border-bottom:3px solid #789F90; padding-bottom:10px; }
h2, h3 { color:#3F4443 !important; }
.stButton > button[kind="primary"] {
    background-color:#789F90 !important; border:none !important;
    color:white !important; font-weight:600 !important;
}
.stButton > button[kind="primary"]:hover { background-color:#5d8577 !important; }
.stDownloadButton > button {
    background-color:#F67728 !important; border:none !important;
    color:white !important; font-weight:600 !important;
}
.stDownloadButton > button:hover { background-color:#d4601a !important; }
[data-testid="stExpander"] summary {
    background-color:#789F90 !important; color:white !important;
    border-radius:6px; font-weight:600;
}
hr { border-color:#789F90 !important; }
[data-testid="stAlert"] { border-left:4px solid #789F90; }
</style>
"""
