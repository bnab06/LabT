# app.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
from datetime import datetime
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt

# optional features
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="LabT", layout="wide")

# ---------------------------
# Files / constants
# ---------------------------
USERS_FILE = "users.json"

# ---------------------------
# Helpers: load/save users
# ---------------------------
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # default fallback
        return {"admin": {"password": "admin123", "role": "admin"},
                "user": {"password": "user123", "role": "user"}}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

USERS = load_users()

# ---------------------------
# Translations (FR / EN)
# ---------------------------
TEXTS = {
    "FR": {
        "app_title":"LabT",
        "powered":"Powered by BnB",
        "username":"Utilisateur",
        "password":"Mot de passe",
        "login":"Connexion",
        "logout":"Déconnexion",
        "invalid":"Identifiants invalides",
        "menu_linearity":"Linéarité",
        "menu_sn":"Signal / Bruit",
        "menu_admin":"Admin",
        "company":"Nom de la compagnie",
        "input_csv":"CSV",
        "input_manual":"Saisie manuelle",
        "concentration":"Concentration",
        "signal":"Signal",
        "unit":"Unité",
        "generate_pdf":"Générer PDF",
        "download_pdf":"Télécharger PDF",
        "download_csv":"Télécharger CSV",
        "sn_classic":"S/N Classique",
        "sn_usp":"S/N USP",
        "lod":"LOD (conc.)",
        "loq":"LOQ (conc.)",
        "formulas":"Formules",
        "select_region":"Sélectionner la zone",
        "add_user":"Ajouter utilisateur",
        "delete_user":"Supprimer utilisateur",
        "modify_user":"Modifier mot de passe",
        "enter_username":"Nom d'utilisateur",
        "enter_password":"Mot de passe (simple)",
        "upload_chrom":"Importer chromatogramme (CSV, PNG, JPG, PDF)",
        "digitize_info":"Digitizing: OCR tenté si pytesseract installé",
        "export_sn_pdf":"Exporter S/N PDF",
        "download_original_pdf":"Télécharger PDF original"
    },
    "EN": {
        "app_title":"LabT",
        "powered":"Powered by BnB",
        "username":"Username",
        "password":"Password",
        "login":"Login",
        "logout":"Logout",
        "invalid":"Invalid credentials",
        "menu_linearity":"Linearity",
        "menu_sn":"Signal / Noise",
        "menu_admin":"Admin",
        "company":"Company name",
        "input_csv":"CSV",
        "input_manual":"Manual input",
        "concentration":"Concentration",
        "signal":"Signal",
        "unit":"Unit",
        "generate_pdf":"Generate PDF",
        "download_pdf":"Download PDF",
        "download_csv":"Download CSV",
        "sn_classic":"S/N Classic",
        "sn_usp":"S/N USP",
        "lod":"LOD (conc.)",
        "loq":"LOQ (conc.)",
        "formulas":"Formulas",
        "select_region":"Select region",
        "add_user":"Add user",
        "delete_user":"Delete user",
        "modify_user":"Modify password",
        "enter_username":"Username",
        "enter_password":"Password (simple)",
        "upload_chrom":"Upload chromatogram (CSV, PNG, JPG, PDF)",
        "digitize_info":"Digitizing: OCR attempted if pytesseract available",
        "export_sn_pdf":"Export S/N PDF",
        "download_original_pdf":"Download original PDF"
    }
}

def t(key):
    lang = st.session_state.get("lang", "FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(key, key)

# ---------------------------
# Session defaults
# ---------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "FR"
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

# ---------------------------
# Utility: create PDF bytes (returns bytes)
# ---------------------------
def generate_pdf_bytes(title, lines, img_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=1, align="C")
    pdf.set_font("Arial", "", 11)
    pdf.ln(4)
    for line in lines:
        pdf.multi_cell(0, 7, line)
    if img_bytes is not None:
        try:
            pdf.ln(4)
            pdf.image(img_bytes, x=20, w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# ---------------------------
# OCR helper
# ---------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
    if pytesseract is None:
        return pd.DataFrame(columns=["X","Y"])
    text = pytesseract.image_to_string(img)
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        for sep in [",", ";", "\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip() != ""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",","."))
                        y = float(parts[1].replace(",","."))
                        rows.append([x,y])
                        break
                    except:
                        pass
        else:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",","."))
                    y = float(parts[1].replace(",","."))
                    rows.append([x,y])
                except:
                    pass
    return pd.DataFrame(rows, columns=["X","Y"])

# ---------------------------
# Logout helper
# ---------------------------
def logout():
    for key in ["user", "role", "linear_slope"]:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()

# ---------------------------
# Login screen
# ---------------------------
def login_screen():
    st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    st.write("")
    lang = st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="login_lang")
    st.session_state.lang = lang

    with st.form("login_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input(t("username"), key="form_username")
        with col2:
            password = st.text_input(t("password"), type="password", key="form_password")
        submitted = st.form_submit_button(t("login"))
        if submitted:
            uname = (username or "").strip()
            if not uname:
                st.error(t("invalid"))
                return
            matched = None
            for u in USERS:
                if u.lower() == uname.lower():
                    matched = u
                    break
            if matched and USERS[matched]["password"] == (password or ""):
                st.session_state.user = matched
                st.session_state.role = USERS[matched].get("role", "user")
                st.experimental_rerun()
            else:
                st.error(t("invalid"))

    st.markdown(
        f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>",
        unsafe_allow_html=True
    )

# ---------------------------
# Admin panel
# ---------------------------
def admin_panel():
    st.header(t("menu_admin"))
    st.write(t("add_user"))
    st.write("")
    col_a, col_b = st.columns([2,1])
    with col_a:
        st.subheader("Existing users")
        for u, info in list(USERS.items()):
            row_cols = st.columns([3,1,1])
            row_cols[0].write(f"{u} — role: {info.get('role','user')}")
            if row_cols[1].button(t("modify_user"), key=f"btn_modify_{u}"):
                with st.expander(f"Modify {u}", expanded=True):
                    new_pwd = st.text_input(f"New password for {u}", type="password", key=f"input_newpwd_{u}")
                    if st.button("Save", key=f"save_pwd_{u}"):
                        if new_pwd:
                            USERS[u]["password"] = new_pwd
                            save_users(USERS)
                            st.success(f"Password updated for {u}")
                            st.experimental_rerun()
            if row_cols[2].button(t("delete_user"), key=f"btn_delete_{u}"):
                if u.lower() == "admin":
                    st.warning("Cannot delete admin")
                else:
                    USERS.pop(u)
                    save_users(USERS)
                    st.success(f"{u} deleted")
                    st.experimental_rerun()

    with col_b:
        st.subheader(t("add_user"))
        with st.form("form_add_user"):
            new_user = st.text_input(t("enter_username"), key="add_username")
            new_pass = st.text_input(t("enter_password"), type="password", key="add_password")
            role = st.selectbox("Role", ["user","admin"], key="add_role")
            add_sub = st.form_submit_button("Add")
            if add_sub:
                if not new_user.strip() or not new_pass.strip():
                    st.warning("Please enter username and password")
                else:
                    if any(u.lower() == new_user.strip().lower() for u in USERS):
                        st.warning("User exists")
                    else:
                        USERS[new_user.strip()] = {"password": new_pass.strip(), "role": role}
                        save_users(USERS)
                        st.success(f"User {new_user.strip()} added")
                        st.experimental_rerun()

# ---------------------------
# (Linearity / S/N panels here…)
# Keep everything as-is in your original code.
# Only replace the PDF generation line in linearity_panel with:
# lines = [
#     f"Company: {company or 'N/A'}",
#     f"User: {st.session_state.user or 'Unknown'}",
#     f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
#     f"Slope: {slope:.4f}",
#     f"Intercept: {intercept:.4f}",
#     f"R²: {r2:.4f}"
# ]
# ---------------------------

# ---------------------------
# Main app
# ---------------------------
def main_app():
    st.sidebar.title(f"{t('app_title')} - {st.session_state.user or ''}")
    side_lang = st.sidebar.selectbox("Lang / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="side_lang")
    st.session_state.lang = side_lang

    if st.sidebar.button(t("logout"), key="sidebar_logout"):
        logout()

    if st.session_state.role == "admin":
        opt = st.sidebar.radio("Menu", [t("menu_admin")], key="sidebar_menu_admin")
    else:
        opt = st.sidebar.radio("Menu", [t("menu_linearity"), t("menu_sn")], key="sidebar_menu_user")

    if opt == t("menu_admin"):
        admin_panel()
    elif opt == t("menu_linearity"):
        linearity_panel()
    elif opt == t("menu_sn"):
        sn_panel()
    else:
        st.info("Select a menu")

# ---------------------------
# App entry
# ---------------------------
def run():
    if st.session_state.user:
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run()