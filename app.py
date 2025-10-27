# app.py - Version complète et exécutable
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io
import json
import tempfile
from datetime import datetime
import os

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
# Config
# -------------------------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")
USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

# -------------------------
# Users
# -------------------------
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {"admin": {"password": "admin123", "role": "admin"},
                   "user": {"password": "user123", "role": "user"}}
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

# -------------------------
# Translations
# -------------------------
TEXTS = {
    "FR": { "app_title":"LabT","powered":"Powered by BnB","username":"Utilisateur","password":"Mot de passe",
            "login":"Connexion","logout":"Déconnexion","invalid":"Identifiants invalides",
            "linearity":"Linéarité","sn":"S/N","admin":"Admin","company":"Nom de la compagnie",
            "input_csv":"CSV","input_manual":"Saisie manuelle","concentration":"Concentration","signal":"Signal",
            "unit":"Unité","generate_pdf":"Générer PDF","download_pdf":"Télécharger PDF","download_csv":"Télécharger CSV",
            "sn_classic":"S/N Classique","sn_usp":"S/N USP","lod":"LOD (conc.)","loq":"LOQ (conc.)",
            "formulas":"Formules","select_region":"Sélectionner la zone","add_user":"Ajouter utilisateur",
            "delete_user":"Supprimer utilisateur","modify_user":"Modifier mot de passe","enter_username":"Nom d'utilisateur",
            "enter_password":"Mot de passe (simple)","upload_chrom":"Importer chromatogramme (CSV, PNG, JPG, PDF)",
            "digitize_info":"Digitizing : OCR tenté si pytesseract installé (best-effort)",
            "export_sn_pdf":"Exporter S/N PDF","download_original_pdf":"Télécharger PDF original",
            "change_pwd":"Changer mot de passe (hors session)", "compute":"Compute", "company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport."},
    "EN": { "app_title":"LabT","powered":"Powered by BnB","username":"Username","password":"Password",
            "login":"Login","logout":"Logout","invalid":"Invalid credentials",
            "linearity":"Linearity","sn":"S/N","admin":"Admin","company":"Company name",
            "input_csv":"CSV","input_manual":"Manual input","concentration":"Concentration","signal":"Signal",
            "unit":"Unit","generate_pdf":"Generate PDF","download_pdf":"Download PDF","download_csv":"Download CSV",
            "sn_classic":"S/N Classic","sn_usp":"S/N USP","lod":"LOD (conc.)","loq":"LOQ (conc.)",
            "formulas":"Formulas","select_region":"Select region","add_user":"Add user",
            "delete_user":"Delete user","modify_user":"Modify password","enter_username":"Username",
            "enter_password":"Password (simple)","upload_chrom":"Upload chromatogram (CSV, PNG, JPG, PDF)",
            "digitize_info":"Digitizing: OCR attempted if pytesseract available (best-effort)",
            "export_sn_pdf":"Export S/N PDF","download_original_pdf":"Download original PDF",
            "change_pwd":"Change password (outside session)", "compute":"Compute", "company_missing":"Please enter company name before generating the report."}
}

def t(key):
    lang = st.session_state.get("lang", "FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(key, key)

# -------------------------
# Session defaults
# -------------------------
for key, default in [("lang","FR"),("user",None),("role",None),("linear_slope",None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------
# Utilities
# -------------------------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_path:
        try:
            pdf.image(logo_path, x=10, y=8, w=20)
            pdf.set_xy(35,10)
        except:
            pdf.set_xy(10,10)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,title,ln=1,align="C")
    pdf.ln(4)
    pdf.set_font("Arial","",11)
    for line in lines:
        pdf.multi_cell(0,7,line)
    if img_bytes:
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
                pdf.ln(4)
                pdf.image(img_bytes, x=20, w=170)
        except:
            pass
    return pdf.output(dest="S").encode("latin1")

def extract_xy_from_image_pytesseract(img: Image.Image):
    if pytesseract is None:
        return pd.DataFrame(columns=["X","Y"])
    text = pytesseract.image_to_string(img)
    rows=[]
    for line in text.splitlines():
        if not line.strip(): continue
        for sep in [",",";","\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip()!=""]
                if len(parts)>=2:
                    try:
                        x=float(parts[0].replace(",",".")); y=float(parts[1].replace(",","."))
                        rows.append([x,y]); break
                    except: pass
        else:
            parts=line.split()
            if len(parts)>=2:
                try:
                    x=float(parts[0].replace(",",".")); y=float(parts[1].replace(",","."))
                    rows.append([x,y])
                except: pass
    return pd.DataFrame(rows, columns=["X","Y"])

# -------------------------
# Panels
# -------------------------
def login_screen():
    st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    lang=st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="login_lang")
    st.session_state.lang=lang
    with st.form("login_form"):
        cols=st.columns([2,1])
        with cols[0]: username=st.text_input(t("username"), key="username_login")
        with cols[1]: password=st.text_input(t("password"), type="password", key="password_login")
        submitted=st.form_submit_button(t("login"))
    if submitted:
        uname=(username or "").strip()
        if not uname: st.error(t("invalid")); return
        matched=None
        for u in USERS:
            if u.lower()==uname.lower(): matched=u; break
        if matched and USERS[matched]["password"]==(password or ""):
            st.session_state.user=matched
            st.session_state.role=USERS[matched].get("role","user")
            return
        else: st.error(t("invalid"))
    st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)
    with st.expander(t("change_pwd"), expanded=False):
        st.write("Change a user's password (works even if not logged in).")
        u_name=st.text_input("Username to change", key="chg_user")
        u_pwd=st.text_input("New password", type="password", key="chg_pwd")
        if st.button("Change password", key="chg_btn"):
            if not u_name.strip() or not u_pwd: st.warning("Enter username and new password")
            else:
                found=None
                for u in USERS:
                    if u.lower()==u_name.strip().lower(): found=u; break
                if not found: st.warning("User not found")
                else: USERS[found]["password"]=u_pwd.strip(); save_users(USERS); st.success(f"Password updated for {found}")

# -------------------------
# Main
# -------------------------
def main():
    if st.session_state.user is None:
        login_screen()
        return
    st.sidebar.write(f"User: {st.session_state.user} ({st.session_state.role})")
    st.sidebar.button(t("logout"), on_click=lambda: st.session_state.update({"user":None,"role":None}))
    if st.session_state.role=="admin":
        panel=st.sidebar.selectbox("Admin panel", ["Admin","Linearity","S/N"])
        if panel=="Admin": admin_panel()
        elif panel=="Linearity": linearity_panel()
        else: sn_panel()
    else:
        panel=st.sidebar.selectbox("Panel", ["Linearity","S/N"])
        if panel=="Linearity": linearity_panel()
        else: sn_panel()

if __name__=="__main__":
    main()