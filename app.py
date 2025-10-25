# =========================
# LabT Application - Bilingue FR/EN
# =========================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from fpdf import FPDF
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io
import plotly.graph_objects as go
import hashlib
import json

# ---------- Config ----------
st.set_page_config(page_title="LabT", layout="wide")

# ---------- Traductions ----------
TEXTS = {
    "login": {"FR": "Connexion", "EN": "Login"},
    "username": {"FR": "Nom d'utilisateur", "EN": "Username"},
    "password": {"FR": "Mot de passe", "EN": "Password"},
    "logout": {"FR": "Se déconnecter", "EN": "Logout"},
    "linearity": {"FR": "Linéarité", "EN": "Linearity"},
    "sn": {"FR": "S/N", "EN": "S/N"},
    "upload_file": {"FR": "Charger fichier", "EN": "Upload file"},
    "file_type": {"FR": "Type de fichier", "EN": "File type"},
    "show_formulas": {"FR": "Afficher formules", "EN": "Show formulas"},
    "export_pdf": {"FR": "Exporter PDF", "EN": "Export PDF"},
    "menu": {"FR": "Menu", "EN": "Menu"},
    "select_module": {"FR": "Sélectionner module", "EN": "Select Module"},
    "concentration": {"FR": "Concentration", "EN": "Concentration"},
    "signal": {"FR": "Signal", "EN": "Signal"},
    "choose_file": {"FR": "Choisir fichier", "EN": "Choose file"},
    "powered_by": {"FR": "Propulsé par BnB", "EN": "Powered by BnB"},
}

def t(key):
    lang = st.session_state.get("lang","FR")
    return TEXTS.get(key,{}).get(lang,key)

# ---------- Session state ----------
if "user" not in st.session_state: st.session_state.user = None
if "role" not in st.session_state: st.session_state.role = None
if "lang" not in st.session_state: st.session_state.lang = "FR"
if "linear_slope" not in st.session_state: st.session_state.linear_slope = None

# ---------- Users database ----------
USERS = {
    "admin":"admin123",
    "user":"user123"
}

# ---------- Auth helpers ----------
def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_password(user,pwd):
    return USERS.get(user)==pwd

# ---------- Digitizing helpers ----------
def extract_from_image(image):
    text = pytesseract.image_to_string(image)
    data=[]
    for line in text.splitlines():
        if "," in line or "\t" in line:
            parts=line.replace("\t",",").split(",")
            try:
                x,y=float(parts[0]),float(parts[1])
                data.append([x,y])
            except: pass
    return pd.DataFrame(data,columns=["X","Y"])

def extract_from_pdf(file):
    images = convert_from_path(file)
    all_data=pd.DataFrame(columns=["X","Y"])
    for img in images:
        df = extract_from_image(img)
        all_data = pd.concat([all_data,df])
    return all_data.reset_index(drop=True)

# ---------- S/N helpers ----------
def sn_classic(signal_peak, signal_noise):
    return signal_peak / signal_noise

def sn_usp(signal_peak, std_noise):
    return signal_peak / std_noise

# ---------- Login Panel ----------
def login_panel():
    st.title("LabT")
    st.selectbox("Langue / Language", ["FR","EN"], key="lang")
    st.write(t("powered_by"))
    if st.session_state.user is None:
        username = st.text_input(t("username"))
        password = st.text_input(t("password"), type="password")
        if st.button(t("login")):
            if check_password(username,password):
                st.session_state.user = username
                st.session_state.role = "admin" if username=="admin" else "user"
                st.experimental_rerun()
            else:
                st.error("Identifiants invalides / Invalid login")

# ---------- Logout ----------
def logout():
    st.session_state.user = None
    st.session_state.role = None
    st.experimental_rerun()

# ---------- Linearity Panel ----------
def linear_panel():
    st.header(t("linearity"))
    input_type = st.radio("Input type / Type de saisie", ["CSV","Manual"])
    df=None
    if input_type=="CSV":
        file = st.file_uploader(t("choose_file"), type=["csv"])
        if file:
            try:
                df = pd.read_csv(file)
                if "Concentration" not in df.columns or "Signal" not in df.columns:
                    st.error("CSV must contain Concentration and Signal columns")
                    return
            except:
                st.error("Error reading CSV")
                return
    else:
        conc_values = st.text_area("Concentration values (comma separated)")
        signal_values = st.text_area("Signal values (comma separated)")
        try:
            conc = [float(i) for i in conc_values.split(",")]
            signal = [float(i) for i in signal_values.split(",")]
            df = pd.DataFrame({"Concentration":conc,"Signal":signal})
        except:
            st.error("Invalid manual input")
            return
    if df is not None:
        slope, intercept = np.polyfit(df["Concentration"], df["Signal"],1)
        r2 = np.corrcoef(df["Concentration"],df["Signal"])[0,1]**2
        st.session_state.linear_slope = slope
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Concentration"],y=df["Signal"],mode="markers",name="Data"))
        fig.add_trace(go.Scatter(x=df["Concentration"],y=slope*df["Concentration"]+intercept,mode="lines",name="Fit"))
        fig.update_layout(xaxis_title=t("concentration"), yaxis_title=t("signal"))
        st.plotly_chart(fig)
        st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée: {intercept:.4f}, R²: {r2:.4f}")

        # Calcul automatique
        calc_choice = st.selectbox("Calculate / Calculer", ["Y from X", "X from Y"])
        if calc_choice=="Y from X":
            val = st.number_input("X value")
            st.write("Y:", slope*val+intercept)
        else:
            val = st.number_input("Y value")
            st.write("X:", (val-intercept)/slope)

        # Export PDF
        if st.button(t("export_pdf")):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial",size=12)
            pdf.cell(200,10,txt="LabT - Linearity Report",ln=True,align="C")
            pdf.cell(200,10,txt=f"User: {st.session_state.user}",ln=True)
            pdf.cell(200,10,txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
            pdf.cell(200,10,txt=f"Slope: {slope:.4f}",ln=True)
            pdf.cell(200,10,txt=f"Intercept: {intercept:.4f}",ln=True)
            pdf.cell(200,10,txt=f"R²: {r2:.4f}",ln=True)
            pdf_output = io.BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)
            st.download_button("Download PDF", pdf_output, file_name="linearity_report.pdf", mime="application/pdf")

# ---------- S/N Panel ----------
def sn_panel():
    st.header(t("sn"))
    file_type = st.selectbox(t("file_type"), ["CSV","PDF","PNG"])
    file = st.file_uploader(t("choose_file"), type=["csv","pdf","png"])
    df=None
    if file:
        if file_type=="CSV":
            try: df=pd.read_csv(file)
            except: st.error("CSV read error"); return
        elif file_type=="PDF":
            df = extract_from_pdf(file)
        elif file_type=="PNG":
            img = Image.open(file)
            df = extract_from_image(img)
    if df is not None and not df.empty:
        st.line_chart(df.set_index("X")["Y"])
        x_min,x_max = st.slider("Select zone / Zone de calcul", float(df["X"].min()), float(df["X"].max()), (float(df["X"].min()), float(df["X"].max())))
        selected = df[(df["X"]>=x_min)&(df["X"]<=x_max)]
        signal_peak = selected["Y"].max()
        signal_noise = selected["Y"].min()
        std_noise = selected["Y"].std()
        classic = sn_classic(signal_peak, signal_noise)
        usp = sn_usp(signal_peak, std_noise)
        st.subheader("S/N Values")
        st.write(f"Classical / Classique: {classic:.2f}")
        st.write(f"USP: {usp:.2f}")
        if st.button(t("show_formulas")):
            st.info("S/N Classic = Signal Peak / Noise\nS/N USP = Signal Peak / Std(Noise)")
        if st.button(t("export_pdf")):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial",size=12)
            pdf.cell(200,10,txt="LabT - S/N Report",ln=True,align="C")
            pdf.cell(200,10,txt=f"User: {st.session_state.user}",ln=True)
            pdf.cell(200,10,txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
            pdf.cell(200,10,txt=f"S/N Classic: {classic:.2f}",ln=True)
            pdf.cell(200,10,txt=f"S/N USP: {usp:.2f}",ln=True)
            pdf_output = io.BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)
            st.download_button("Download PDF", pdf_output, file_name="sn_report.pdf", mime="application/pdf")

# ---------- Admin Panel ----------
def admin_panel():
    st.header("Admin Panel / Gestion des utilisateurs")
    st.write("Users:")
    for user in USERS.keys():
        st.write(f"- {user}")
    new_user = st.text_input("New Username / Nouvel utilisateur")
    new_password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Add User / Ajouter utilisateur"):
        if new_user and new_password:
            USERS[new_user] = new_password
            st.success(f"User {new_user} added")
    st.sidebar.button(t("logout"), on_click=logout)

# ---------- Main App ----------
def main_app():
    menu = st.sidebar.selectbox(t("menu"), [t("linearity"), t("sn")])
    if menu==t("linearity"): linear_panel()
    elif menu==t("sn"): sn_panel()
    if st.session_state.role=="admin":
        st.sidebar.subheader("Admin")
        st.sidebar.button("Admin Panel", on_click=admin_panel)
    st.sidebar.button(t("logout"), on_click=logout)

# ---------- Main ----------
if st.session_state.user is None:
    login_panel()
else:
    main_app()