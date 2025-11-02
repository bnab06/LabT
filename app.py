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

# Optional features
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"  # optional logo

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
# OCR helper
# -------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
    if pytesseract is None:
        return pd.DataFrame(columns=["X","Y"])
    try:
        text = pytesseract.image_to_string(img)
    except Exception:
        return pd.DataFrame(columns=["X","Y"])
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        for sep in [",",";","\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip()!=""]
                if len(parts)>=2:
                    try:
                        x = float(parts[0].replace(",","."))
                        y = float(parts[1].replace(",","."))
                        rows.append([x,y])
                        break
                    except Exception:
                        pass
        else:
            parts = line.split()
            if len(parts)>=2:
                try:
                    x = float(parts[0].replace(",","."))
                    y = float(parts[1].replace(",","."))
                    rows.append([x,y])
                except Exception:
                    pass
    return pd.DataFrame(rows, columns=["X","Y"])

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
# Login screen
# -------------------------
def login_screen():
    st.markdown(f"### 🔐 {t('login')}")
    st.markdown(f"<div style='text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

    lang = st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.get("lang","FR")=="FR" else 1)
    st.session_state.lang = lang

    username = st.text_input(t("username"))
    password = st.text_input(t("password"), type="password")
    if st.button(t("login")):
        uname = (username or "").strip()
        matched = find_user_key(uname)
        if matched and USERS[matched]["password"]==(password or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            st.session_state.page = "home"
        else:
            st.error(t("invalid"))

# -------------------------
# Logout
# -------------------------
def logout():
    for key in ["user","role","page"]:
        st.session_state.pop(key,None)
    st.session_state.page = "login"
# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.subheader("Admin Panel")
    action = st.selectbox("Action", [t("add_user"), t("delete_user"), t("modify_user")])
    if action == t("add_user"):
        new_user = st.text_input("New username")
        new_pwd = st.text_input("Password", type="password")
        if st.button("Add"):
            if new_user and new_pwd:
                USERS[new_user] = {"password": new_pwd, "role":"user"}
                save_users(USERS)
                st.success(f"User {new_user} added")
    elif action == t("delete_user"):
        del_user = st.selectbox("Select user", list(USERS.keys()))
        if st.button("Delete"):
            if del_user in USERS:
                USERS.pop(del_user)
                save_users(USERS)
                st.success(f"User {del_user} deleted")
    elif action == t("modify_user"):
        sel_user = st.selectbox("Select user", list(USERS.keys()))
        new_pwd = st.text_input("New password", type="password")
        if st.button("Modify"):
            if sel_user in USERS and new_pwd:
                USERS[sel_user]["password"] = new_pwd
                save_users(USERS)
                st.success(f"Password changed for {sel_user}")

# -------------------------
# Linearity Panel
# -------------------------
def linearity_panel():
    st.subheader(t("linearity"))
    input_type = st.radio("Input type", [t("input_csv"), t("input_manual")])

    concentrations = []
    signals = []

    if input_type==t("input_csv"):
        uploaded_file = st.file_uploader("Upload CSV", type="csv", key="lin_csv")
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                if "Concentration" in df.columns and "Signal" in df.columns:
                    concentrations = df["Concentration"].astype(float).tolist()
                    signals = df["Signal"].astype(float).tolist()
                else:
                    st.error("CSV must have columns: Concentration, Signal")
            except Exception as e:
                st.error(f"CSV parse error: {e}")
    else:
        conc_str = st.text_area("Concentrations (comma separated)")
        sig_str = st.text_area("Signals (comma separated)")
        try:
            concentrations = [float(c.strip()) for c in conc_str.split(",") if c.strip()!=""]
            signals = [float(s.strip()) for s in sig_str.split(",") if s.strip()!=""]
        except:
            st.warning("Invalid manual input")

    slope = None
    if concentrations and signals and len(concentrations)==len(signals):
        slope = np.polyfit(concentrations, signals, 1)[0]
        st.session_state.linear_slope = slope
        st.write(f"Slope: {slope:.4f}")
        fig, ax = plt.subplots()
        ax.scatter(concentrations, signals, label="Data")
        ax.plot(concentrations, np.array(concentrations)*slope, color="red", label="Fit")
        ax.set_xlabel("Concentration")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)
    else:
        st.info("Enter valid data to see linearity fit")

# -------------------------
# Chromatogram/SN Panel
# -------------------------
def sn_panel():
    st.subheader(t("sn"))

    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_upload")
    df = None
    img_original = None
    img_processed = None
    x_vals = []
    y_vals = []

    if uploaded is not None:
        name = uploaded.name.lower()
        if name.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded)
                if "Time" in df.columns and "Signal" in df.columns:
                    x_vals = df["Time"].astype(float).tolist()
                    y_vals = df["Signal"].astype(float).tolist()
                else:
                    st.warning("CSV must include columns Time and Signal")
            except Exception as e:
                st.error(f"CSV parse error: {e}")
        else:
            # Convert PDF to PNG
            if name.endswith(".pdf") and convert_from_bytes is not None:
                try:
                    pages = convert_from_bytes(uploaded.read())
                    img_original = pages[0]
                except Exception:
                    st.error("PDF conversion failed")
            else:
                try:
                    img_original = Image.open(uploaded)
                except:
                    st.error("Cannot open image")

        if img_original is not None:
            st.image(img_original, caption="Original Chromatogram", use_column_width=True)
            # OCR extraction
            df = extract_xy_from_image_pytesseract(img_original)
            if df.empty:
                st.warning("OCR could not detect points")
            else:
                x_vals = df["X"].astype(float).tolist()
                y_vals = df["Y"].astype(float).tolist()

    if x_vals and y_vals:
        # Invert image for processing
        y_vals_proc = [max(y_vals)-y for y in y_vals]

        # Slider unique pour zone de bruit
        min_x = min(x_vals)
        max_x = max(x_vals)
        default_start = min_x
        default_end = max_x
        region = st.slider(t("select_region"), float(min_x), float(max_x), (float(default_start), float(default_end)))
        x_region = [x for x in x_vals if region[0]<=x<=region[1]]
        y_region = [y for i,x in enumerate(x_vals) if region[0]<=x<=region[1]]

        if not y_region:
            y_region = y_vals_proc  # fallback

        H = max(y_vals_proc)
        h = np.std(y_region)
        W_half = None
        try:
            half = H/2
            indices = [i for i,y in enumerate(y_vals_proc) if y>=half]
            if indices:
                W_half = x_vals[indices[-1]] - x_vals[indices[0]]
        except:
            W_half = None

        tR = x_vals[y_vals_proc.index(max(y_vals_proc))]

        st.write(f"tR (peak max) : {tR:.2f}")
        st.write(f"H (peak height) : {H:.2f}")
        st.write(f"h (noise) : {h:.2f}")
        st.write(f"W1/2 : {W_half:.2f} (if calculable)")

        sn_classic = H/h if h>0 else None
        sn_usp = 2*H/h if h>0 else None
        st.write(f"S/N classic: {sn_classic:.2f}" if sn_classic else "N/A")
        st.write(f"S/N USP: {sn_usp:.2f}" if sn_usp else "N/A")

        # Plot
        fig, ax = plt.subplots()
        ax.plot(x_vals, y_vals_proc, label="Processed Chromatogram")
        ax.axhline(H/2, color="orange", linestyle="--", label="H/2")
        ax.axvline(tR, color="red", linestyle="--", label="tR")
        ax.fill_between(x_region, 0, y_region, color="gray", alpha=0.3, label="Noise region")
        ax.set_xlabel("Time")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)

        # Export processed image
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        st.download_button("Download processed image", buf, "chrom_processed.png", "image/png")

        # Formulas
        with st.expander(t("formulas")):
            st.markdown("""
            **S/N Classic:** H / h  
            **S/N USP:** 2 * H / h  
            **W1/2:** Width at half maximum  
            **tR:** Retention time of the main peak
            """)
# -------------------------
# Header (logo + title)
# -------------------------
def header_area():
    cols = st.columns([3,1])
    with cols[0]:
        st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    with cols[1]:
        upl = st.file_uploader(t("upload_logo"), type=["png","jpg","jpeg"])
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
# Main App
# -------------------------
def main_app():
    header_area()

    # Language selection
    lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1)
    st.session_state.lang = lang

    if st.session_state.role == "admin":
        tabs = st.tabs([t("admin")])
        with tabs[0]:
            admin_panel()
    else:
        tabs = st.tabs([t("linearity"), t("sn")])
        with tabs[0]:
            linearity_panel()
        with tabs[1]:
            sn_panel()

    if st.button(t("logout")):
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.linear_slope = None
        st.experimental_rerun()

# -------------------------
# Run Application
# -------------------------
def run():
    st.set_page_config(page_title="LabT", layout="wide")
    if "lang" not in st.session_state:
        st.session_state.lang = "FR"
    if "user" not in st.session_state or st.session_state.user is None:
        # Login page
        st.markdown("### 🔐 " + t("login"))
        st.text_input(t("username"), key="login_user")
        st.text_input(t("password"), type="password", key="login_pwd")
        if st.button(t("login")):
            uname = st.session_state.get("login_user", "").strip()
            pwd = st.session_state.get("login_pwd", "")
            matched = find_user_key(uname)
            if matched and USERS[matched]["password"]==pwd:
                st.session_state.user = matched
                st.session_state.role = USERS[matched].get("role","user")
                st.experimental_rerun()
            else:
                st.error(t("invalid"))
        st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>Powered by: BnB</div>", unsafe_allow_html=True)
    else:
        main_app()

# -------------------------
# Entry point
# -------------------------
if __name__=="__main__":
    run()
