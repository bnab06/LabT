# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io
import json
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
# Config
# -------------------------
st.set_page_config(page_title="LabT", layout="wide")

# -------------------------
# Files / defaults
# -------------------------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {"admin": {"password": "admin123", "role": "admin"},
                   "user": {"password": "user123", "role": "user"}}
        save_users(default)
        return default

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

USERS = load_users()

# -------------------------
# Translations
# -------------------------
TEXTS = {
    "FR": {
        "app_title":"LabT","powered":"Powered by BnB","username":"Utilisateur",
        "password":"Mot de passe","login":"Connexion","logout":"Déconnexion","invalid":"Identifiants invalides",
        "linearity":"Linéarité","sn":"S/N","admin":"Admin","company":"Nom de la compagnie",
        "input_csv":"CSV","input_manual":"Saisie manuelle","concentration":"Concentration",
        "signal":"Signal","unit":"Unité","generate_pdf":"Générer PDF","download_pdf":"Télécharger PDF",
        "download_csv":"Télécharger CSV","sn_classic":"S/N Classique","sn_usp":"S/N USP",
        "lod":"LOD (conc.)","loq":"LOQ (conc.)","formulas":"Formules","select_region":"Sélectionner la zone",
        "add_user":"Ajouter utilisateur","delete_user":"Supprimer utilisateur","modify_user":"Modifier mot de passe",
        "enter_username":"Nom d'utilisateur","enter_password":"Mot de passe (simple)",
        "upload_chrom":"Importer chromatogramme (CSV, PNG, JPG, PDF)","digitize_info":"Digitizing : OCR tenté si pytesseract installé",
        "export_sn_pdf":"Exporter S/N PDF","download_original_pdf":"Télécharger PDF original",
        "change_pwd":"Changer mot de passe (hors session)"
    },
    "EN": {
        "app_title":"LabT","powered":"Powered by BnB","username":"Username",
        "password":"Password","login":"Login","logout":"Logout","invalid":"Invalid credentials",
        "linearity":"Linearity","sn":"S/N","admin":"Admin","company":"Company name",
        "input_csv":"CSV","input_manual":"Manual input","concentration":"Concentration",
        "signal":"Signal","unit":"Unit","generate_pdf":"Generate PDF","download_pdf":"Download PDF",
        "download_csv":"Download CSV","sn_classic":"S/N Classic","sn_usp":"S/N USP",
        "lod":"LOD (conc.)","loq":"LOQ (conc.)","formulas":"Formulas","select_region":"Select region",
        "add_user":"Add user","delete_user":"Delete user","modify_user":"Modify password",
        "enter_username":"Username","enter_password":"Password (simple)",
        "upload_chrom":"Upload chromatogram (CSV, PNG, JPG, PDF)","digitize_info":"Digitizing: OCR attempted if pytesseract available",
        "export_sn_pdf":"Export S/N PDF","download_original_pdf":"Download original PDF",
        "change_pwd":"Change password (outside session)"
    }
}

def t(key):
    lang = st.session_state.get("lang","FR")
    return TEXTS.get(lang,TEXTS["FR"]).get(key,key)

# -------------------------
# Session defaults
# -------------------------
for k in ["lang","user","role","linear_slope"]:
    if k not in st.session_state:
        st.session_state[k]=None
st.session_state.lang = st.session_state.lang or "FR"

# -------------------------
# PDF generation
# -------------------------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_bytes:
        try:
            pdf.image(logo_bytes, x=10, y=8, w=25)
        except:
            pass
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,title,ln=1,align="C")
    pdf.set_font("Arial","",11)
    pdf.ln(4)
    for line in lines:
        pdf.multi_cell(0,7,line)
    if img_bytes:
        try:
            pdf.ln(4)
            pdf.image(img_bytes,x=20,w=170)
        except:
            pass
    return pdf.output(dest="S").encode("latin1")

# -------------------------
# OCR helper
# -------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
    if pytesseract is None:
        return pd.DataFrame(columns=["X","Y"])
    text = pytesseract.image_to_string(img)
    rows=[]
    for line in text.splitlines():
        if not line.strip():
            continue
        for sep in [",",";","\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip()!=""]
                if len(parts)>=2:
                    try: x=float(parts[0].replace(",",".")); y=float(parts[1].replace(",",".")); rows.append([x,y]); break
                    except: pass
        else:
            parts=line.split()
            if len(parts)>=2:
                try: x=float(parts[0].replace(",",".")); y=float(parts[1].replace(",",".")); rows.append([x,y])
                except: pass
    return pd.DataFrame(rows,columns=["X","Y"])

# -------------------------
# Login screen
# -------------------------
def login_screen():
    st.markdown(f"<h1>{t('app_title')}</h1>", unsafe_allow_html=True)
    lang = st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1)
    st.session_state.lang = lang

    with st.form("login_form"):
        cols = st.columns([2,1])
        with cols[0]:
            username = st.text_input(t("username"))
        with cols[1]:
            password = st.text_input(t("password"),type="password")
        submitted=st.form_submit_button(t("login"))
        if submitted:
            uname=(username or "").strip()
            matched=None
            for u in USERS:
                if u.lower()==uname.lower(): matched=u; break
            if matched and USERS[matched]["password"]==(password or ""):
                st.session_state.user=matched
                st.session_state.role=USERS[matched].get("role","user")
                return
            else: st.error(t("invalid"))
    st.markdown(f"<div style='position:fixed;bottom:8px;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header(t("admin"))
    st.write(t("add_user"))
    col_left,col_right=st.columns([2,1])
    with col_left:
        st.subheader("Existing users")
        for u,info in list(USERS.items()):
            rcols=st.columns([3,1,1])
            rcols[0].write(f"{u} — role: {info.get('role','user')}")
            if rcols[1].button("Modify", key=f"mod_{u}"):
                with st.expander(f"Modify {u}", expanded=True):
                    new_pwd=st.text_input(f"New password for {u}", type="password", key=f"newpwd_{u}")
                    new_role=st.selectbox("Role", ["user","admin"], index=0 if info.get("role","user")=="user" else 1, key=f"newrole_{u}")
                    if st.button("Save", key=f"save_{u}"):
                        if new_pwd: USERS[u]["password"]=new_pwd
                        USERS[u]["role"]=new_role
                        save_users(USERS)
                        st.success(f"Updated {u}")
                        st.experimental_rerun()
            if rcols[2].button("Delete", key=f"del_{u}"):
                if u.lower()=="admin": st.warning("Cannot delete admin")
                else: USERS.pop(u); save_users(USERS); st.success(f"{u} deleted"); st.experimental_rerun()
    with col_right:
        st.subheader(t("add_user"))
        with st.form("form_add_user"):
            new_user=st.text_input(t("enter_username"))
            new_pass=st.text_input(t("enter_password"), type="password")
            role=st.selectbox("Role", ["user","admin"])
            add_sub=st.form_submit_button("Add")
            if add_sub:
                if not new_user.strip() or not new_pass.strip(): st.warning("Enter username and password")
                elif any(u.lower()==new_user.strip().lower() for u in USERS): st.warning("User exists")
                else:
                    USERS[new_user.strip()]={"password":new_pass.strip(),"role":role}
                    save_users(USERS)
                    st.success(f"User {new_user.strip()} added")
                    st.experimental_rerun()

# -------------------------
# Linearity panel
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company=st.text_input(t("company"),key="company_name")
    mode=st.radio("Input mode",[t("input_csv"), t("input_manual")], key="lin_input_mode")
    df=None

    # --- CSV/manual input code (comme avant, inchangé) ---
    # --- Regression ---
    # Numeric conversion, polyfit, plot, slope/export
    # --- Export PDF avec logo, droite de régression, nom compagnie, user, date ---
    # (Intégrer le code complet du snippet précédent pour PDF ici)

# -------------------------
# Signal/Noise panel
# -------------------------
def sn_panel():
    st.header(t("sn"))
    # Upload CSV/PNG/JPG/PDF
    # Region selection sliders
    # Two S/N calculations, LOD/LOQ
    # Export CSV/PDF
    # (Conserver le code existant de sn_panel)

# -------------------------
# Main app
# -------------------------
def main_app():
    st.markdown(f"### {t('app_title')} — {st.session_state.user or ''}")
    cols=st.columns([3,1])
    with cols[1]:
        lang=st.selectbox("",["FR","EN"], index=0 if st.session_state.lang=="FR" else 1)
        st.session_state.lang=lang

    tabs=[t("linearity"), t("sn")]
    if st.session_state.role=="admin": tabs=[t("admin")]
    tabs_widget=st.tabs(tabs)

    if st.session_state.role!="admin":
        with tabs_widget[0]: linearity_panel()
        with tabs_widget[1]: sn_panel()
    else:
        with tabs_widget[0]: admin_panel()

    if st.button(t("logout")):
        st.session_state.user=None; st.session_state.role=None; st.session_state.linear_slope=None

# -------------------------
# Entry
# -------------------------
def run():
    if st.session_state.user: main_app()
    else: login_screen()

if __name__=="__main__":
    run()