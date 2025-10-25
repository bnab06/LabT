# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import base64

# ---------------------
# Traduction bilingue
# ---------------------
LANG = 'fr'  # 'en' ou 'fr'

translations = {
    "login": {"fr": "Connexion", "en": "Login"},
    "username": {"fr": "Nom d'utilisateur", "en": "Username"},
    "password": {"fr": "Mot de passe", "en": "Password"},
    "logout": {"fr": "Déconnexion", "en": "Logout"},
    "linearity": {"fr": "Linéarité", "en": "Linearity"},
    "sn": {"fr": "S/N", "en": "S/N"},
    "submit": {"fr": "Valider", "en": "Submit"},
    "manual_input": {"fr": "Saisie manuelle", "en": "Manual input"},
    "csv_upload": {"fr": "Téléverser CSV", "en": "Upload CSV"},
    "concentration": {"fr": "Concentration", "en": "Concentration"},
    "signal": {"fr": "Signal", "en": "Signal"},
    "unknown_conc": {"fr": "Concentration inconnue", "en": "Unknown concentration"},
    "unknown_signal": {"fr": "Signal inconnu", "en": "Unknown signal"},
    "formula": {"fr": "Formules de calcul", "en": "Calculation formulas"},
    "powered_by": {"fr": "Powered by BnB", "en": "Powered by BnB"}
}

def t(key):
    return translations.get(key, {}).get(LANG, key)

# ---------------------
# Users / Admin
# ---------------------
USERS = {
    "user": "1234",
    "admin": "admin"
}

def check_login(username, password):
    return USERS.get(username) == password

# ---------------------
# Page de configuration
# ---------------------
st.set_page_config(page_title="LabT", layout="wide")

# ---------------------
# Footer
# ---------------------
def footer():
    st.markdown(f"<div style='text-align:center;color:gray;margin-top:50px'>{t('powered_by')}</div>", unsafe_allow_html=True)

# ---------------------
# Login panel
# ---------------------
def login_panel():
    st.title(t("login"))
    username = st.text_input(t("username"))
    password = st.text_input(t("password"), type="password")
    if st.button(t("login")):
        if check_login(username, password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")
    footer()

# ---------------------
# Logout
# ---------------------
def logout():
    for key in ['logged_in', 'username']:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()

# ---------------------
# Linéarité
# ---------------------
def linear_panel():
    st.header(t("linearity"))

    input_type = st.radio("Input type:", [t("manual_input"), t("csv_upload")])
    
    if input_type == t("manual_input"):
        conc_str = st.text_input(f"{t('concentration')} (comma separated)", "1,2,3,4")
        signal_str = st.text_input(f"{t('signal')} (comma separated)", "10,20,30,40")
        try:
            conc = np.array([float(x.strip()) for x in conc_str.split(',')])
            signal = np.array([float(x.strip()) for x in signal_str.split(',')])
        except:
            st.error("Invalid manual input")
            return
    else:
        file = st.file_uploader(t("csv_upload"), type="csv")
        if file:
            df = pd.read_csv(file)
            conc = df[t("concentration")].values
            signal = df[t("signal")].values
        else:
            return
    
    # Calcul linéarité
    m, b = np.polyfit(conc, signal, 1)
    r2 = np.corrcoef(conc, signal)[0,1]**2
    
    st.write(f"R² = {r2:.4f}")
    st.write(f"Pente = {m:.4f}")
    
    # Tracé
    fig, ax = plt.subplots()
    ax.scatter(conc, signal)
    ax.plot(conc, m*conc+b, color='red')
    ax.set_xlabel(t("concentration"))
    ax.set_ylabel(t("signal"))
    st.pyplot(fig)
    
    # Export PDF
    pdf_buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200,10,"Linéarité", ln=True)
    pdf.cell(200,10,f"R2={r2:.4f}, Pente={m:.4f}", ln=True)
    pdf_output = pdf_buffer
    pdf.output(pdf_output)
    st.download_button("Download PDF", data=pdf_buffer.getvalue(), file_name="linearity.pdf", mime="application/pdf")

# ---------------------
# S/N panel
# ---------------------
def sn_panel():
    st.header(t("sn"))
    file = st.file_uploader("Upload image or PDF", type=["png","jpg","pdf"])
    if file:
        st.success("File uploaded successfully")
        # Ici tu peux ajouter l’extraction des données depuis image/pdf
        st.info("S/N calculation to be implemented")

# ---------------------
# Main app
# ---------------------
def main_app():
    st.sidebar.title("Menu")
    menu = st.sidebar.radio("Select", [t("linearity"), t("sn")])
    
    if 'username' in st.session_state and st.session_state['username'] == "admin":
        st.sidebar.button(t("logout"), on_click=logout)
        st.info("Admin panel: gestion des users")
    else:
        st.sidebar.button(t("logout"), on_click=logout)
    
    if menu == t("linearity"):
        linear_panel()
    elif menu == t("sn"):
        sn_panel()

# ---------------------
# Run
# ---------------------
if 'logged_in' not in st.session_state:
    login_panel()
else:
    main_app()