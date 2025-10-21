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
from PIL import Image

# ---------------------------
# Config
# ---------------------------
st.set_page_config(page_title="LabT", layout="wide")

USERS_FILE = "users.json"
LOGO_FILE = "logo.png"

# ---------------------------
# Utilitaires
# ---------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"admin":{"password":"admin"}}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_pwd(pwd):
    return pwd  # simple pour l'exemple

def check_login(username, password):
    users = load_users()
    username_lower = username.lower()
    if username_lower in users and users[username_lower]["password"] == hash_pwd(password):
        return True
    return False

def add_user(username, password):
    users = load_users()
    users[username.lower()] = {"password": hash_pwd(password)}
    save_users(users)

def remove_user(username):
    users = load_users()
    username_lower = username.lower()
    if username_lower in users:
        del users[username_lower]
        save_users(users)

def change_password(username, new_password):
    users = load_users()
    users[username.lower()]["password"] = hash_pwd(new_password)
    save_users(users)

# ---------------------------
# Bilingue
# ---------------------------
def t(fr, en):
    return fr if st.session_state.lang == "FR" else en

# ---------------------------
# Login / Logout
# ---------------------------
def login_page():
    st.title(t("Connexion", "Login"))
    username = st.text_input(t("Nom d'utilisateur", "Username"))
    password = st.text_input(t("Mot de passe", "Password"), type="password")
    if st.button(t("Se connecter", "Login")):
        if check_login(username, password):
            st.session_state.user = username.lower()
            st.session_state.page = "user_menu"
            st.experimental_rerun()
        else:
            st.error(t("Nom d'utilisateur ou mot de passe incorrect", "Wrong username or password"))

def logout():
    st.session_state.user = None
    st.session_state.page = "login"
    st.experimental_rerun()

# ---------------------------
# Admin
# ---------------------------
def admin_page():
    st.title(t("Admin", "Admin"))
    users = load_users()
    st.subheader(t("Utilisateurs existants", "Existing Users"))
    st.write(list(users.keys()))

    new_user = st.text_input(t("Nouvel utilisateur", "New username"))
    new_pwd = st.text_input(t("Mot de passe", "Password"), type="password")
    if st.button(t("Ajouter utilisateur", "Add User")):
        if new_user and new_pwd:
            add_user(new_user, new_pwd)
            st.success(t("Utilisateur ajouté", "User added"))
            st.experimental_rerun()

    del_user = st.text_input(t("Supprimer utilisateur", "Delete username"))
    if st.button(t("Supprimer", "Delete")):
        if del_user:
            remove_user(del_user)
            st.success(t("Utilisateur supprimé", "User removed"))
            st.experimental_rerun()

    if st.button(t("Se déconnecter", "Logout")):
        logout()

# ---------------------------
# Linéarité
# ---------------------------
def linearity_page():
    st.header(t("Linéarité", "Linearity"))
    input_type = st.radio(t("Type d'entrée", "Input type"), [t("CSV", "CSV"), t("Saisie manuelle", "Manual")])
    df = None
    if input_type == t("CSV", "CSV"):
        uploaded_file = st.file_uploader(t("Importer fichier CSV", "Upload CSV"), type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
    else:
        n = st.number_input(t("Nombre de points", "Number of points"), min_value=2, value=2)
        conc = [st.number_input(f"{t('Concentration', 'Concentration')} {i+1}") for i in range(n)]
        signal = [st.number_input(f"{t('Signal', 'Signal')} {i+1}") for i in range(n)]
        df = pd.DataFrame({"Concentration": conc, "Signal": signal})

    if df is not None:
        x = df["Concentration"].values
        y = df["Signal"].values
        slope, intercept = np.polyfit(x, y, 1)
        r2 = np.corrcoef(x, y)[0,1]**2
        st.write(f"{t('Équation', 'Equation')}: y = {slope:.4f}x + {intercept:.4f}")
        st.write(f"R² = {r2:.4f}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name="Points"))
        fig.add_trace(go.Scatter(x=x, y=slope*x+intercept, mode="lines", name="Fit"))
        st.plotly_chart(fig, use_container_width=True)

        choice = st.radio(t("Calculer", "Calculate"), [t("Concentration inconnue", "Unknown concentration"), t("Signal inconnu", "Unknown signal")])
        if choice == t("Concentration inconnue", "Unknown concentration"):
            sig = st.number_input(t("Entrer le signal", "Enter signal"))
            conc_calc = (sig - intercept)/slope
            st.success(f"{t('Concentration calculée', 'Calculated concentration')}: {conc_calc:.4f}")
        else:
            conc_val = st.number_input(t("Entrer la concentration", "Enter concentration"))
            sig_calc = slope*conc_val + intercept
            st.success(f"{t('Signal calculé', 'Calculated signal')}: {sig_calc:.4f}")

        st.session_state["linearity_slope"] = slope

# ---------------------------
# S/N et LOD/LOQ
# ---------------------------
def sn_page():
    st.header(t("Signal / Bruit", "Signal / Noise"))

    uploaded_file = st.file_uploader(t"Importer chromatogramme CSV", "Upload chromatogram CSV"), type=["csv"])
    df = None
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write(df.head())
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.iloc[:,0], y=df.iloc[:,1], mode="lines"))
        st.plotly_chart(fig, use_container_width=True)
        noise_region = st.slider(t("Choisir zone bruit", "Select noise region"), 0, len(df)-1, (0, 10))
        s = df.iloc[noise_region[0]:noise_region[1],1].values
        noise = np.std(s)
        peak = np.max(df.iloc[:,1].values)
        sn_classic = peak / noise
        st.success(f"S/N classique: {sn_classic:.2f}")

        slope = st.session_state.get("linearity_slope")
        if slope:
            lod = 3.3*noise/slope
            loq = 10*noise/slope
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

# ---------------------------
# PDF Export
# ---------------------------
def pdf_page():
    st.header(t("Exporter rapport PDF", "Export PDF Report"))
    company = st.text_input(t("Nom de l'entreprise", "Company name"))
    if not company:
        st.warning(t("Veuillez saisir le nom de l'entreprise", "Please enter company name"))
        return
    user = st.session_state.get("user", "Unknown")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if st.button(t("Générer PDF", "Generate PDF")):
        pdf = FPDF()
        pdf.add_page()
        if os.path.exists(LOGO_FILE):
            pdf.image(LOGO_FILE, 10, 8, 33)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"{company}", ln=True)
        pdf.cell(0, 10, f"{t('Utilisateur', 'User')}: {user}", ln=True)
        pdf.cell(0, 10, f"{t('Date', 'Date')}: {now}", ln=True)
        pdf.output("rapport.pdf")
        st.success(t("PDF généré avec succès", "PDF successfully generated"))
        with open("rapport.pdf", "rb") as f:
            st.download_button(t("Télécharger PDF", "Download PDF"), f, file_name="rapport.pdf")

# ---------------------------
# Changement mot de passe
# ---------------------------
def change_password_page():
    st.header(t("Changer mot de passe", "Change password"))
    new_pwd = st.text_input(t("Nouveau mot de passe", "New password"), type="password")
    if st.button(t("Valider", "Submit")):
        if new_pwd:
            change_password(st.session_state.user, new_pwd)
            st.success(t("Mot de passe modifié", "Password changed"))

# ---------------------------
# Menu utilisateur
# ---------------------------
def user_menu():
    st.sidebar.title(t("Menu", "Menu"))
    choice = st.sidebar.radio("Navigation", [
        t("Linéarité", "Linearity"),
       