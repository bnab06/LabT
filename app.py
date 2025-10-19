import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "selected_option" not in st.session_state:
    st.session_state.selected_option = None
if "unit" not in st.session_state:
    st.session_state.unit = ""
if "previous_menu" not in st.session_state:
    st.session_state.previous_menu = None
if "slope" not in st.session_state:
    st.session_state.slope = None
if "intercept" not in st.session_state:
    st.session_state.intercept = None

# Example users database
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}
# ----------------------------
# Utility functions
# ----------------------------
def check_login(user, pwd):
    return user.lower() in USERS and USERS[user.lower()]["password"] == pwd

def main_menu():
    options = ["Unknown calculation", "S/N Analysis", "Admin"]
    if st.session_state.language == "French":
        options = ["Calcul inconnu", "Analyse S/N", "Panneau Admin"]
    return st.selectbox("Choose option / Choisir une option:", options, key="main_menu")

def previous_menu_button():
    if st.session_state.previous_menu:
        if st.button("← Back / ← Retour"):
            st.session_state.selected_option = st.session_state.previous_menu

# ----------------------------
# Login
# ----------------------------
def login_page():
    st.title("LabT Application")
    st.session_state.language = st.radio(
        "Language / Langue:", ("English", "French"), index=0, key="language_selector"
    )

    user = st.text_input("Username / Nom d'utilisateur")
    pwd = st.text_input("Password / Mot de passe", type="password")

    if st.button("Login / Connexion"):
        if check_login(user, pwd):
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Invalid credentials / Identifiants incorrects")
def admin_menu():
    st.header("Admin Panel / Panneau Admin")
    actions = ["Add user", "Delete user"]
    if st.session_state.language == "French":
        actions = ["Ajouter un utilisateur", "Supprimer un utilisateur"]

    action = st.selectbox("Action / Action:", actions, key="admin_actions")
    st.session_state.previous_menu = st.session_state.selected_option

def unknown_calculation():
    st.header("Unknown Calculation / Calcul Inconnu")
    st.session_state.previous_menu = st.session_state.selected_option
    # Inputs
    conc = st.number_input("Concentration / Concentration", min_value=0.0)
    signal = st.number_input("Signal / Signal", min_value=0.0)
    st.session_state.unit = st.text_input("Unit / Unité")
    if st.button("Calculate / Calculer"):
        if not st.session_state.unit:
            st.warning("Please enter the unit before calculating / Veuillez entrer l'unité avant de calculer")
        else:
            result = signal / conc if conc else 0
            st.success(f"Result / Résultat: {result:.4f} {st.session_state.unit}")
def sn_analysis():
    st.header("S/N Analysis / Analyse S/N")
    st.session_state.previous_menu = st.session_state.selected_option
    st.write("Upload CSV or input data / Importer CSV ou saisir données")
    # Exemple simplifié pour CSV upload
    uploaded_file = st.file_uploader("Upload CSV / Importer CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())
        if st.button("Compute S/N / Calculer S/N"):
            st.success("S/N computed / S/N calculé (placeholder)")

# ----------------------------
# Main execution
# ----------------------------
if not st.session_state.logged_in:
    login_page()
else:
    st.session_state.selected_option = main_menu()
    selected_option = st.session_state.selected_option

    previous_menu_button()

    if selected_option in ["Admin", "Panneau Admin"]:
        admin_menu()
    elif selected_option in ["Unknown calculation", "Calcul inconnu"]:
        unknown_calculation()
    elif selected_option in ["S/N Analysis", "Analyse S/N"]:
        sn_analysis()