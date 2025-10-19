# ========================
# PARTIE 1 : IMPORTS & INITIALISATION
# ========================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import os

# ----------------------
# Initialisation session_state
# ----------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

if "role" not in st.session_state:
    st.session_state.role = None

if "unit" not in st.session_state:
    st.session_state.unit = ""  # Unité pour calcul inconnu

if "lang" not in st.session_state:
    st.session_state.lang = "en"  # Langue par défaut

if "company_name" not in st.session_state:
    st.session_state.company_name = ""

if "df" not in st.session_state:
    st.session_state.df = None

if "slope" not in st.session_state:
    st.session_state.slope = NoneType
# ========================
# PARTIE 2 : LOGIN & LANGUE
# ========================

def login_action(username, password):
    # Exemples simples d'utilisateurs
    users = {
        "admin": {"password": "admin", "role": "admin"},
        "user": {"password": "user", "role": "user"}
    }
    if username in users and password == users[username]["password"]:
        st.session_state.role = users[username]["role"]
        st.session_state.current_page = "menu"
        st.success("Login successful ✅ / Connexion réussie ✅")
    else:
        st.error("Invalid credentials / Identifiants invalides")

def login_page():
    st.title("LabT App")
    lang = st.selectbox("Language / Langue:", ["English", "Français"], index=0 if st.session_state.lang=="en" else 1)
    st.session_state.lang = "en" if lang=="English" else "fr"

    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    st.button("Login / Connexion", on_click=login_action, args=(username, password))
# ========================
# PARTIE 3 : MENU & UPLOAD CSV
# ========================

def menu_page():
    st.header("Main Menu / Menu Principal")
    
    st.text_input("Company Name / Nom de l’entreprise", key="company_name")
    
    choice = st.radio(
        "Choose an option / Choisissez une option:",
        ["Calculate / Calculer", "Generate PDF / Générer PDF", "Logout / Déconnexion"]
    )
    
    if choice == "Calculate / Calculer":
        st.session_state.current_page = "calculate"
    elif choice == "Generate PDF / Générer PDF":
        st.session_state.current_page = "export_pdf"
    elif choice == "Logout / Déconnexion":
        st.session_state.current_page = "login"
        st.session_state.role = None

def calculate_page():
    st.header("Calculation / Calcul")
    
    uploaded_file = st.file_uploader("Upload CSV / Importer CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            st.session_state.df = pd.read_csv(uploaded_file)
            st.success("CSV loaded successfully / CSV chargé avec succès")
        except Exception as e:
            st.error(f"Error reading CSV / Erreur lecture CSV: {str(e)}")

    # Bouton retour
    st.button("Back / Retour", on_click=lambda: st.session_state.update({"current_page":"menu"}))
# ========================
# PARTIE 4 : CALCULS & PDF
# ========================

def calculate_sn(df, unit, use_linearity=False):
    try:
        # Exemple S/N classique et USP
        sn_classic = df['Signal'].max() / df['Signal'].std()
        sn_usp = sn_classic * 0.9  # Simplifié pour illustration
        slope = None
        if use_linearity:
            x = df['Concentration']
            y = df['Signal']
            slope = np.polyfit(x, y, 1)[0]
        return sn_classic, sn_usp, slope
    except Exception as e:
        st.error(f"Error in calculation / Erreur dans les calculs: {str(e)}")
        return None, None, None

def export_pdf():
    if st.session_state.company_name.strip() == "":
        st.warning("Please enter the company name / Veuillez saisir le nom de l’entreprise")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"App: LabT / Société: {st.session_state.company_name}", ln=True)
    
    if st.session_state.df is not None:
        sn_classic, sn_usp, slope = calculate_sn(st.session_state.df, st.session_state.unit)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"S/N classic: {sn_classic:.2f if sn_classic else 'N/A'} {st.session_state.unit}", ln=True)
        pdf.cell(0, 10, f"S/N USP: {sn_usp:.2f if sn_usp else 'N/A'} {st.session_state.unit}", ln=True)
        if slope:
            pdf.cell(0, 10, f"Slope for LOQ/LOD: {slope:.4f}", ln=True)

    pdf_file = f"{st.session_state.company_name}_LabT_report.pdf"
    pdf.output(pdf_file)
    st.success(f"PDF generated: {pdf_file}")

# ----------------------
# PAGE ROUTING
# ----------------------
if st.session_state.current_page == "login":
    login_page()
elif st.session_state.current_page == "menu":
    menu_page()
elif st.session_state.current_page == "calculate":
    calculate_page()
elif st.session_state.current_page == "export_pdf":
    export_pdf()
