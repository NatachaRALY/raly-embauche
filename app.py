import streamlit as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils import CSS, logo_html, load_config

st.set_page_config(
    page_title="Raly Conseils",
    page_icon="👥",
    layout="wide",
)

# ── Vérification mot de passe ──────────────────────────────────────────────────
def check_password() -> bool:
    if st.session_state.get("authentifie"):
        return True

    cfg = load_config()
    app_password = cfg.get("app_password", "")
    if not app_password:
        # Pas de mot de passe configuré → accès libre
        return True

    # Page de connexion
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(logo_html(), unsafe_allow_html=True)

    st.markdown("""
    <div style="max-width:400px;margin:80px auto 0;text-align:center;">
        <div style="font-size:2rem;margin-bottom:8px;">🔒</div>
        <div style="font-size:1.5rem;font-weight:700;color:#3F4443;">Raly Conseils</div>
        <div style="color:#789F90;margin-bottom:32px;">Outil interne — accès restreint</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        pwd = st.text_input("Mot de passe", type="password", placeholder="Entrez le mot de passe")
        if st.button("Connexion", type="primary", use_container_width=True):
            if pwd == app_password:
                st.session_state["authentifie"] = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
    return False

if not check_password():
    st.stop()

# ── Navigation ─────────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/1_Generateur_Import_Salaries.py", title="Générateur Import Salariés", icon="👥"),
    st.Page("pages/2_Formulaire_Embauche.py",        title="Formulaire Embauche",         icon="📋"),
    st.Page("pages/3_Soumissions.py",                title="Soumissions",                 icon="📥"),
    st.Page("pages/4_Parametres.py",                 title="Paramètres",                  icon="⚙️"),
])

st.markdown(CSS, unsafe_allow_html=True)
with st.sidebar:
    st.markdown(logo_html(), unsafe_allow_html=True)

pg.run()
