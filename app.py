# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import json
import os

# ----------------- Config -----------------
st.set_page_config(page_title="LabT App", layout="wide")

# ----------------- Utils -----------------
def t(fr, en):
    lang = st.session_state.get("lang", "FR")
    return fr if lang == "FR" else en

# ----------------- Session State -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

# ----------------- Users -----------------
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"admin":{"password":"admin"}}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ----------------- Authentication -----------------
def login_screen():
    st.title(t("Connexion", "Login"))
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(t("Nom d'utilisateur", "Username")).lower()
    with col2:
        password = st.text_input(t("Mot de passe", "Password"), type="password")
    if st.button(t("Se connecter", "Login")):
        users = load_users()
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.experimental_rerun()
        else:
            st.error(t("Nom d’utilisateur ou mot de passe incorrect", "Wrong username or password"))

def logout():
    if st.button(t("Se déconnecter", "Logout")):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.experimental_rerun()

# ----------------- Admin -----------------
def admin_page():
    st.header(t("Administration", "Admin Panel"))
    logout()
    st.subheader(t("Ajouter un utilisateur", "Add User"))
    new_user = st.text_input(t("Nom d'utilisateur", "Username"))
    new_pass = st.text_input(t("Mot de passe", "Password"), type="password")
    if st.button(t("Ajouter", "Add")):
        if new_user and new_pass:
            users = load_users()
            users[new_user.lower()] = {"password": new_pass}
            save_users(users)
            st.success(t("Utilisateur ajouté", "User added"))
    st.subheader(t("Liste des utilisateurs", "Users List"))
    users = load_users()
    for u in users:
        st.write(u)

# ----------------- User -----------------
def change_password():
    st.subheader(t("Changer mot de passe", "Change Password"))
    old = st.text_input(t("Ancien mot de passe", "Old Password"), type="password")
    new = st.text_input(t("Nouveau mot de passe", "New Password"), type="password")
    if st.button(t("Valider", "Submit")):
        users = load_users()
        uname = st.session_state.user
        if users[uname]["password"] == old:
            users[uname]["password"] = new
            save_users(users)
            st.success(t("Mot de passe changé", "Password changed"))
        else:
            st.error(t("Ancien mot de passe incorrect", "Old password incorrect"))

# ----------------- Linearity -----------------
def linearity_screen():
    st.header(t("Linéarité", "Linearity"))
    option = st.radio(t("Choisissez la méthode", "Choose input method"), [t("Saisie manuelle", "Manual"), t("Importer CSV", "Upload CSV")])
    if option == t("Saisie manuelle", "Manual"):
        conc = st.text_area(t("Concentrations séparées par virgule", "Concentrations comma-separated"))
        sig = st.text_area(t("Signaux séparés par virgule", "Signals comma-separated"))
        if st.button(t("Calculer", "Calculate")):
            try:
                x = np.array([float(i) for i in conc.split(",")])
                y = np.array([float(i) for i in sig.split(",")])
                slope, intercept = np.polyfit(x, y, 1)
                r2 = np.corrcoef(x, y)[0,1]**2
                st.write(f"{t('Pente', 'Slope')}: {slope}, {t('Intercept', 'Intercept')}: {intercept}, R²: {r2}")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=x, y=y, mode='markers', name='Data'))
                fig.add_trace(go.Scatter(x=x, y=slope*x+intercept, mode='lines', name='Fit'))
                st.plotly_chart(fig)
            except:
                st.error(t("Erreur dans les données", "Data error"))
    else:
        uploaded_file = st.file_uploader(t("Importer CSV", "Upload CSV"), type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            if "Concentration" in df.columns and "Signal" in df.columns:
                x = df["Concentration"].values
                y = df["Signal"].values
                slope, intercept = np.polyfit(x, y, 1)
                r2 = np.corrcoef(x, y)[0,1]**2
                st.write(f"{t('Pente', 'Slope')}: {slope}, {t('Intercept', 'Intercept')}: {intercept}, R²: {r2}")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=x, y=y, mode='markers', name='Data'))
                fig.add_trace(go.Scatter(x=x, y=slope*x+intercept, mode='lines', name='Fit'))
                st.plotly_chart(fig)
            else:
                st.error(t("CSV doit contenir 'Concentration' et 'Signal'", "CSV must contain 'Concentration' and 'Signal'"))

# ----------------- Main -----------------
def main():
    st.sidebar.title("Lang")
    if st.sidebar.button("FR"):
        st.session_state.lang = "FR"
    if st.sidebar.button("EN"):
        st.session_state.lang = "EN"

    if not st.session_state.logged_in:
        login_screen()
    else:
        if st.session_state.user.lower() == "admin":
            admin_page()
        else:
            st.header(f"{t('Bienvenue', 'Welcome')}, {st.session_state.user}")
            logout()
            change_password()
            linearity_screen()
            st.info(t("Fonctionnalités S/N et LOD/LOQ à ajouter ici", "S/N and LOD/LOQ functionalities here"))

if __name__ == "__main__":
    main()