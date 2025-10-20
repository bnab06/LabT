# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
from scipy.signal import find_peaks

# ======================
#   CONFIGURATION
# ======================
st.set_page_config(page_title="LabT", layout="wide")

LANGUAGES = {"Français": "fr", "English": "en"}
USER_FILE = "users.json"


# ======================
#   FONCTIONS UTILISATEURS
# ======================
def load_users():
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"admin": {"password": "admin", "role": "admin"}}


def save_users(users):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


# ======================
#   LOGIN & ADMIN
# ======================
def login_page():
    st.title("🔐 LabT Login")

    users = load_users()
    username = st.text_input("👤 Nom d'utilisateur / Username")
    password = st.text_input("🔑 Mot de passe / Password", type="password")
    lang = st.radio("🌐 Langue / Language", ["Français", "English"], horizontal=True)

    if st.button("Se connecter / Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.user = username
            st.session_state.role = users[username]["role"]
            st.session_state.lang = LANGUAGES[lang]
            st.success("Connexion réussie / Login successful ✅")
            st.rerun()
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect / Invalid username or password")


def admin_panel():
    st.subheader("👑 Gestion des utilisateurs / User management")
    users = load_users()

    st.write("### Liste des utilisateurs")
    for user, info in users.items():
        st.write(f"- {user} ({info['role']})")

    st.write("---")
    st.write("### ➕ Ajouter un utilisateur")
    new_user = st.text_input("Nom d'utilisateur / Username")
    new_pass = st.text_input("Mot de passe / Password", type="password")
    new_role = st.selectbox("Rôle / Role", ["user", "admin"])

    if st.button("Ajouter / Add"):
        if new_user:
            users[new_user] = {"password": new_pass, "role": new_role}
            save_users(users)
            st.success("Utilisateur ajouté / User added ✅")
            st.rerun()

    st.write("---")
    st.write("### ❌ Supprimer un utilisateur")
    del_user = st.selectbox("Choisir / Select", list(users.keys()))
    if st.button("Supprimer / Delete"):
        if del_user != "admin":
            users.pop(del_user)
            save_users(users)
            st.success("Supprimé / Deleted ✅")
            st.rerun()
        else:
            st.warning("Impossible de supprimer l’administrateur principal")


def change_password_page():
    users = load_users()
    st.subheader("🔒 Modifier le mot de passe / Change password")

    old_pass = st.text_input("Ancien mot de passe / Old password", type="password")
    new_pass = st.text_input("Nouveau mot de passe / New password", type="password")

    if st.button("Changer / Change"):
        user = st.session_state.user
        if users[user]["password"] == old_pass:
            users[user]["password"] = new_pass
            save_users(users)
            st.success("Mot de passe changé ✅ / Password updated ✅")
        else:
            st.error("Ancien mot de passe incorrect / Incorrect old password")


# ======================
#   CALCULS
# ======================
def calculate_sn(df, signal_col="Signal", time_col="Time"):
    try:
        y = df[signal_col].values
        peaks, _ = find_peaks(y, height=np.mean(y) + np.std(y))
        if len(peaks) == 0:
            return None, None
        noise = np.std(y)
        sn = np.max(y[peaks]) / noise if noise != 0 else np.nan
        return sn, peaks
    except Exception:
        return None, None


def calculate_lod_loq(sn):
    if sn is None or np.isnan(sn):
        return None, None
    lod = 3 / sn
    loq = 10 / sn
    return lod, loq


def unknown_concentration(std_df, unk_df):
    slope, intercept = np.polyfit(std_df["Concentration"], std_df["Signal"], 1)
    signal_unk = np.mean(unk_df["Signal"])
    conc_unk = (signal_unk - intercept) / slope
    return conc_unk


# ======================
#   APPLICATION PRINCIPALE
# ======================
def main_app():
    lang = st.session_state.lang
    st.title("🧪 LabT – Analyse spectrale")

    options = {
        "fr": ["Calcul S/N", "Calcul inconnu", "LOD & LOQ"],
        "en": ["S/N Calculation", "Unknown Calculation", "LOD & LOQ"]
    }

    selected = st.sidebar.selectbox("Sélection / Select", options[lang])
    uploaded_file = st.file_uploader("📄 Importer un CSV / Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write(df.head())

        if selected in ["Calcul S/N", "S/N Calculation"]:
            sn, peaks = calculate_sn(df)
            if sn:
                st.success(f"S/N = {sn:.2f}")
            else:
                st.warning("Aucun pic détecté / No peak found")

        elif selected in ["Calcul inconnu", "Unknown Calculation"]:
            st.info("Importer un fichier standard / Upload standard CSV")
            std_file = st.file_uploader("Fichier standard", type=["csv"], key="std")
            if std_file:
                std_df = pd.read_csv(std_file)
                conc = unknown_concentration(std_df, df)
                st.success(f"Concentration inconnue = {conc:.4f}")

        elif selected in ["LOD & LOQ"]:
            sn, _ = calculate_sn(df)
            lod, loq = calculate_lod_loq(sn)
            if lod:
                st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")
            else:
                st.warning("Impossible de calculer / Unable to compute")


# ======================
#   ROUTAGE & NAVIGATION
# ======================
def logout():
    st.session_state.clear()
    st.rerun()


if "user" not in st.session_state:
    login_page()
else:
    st.sidebar.write(f"👋 {st.session_state.user}")
    if st.button("Se déconnecter / Logout"):
        logout()

    if st.session_state.role == "admin":
        menu = st.sidebar.radio("Menu", ["Application", "Admin", "Mot de passe"])
        if menu == "Admin":
            admin_panel()
        elif menu == "Mot de passe":
            change_password_page()
        else:
            main_app()
    else:
        menu = st.sidebar.radio("Menu", ["Application", "Mot de passe"])
        if menu == "Mot de passe":
            change_password_page()
        else:
            main_app()