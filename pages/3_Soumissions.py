"""
Page 3 — Soumissions reçues (depuis Asana)
Consultation des fiches envoyées via le formulaire cloud + génération XLS Silae
"""
import streamlit as st
import json
import xlwt
import io
import requests
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import CSS, logo_html, load_config

ASANA_PROJECT_GID = "1213986643545923"
ASANA_BASE        = "https://app.asana.com/api/1.0"

st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.divider()
    st.markdown("### 📥 Soumissions reçues")
    st.caption("Fiches reçues via le formulaire client · génération XLS Silae")

st.markdown("""
<div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
    <div style="background:#789F90;width:6px;height:48px;border-radius:3px;"></div>
    <div>
        <div style="font-size:1.8rem;font-weight:700;color:#3F4443;line-height:1.1;">Soumissions reçues</div>
        <div style="font-size:1rem;color:#789F90;font-weight:500;">Fiches d'embauche · Raly Conseils</div>
    </div>
</div>
""", unsafe_allow_html=True)


def get_asana_token() -> str:
    return load_config().get("asana_token", "")


def fetch_tasks(token: str, completed: bool = False) -> list[dict]:
    """Récupère les tâches du projet Asana."""
    # completed_since=now → tâches incomplètes uniquement
    # completed_since=2000-01-01 → toutes les tâches (incomplètes + complétées)
    params = {
        "opt_fields":      "gid,name,notes,completed,created_at",
        "completed_since": "2000-01-01T00:00:00Z" if completed else "now",
        "limit":           100,
    }
    r = requests.get(
        f"{ASANA_BASE}/projects/{ASANA_PROJECT_GID}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=15,
    )
    if r.status_code != 200:
        return []
    return r.json().get("data", [])


def parse_task_data(task: dict) -> dict | None:
    """Extrait le JSON structuré depuis les notes de la tâche."""
    notes = task.get("notes", "")
    marker = "---JSON---"
    if marker not in notes:
        return None
    try:
        json_str = notes.split(marker, 1)[1].strip()
        return json.loads(json_str)
    except Exception:
        return None


def complete_task(token: str, gid: str) -> tuple[bool, str]:
    """Marque une tâche Asana comme terminée."""
    try:
        r = requests.put(
            f"{ASANA_BASE}/tasks/{gid}",
            headers={"Authorization": f"Bearer {token}"},
            json={"data": {"completed": True}},
            timeout=15,
        )
        return r.status_code == 200, r.text[:200] if r.status_code != 200 else ""
    except Exception as e:
        return False, str(e)


def reopen_task(token: str, gid: str) -> tuple[bool, str]:
    """Rouvre une tâche Asana."""
    try:
        r = requests.put(
            f"{ASANA_BASE}/tasks/{gid}",
            headers={"Authorization": f"Bearer {token}"},
            json={"data": {"completed": False}},
            timeout=15,
        )
        return r.status_code == 200, r.text[:200] if r.status_code != 200 else ""
    except Exception as e:
        return False, str(e)


def fetch_attachments(token: str, task_gid: str) -> list[dict]:
    """Récupère les pièces jointes d'une tâche Asana."""
    r = requests.get(
        f"{ASANA_BASE}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        params={"parent": task_gid, "opt_fields": "name,download_url"},
        timeout=15,
    )
    if r.status_code != 200:
        return []
    return r.json().get("data", [])


# ── Mapping form → Silae ───────────────────────────────────────────────────────
def form_to_silae(d: dict) -> dict:
    silae = {}
    def s(k): return str(d.get(k, "") or "").strip()

    if s("nom"):            silae["Nom usuel"]                       = s("nom")
    nom_naiss = s("nom_naissance") or s("nom")  # fallback : nom usuel si nom de naissance vide
    if nom_naiss:           silae["Nom de naissance"]                = nom_naiss
    if s("prenom"):         silae["Prénom (salarié)"]                = s("prenom")
    if s("date_naissance"): silae["Date de naissance (salarié)"]     = s("date_naissance")
    if s("lieu_naissance"): silae["Commune de naissance"]            = s("lieu_naissance")

    nss_raw = s("nss").replace(" ", "").replace("-", "")
    if len(nss_raw) >= 13:
        silae["Numéro de sécurité sociale"] = nss_raw[:13]
        if len(nss_raw) == 15:
            silae["Clé numéro sécurité sociale"] = nss_raw[13:15]
            dept = nss_raw[5:7]
            silae["Département de naissance"] = dept
            silae["Etranger ?"] = "Oui" if dept == "99" else "Non"

    pays = s("pays_naissance").upper()
    if pays:
        codes = {"FRANCE": "FR", "MAROC": "MA", "ALGÉRIE": "DZ", "ALGERIE": "DZ",
                 "TUNISIE": "TN", "SÉNÉGAL": "SN", "SENEGAL": "SN", "BELGIQUE": "BE",
                 "ESPAGNE": "ES", "ITALIE": "IT", "PORTUGAL": "PT", "CAMEROUN": "CM",
                 "CÔTE D'IVOIRE": "CI", "MALI": "ML", "TURQUIE": "TR", "CHINE": "CN"}
        silae["Code pays de naissance"] = codes.get(pays, pays[:2])

    nat = s("nationalite").upper()
    if nat:
        codes_nat = {"FRANÇAISE": "FR", "MAROCAINE": "MA", "ALGÉRIENNE": "DZ", "ALGERIENNE": "DZ",
                     "TUNISIENNE": "TN", "BELGE": "BE", "ESPAGNOLE": "ES", "ITALIENNE": "IT",
                     "PORTUGAISE": "PT", "TURQUE": "TR", "CHINOISE": "CN"}
        silae["Code pays nationalité"] = codes_nat.get(nat, nat[:2])

    sit_map = {"Célibataire": "10", "Vie maritale": "20", "Pacsé(e)": "30",
               "Marié(e)": "40", "Divorcé(e)": "60", "Veuf/Veuve": "70"}
    if s("situation_familiale") in sit_map:
        silae["Situation familiale"] = sit_map[s("situation_familiale")]

    if s("adresse_numero"):    silae["Numéro de la voie"]     = s("adresse_numero")
    if s("adresse_complement"):silae["Complément d'adresse"]  = s("adresse_complement")
    if s("ville"):             silae["Ville"]                 = s("ville")
    if s("code_postal"):       silae["Code postal"]           = s("code_postal")
    silae["Code pays"] = "FR"

    if s("email"): silae["E-mail"] = s("email")

    if s("date_embauche"):
        silae["Date d'entrée dans l'entreprise"] = s("date_embauche")
        silae["Date début"] = s("date_embauche")

    contrat_map = {"CDI": "01", "CDD": "02"}
    if s("type_contrat") in contrat_map:
        silae["Code contrat"] = contrat_map[s("type_contrat")]

    if s("date_fin_cdd"): silae["Date fin"]     = s("date_fin_cdd")
    if s("motif_cdd"):    silae["Motif du CDD"] = s("motif_cdd")

    if s("emploi"):     silae["Emploi"]                   = s("emploi")
    if s("convention"): silae["CCN"]                      = s("convention")
    if s("salaire"):    silae["Salaire de base (emploi)"] = s("salaire")

    nb_h = s("nb_heures").replace("h", "").replace("H", "").strip()
    if nb_h.replace(".", "").isdigit():
        silae["Nb heures"]    = nb_h
        silae["Code salaire"] = "Mensuel"

    silae["Mode de paiement"] = "Virement"
    return silae


def generate_xls(data: dict) -> bytes:
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Import Salariés")
    hdr_style = xlwt.easyxf(
        "font: bold true, colour white; pattern: pattern solid, fore_colour dark_red; alignment: horizontal centre;"
    )
    val_style = xlwt.easyxf("alignment: horizontal left;")
    for col, (k, v) in enumerate(data.items()):
        ws.write(0, col, k, hdr_style)
        ws.write(1, col, str(v) if v is not None else "", val_style)
        ws.col(col).width = max(len(str(k)), len(str(v or ""))) * 300 + 500
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Chargement des tâches Asana ────────────────────────────────────────────────
token = get_asana_token()

if not token:
    st.warning("Token Asana non configuré. Ajoutez-le dans la sidebar du Générateur.")
    st.stop()

col_refresh, col_filtre = st.columns([1, 3])
with col_refresh:
    if st.button("🔄 Actualiser"):
        st.rerun()
with col_filtre:
    afficher_traitees = st.toggle("Afficher les soumissions traitées", value=False)

try:
    taches = fetch_tasks(token, completed=False)
    if afficher_traitees:
        taches += fetch_tasks(token, completed=True)
except Exception as e:
    st.error(f"Erreur Asana : {e}")
    st.stop()

# Filtrer celles qui ont des données JSON
soumissions = []
for t in taches:
    d = parse_task_data(t)
    if d:
        soumissions.append((t, d))

if not soumissions:
    st.info("Aucune soumission reçue pour le moment.")
    st.stop()

en_attente  = [(t, d) for t, d in soumissions if not t.get("completed")]
traitees    = [(t, d) for t, d in soumissions if t.get("completed")]

st.markdown(f"**{len(en_attente)} en attente** · {len(traitees)} traitée(s)")
st.divider()


def afficher_soumission(task: dict, d: dict, est_traitee: bool):
    label = f"{'✅ ' if est_traitee else ''}**{d.get('entreprise','?')}** — {d.get('prenom','?')} {d.get('nom','?')} · _{d.get('soumis_le','?')}_ · Réf. {d.get('id','?')}"

    with st.expander(label, expanded=not est_traitee):
        tabs = st.tabs(["📋 Fiche", "⚙️ Données Silae", "📎 Documents"])

        with tabs[0]:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Entreprise**")
                st.write(d.get("entreprise", ""))
                st.write(f"SIRET : {d.get('siret','—')}")
                st.write(f"DPAE : {d.get('dpae','—')} · Contrat : {d.get('contrat_a_etablir','—')}")
                st.divider()
                st.markdown("**Salarié**")
                st.write(f"{d.get('prenom','')} **{d.get('nom','')}**")
                if d.get("nom_naissance"): st.write(f"Nom naissance : {d['nom_naissance']}")
                st.write(f"Né(e) le {d.get('date_naissance','—')} à {d.get('lieu_naissance','—')} ({d.get('pays_naissance','—')})")
                st.write(f"Nationalité : {d.get('nationalite','—')}")
                if d.get("nss"):   st.write(f"N°SS : {d['nss']}")
                if d.get("email"): st.write(f"Email : {d['email']}")
            with col2:
                st.markdown("**Contrat**")
                st.write(f"Entrée : {d.get('date_embauche','—')} {d.get('heure_embauche','')}")
                st.write(f"Type : {d.get('type_contrat','—')}")
                if d.get("date_fin_cdd"): st.write(f"Fin CDD : {d['date_fin_cdd']}")
                if d.get("motif_cdd"):    st.write(f"Motif CDD : {d['motif_cdd']}")
                st.write(f"Heures : {d.get('nb_heures','—')}")
                st.divider()
                st.markdown("**Poste & Rémunération**")
                st.write(f"Emploi : {d.get('emploi','—')} ({d.get('categorie','—')})")
                st.write(f"Convention : {d.get('convention','—')}")
                if d.get("coefficient"): st.write(f"Coeff. : {d['coefficient']}")
                st.write(f"Salaire brut : {d.get('salaire','—')} €")
                st.divider()
                st.markdown("**Avantages**")
                st.write(f"Mutuelle : {d.get('mutuelle','—')}")
                st.write(f"Transport : {d.get('transport','—')}")

            if d.get("horaires"):
                st.markdown("**Horaires détaillés**")
                rows = [f"{j} : {h.get('de1','')}–{h.get('a1','')} / {h.get('de2','')}–{h.get('a2','')}"
                        for j, h in d["horaires"].items()]
                st.write(" · ".join(rows))

        with tabs[1]:
            silae_data = form_to_silae(d)
            col1, col2, col3 = st.columns(3)
            for i, (k, v) in enumerate(silae_data.items()):
                with [col1, col2, col3][i % 3]:
                    st.metric(label=k, value=v)

        with tabs[2]:
            attachments = fetch_attachments(token, task["gid"])
            if attachments:
                for att in attachments:
                    col_nom, col_dl = st.columns([4, 1])
                    col_nom.write(att["name"])
                    if att.get("download_url"):
                        try:
                            r = requests.get(att["download_url"], timeout=30)
                            col_dl.download_button(
                                label="⬇️",
                                data=r.content,
                                file_name=att["name"],
                                key=f"att_{task['gid']}_{att['gid']}",
                            )
                        except Exception:
                            col_dl.write("—")
            else:
                st.info("Aucun document joint à cette soumission.")

        # ── Matricule + téléchargement XLS (hors onglets pour éviter la perte de valeur) ──
        st.divider()
        mat_key = f"matricule_{task['gid']}"
        silae_data = form_to_silae(d)
        col_mat, col_dl = st.columns([2, 3])
        with col_mat:
            st.text_input(
                "Matricule Silae *",
                placeholder="Ex : 00042",
                key=mat_key,
                help="Identifiant unique du salarié (obligatoire pour l'import Silae)",
            )
        with col_dl:
            matricule_val = st.session_state.get(mat_key, "")
            silae_data_final = {"Matricule": matricule_val, **silae_data}
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"import_silae_{d.get('nom','').upper()}_{d.get('prenom','').capitalize()}_{ts}.xls"
            st.write("")  # alignement vertical
            st.download_button(
                label="📥  Télécharger le fichier XLS Silae",
                data=generate_xls(silae_data_final),
                file_name=filename,
                mime="application/vnd.ms-excel",
                use_container_width=True,
                key=f"dl_{task['gid']}",
            )

        st.divider()
        if not est_traitee:
            if st.button("✅ Marquer comme traitée", key=f"done_{task['gid']}"):
                ok, err = complete_task(token, task["gid"])
                if ok:
                    st.rerun()
                else:
                    st.error(f"Erreur : {err}")
        else:
            if st.button("↩️ Rouvrir", key=f"reopen_{task['gid']}"):
                ok, err = reopen_task(token, task["gid"])
                if ok:
                    st.rerun()
                else:
                    st.error(f"Erreur : {err}")


for task, d in en_attente:
    afficher_soumission(task, d, est_traitee=False)

if afficher_traitees and traitees:
    st.divider()
    st.markdown("#### Soumissions traitées")
    for task, d in traitees:
        afficher_soumission(task, d, est_traitee=True)
