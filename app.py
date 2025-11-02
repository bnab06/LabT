# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io
import json
import tempfile
import os
from datetime import datetime

# Optional OCR / PDF features
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# -------------------------
# Page config (no sidebar)
# -------------------------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

# -------------------------
# Users helpers
# -------------------------
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {
            "admin": {"password": "admin123", "role": "admin"},
            "user": {"password": "user123", "role": "user"},
        }
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        return default

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

USERS = load_users()

def find_user_key(username):
    if username is None:
        return None
    for u in USERS.keys():
        if u.lower() == username.strip().lower():
            return u
    return None

# -------------------------
# Translations
# -------------------------
TEXTS = {
    "FR": {
        "app_title":"LabT",
        "powered":"Powered by BnB",
        "username":"Utilisateur",
        "password":"Mot de passe",
        "login":"Connexion",
        "logout":"Déconnexion",
        "invalid":"Identifiants invalides",
        "linearity":"Linéarité",
        "sn":"S/N",
        "admin":"Admin",
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
        "digitize_info":"Digitizing : OCR tenté si pytesseract installé (best-effort)",
        "export_sn_pdf":"Exporter S/N PDF",
        "download_original_pdf":"Télécharger PDF original",
        "change_pwd":"Changer mot de passe (hors session)",
        "compute":"Compute",
        "company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport.",
        "select_section":"Section",
        "upload_logo":"Uploader un logo (optionnel)"
    },
    "EN": {
        "app_title":"LabT",
        "powered":"Powered by BnB",
        "username":"Username",
        "password":"Password",
        "login":"Login",
        "logout":"Logout",
        "invalid":"Invalid credentials",
        "linearity":"Linearity",
        "sn":"S/N",
        "admin":"Admin",
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
        "digitize_info":"Digitizing: OCR attempted if pytesseract available (best-effort)",
        "export_sn_pdf":"Export S/N PDF",
        "download_original_pdf":"Download original PDF",
        "change_pwd":"Change password (outside session)",
        "compute":"Compute",
        "company_missing":"Please enter company name before generating the report.",
        "select_section":"Section",
        "upload_logo":"Upload logo (optional)"
    }
}

def t(key):
    lang = st.session_state.get("lang", "FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(key, key)

# -------------------------
# Session defaults
# -------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "FR"
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

# -------------------------
# PDF generator
# -------------------------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=8, w=25)
            pdf.set_xy(40, 10)
        except Exception:
            pdf.set_xy(10, 10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=1, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 11)
    for line in lines:
        pdf.multi_cell(0, 7, line)
    if img_bytes is not None:
        try:
            if isinstance(img_bytes, io.BytesIO):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes.getvalue())
                    tmpname = tmpf.name
                pdf.ln(4)
                pdf.image(tmpname, x=20, w=170)
            elif isinstance(img_bytes, bytes):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes)
                    tmpname = tmpf.name
                pdf.ln(4)
                pdf.image(tmpname, x=20, w=170)
            else:
                if isinstance(img_bytes, str) and os.path.exists(img_bytes):
                    pdf.ln(4)
                    pdf.image(img_bytes, x=20, w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# -------------------------
# Header area
# -------------------------
def header_area():
    cols = st.columns([3,1])
    with cols[0]:
        st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    with cols[1]:
        upl = st.file_uploader(t("upload_logo"), type=["png","jpg","jpeg"], key="upload_logo")
        if upl is not None:
            try:
                upl.seek(0)
                data = upl.read()
                with open(LOGO_FILE, "wb") as f:
                    f.write(data)
                st.success("Logo saved")
            except Exception as e:
                st.warning(f"Logo save error: {e}")

# -------------------------
# Login page (bilingue, powered by BnB)
# -------------------------
def login_screen():
    st.subheader(t("login"))
    st.markdown(f"<div style='color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

    st.session_state.lang = st.selectbox("Lang / Language", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1)
    username = st.text_input(t("username"))
    password = st.text_input(t("password"), type="password")
    if st.button(t("login")):
        uname = (username or "").strip()
        matched = find_user_key(uname)
        if matched and USERS[matched]["password"] == (password or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            st.session_state.page = "home"
        else:
            st.error(t("invalid"))

# -------------------------
# Logout
# -------------------------
def logout():
    for k in ["user","role","page"]:
        st.session_state.pop(k,None)
    st.session_state.page="login"

# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header(t("admin"))
    col1,col2=st.columns([2,1])
    with col1:
        st.subheader("Utilisateurs existants")
        users_list=list(USERS.keys())
        sel=st.selectbox("Sélectionner un utilisateur",users_list)
        if sel:
            info=USERS.get(sel,{})
            st.write(f"**Nom d'utilisateur :** {sel}")
            st.write(f"**Rôle :** {info.get('role','user')}")
            new_pwd=st.text_input(f"Nouveau mot de passe pour {sel}", type="password", key=f"pwd_{sel}")
            new_role=st.selectbox("Rôle", ["user","admin"], index=0 if info.get("role","user")=="user" else 1, key=f"role_{sel}")
            if st.button("Modifier", key=f"mod_{sel}"):
                USERS[sel]["password"]=new_pwd
                USERS[sel]["role"]=new_role
                save_users(USERS)
                st.success("Utilisateur modifié")
            if st.button("Supprimer", key=f"del_{sel}"):
                USERS.pop(sel,None)
                save_users(USERS)
                st.success("Utilisateur supprimé")
    with col2:
        st.subheader("Ajouter nouvel utilisateur")
        new_user=st.text_input(t("enter_username"))
        new_password=st.text_input(t("enter_password"), type="password")
        new_role=st.selectbox("Rôle", ["user","admin"], key="add_role")
        if st.button("Ajouter"):
            if new_user and new_password:
                USERS[new_user]={"password":new_password,"role":new_role}
                save_users(USERS)
                st.success("Utilisateur ajouté")
            else:
                st.warning("Veuillez saisir nom et mot de passe")

# -------------------------
# Linearity panel (inchangé)
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    st.write("Importer CSV ou saisie manuelle des concentrations et signaux.")
    uploaded=st.file_uploader("CSV file", type=["csv"])
    manual_mode=False
    conc=None
    signal=None
    if uploaded:
        df=pd.read_csv(uploaded)
        conc=df["Conc"].values
        signal=df["Signal"].values
    else:
        manual_mode=True
        conc_str=st.text_input("Concentrations (comma-separated)")
        signal_str=st.text_input("Signals (comma-separated)")
        try:
            conc=np.array([float(x.strip()) for x in conc_str.split(",")])
            signal=np.array([float(x.strip()) for x in signal_str.split(",")])
        except Exception:
            st.warning("Invalid manual input")
            return
    if conc is not None and signal is not None:
        coeffs=np.polyfit(conc,signal,1)
        slope=coeffs[0]
        st.write(f"Slope: {slope:.4f}")
        st.session_state.linear_slope=slope
        plt.figure(figsize=(6,3))
        plt.plot(conc,signal,'o',label="Data")
        plt.plot(conc,coeffs[0]*conc+coeffs[1],label="Fit")
        plt.xlabel("Concentration")
        plt.ylabel("Signal")
        plt.legend()
        st.pyplot(plt)

# -------------------------
# S/N panel (amélioré)
# -------------------------
def sn_panel():
    st.header(t("sn"))

    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"])
    manual_mode = False
    signal = None
    time = None
    img_display = None

    # CSV import
    if uploaded and uploaded.type=="text/csv":
        try:
            df = pd.read_csv(uploaded, sep=None, engine='python')
            if "Time" in df.columns and "Signal" in df.columns:
                time = df["Time"].values
                signal = df["Signal"].values
            else:
                st.error("CSV must contain 'Time' and 'Signal' columns")
                return
        except Exception as e:
            st.error(f"CSV read error: {e}")
            return

    # Image import
    elif uploaded:
        try:
            if uploaded.type=="application/pdf" and convert_from_bytes:
                pages = convert_from_bytes(uploaded.read())
                img = pages[0].convert("L")
            else:
                img = Image.open(uploaded).convert("L")
            img_display = img.copy()
            arr = np.array(img)
            arr_inv = 255 - arr
            signal = arr_inv.mean(axis=0)
            time = np.arange(len(signal))
        except Exception as e:
            st.error(f"Image processing failed: {e}")
            return
    else:
        manual_mode = True

    # Manual input
    if manual_mode:
        st.subheader("Manual S/N calculation")
        conc_str = st.text_input("Concentrations (comma-separated)")
        signal_str = st.text_input("Signals (comma-separated)")
        try:
            conc = np.array([float(x.strip()) for x in conc_str.split(",")])
            signal = np.array([float(x.strip()) for x in signal_str.split(",")])
            time = np.arange(len(signal))
        except Exception:
            st.warning("Invalid manual input")
            return

    # Zone selection slider
    if signal is not None:
        start_idx, end_idx = st.slider(
            t("select_section"), 
            0, len(signal)-1, (0,len(signal)-1), step=1
        )

        signal_region = signal[start_idx:end_idx+1]
        time_region = time[start_idx:end_idx+1]

        H = signal.max()
        H_idx = np.argmax(signal)
        t_R = time[H_idx]
        h = signal_region.std()
        W_half = H/2

        st.write(f"**H (peak):** {H:.3f}")
        st.write(f"**h (noise):** {h:.3f}")
        st.write(f"**W1/2:** {W_half:.3f}")
        st.write(f"**Retention time:** {t_R:.3f}")

        sn_classic = H/h if h>0 else np.nan
        sn_usp = H/h if h>0 else np.nan
        st.write(f"**S/N classic:** {sn_classic:.2f}")
        st.write(f"**S/N USP:** {sn_usp:.2f}")

        fig, ax = plt.subplots(figsize=(10,3))
        ax.plot(time, signal, color='black')
        ax.axhline(H/2,color='red',linestyle="--",label="W1/2")
        ax.axhline(H,color='green',linestyle="--",label="H max")
        ax.axhline(h,color='orange',linestyle="--",label="Noise h")
        ax.axvline(t_R,color='blue',linestyle=":",label="t_R")
        ax.set_xlabel("Time")
        ax.set_ylabel("Signal")
        ax.set_title("Chromatogram with S/N indicators")
        ax.legend()
        st.pyplot(fig)

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        st.download_button("Download S/N Image", data=buf, file_name="sn.png", mime="image/png")

        pdf_bytes = generate_pdf_bytes("S/N Report", [
            f"H (peak): {H:.3f}",
            f"h (noise): {h:.3f}",
            f"W1/2: {W_half:.3f}",
            f"Retention time: {t_R:.3f}",
            f"S/N classic: {sn_classic:.2f}",
            f"S/N USP: {sn_usp:.2f}"
        ], img_bytes=buf)
        st.download_button(t("export_sn_pdf"), pdf_bytes, "sn_report.pdf", "application/pdf")

# -------------------------
# Main app
# -------------------------
def main_app():
    header_area()
    st.sidebar.button(t("logout"), on_click=logout)
    menu = ["Home", t("linearity"), t("sn")]
    if st.session_state.role=="admin":
        menu.append(t("admin"))

    choice = st.sidebar.radio("Menu", menu)
    if choice==t("linearity"):
        linearity_panel()
    elif choice==t("sn"):
        sn_panel()
    elif choice==t("admin") and st.session_state.role=="admin":
        admin_panel()
    else:
        st.write("Welcome")

# -------------------------
# Run app
# -------------------------
def run():
    if st.session_state.get("user") is None:
        login_screen()
    else:
        main_app()

if __name__=="__main__":
    run()