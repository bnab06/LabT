# app.py
import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from fpdf import FPDF
import io
from PIL import Image
import matplotlib.pyplot as plt

# -------------------------
# Configuration
# -------------------------
USERS_FILE = "users.json"
LOGO_FILE = "labt_logo.png"  # put your logo file here
DEFAULT_LANGUAGE = "en"      # "en" by default per your request

# -------------------------
# Simple translations
# -------------------------
TXT = {
    "en": {
        "app_title": "LabT",
        "login_title": "🔬 LabT - Login",
        "choose_user": "Choose user",
        "password": "Password",
        "login_btn": "Log in",
        "logout": "Log out",
        "login_success": "Login successful ✅ / You are logged in as",
        "login_error": "Wrong username or password ❌",
        "admin_title": "👥 User Management (admin)",
        "action": "Action",
        "add": "Add / Ajouter",
        "modify": "Modify / Modifier",
        "delete": "Delete / Supprimer",
        "username": "Username",
        "role": "Role",
        "role_user": "user",
        "role_admin": "admin",
        "validate": "Validate",
        "linearity_title": "📈 Linearity",
        "conc_input": "Known concentrations (comma-separated)",
        "resp_input": "Responses (comma-separated)",
        "unknown_type": "Unknown type",
        "unknown_conc": "Unknown concentration",
        "unknown_signal": "Unknown signal",
        "unknown_value": "Unknown value",
        "unit": "Concentration unit",
        "plot_curve": "Plot curve",
        "equation": "Equation",
        "r2": "R²",
        "sn_title": "📊 Signal-to-Noise (S/N)",
        "upload_chrom": "Upload chromatogram (CSV / PNG / PDF)",
        "sn_result": "S/N result",
        "sn_usp": "USP S/N",
        "lod": "LOD",
        "loq": "LOQ",
        "export_pdf": "Export report PDF",
        "company_name": "Company name for PDF",
        "fill_company": "Please enter the company name before exporting.",
        "download_pdf": "⬇️ Download PDF",
        "user_logged_as": "You are logged in as",
        "change_password": "Change my password",
        "new_password": "New password",
        "password_changed": "Password changed ✅",
        "csv_cols_error": "CSV must contain columns: Time and Signal",
        "choose_option": "Choose option",
        "linearity_option": "Linearity",
        "sn_option": "S/N calculation",
        "back_menu": "Back to main menu",
        "select_language": "Language / Langue",
    },
    "fr": {
        "app_title": "LabT",
        "login_title": "🔬 LabT - Connexion",
        "choose_user": "Choisir un utilisateur",
        "password": "Mot de passe",
        "login_btn": "Se connecter",
        "logout": "Déconnexion",
        "login_success": "Connexion réussie ✅ / Vous êtes connecté en tant que",
        "login_error": "Nom d’utilisateur ou mot de passe incorrect ❌",
        "admin_title": "👥 Gestion des utilisateurs (admin)",
        "action": "Action",
        "add": "Ajouter",
        "modify": "Modifier",
        "delete": "Supprimer",
        "username": "Nom d’utilisateur",
        "role": "Rôle",
        "role_user": "user",
        "role_admin": "admin",
        "validate": "Valider",
        "linearity_title": "📈 Courbe de linéarité",
        "conc_input": "Concentrations connues (séparées par des virgules)",
        "resp_input": "Réponses (séparées par des virgules)",
        "unknown_type": "Type d'inconnu",
        "unknown_conc": "Concentration inconnue",
        "unknown_signal": "Signal inconnu",
        "unknown_value": "Valeur inconnue",
        "unit": "Unité de concentration",
        "plot_curve": "Tracer la courbe",
        "equation": "Équation",
        "r2": "R²",
        "sn_title": "📊 Rapport signal/bruit (S/N)",
        "upload_chrom": "Téléverser chromatogramme (CSV / PNG / PDF)",
        "sn_result": "Rapport S/N",
        "sn_usp": "USP S/N",
        "lod": "LOD",
        "loq": "LOQ",
        "export_pdf": "Exporter rapport PDF",
        "company_name": "Nom de la compagnie pour le PDF",
        "fill_company": "Veuillez saisir le nom de la compagnie avant l'export.",
        "download_pdf": "⬇️ Télécharger le PDF",
        "user_logged_as": "Vous êtes connecté en tant que",
        "change_password": "Changer mon mot de passe",
        "new_password": "Nouveau mot de passe",
        "password_changed": "Mot de passe modifié ✅",
        "csv_cols_error": "CSV doit contenir les colonnes : Time et Signal",
        "choose_option": "Choisir une option",
        "linearity_option": "Courbe de linéarité",
        "sn_option": "Calcul S/N",
        "back_menu": "Retour au menu principal",
        "select_language": "Langue / Language",
    },
}

# -------------------------
# Utilities: load/save users (case-insensitive usernames)
# -------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "bb": {"password": "bb", "role": "user"},
            "user": {"password": "user", "role": "user"},
        }
        save_users(users)
    with open(USERS_FILE, "r") as f:
        raw = json.load(f)
    # normalize keys to lowercase for case-insensitive matching
    return {k.lower(): v for k, v in raw.items()}

def save_users(users):
    # preserve keys as stored (lowercase). Simple approach.
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------
# PDF generation (text + images)
# -------------------------
def generate_pdf(title, content_lines, image_bytes=None, company="", username=""):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # header logo if exists
    if os.path.exists(LOGO_FILE):
        try:
            pdf.image(LOGO_FILE, x=10, y=8, w=25)
        except Exception:
            pass
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "LabT", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Company: {company}", ln=True)
    pdf.cell(0, 6, f"User: {username}", ln=True)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 6, f"App: LabT", ln=True)
    pdf.ln(6)
    pdf.set_font("Arial", "", 10)
    for line in content_lines:
        pdf.multi_cell(0, 6, str(line))
    # add image if provided
    if image_bytes:
        try:
            # write image bytes to a temp buffer and add
            tmp = "temp_plot.png"
            with open(tmp, "wb") as f:
                f.write(image_bytes)
            pdf.ln(4)
            pdf.image(tmp, w=170)
            try:
                os.remove(tmp)
            except Exception:
                pass
        except Exception:
            pass
    out_name = f"{title}_{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(out_name)
    return out_name

# -------------------------
# Session initialization
# -------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "page" not in st.session_state:
    st.session_state.page = None
if "language" not in st.session_state:
    st.session_state.language = DEFAULT_LANGUAGE
if "linearity" not in st.session_state:
    st.session_state.linearity = {}  # will store slope/intercept/unit etc.

# small helper for translations
def t(key):
    lang = st.session_state.language if st.session_state.language in TXT else "en"
    return TXT[lang].get(key, key)

# -------------------------
# Authentication
# -------------------------
def login_action(user_input, password_input):
    users = load_users()
    user_lower = user_input.strip().lower()
    if user_lower in users and users[user_lower]["password"] == password_input:
        st.session_state.logged_in = True
        st.session_state.username = user_lower
        st.session_state.role = users[user_lower]["role"]
        # default page depending on role
        st.session_state.page = "admin" if st.session_state.role == "admin" else "menu"
        # no rerun call inside callback; Streamlit will re-run automatically
    else:
        st.error(t("login_error"))

def logout_action():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.page = None

# -------------------------
# Admin: user management
# -------------------------
def admin_page():
    st.header(t("admin_title"))
    st.write(f"{t('user_logged_as')}: **{st.session_state.username}**")
    users = load_users()

    # admin actions (localized choices)
    action = st.selectbox(t("action"), [t("add"), t("modify"), t("delete")], key="admin_action")
    username = st.text_input(t("username"), key="admin_username")
    password = st.text_input(t("password"), key="admin_password")
    role = st.selectbox(t("role"), [t("role_user"), t("role_admin")], key="admin_role")

    def do_admin_action():
        if not username:
            st.warning("Username is required")
            return
        uname = username.strip().lower()
        users = load_users()
        if action == t("add"):
            if uname in users:
                st.warning("User already exists.")
            else:
                if not password:
                    st.warning("Password required to add user.")
                    return
                users[uname] = {"password": password, "role": role}
                save_users(users)
                st.success("User added ✅")
        elif action == t("modify"):
            if uname not in users:
                st.warning("User not found.")
            else:
                if password:
                    users[uname]["password"] = password
                users[uname]["role"] = role
                save_users(users)
                st.success("User modified ✅")
        elif action == t("delete"):
            if uname not in users:
                st.warning("User not found.")
            else:
                del users[uname]
                save_users(users)
                st.success("User deleted ✅")

    st.button(t("validate"), on_click=do_admin_action)
    st.button(t("back_menu"), on_click=lambda: st.session_state.__setitem__("page", "menu"))

# -------------------------
# User: change own password
# -------------------------
def user_change_password():
    st.subheader(t("change_password"))
    new_pw = st.text_input(t("new_password"), type="password", key="new_pw_user")
    if st.button(t("validate")):
        if not new_pw:
            st.warning("Password cannot be empty.")
            return
        users = load_users()
        uname = st.session_state.username
        if uname in users:
            users[uname]["password"] = new_pw
            save_users(users)
            st.success(t("password_changed"))
        else:
            st.error("User not found in JSON.")

# -------------------------
# Linearity page (manual input or CSV)
# -------------------------
def linearity_page():
    st.header(t("linearity_title"))
    st.write(f"{t('user_logged_as')}: **{st.session_state.username}**")

    # allow switching between manual / csv
    input_mode = st.radio("", ["Manual / Saisie", "CSV"], key="linearity_input_mode")
    unit = st.selectbox(t("unit"), ["µg/mL", "mg/L", "g/L", "ppm"], index=0, key="unit_select")
    # keep unit in session so S/N can use it
    st.session_state.linearity.setdefault("unit", unit)

    conc = np.array([])
    resp = np.array([])

    if input_mode == "Manual / Saisie":
        conc_text = st.text_area(t("conc_input"), key="conc_text")
        resp_text = st.text_area(t("resp_input"), key="resp_text")
        if st.button(t("plot_curve")):
            try:
                conc = np.array([float(x.strip()) for x in conc_text.split(",") if x.strip()])
                resp = np.array([float(x.strip()) for x in resp_text.split(",") if x.strip()])
                if len(conc) == 0 or len(resp) == 0 or len(conc) != len(resp):
                    st.error("Lists must be same length and not empty.")
                else:
                    slope, intercept = np.polyfit(conc, resp, 1)
                    r2 = np.corrcoef(conc, resp)[0, 1] ** 2
                    st.session_state.linearity.update({
                        "slope": float(slope),
                        "intercept": float(intercept),
                        "r2": float(r2),
                        "conc": conc.tolist(),
                        "resp": resp.tolist(),
                        "unit": unit
                    })
                    # plot interactive via matplotlib and show
                    fig, ax = plt.subplots()
                    ax.scatter(conc, resp, label="Points")
                    xs = np.linspace(min(conc), max(conc), 100)
                    ax.plot(xs, slope * xs + intercept, label=f"y={slope:.4f}x+{intercept:.4f}")
                    ax.set_xlabel(f"Concentration ({unit})")
                    ax.set_ylabel("Signal")
                    ax.legend()
                    st.pyplot(fig)
                    st.success(f"{t('equation')}: y = {slope:.4f} x + {intercept:.4f} ({t('r2')}: {r2:.4f})")
            except Exception as e:
                st.error(f"Error in calculation: {e}")

    else:  # CSV
        up = st.file_uploader("Upload linearity CSV", type=["csv"], key="linearity_csv")
        if up is not None:
            try:
                df = pd.read_csv(up)
                cols = [c.strip().lower() for c in df.columns]
                # try to find concentration and signal
                # accept multiple names
                conc_col = None
                signal_col = None
                for c in df.columns:
                    cl = c.strip().lower()
                    if "conc" in cl or "concentration" in cl:
                        conc_col = c
                    if "signal" in cl or "response" in cl or "absorbance" in cl or "area" in cl:
                        signal_col = c
                if conc_col is None or signal_col is None:
                    st.error("CSV must contain concentration and signal columns (names containing 'conc' and 'signal/response').")
                else:
                    conc = df[conc_col].astype(float).values
                    resp = df[signal_col].astype(float).values
                    slope, intercept = np.polyfit(conc, resp, 1)
                    r2 = np.corrcoef(conc, resp)[0, 1] ** 2
                    st.session_state.linearity.update({
                        "slope": float(slope),
                        "intercept": float(intercept),
                        "r2": float(r2),
                        "conc": conc.tolist(),
                        "resp": resp.tolist(),
                        "unit": unit
                    })
                    fig, ax = plt.subplots()
                    ax.scatter(conc, resp, label="Points")
                    xs = np.linspace(min(conc), max(conc), 100)
                    ax.plot(xs, slope * xs + intercept, label=f"y={slope:.4f}x+{intercept:.4f}")
                    ax.set_xlabel(f"Concentration ({unit})")
                    ax.set_ylabel("Signal")
                    ax.legend()
                    st.pyplot(fig)
                    st.success(f"{t('equation')}: y = {slope:.4f} x + {intercept:.4f} ({t('r2')}: {r2:.4f})")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    # show stored linearity results if present
    if st.session_state.linearity.get("slope") is not None:
        slope = st.session_state.linearity["slope"]
        intercept = st.session_state.linearity["intercept"]
        r2 = st.session_state.linearity["r2"]
        st.info(f"{t('equation')}: y = {slope:.4f} x + {intercept:.4f} ({t('r2')}: {r2:.4f})")

        # unknown calculation instantaneous when changing unknown input
        unknown_choice = st.selectbox(t("unknown_type"), [t("unknown_conc"), t("unknown_signal")], key="linear_unknown_choice")
        unknown_val = st.number_input(t("unknown_value"), value=0.0, step=0.01, key="linear_unknown_val")
        if unknown_choice == t("unknown_conc"):
            # compute concentration from signal: (signal - intercept)/slope
            if slope == 0:
                st.error("Slope is zero, cannot compute concentration.")
            else:
                conc_res = (unknown_val - intercept) / slope
                st.success(f"🔹 {t('unknown_conc')} = {conc_res:.4f} {st.session_state.linearity.get('unit','')}")
        else:
            # compute signal from concentration
            sig_res = slope * unknown_val + intercept
            st.success(f"🔹 {t('unknown_signal')} = {sig_res:.4f}")

    # Export PDF for linearity
    company_name = st.text_input(t("company_name"), key="company_linearity")
    def export_linearity_pdf():
        if not company_name:
            st.warning(t("fill_company"))
            return
        if "slope" not in st.session_state.linearity:
            st.warning("No linearity calculated yet.")
            return
        # rebuild simple matplotlib image for embedding
        conc = np.array(st.session_state.linearity["conc"])
        resp = np.array(st.session_state.linearity["resp"])
        slope = st.session_state.linearity["slope"]
        intercept = st.session_state.linearity["intercept"]
        fig, ax = plt.subplots()
        ax.scatter(conc, resp)
        xs = np.linspace(min(conc), max(conc), 100)
        ax.plot(xs, slope * xs + intercept)
        ax.set_xlabel(f"Concentration ({st.session_state.linearity.get('unit','')})")
        ax.set_ylabel("Signal")
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        img_bytes = buf.getvalue()
        content_lines = [
            "Linearity report",
            f"Equation: y = {slope:.4f} x + {intercept:.4f}",
            f"R²: {st.session_state.linearity.get('r2',0):.4f}"
        ]
        pdf_file = generate_pdf("Linearity_Report", content_lines, image_bytes=img_bytes, company=company_name, username=st.session_state.username)
        st.success(f"PDF exported: {pdf_file}")
        with open(pdf_file, "rb") as f:
            st.download_button(t("download_pdf"), f, file_name=pdf_file)

    st.button(t("export_pdf"), on_click=export_linearity_pdf)
    st.button(t("back_menu"), on_click=lambda: st.session_state.__setitem__("page", "menu"))

# -------------------------
# S/N page
# -------------------------
def sn_page():
    st.header(t("sn_title"))
    st.write(f"{t('user_logged_as')}: **{st.session_state.username}**")
    company_name = st.text_input(t("company_name"), key="company_sn")
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","pdf"], key="sn_upload")

    # allow user to choose whether to use slope from linearity for conversion to concentration
    use_linearity_for_conversion = st.checkbox("Use linearity slope to convert LOD/LOQ to concentration", value=True)

    if uploaded:
        name_lower = uploaded.name.lower()
        if name_lower.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded)
                # normalize columns
                cols = [c.strip().lower() for c in df.columns]
                if "time" not in cols or "signal" not in cols:
                    st.error(t("csv_cols_error"))
                    return
                # map columns to consistent names
                df.columns = [c.strip() for c in df.columns]
                time_col = [c for c in df.columns if c.strip().lower() == "time"][0]
                signal_col = [c for c in df.columns if c.strip().lower() == "signal"][0]
                df = df[[time_col, signal_col]].rename(columns={time_col:"time", signal_col:"signal"})
                df["time"] = pd.to_numeric(df["time"], errors='coerce')
                df["signal"] = pd.to_numeric(df["signal"], errors='coerce')
                df = df.dropna()
                # display plot
                fig, ax = plt.subplots()
                ax.plot(df["time"], df["signal"])
                ax.set_xlabel("Time")
                ax.set_ylabel("Signal")
                st.pyplot(fig)

                # let user choose region for baseline (for USP noise) using slider selecting time window
                tmin = float(df["time"].min())
                tmax = float(df["time"].max())
                window = st.slider("Select time window for baseline noise (USP)", min_value=tmin, max_value=tmax, value=(tmin, tmin + (tmax-tmin)*0.1))
                # compute noise from selected window
                baseline_df = df[(df["time"] >= window[0]) & (df["time"] <= window[1])]
                if baseline_df.empty:
                    st.warning("Selected baseline window is empty - choose another.")
                    noise_baseline = np.nan
                else:
                    noise_baseline = float(baseline_df["signal"].std())

                # classic noise: std of the whole signal (simple approach)
                noise_all = float(df["signal"].std())
                peak_val = float(df["signal"].max())
                sn_classic = peak_val / noise_all if noise_all != 0 else np.nan
                sn_usp = peak_val / noise_baseline if noise_baseline and noise_baseline !=0 else np.nan
                lod = 3 * noise_all
                loq = 10 * noise_all

                st.success(f"{t('sn_result')}: {sn_classic:.2f}")
                st.info(f"{t('sn_usp')}: {sn_usp:.2f} (baseline noise {noise_baseline:.4f})")
                st.info(f"{t('lod')}: {lod:.4f}, {t('loq')}: {loq:.4f}")

                # convert to concentration using slope if requested and available
                if use_linearity_for_conversion and st.session_state.linearity.get("slope"):
                    slope = st.session_state.linearity["slope"]
                    if slope != 0:
                        lod_conc = lod / slope
                        loq_conc = loq / slope
                        st.info(f"LOD (concentration): {lod_conc:.4f} {st.session_state.linearity.get('unit','')}")
                        st.info(f"LOQ (concentration): {loq_conc:.4f} {st.session_state.linearity.get('unit','')}")
                    else:
                        st.warning("Linearity slope is zero - cannot convert to concentration.")

                # Export PDF
                def export_sn_pdf():
                    if not company_name:
                        st.warning(t("fill_company"))
                        return
                    content_lines = [
                        "S/N report",
                        f"Peak signal: {peak_val:.4f}",
                        f"Noise (whole): {noise_all:.4f}",
                        f"S/N (classic): {sn_classic:.2f}",
                        f"S/N (USP): {sn_usp:.2f}",
                        f"LOD: {lod:.4f}",
                        f"LOQ: {loq:.4f}"
                    ]
                    # save current figure to bytes
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png")
                    buf.seek(0)
                    img_bytes = buf.getvalue()
                    pdf_file = generate_pdf("SN_Report", content_lines, image_bytes=img_bytes, company=company_name, username=st.session_state.username)
                    st.success(f"PDF exported: {pdf_file}")
                    with open(pdf_file, "rb") as f:
                        st.download_button(t("download_pdf"), f, file_name=pdf_file)
                st.button(t("export_pdf"), on_click=export_sn_pdf)

            except Exception as e:
                st.error(f"Error reading CSV: {e}")

        else:
            # PNG or PDF uploaded: display image and allow user to input numeric peak/noise
            st.info("Image or PDF uploaded: numeric extraction not available. Displaying the file and allowing manual entry of peak and noise.")
            try:
                if name_lower.endswith(".png") or name_lower.endswith(".jpg") or name_lower.endswith(".jpeg"):
                    img = Image.open(uploaded)
                    st.image(img, use_column_width=True)
                else:
                    # PDF preview: show first page as image if possible
                    try:
                        from pdf2image import convert_from_bytes
                        pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1)
                        st.image(pages[0], use_column_width=True)
                    except Exception:
                        st.write("PDF preview not available (pdf2image not installed).")
                # manual numeric entry
                peak_val = st.number_input("Peak signal (enter manually)", value=0.0, step=0.1, key="manual_peak")
                noise_val = st.number_input("Noise (enter manually)", value=0.0, step=0.0001, key="manual_noise")
                if st.button("Compute S/N from manual values"):
                    if noise_val == 0:
                        st.error("Noise cannot be zero.")
                    else:
                        sn_classic = peak_val / noise_val
                        st.success(f"{t('sn_result')}: {sn_classic:.2f}")
                        lod = 3 * noise_val
                        loq = 10 * noise_val
                        st.info(f"{t('lod')}: {lod:.4f}, {t('loq')}: {loq:.4f}")
                        if use_linearity_for_conversion and st.session_state.linearity.get("slope"):
                            slope = st.session_state.linearity["slope"]
                            if slope != 0:
                                st.info(f"LOD (conc): {lod / slope:.4f} {st.session_state.linearity.get('unit','')}")
                                st.info(f"LOQ (conc): {loq / slope:.4f} {st.session_state.linearity.get('unit','')}")
            except Exception as e:
                st.error(f"Error handling image/pdf: {e}")

    st.button(t("back_menu"), on_click=lambda: st.session_state.__setitem__("page", "menu"))

# -------------------------
# Main menu
# -------------------------
def main_menu():
    st.title(t("app_title"))
    # show logo
    if os.path.exists(LOGO_FILE):
        try:
            st.image(LOGO_FILE, width=120)
        except Exception:
            pass

    st.write(f"{t('user_logged_as')}: **{st.session_state.username}**")
    choice = st.selectbox(t("choose_option"), [t("linearity_option"), t("sn_option")], key="main_choice")
    if st.button("Go"):
        if choice == t("linearity_option"):
            st.session_state.page = "linearity"
        else:
            st.session_state.page = "sn"

    # allow change password for user
    if st.session_state.role == "user":
        user_change_password()

    if st.session_state.role == "admin":
        if st.button("Go to admin"):
            st.session_state.page = "admin"

    st.button(t("logout"), on_click=logout_action)

# -------------------------
# Login screen
# -------------------------
def login_screen():
    st.set_page_config(page_title="LabT", layout="centered")
    # language selector at top (English default)
    lang = st.selectbox(TXT["en"]["select_language"], ["en", "fr"], index=0, key="lang_select")
    st.session_state.language = lang

    st.title(t("login_title"))
    if os.path.exists(LOGO_FILE):
        try:
            st.image(LOGO_FILE, width=120)
        except Exception:
            pass

    users = load_users()
    # show usernames in selectbox (original keys) but we normalize display as original file items
    display_users = list(users.keys())
    selected = st.selectbox(t("choose_user"), display_users, key="login_user")
    passwd = st.text_input(t("password"), type="password", key="login_pass")
    if st.button(t("login_btn")):
        login_action(selected, passwd)
    # show status
    if st.session_state.logged_in:
        st.success(f"{t('login_success')} {st.session_state.username}")
        # go to menu immediately
        st.session_state.page = "menu"

# -------------------------
# App runner
# -------------------------
def app():
    if not st.session_state.logged_in:
        login_screen()
        return

    # Show appropriate page
    if st.session_state.page == "admin":
        admin_page()
    elif st.session_state.page == "linearity":
        linearity_page()
    elif st.session_state.page == "sn":
        sn_page()
    else:
        main_menu()

if __name__ == "__main__":
    app()