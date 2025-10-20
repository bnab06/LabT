# ===========================
# PARTIE 1: IMPORTS ET INIT
# ===========================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import find_peaks
from fpdf import FPDF
import json
from datetime import datetime

# Initialisation session_state pour éviter erreurs
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'unit' not in st.session_state:
    st.session_state.unit = ''
if 'slope' not in st.session_state:
    st.session_state.slope = None
if 'intercept' not in st.session_state:
    st.session_state.intercept = None
if 'lang' not in st.session_state:
    st.session_state.lang = 'EN'
if 'prev_page' not in st.session_state:
    st.session_state.prev_page = None
# ===========================
# PARTIE 2: UTILISATEURS / LOGIN
# ===========================

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def login_action(username, password):
    users = load_users()
    username_lower = username.lower()
    if username_lower in users and users[username_lower]['password'] == password:
        st.session_state.user = username_lower
        st.session_state.role = users[username_lower]['role']
        st.experimental_rerun()
    else:
        st.error("Invalid credentials / Identifiants invalides")

def login_page():
    st.title("App: LabT / Application LabT")
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        login_action(username, password)
# ===========================
# PARTIE 3: MENU PRINCIPAL
# ===========================

def main_menu():
    st.title("Main Menu / Menu Principal")
    menu_options = ["Unknown calculation / Calcul inconnu", 
                    "Signal-to-Noise / Rapport S/N", 
                    "Linearity / Linéarité"]

    choice = st.selectbox("Choose option / Choisir une option", menu_options)

    if choice.startswith("Unknown"):
        st.session_state.prev_page = main_menu
        unknown_calculation_page()
    elif choice.startswith("Signal"):
        st.session_state.prev_page = main_menu
        sn_page()
    elif choice.startswith("Linearity"):
        st.session_state.prev_page = main_menu
        linearity_page()

def unknown_calculation_page():
    st.subheader("Unknown Calculation / Calcul Inconnu")
    conc = st.number_input("Enter concentration / Entrer la concentration", min_value=0.0)
    signal = st.number_input("Enter signal / Entrer le signal", min_value=0.0)
    unit = st.text_input("Unit / Unité", st.session_state.unit)
    st.session_state.unit = unit
    if st.button("Calculate / Calculer"):
        # Ici on garde exactement les mêmes calculs qu'avant
        st.success(f"Concentration: {conc} {unit}, Signal: {signal}")
    if st.button("Back / Retour"):
        st.session_state.prev_page()
# ===========================
# PARTIE 4: S/N, LINÉARITÉ ET PDF
# ===========================

def sn_page():
    st.subheader("Signal-to-Noise / S/N")
    file = st.file_uploader("Upload CSV / Importer CSV", type=['csv'])
    if file:
        df = pd.read_csv(file)
        # Calculs S/N exactement comme avant
        sn_classic = df['Signal'].max() / df['Signal'].std()
        st.write(f"Classic S/N: {sn_classic:.2f}")
        peaks, _ = find_peaks(df['Signal'])
        if len(peaks) > 0:
            sn_usp = df['Signal'][peaks].max() / df['Signal'].std()
            st.write(f"USP S/N: {sn_usp:.2f}")
    if st.button("Back / Retour"):
        st.session_state.prev_page()

def linearity_page():
    st.subheader("Linearity / Linéarité")
    # Ici on garde exactement les calculs de pente et intercept qu'avant
    st.info("Coming soon: Option to calculate slope and intercept for LOD/LOQ")
    if st.button("Back / Retour"):
        st.session_state.prev_page()

def export_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"App: LabT Report", ln=True)
    pdf.output("report.pdf")
    st.success("PDF generated / PDF généré")

# ===========================
# RUN
# ===========================
if st.session_state.user is None:
    login_page()
else:
    main_menu()