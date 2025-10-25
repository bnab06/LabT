# =========================
# LabT - Application Fusionnée
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

# ---------- Session ----------
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

# ---------- Traductions ----------
texts = {
    "FR": {
        "login": "Connexion",
        "user": "Utilisateur",
        "password": "Mot de passe",
        "logout": "Se déconnecter",
        "linear": "Linéarité",
        "sn": "S/N",
        "choose_file": "Charger fichier",
        "file_type": "Type de fichier",
        "upload": "Importer",
        "classic": "Classique",
        "usp": "USP",
        "show_formulas": "Afficher formules",
        "export_pdf": "Exporter PDF",
        "select_module": "Sélectionner le module",
        "navigation": "Navigation",
    },
    "EN": {
        "login": "Login",
        "user": "User",
        "password": "Password",
        "logout": "Logout",
        "linear": "Linearity",
        "sn": "S/N",
        "choose_file": "Upload file",
        "file_type": "File type",
        "upload": "Upload",
        "classic": "Classic",
        "usp": "USP",
        "show_formulas": "Show formulas",
        "export_pdf": "Export PDF",
        "select_module": "Select Module",
        "navigation": "Navigation",
    }
}

def t(key):
    return texts[st.session_state.lang].get(key, key)

# ---------- Authentification ----------
USERS = {"admin": "admin123", "user": "user123"}

def login_panel():
    st.title("LabT")
    st.selectbox("Langue / Language", ["FR", "EN"], key="lang")
    
    if st.session_state.user is None:
        username = st.text_input(t("user"))
        password = st.text_input(t("password"), type="password")
        if st.button(t("login")):
            if username in USERS and USERS[username] == password:
                st.session_state.user = username
                st.session_state.role = "admin" if username=="admin" else "user"
                st.experimental_rerun()
            else:
                st.error("Invalid login / Identifiants invalides")

# ---------- Logout ----------
def logout():
    st.session_state.user = None
    st.session_state.role = None
    st.experimental_rerun()

# ---------- Linéarité ----------
def linear_panel():
    st.header(t("linear"))
    
    input_type = st.radio("Input type / Type de saisie", ["CSV", "Manual"])
    
    df = None
    if input_type == "CSV":
        file = st.file_uploader(t("choose_file"), type=["csv"])
        if file:
            try:
                df = pd.read_csv(file)
                if "X" not in df.columns or "Y" not in df.columns:
                    st.error("CSV must contain X and Y columns")
                    return
            except:
                st.error("Error reading CSV")
                return
    else:
        x_values = st.text_area("X values (comma separated)")
        y_values = st.text_area("Y values (comma separated)")
        try:
            x = [float(i) for i in x_values.split(",")]
            y = [float(i) for i in y_values.split(",")]
            df = pd.DataFrame({"X": x, "Y": y})
        except:
            st.error("Invalid manual input")
            return
    
    if df is not None:
        slope, intercept = np.polyfit(df["X"], df["Y"], 1)
        r2 = np.corrcoef(df["X"], df["Y"])[0,1]**2
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode="markers", name="Data"))
        fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode="lines", name="Fit"))
        st.plotly_chart(fig)
        
        st.write(f"Slope / Pente: {slope:.4f}")
        st.write(f"Intercept / Ordonnée: {intercept:.4f}")
        st.write(f"R²: {r2:.4f}")
        
        calc_choice = st.selectbox("Calculate / Calculer", ["Y from X", "X from Y"])
        val = st.number_input("Value / Valeur")
        if calc_choice=="Y from X":
            st.write("Y:", slope*val+intercept)
        else:
            st.write("X:", (val-intercept)/slope)
        
        if st.button(t("export_pdf")):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
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
        
        return slope
    return None

# ---------- S/N ----------
def read_csv(file):
    try:
        return pd.read_csv(file)
    except:
        st.error("CSV read error")
        return None

def extract_from_image(image):
    text = pytesseract.image_to_string(image)
    data = []
    for line in text.splitlines():
        if "," in line or "\t" in line:
            parts = line.replace("\t",",").split(",")
            try:
                x, y = float(parts[0]), float(parts[1])
                data.append([x, y])
            except:
                pass
    return pd.DataFrame(data, columns=["X","Y"])

def extract_from_pdf(file):
    images = convert_from_path(file)
    all_data = pd.DataFrame(columns=["X","Y"])
    for img in images:
        df = extract_from_image(img)
        all_data = pd.concat([all_data, df])
    return all_data.reset_index(drop=True)

def sn_classic(signal_peak, signal_noise):
    return signal_peak / signal_noise

def sn_usp(signal_peak, std_noise):
    return signal_peak / std_noise

def sn_panel(slope=None):
    st.header(t("sn"))
    
    file_type = st.selectbox(t("file_type"), ["CSV","PDF","PNG"])
    file = st.file_uploader(t("choose_file"), type=["csv","pdf","png"])
    
    df = None
    if file:
        if file_type=="CSV":
            df = read_csv(file)
        elif file_type=="PDF":
            df = extract_from_pdf(file)
        elif file_type=="PNG":
            img = Image.open(file)
            df = extract_from_image(img)
    
    if df is not None and not df.empty:
        st.line_chart(df.set_index("X")["Y"])
        
        x_min,x_max = st.slider("Select zone / Zone de calcul", float(df["X"].min()), float(df["X"].max()), (float(df["X"].min()), float(df["X"].max())))
        selected = df[(df["X"]>=x_min) & (df["X"]<=x_max)]
        
        signal_peak = selected["Y"].max()
        signal_noise = selected["Y"].min()
        std_noise = selected["Y"].std()
        
        classic = sn_classic(signal_peak, signal_noise)
        usp = sn_usp(signal_peak, std_noise)
        if slope:
            usp *= slope
        
        st.subheader("S/N Values")
        st.write(f"Classical / Classique: {classic:.2f}")
        st.write(f"USP: {usp:.2f}")
        
        if st.button(t("show_formulas")):
            st.info("S/N Classic = Signal Peak / Noise\nS/N USP = Signal Peak / Std(Noise)")
        
        if st.button(t("export_pdf")):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200,10,txt="LabT - S/N Report",ln=True,align="C")
            pdf.cell(200,10,txt=f"User: {st.session_state.user}",ln=True)
            pdf.cell(200,10,txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
            pdf.cell(200,10,txt=f"S/N Classic: {classic:.2f}",ln=True)
            pdf.cell(200,10,txt=f"S/N USP: {usp:.2f}",ln=True)
            pdf_output = io.BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)
            st.download_button("Download PDF", pdf_output, file_name="sn_report.pdf", mime="application/pdf")

# ---------- Main App ----------
def main():
    st.set_page_config(page_title="LabT", layout="wide")
    
    if st.session_state.user is None:
        login_panel()
    else:
        st.sidebar.write(f"{t('user')}: {st.session_state.user} ({st.session_state.role})")
        st.sidebar.button(t("logout"), on_click=logout)
        
        slope = None
        choice = st.sidebar.radio(t("navigation"), [t("linear"), t("sn")])
        
        if choice == t("linear"):
            slope = linear_panel()
        else:
            sn_panel(slope=slope)

if __name__=="__main__":
    main()