# =========================
# PARTIE 1/4 - Imports & init
# =========================
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import os
import base64
from typing import Optional

st.set_page_config(page_title="LabT", page_icon="🧪", layout="wide")

USERS_FILE = "users.json"

# ---- helpers pour traduction (EN/FR) ----
def t(key: str):
    """Renvoie le texte selon la langue choisie (EN par défaut)."""
    lang = st.session_state.get("lang", "EN")
    texts = {
        "title": {"EN": "LabT - Analytical tools", "FR": "LabT - Outils d'analyse"},
        "login_title": {"EN": "Login", "FR": "Connexion"},
        "username": {"EN": "Choose user", "FR": "Choisir un utilisateur"},
        "password": {"EN": "Password", "FR": "Mot de passe"},
        "login_btn": {"EN": "Login", "FR": "Se connecter"},
        "logout_btn": {"EN": "Logout", "FR": "Déconnexion"},
        "admin_panel": {"EN": "Admin panel", "FR": "Panneau admin"},
        "linearity": {"EN": "Linearity", "FR": "Linéarité"},
        "sn": {"EN": "Signal-to-Noise (S/N)", "FR": "Signal/Bruit (S/N)"},
        "company_required": {"EN": "Please enter a company name before exporting.", "FR": "Veuillez saisir le nom de la compagnie avant d'exporter."},
        "csv_time_signal": {"EN": "CSV must contain 'Time' and 'Signal' columns.", "FR": "Le CSV doit contenir les colonnes 'Time' et 'Signal'."},
        "csv_conc_resp": {"EN": "CSV must contain 'Concentration' and 'Response' columns.", "FR": "Le CSV doit contenir les colonnes 'Concentration' et 'Response'."},
    }
    return texts.get(key, {}).get(lang, key)

# ---- initialisation de st.session_state ----
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = None
if "current_page" not in st.session_state:
    st.session_state.current_page = None
if "slope" not in st.session_state:
    st.session_state.slope = None
if "unit" not in st.session_state:
    st.session_state.unit = "µg/mL"
if "lang" not in st.session_state:
    st.session_state.lang = "EN"
# =========================
# PARTIE 2/4 - Authentication & user management
# =========================

# ---- I/O users.json ----
def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        default = {
            "admin": {"password": "admin", "role": "admin"},
            "user": {"password": "user", "role": "user"}
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ---- Login / logout ----
def login_action(selected_user: str, password: str):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user].get("role", "user")
        st.success(f"{'Connexion réussie' if st.session_state.lang=='FR' else 'Login successful'} ✅")
    else:
        st.error("Nom d’utilisateur ou mot de passe incorrect ❌" if st.session_state.lang=="FR" else "Invalid username or password ❌")

def logout_action():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = None
    st.session_state.current_page = None

# ---- Login UI ----
def login_page():
    st.title(t("login_title"))
    # langue (EN par défaut)
    lang_choice = st.selectbox("Language / Langue", ["EN", "FR"], index=0 if st.session_state.lang=="EN" else 1, key="lang_login")
    st.session_state.lang = lang_choice

    users = load_users()
    selected_user = st.selectbox(f"{t('username')} :", list(users.keys()), key="login_user_select")
    password = st.text_input(f"{t('password')} :", type="password", key="login_password_input")
    if st.button(f"{t('login_btn')}", key="login_button"):
        login_action(selected_user, password)

    st.markdown("---")
    st.caption("Default accounts: admin/admin, user/user" if st.session_state.lang=="EN" else "Comptes par défaut : admin/admin, user/user")
# =========================
# PARTIE 3/4 - Admin, Linearity & PDF
# =========================

# ---- Admin management UI ----
def validate_user_action(action: str, username: str, password: str, role: str):
    users = load_users()
    if action == "Add":
        if not username or not password:
            st.warning("All fields required / Tous les champs sont requis")
            return
        if username in users:
            st.warning("User exists / Utilisateur déjà existant")
            return
        users[username] = {"password": password, "role": role}
        save_users(users)
        st.success("User added ✅ / Utilisateur ajouté ✅")
    elif action == "Edit":
        if username not in users:
            st.warning("User not found / Utilisateur introuvable")
            return
        if password:
            users[username]["password"] = password
        users[username]["role"] = role
        save_users(users)
        st.success("User updated ✅ / Utilisateur modifié ✅")
    elif action == "Delete":
        if username not in users:
            st.warning("User not found / Utilisateur introuvable")
            return
        del users[username]
        save_users(users)
        st.success("User deleted ✅ / Utilisateur supprimé ✅")

def manage_users_page():
    st.header(t("admin_panel"))
    st.write(f"{'Logged in as' if st.session_state.lang=='EN' else 'Connecté en tant que'}: **{st.session_state.username}**")
    action = st.selectbox("Action / Action", ["Add", "Edit", "Delete"], key="admin_action_select")
    username = st.text_input("Username / Nom d'utilisateur", key="admin_username_input")
    password = st.text_input("Password / Mot de passe", key="admin_password_input")
    role = st.selectbox("Role / Rôle", ["user", "admin"], key="admin_role_select")
    if st.button("Confirm / Confirmer", key="admin_confirm_btn"):
        validate_user_action(action, username, password, role)
    if st.button(t("logout_btn"), key="admin_logout_btn"):
        logout_action()

# ---- PDF helper (texte uniquement) ----
def generate_text_pdf(title: str, content: str, company: str) -> Optional[str]:
    if not company or not company.strip():
        st.warning(t("company_required"))
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report / Rapport LabT", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"{'Company' if st.session_state.lang=='EN' else 'Entreprise'}: {company}", ln=True)
    pdf.cell(0, 8, f"{'User' if st.session_state.lang=='EN' else 'Utilisateur'}: {st.session_state.username}", ln=True)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 8, "App: LabT", ln=True)
    pdf.ln(6)
    pdf.multi_cell(0, 7, content)
    filename = f"{title}_{st.session_state.username}.pdf"
    pdf.output(filename)
    return filename

def download_pdf_button(filepath: str):
    if not filepath:
        return
    with open(filepath, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{os.path.basename(filepath)}">⬇️ {"Download PDF" if st.session_state.lang=="EN" else "Télécharger le PDF"}</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---- Linearity page (manual inputs OR CSV) ----
def linearity_page():
    st.header(t("linearity"))
    st.write(f"{'Logged in as' if st.session_state.lang=='EN' else 'Connecté en tant que'}: **{st.session_state.username}**")

    # Choose input mode
    mode = st.selectbox("Input mode / Mode d'entrée", ["Manual / Manuel", "CSV"], key="linearity_mode")
    conc = resp = None
    if mode.startswith("Manual"):
        conc_str = st.text_input("Concentrations (comma-separated) / Concentrations (séparées par des virgules)", key="linearity_conc_input")
        resp_str = st.text_input("Responses (comma-separated) / Réponses (séparées par des virgules)", key="linearity_resp_input")
        if conc_str and resp_str:
            try:
                conc = np.array([float(x.strip()) for x in conc_str.split(",") if x.strip() != ""])
                resp = np.array([float(x.strip()) for x in resp_str.split(",") if x.strip() != ""])
            except Exception as e:
                st.error("Invalid numeric input / Entrée numérique invalide")
                return
    else:
        uploaded = st.file_uploader("Upload CSV with Concentration,Response columns / Importer CSV", type=["csv"], key="linearity_csv")
        if uploaded:
            try:
                dfcsv = pd.read_csv(uploaded)
                cols = [c.lower() for c in dfcsv.columns]
                if "concentration" in cols and ("response" in cols or "signal" in cols):
                    # pick matching names
                    conc = dfcsv.iloc[:, cols.index("concentration")].to_numpy(dtype=float)
                    # prefer 'response' else 'signal'
                    resp_col = "response" if "response" in cols else "signal"
                    resp = dfcsv.iloc[:, cols.index(resp_col)].to_numpy(dtype=float)
                else:
                    st.error(t("csv_conc_resp"))
                    return
            except Exception as e:
                st.error(f"CSV read error: {e}")
                return

    # unit selection
    unit = st.selectbox("Unit / Unité", ["µg/mL", "mg/L", "g/L"], key="linearity_unit_select")
    st.session_state.unit = unit

    # unknown type and value
    unknown_type = st.selectbox("Unknown type / Type d'inconnu", ["Concentration unknown / Concentration inconnue", "Signal unknown / Signal inconnu"], key="linearity_unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue", value=0.0, step=0.1, key="linearity_unknown_value")

    if conc is not None and resp is not None:
        if len(conc) != len(resp) or len(conc) == 0:
            st.error("Lists length mismatch / Longueur différente des listes")
            return
        # compute regression
        slope, intercept = np.polyfit(conc, resp, 1)
        r2 = np.corrcoef(conc, resp)[0,1]**2
        eq_text = f"y = {slope:.6f}x + {intercept:.6f}   (R² = {r2:.4f})"
        st.success(f"Equation: {eq_text}")
        st.session_state.slope = slope

        # plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
        fit_y = slope * np.array(conc) + intercept
        fig.add_trace(go.Scatter(x=conc, y=fit_y, mode="lines", name="Fit"))
        fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal/Response", title="Linearity Plot")
        st.plotly_chart(fig, use_container_width=True)

        # compute unknown
        if slope != 0:
            if unknown_type.startswith("Concentration"):
                result_conc = (unknown_value - intercept) / slope
                st.info(f"{'Unknown concentration' if st.session_state.lang=='EN' else 'Concentration inconnue'} = {result_conc:.6f} {unit}")
                result_display = f"{result_conc:.6f} {unit}"
            else:
                result_signal = slope * unknown_value + intercept
                st.info(f"{'Unknown signal' if st.session_state.lang=='EN' else 'Signal inconnu'} = {result_signal:.6f}")
                result_display = f"{result_signal:.6f}"

        # export PDF
        company = st.text_input("Company name for PDF / Nom de la compagnie", value="", key="linearity_company_input")
        if st.button("Export Linearity PDF / Exporter PDF (Linearity)", key="linearity_export_btn"):
            if not company.strip():
                st.warning(t("company_required"))
            else:
                content = f"Linearity report\nEquation: {eq_text}\nUnknown type: {unknown_type}\nUnknown value: {unknown_value}\nResult: {result_display}\n"
                pdf_file = generate_text_pdf("Linearity_Report", content, company)
                if pdf_file:
                    download_pdf_button(pdf_file)
# =========================
# PARTIE 4/4 - S/N, LOD/LOQ, menu principal
# =========================

# ---- S/N computation helpers ----
def compute_sn_from_signal(signal_array: np.ndarray):
    """Compute classic and USP S/N and noise estimates."""
    if len(signal_array) == 0:
        return np.nan, np.nan, np.nan, np.nan
    peak = np.max(signal_array)
    # baseline region: first 10% of data (or at least 1 point)
    n_base = max(1, int(0.1 * len(signal_array)))
    baseline = signal_array[:n_base]
    noise_std = np.std(baseline, ddof=1) if len(baseline) > 1 else np.std(signal_array, ddof=1)
    sn_classic = peak / noise_std if noise_std != 0 else np.nan
    # USP S/N often uses baseline region noise as well
    sn_usp = peak / noise_std if noise_std != 0 else np.nan
    return sn_classic, sn_usp, peak, noise_std

# ---- S/N page ----
def sn_page():
    st.header(t("sn"))
    st.write(f"{'Logged in as' if st.session_state.lang=='EN' else 'Connecté en tant que'}: **{st.session_state.username}**")

    uploaded = st.file_uploader("Upload chromatogram CSV (Time, Signal) / Importer CSV (Time, Signal)", type=["csv"], key="sn_csv")
    use_linearity = st.checkbox("Use linearity slope to convert LOD/LOQ to concentration / Utiliser la pente pour LOD/LOQ", key="sn_use_linearity")

    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            cols_lower = [c.lower() for c in df.columns]
            # find time/signal columns (case-insensitive)
            time_col = next((c for c in df.columns if 'time' in c.lower()), None)
            signal_col = next((c for c in df.columns if 'signal' in c.lower() or 'response' in c.lower()), None)
            if not time_col or not signal_col:
                st.error(t("csv_time_signal"))
                return
            df = df[[time_col, signal_col]].rename(columns={time_col: "Time", signal_col: "Signal"})
            st.dataframe(df.head())

            # compute S/N
            sn_classic, sn_usp, peak, noise_std = compute_sn_from_signal(df["Signal"].to_numpy())
            st.success(f"{'Classic S/N' if st.session_state.lang=='EN' else 'S/N classique'} = {sn_classic:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f}   ({'baseline noise' if st.session_state.lang=='EN' else 'bruit baseline'} = {noise_std:.6f})")

            # LOD/LOQ in signal units
            lod_signal = 3.3 * noise_std
            loq_signal = 10 * noise_std
            st.write(f"LOD (signal units): {lod_signal:.6f}")
            st.write(f"LOQ (signal units): {loq_signal:.6f}")

            # convert to concentration if requested & slope available
            lod_conc = loq_conc = None
            if use_linearity and st.session_state.slope and st.session_state.slope != 0:
                lod_conc = lod_signal / st.session_state.slope
                loq_conc = loq_signal / st.session_state.slope
                st.info(f"LOD (concentration): {lod_conc:.6f} {st.session_state.unit}")
                st.info(f"LOQ (concentration): {loq_conc:.6f} {st.session_state.unit}")
            else:
                if use_linearity:
                    st.warning("No slope available from linearity yet. Compute a linearity first to enable conversion." if st.session_state.lang=="EN" else "Aucune pente disponible. Calculez d'abord la linéarité pour activer la conversion.")

            # save results in session for PDF
            st.session_state.sn_results = {
                "sn_classic": float(sn_classic) if not np.isnan(sn_classic) else None,
                "sn_usp": float(sn_usp) if not np.isnan(sn_usp) else None,
                "peak": float(peak),
                "noise": float(noise_std),
                "lod_signal": float(lod_signal),
                "loq_signal": float(loq_signal),
                "lod_conc": float(lod_conc) if lod_conc is not None else None,
                "loq_conc": float(loq_conc) if loq_conc is not None else None,
            }

            # Plot
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Time"], y=df["Signal"], mode="lines", name="Signal"))
            st.plotly_chart(fig, use_container_width=True)

            # PDF export UI
            company = st.text_input("Company name for PDF / Nom de la compagnie (required)", value="", key="sn_company_input")
            if st.button("Export S/N PDF / Exporter le PDF (S/N)", key="sn_export_btn"):
                if not company.strip():
                    st.warning(t("company_required"))
                else:
                    # prepare content
                    res = st.session_state.get("sn_results", {})
                    content_lines = []
                    content_lines.append("S/N Report" if st.session_state.lang=="EN" else "Rapport S/N")
                    content_lines.append(f"Peak signal: {res.get('peak')}")
                    content_lines.append(f"Noise (std): {res.get('noise'):.6f}")
                    content_lines.append(f"Classic S/N: {res.get('sn_classic')}")
                    content_lines.append(f"USP S/N: {res.get('sn_usp')}")
                    content_lines.append(f"LOD (signal): {res.get('lod_signal'):.6f}")
                    content_lines.append(f"LOQ (signal): {res.get('loq_signal'):.6f}")
                    if res.get('lod_conc') is not None:
                        content_lines.append(f"LOD (conc): {res.get('lod_conc'):.6f} {st.session_state.unit}")
                        content_lines.append(f"LOQ (conc): {res.get('loq_conc'):.6f} {st.session_state.unit}")
                    content = "\n".join(content_lines)
                    pdf_file = generate_text_pdf("SN_Report", content, company)
                    if pdf_file:
                        download_pdf_button(pdf_file)

        except Exception as e:
            st.error(f"CSV read error: {e}")

# ---- Main menu (role-based) ----
def main_menu():
    st.title(t("title"))
    # language selector in top-right area
    with st.sidebar:
        lang_choice = st.selectbox("Language / Langue", ["EN", "FR"], index=0 if st.session_state.lang=="EN" else 1, key="lang_sidebar")
        st.session_state.lang = lang_choice

    if not st.session_state.logged_in:
        login_page()
        return

    # show top info + logout
    st.sidebar.markdown(f"**{st.session_state.username}**")
    if st.sidebar.button(t("logout_btn"), key="logout_sidebar"):
        logout_action()
        st.experimental_rerun()

    # role-based navigation
    pages = []
    if st.session_state.role == "admin":
        pages.append(("Admin", manage_users_page))
    pages.extend([
        (t("linearity"), linearity_page),
        (t("sn"), sn_page),
    ])

    page_labels = [p[0] for p in pages]
    choice = st.selectbox("Page / Page", page_labels, key="main_page_select")
    # execute selected page function
    for label, func in pages:
        if label == choice:
            func()
            break

# ---- run app ----
if __name__ == "__main__":
    main_menu()
