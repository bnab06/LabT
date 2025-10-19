import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import os
import base64

USERS_FILE = "users.json"

# -----------------------
# Traductions (FR / EN)
# -----------------------
TEXT = {
    "fr": {
        "app_title": "🔬 LabT",
        "login_title": "🔬 LabT - Connexion",
        "choose_user": "Choisir un utilisateur :",
        "password": "Mot de passe :",
        "login": "Se connecter",
        "logout": "⬅️ Déconnexion",
        "logged_as": "Vous êtes connecté en tant que",
        "manage_users": "👥 Gestion des utilisateurs",
        "action": "Action :",
        "username": "Nom d’utilisateur :",
        "role": "Rôle :",
        "password_input": "Mot de passe :",
        "validate": "Valider",
        "linearity": "📈 Courbe de linéarité",
        "conc_input": "Concentrations connues (séparées par des virgules)",
        "resp_input": "Réponses (séparées par des virgules)",
        "unknown_type": "Type d'inconnu :",
        "unknown_conc": "Concentration inconnue",
        "unknown_sig": "Signal inconnu",
        "unknown_value": "Valeur inconnue :",
        "unit": "Unité :",
        "export_pdf": "Exporter le rapport PDF",
        "sn": "📊 Calcul S/N",
        "upload_csv": "Téléverser un chromatogramme (CSV)",
        "csv_error": "CSV doit contenir les colonnes : Time et Signal",
        "sn_result": "Rapport S/N =",
        "usp_sn": "USP S/N =",
        "lod": "LOD",
        "loq": "LOQ",
        "sn_conc": "S/N en concentration",
        "usp_sn_conc": "USP S/N en concentration",
        "eq": "Équation",
        "r2": "R²",
        "add_user_success": "Utilisateur ajouté ✅",
        "modify_user_success": "Utilisateur modifié ✅",
        "delete_user_success": "Utilisateur supprimé ✅",
        "fields_required": "Tous les champs doivent être remplis !",
        "user_exists": "Utilisateur déjà existant.",
        "user_not_found": "Utilisateur introuvable.",
        "pdf_company": "Nom de la compagnie pour le rapport PDF :",
        "pdf_download": "⬇️ Télécharger le PDF",
        "log_label": "Log: LabT",
        "ok": "OK",
        "choose_option": "Choisir une option :",
        "linear_option": "Courbe de linéarité",
        "sn_option": "Calcul S/N",
        "language": "Langue / Language",
        "fr": "Français",
        "en": "English",
        "invalid_lists": "Les listes doivent avoir la même taille et ne pas être vides.",
        "error_calc": "Erreur dans les calculs :",
        "error_csv": "Erreur de lecture CSV :",
    },
    "en": {
        "app_title": "🔬 LabT",
        "login_title": "🔬 LabT - Login",
        "choose_user": "Choose a user:",
        "password": "Password:",
        "login": "Sign in",
        "logout": "⬅️ Logout",
        "logged_as": "You are logged in as",
        "manage_users": "👥 User management",
        "action": "Action:",
        "username": "Username:",
        "role": "Role:",
        "password_input": "Password:",
        "validate": "Validate",
        "linearity": "📈 Linearity curve",
        "conc_input": "Known concentrations (comma-separated)",
        "resp_input": "Responses (comma-separated)",
        "unknown_type": "Unknown type:",
        "unknown_conc": "Unknown concentration",
        "unknown_sig": "Unknown signal",
        "unknown_value": "Unknown value:",
        "unit": "Unit:",
        "export_pdf": "Export PDF report",
        "sn": "📊 Signal/Noise calculation (S/N)",
        "upload_csv": "Upload a chromatogram (CSV)",
        "csv_error": "CSV must contain columns: Time and Signal",
        "sn_result": "S/N ratio =",
        "usp_sn": "USP S/N =",
        "lod": "LOD",
        "loq": "LOQ",
        "sn_conc": "S/N in concentration",
        "usp_sn_conc": "USP S/N in concentration",
        "eq": "Equation",
        "r2": "R²",
        "add_user_success": "User added ✅",
        "modify_user_success": "User modified ✅",
        "delete_user_success": "User deleted ✅",
        "fields_required": "All fields must be filled!",
        "user_exists": "User already exists.",
        "user_not_found": "User not found.",
        "pdf_company": "Company name for PDF report:",
        "pdf_download": "⬇️ Download PDF",
        "log_label": "Log: LabT",
        "ok": "OK",
        "choose_option": "Choose an option:",
        "linear_option": "Linearity curve",
        "sn_option": "S/N calculation",
        "language": "Langue / Language",
        "fr": "Français",
        "en": "English",
        "invalid_lists": "Lists must be same length and not empty.",
        "error_calc": "Error in calculations:",
        "error_csv": "CSV read error:",
    }
}

# -----------------------
# Helpers
# -----------------------
def t(key):
    lang = st.session_state.get("lang", "fr")
    return TEXT.get(lang, TEXT["fr"]).get(key, key)

def read_csv_smart(uploaded_file):
    # Try default read, fallback to python engine sep=None
    try:
        return pd.read_csv(uploaded_file)
    except Exception:
        try:
            return pd.read_csv(uploaded_file, sep=None, engine="python")
        except Exception as e:
            raise e

# -----------------------
# Users functions
# -----------------------
def load_users():
    # defined earlier; keep same path logic
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "bb": {"password": "bb", "role": "user"},
            "user": {"password": "user", "role": "user"},
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -----------------------
# Login / Navigation
# -----------------------
def do_logout():
    st.session_state.logged_in = False
    st.session_state.current_page = None
    st.experimental_rerun()

def do_login(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"{t('logged_as')} {selected_user}")
        st.experimental_rerun()
    else:
        st.error(t("user_not_found"))

# -----------------------
# PDF (texte uniquement)
# -----------------------
def generate_pdf(title, content_text, company="", lang="fr"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    header = "LabT Report" if lang == "en" else "Rapport LabT"
    pdf.cell(0, 10, header, ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    if company:
        pdf.cell(0, 10, f"{'Company' if lang=='en' else 'Compagnie'}: {company}", ln=True)
    pdf.cell(0, 10, f"{'User' if lang=='en' else 'Utilisateur'}: {st.session_state.get('username','')}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"{'Log: LabT' if lang=='en' else 'Log : LabT'}", ln=True)
    pdf.ln(8)
    pdf.multi_cell(0, 8, content_text)
    pdf_file = f"{title}_{st.session_state.get('username','')}.pdf"
    pdf.output(pdf_file)
    return pdf_file

def offer_pdf(pdf_file):
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">{t("pdf_download")}</a>', unsafe_allow_html=True)

# -----------------------
# Admin page
# -----------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer" and not password):
        st.warning(t("fields_required"))
        return
    users = load_users()
    if action == "Ajouter":
        if username in users:
            st.warning(t("user_exists"))
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success(t("add_user_success"))
    elif action == "Modifier":
        if username not in users:
            st.warning(t("user_not_found"))
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success(t("modify_user_success"))
    elif action == "Supprimer":
        if username not in users:
            st.warning(t("user_not_found"))
        else:
            del users[username]
            save_users(users)
            st.success(t("delete_user_success"))

def manage_users_page():
    st.header(t("manage_users"))
    st.write(f"{t('logged_as')}: **{st.session_state.get('username','')}**")
    action = st.selectbox(t("action"), ["Ajouter", "Modifier", "Supprimer"] if st.session_state.get("lang","fr")=="fr" else ["Add", "Modify", "Delete"], key="admin_action")
    username = st.text_input(t("username"), key="admin_username")
    password = st.text_input(t("password_input"), key="admin_password")
    role = st.selectbox(t("role"), ["user", "admin"], key="admin_role")
    st.button(t("validate"), on_click=validate_user_action, args=(action, username, password, role))
    st.button(t("logout"), on_click=do_logout)

# -----------------------
# Linéarité
# -----------------------
def linearity_page():
    st.header(t("linearity"))
    st.write(f"{t('logged_as')}: **{st.session_state.get('username','')}**")
    conc_input = st.text_input(t("conc_input"), key="conc_input")
    resp_input = st.text_input(t("resp_input"), key="resp_input")
    unknown_type = st.selectbox(t("unknown_type"), [t("unknown_conc"), t("unknown_sig")], key="unknown_type")
    unknown_value = st.number_input(t("unknown_value"), value=0.0, step=0.1, key="unknown_value")
    unit = st.selectbox(t("unit"), ["µg/mL", "mg/L", "g/L"], index=0, key="unit")
    company_name = st.text_input(t("pdf_company"), value="", key="company_name_lin")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning(t("invalid_lists"))
                return
            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f}"
            st.session_state.slope = slope
            st.session_state.unit = unit
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope*conc+intercept, mode="lines", name=f"{t('eq')}: {eq}  ({t('r2')}: {r2:.4f})"))
            fig.update_layout(xaxis_title=f"{t('unit')} ({unit})", yaxis_title="Signal", title=t("linearity"))
            st.plotly_chart(fig)
            st.success(f"{t('eq')}: {eq}  ({t('r2')}: {r2:.4f})")
            if slope != 0:
                if unknown_type == t("unknown_conc"):
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 {t('unknown_conc')} = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 {t('unknown_sig')} = {result:.4f}")
            def export_pdf_linearity():
                lang = st.session_state.get("lang","fr")
                content = f"{t('eq')}: {eq}\\n{t('r2')}: {r2:.4f}\\n{t('unknown_type')}: {unknown_type}\\n{t('unknown_value')}: {unknown_value}\\nResult: {result:.4f} {unit if unknown_type==t('unknown_conc') else ''}"
                pdf_file = generate_pdf("Linearity_Report", content, company_name, lang=lang)
                offer_pdf(pdf_file)
            st.button(t("export_pdf"), on_click=export_pdf_linearity)
        except Exception as e:
            st.error(f"{t('error_calc')} {e}")
    st.button(t("logout"), on_click=do_logout)

# -----------------------
# S/N page
# -----------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()
    sn_ratio = signal_peak / noise if noise != 0 else np.nan
    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp if noise_usp != 0 else np.nan
    lod = 3 * noise
    loq = 10 * noise
    return sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp

def sn_page():
    st.header(t("sn"))
    st.write(f"{t('logged_as')}: **{st.session_state.get('username','')}**")
    company_name = st.text_input(t("pdf_company"), value="", key="company_name_sn")
    uploaded_file = st.file_uploader(t("upload_csv"), type=["csv"], key="sn_upload")
    if uploaded_file:
        try:
            df = read_csv_smart(uploaded_file)
            df.columns = [c.strip().lower() for c in df.columns]
            if "time" not in df.columns or "signal" not in df.columns:
                st.error(t("csv_error"))
                return
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Time", yaxis_title="Signal", title="Chromatogram")
            st.plotly_chart(fig)
            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)
            st.success(f"{t('sn_result')} {sn_ratio:.2f}")
            st.info(f"{t('usp_sn')} {sn_usp:.2f} ({'baseline noise' if st.session_state.get('lang','fr')=='en' else 'bruit baseline'} = {noise_usp:.4f})")
            st.info(f"{t('lod')}: {lod:.4f}, {t('loq')}: {loq:.4f}")
            sn_conc = sn_usp_conc = None
            if st.session_state.get("slope", None):
                slope = st.session_state.slope
                if slope != 0:
                    sn_conc = sn_ratio / slope
                    sn_usp_conc = sn_usp / slope
                    st.info(f"{t('sn_conc')}: {sn_conc:.4f} {st.session_state.unit}")
                    st.info(f"{t('usp_sn_conc')}: {sn_usp_conc:.4f} {st.session_state.unit}")
            def export_pdf_sn():
                lang = st.session_state.get("lang","fr")
                content_lines = [
                    f"{t('sn_result')} {sn_ratio:.4f}",
                    f"{t('usp_sn')} {sn_usp:.4f}",
                    f"{t('lod')}: {lod:.4f}, {t('loq')}: {loq:.4f}",
                ]
                if sn_conc is not None:
                    content_lines.append(f"{t('sn_conc')}: {sn_conc:.4f} {st.session_state.unit}")
                if sn_usp_conc is not None:
                    content_lines.append(f"{t('usp_sn_conc')}: {sn_usp_conc:.4f} {st.session_state.unit}")
                content = "\\n".join(content_lines)
                pdf_file = generate_pdf("SN_Report", content, company_name, lang=lang)
                offer_pdf(pdf_file)
            st.button(t("export_pdf"), on_click=export_pdf_sn)
        except Exception as e:
            st.error(f"{t('error_csv')} {e}")
    st.button(t("logout"), on_click=do_logout)

# -----------------------
# Main menu
# -----------------------
def main_menu():
    role = st.session_state.get("role", "")
    if role == "admin":
        manage_users_page()
    elif role == "user":
        choice = st.selectbox(t("choose_option"), [t("linear_option"), t("sn_option")], key="main_choice")
        if choice == t("linear_option"):
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Role unknown")

# -----------------------
# Boot / UI start
# -----------------------
def app_start():
    st.set_page_config(page_title="LabT", layout="centered")
    if "lang" not in st.session_state:
        st.session_state.lang = "fr"
    # language selector (top)
    col1, col2 = st.columns([3,1])
    with col1:
        st.title(t("app_title"))
    with col2:
        lang = st.selectbox(t("language"), ["Français", "English"], key="lang_select")
        st.session_state.lang = "fr" if lang.startswith("Fr") else "en"

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("---")
        st.header(t("login_title"))
        users = load_users()
        selected_user = st.selectbox(t("choose_user"), list(users.keys()), key="login_user")
        password = st.text_input(t("password"), type="password", key="login_pwd")
        st.button(t("login"), on_click=do_login, args=(selected_user, password))
        st.markdown("---")
    else:
        st.sidebar = None
        if "username" in st.session_state:
            st.write(f"{t('logged_as')}: **{st.session_state.username}**")
        main_menu()

if __name__ == "__main__":
    app_start()