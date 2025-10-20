# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy.signal import find_peaks
from fpdf import FPDF
import json
from datetime import datetime
import os

# =========================================================
# === CONFIGURATION GLOBALE ===
# =========================================================
st.set_page_config(page_title="LabT - Analyse S/N & Linéarité", layout="wide")

LANGUAGES = {"Français": "fr", "English": "en"}

# =========================================================
# === FONCTIONS UTILITAIRES ===
# =========================================================
def load_users():
    if not os.path.exists("users.json"):
        return {}
    with open("users.json", "r") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def check_login(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return users[username]["role"]
    return None

def change_password(username, new_password):
    users = load_users()
    if username in users:
        users[username]["password"] = new_password
        save_users(users)
        return True
    return False

def add_user(username, password, role="user"):
    users = load_users()
    if username in users:
        return False
    users[username] = {"password": password, "role": role}
    save_users(users)
    return True

def delete_user(username):
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        return True
    return False

# =========================================================
# === CALCULS ===
# =========================================================
def calc_linearity(df):
    x = df["Concentration"].astype(float)
    y = df["Signal"].astype(float)
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs
    y_pred = np.polyval(coeffs, x)
    r2 = np.corrcoef(y, y_pred)[0, 1] ** 2
    return slope, intercept, r2

def calc_sn(signal, noise):
    return np.mean(signal) / np.std(noise)

def calc_sn_usp(peak_region, noise_region):
    signal = np.max(peak_region) - np.min(peak_region)
    noise = np.std(noise_region)
    return signal / noise

def calc_lod_loq(slope, std_dev):
    lod = 3.3 * std_dev / slope
    loq = 10 * std_dev / slope
    return lod, loq

# =========================================================
# === EXPORT PDF ===
# =========================================================
def export_pdf(company, user, data_summary, lang):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Rapport d'analyse" if lang == "fr" else "Analysis Report", 0, 1, "C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Entreprise / Company: {company}", 0, 1)
    pdf.cell(0, 8, f"Utilisateur / User: {user}", 0, 1)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
    pdf.ln(10)
    pdf.multi_cell(0, 8, data_summary)
    pdf.output("rapport.pdf")
    with open("rapport.pdf", "rb") as f:
        st.download_button("📄 Télécharger le rapport PDF", f, file_name="rapport.pdf")

# =========================================================
# === INTERFACE ===
# =========================================================
def login_screen():
    st.title("🔬 LabT - Connexion / Login")
    lang_choice = st.radio("Langue / Language", list(LANGUAGES.keys()))
    lang = LANGUAGES[lang_choice]
    username = st.text_input("Nom d'utilisateur / Username")
    password = st.text_input("Mot de passe / Password", type="password")

    if st.button("Connexion / Login"):
        role = check_login(username, password)
        if role:
            st.session_state["user"] = username
            st.session_state["role"] = role
            st.session_state["lang"] = lang
            st.rerun()
        else:
            st.error("Identifiants invalides / Invalid credentials")

def user_panel():
    lang = st.session_state["lang"]
    username = st.session_state["user"]

    st.sidebar.write(f"👋 {username}")
    if st.sidebar.button("🔐 Changer mot de passe" if lang == "fr" else "Change Password"):
        with st.form("pwd_change"):
            new_pwd = st.text_input("Nouveau mot de passe / New password", type="password")
            submit = st.form_submit_button("Confirmer / Confirm")
            if submit:
                change_password(username, new_pwd)
                st.success("Mot de passe changé / Password updated")

    st.sidebar.button("🚪 Déconnexion / Logout", on_click=lambda: st.session_state.clear())

def admin_panel():
    st.subheader("👤 Gestion des utilisateurs / User Management")
    users = load_users()
    st.write(users)
    new_user = st.text_input("Nouvel utilisateur / New username")
    new_pwd = st.text_input("Mot de passe / Password", type="password")
    if st.button("Ajouter utilisateur / Add user"):
        if add_user(new_user, new_pwd):
            st.success("Utilisateur ajouté / User added")
            st.rerun()
        else:
            st.warning("Utilisateur existe déjà / User already exists")

    del_user = st.selectbox("Supprimer utilisateur / Delete user", list(users.keys()))
    if st.button("Supprimer / Delete"):
        delete_user(del_user)
        st.success("Supprimé / Deleted")
        st.rerun()

def main_app():
    lang = st.session_state["lang"]
    st.title("📊 Analyse S/N, Linéarité, LOD et LOQ")
    company = st.text_input("Entreprise / Company name")
    uploaded_file = st.file_uploader("Importer fichier CSV / Import CSV", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write(df.head())

        # Linéarité
        if st.checkbox("Calculer linéarité / Calculate linearity"):
            slope, intercept, r2 = calc_linearity(df)
            st.success(f"Slope: {slope:.3f}, Intercept: {intercept:.3f}, R²: {r2:.4f}")

        # S/N classique
        if st.checkbox("Calcul S/N classique"):
            sig = df["Signal"]
            noise = sig[:50]
            sn = calc_sn(sig, noise)
            st.info(f"S/N classique = {sn:.2f}")

        # S/N USP
        if st.checkbox("Calcul S/N USP"):
            peak = df["Signal"][100:200]
            noise = df["Signal"][0:50]
            sn_usp = calc_sn_usp(peak, noise)
            st.info(f"S/N USP = {sn_usp:.2f}")

        # LOD / LOQ
        if st.checkbox("Calcul LOD / LOQ"):
            slope, _, _ = calc_linearity(df)
            std_dev = df["Signal"].std()
            lod, loq = calc_lod_loq(slope, std_dev)
            st.success(f"LOD: {lod:.4f}, LOQ: {loq:.4f}")

        # Graph
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.iloc[:, 0], y=df.iloc[:, 1], mode='lines', name="Chromatogramme"))
        st.plotly_chart(fig, use_container_width=True)

        # Export
        if st.button("📤 Générer rapport / Generate report"):
            summary = f"Analyse réalisée par {st.session_state['user']}.\nS/N, linéarité, LOD/LOQ inclus."
            export_pdf(company, st.session_state["user"], summary, lang)

# =========================================================
# === ROUTAGE PRINCIPAL ===
# =========================================================
def main():
    if "user" not in st.session_state:
        login_screen()
    else:
        user_panel()
        if st.session_state["role"] == "admin":
            admin_panel()
        else:
            main_app()

if __name__ == "__main__":
    main()