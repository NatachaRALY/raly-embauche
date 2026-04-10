"""
Page 4 — Paramètres
Configuration de l'outil : clé API, email, Asana
"""
import streamlit as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_config, save_config, is_cloud

st.title("⚙️ Paramètres")
st.caption("Configuration de l'outil Raly Conseils")

_config = load_config()
_cloud = is_cloud()

if _cloud:
    st.info("☁️ **Mode cloud** — Les clés sont gérées via les secrets Streamlit. Contactez l'administrateur pour les modifier.")

# ── Clé API Anthropic ──────────────────────────────────────────────────────────
st.markdown("### 🔑 Clé API Anthropic")
st.caption("Requise pour l'extraction automatique de données depuis les documents.")

api_key_saved = _config.get("api_key", "")
if api_key_saved:
    st.success("✅ Clé API enregistrée")
    if not _cloud and st.button("Modifier la clé API"):
        st.session_state["edit_api"] = True

if not _cloud and (not api_key_saved or st.session_state.get("edit_api")):
    api_key_input = st.text_input(
        "Clé API Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Disponible sur console.anthropic.com → API Keys",
    )
    if st.button("💾 Enregistrer la clé API", type="primary"):
        if api_key_input.strip():
            _config["api_key"] = api_key_input.strip()
            save_config(_config)
            st.session_state.pop("edit_api", None)
            st.success("Clé API enregistrée !")
            st.rerun()
        else:
            st.error("La clé ne peut pas être vide.")

st.divider()

# ── Email Microsoft 365 ────────────────────────────────────────────────────────
st.markdown("### 📧 Email Microsoft 365")
st.caption("Mot de passe de natacha@ralyconseils.com pour les notifications email.")

smtp_saved = _config.get("smtp_password", "")
if smtp_saved:
    st.success("✅ Mot de passe email enregistré")
    if not _cloud and st.button("Modifier le mot de passe email"):
        st.session_state["edit_smtp"] = True

if not _cloud and (not smtp_saved or st.session_state.get("edit_smtp")):
    smtp_input = st.text_input(
        "Mot de passe Microsoft 365",
        type="password",
        placeholder="Mot de passe Outlook...",
    )
    if st.button("💾 Enregistrer le mot de passe", type="primary", key="save_smtp"):
        if smtp_input.strip():
            _config["smtp_password"] = smtp_input.strip()
            save_config(_config)
            st.session_state.pop("edit_smtp", None)
            st.success("Mot de passe enregistré !")
            st.rerun()
        else:
            st.error("Le mot de passe ne peut pas être vide.")

st.divider()

# ── Mot de passe d'accès au site ───────────────────────────────────────────────
st.markdown("### 🔒 Mot de passe d'accès")
st.caption("Protège l'accès au site interne.")

pwd_saved = _config.get("app_password", "")
if pwd_saved:
    st.success("✅ Mot de passe d'accès configuré")
    if not _cloud and st.button("Modifier le mot de passe d'accès"):
        st.session_state["edit_pwd"] = True

if not _cloud and (not pwd_saved or st.session_state.get("edit_pwd")):
    pwd_input = st.text_input(
        "Nouveau mot de passe",
        type="password",
        placeholder="Choisissez un mot de passe...",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Enregistrer le mot de passe", type="primary", key="save_pwd"):
            if pwd_input.strip():
                _config["app_password"] = pwd_input.strip()
                save_config(_config)
                st.session_state.pop("edit_pwd", None)
                st.success("Mot de passe enregistré !")
                st.rerun()
            else:
                st.error("Le mot de passe ne peut pas être vide.")
    with col2:
        if pwd_saved and st.button("🚫 Supprimer la protection", key="del_pwd"):
            _config.pop("app_password", None)
            save_config(_config)
            st.session_state.pop("edit_pwd", None)
            st.success("Protection supprimée.")
            st.rerun()

st.divider()

# ── Token Asana ────────────────────────────────────────────────────────────────
st.markdown("### ✅ Asana")
st.caption("Token d'accès personnel Asana pour les notifications et la page Soumissions.")

asana_saved = _config.get("asana_token", "")
if asana_saved:
    st.success("✅ Token Asana enregistré")
    if not _cloud and st.button("Modifier le token Asana"):
        st.session_state["edit_asana"] = True

if not _cloud and (not asana_saved or st.session_state.get("edit_asana")):
    asana_input = st.text_input(
        "Token Asana",
        type="password",
        placeholder="2/xxxxx...",
        help="app.asana.com/0/developer-console",
    )
    if st.button("💾 Enregistrer le token Asana", type="primary", key="save_asana"):
        if asana_input.strip():
            _config["asana_token"] = asana_input.strip()
            save_config(_config)
            st.session_state.pop("edit_asana", None)
            st.success("Token Asana enregistré !")
            st.rerun()
        else:
            st.error("Le token ne peut pas être vide.")
