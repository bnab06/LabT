# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import cv2
import io
import json
import os
from datetime import datetime
from PIL import Image
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile

# ===============================
# Initialisation session
# ===============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "access" not in st.session_state:
    st.session_state.access = []
if "slope_lin" not in st.session_state:
    st.session_state.slope_lin = None
if "lin_fig" not in st.session_state:
    st.session_state.lin_fig = None
if "sn_result" not in st.session_state:
    st.session_state.sn_result = {}
if "sn_img_annot" not in st.session_state:
    st.session_state.sn_img_annot = None
if "lod_s" not in st.session_state:
    st.session_state.lod_s = None
if "lod_c" not in st.session_state:
    st.session_state.lod_c = None
if "loq_s" not in st.session_state:
    st.session_state.loq_s = None
if "loq_c" not in st.session_state:
    st.session_state.loq_c = None
if "sn_manual" not in st.session_state:
    st.session_state.sn_manual = None
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

# ===============================
# Textes bilingues (FR / EN technical-neutral)
# ===============================
TEXTS = {
    "FR": {
        "app_title": "🔬 LabT — Connexion",
        "username": "Nom d'utilisateur",
        "password": "Mot de passe",
        "login_btn": "Connexion",
        "login_error": "Nom d'utilisateur ou mot de passe incorrect.",
        "powered_by": "Powered by : BnB",
        "linear_title": "📈 Linéarité",
        "sn_title": "📊 Rapport Signal/Bruit (S/N)",
        "download_pdf": "📄 Télécharger le PDF complet avec graphiques",
        "download_pdf_simple": "📄 Télécharger le PDF",
        "lod_label": "**LOD**",
        "loq_label": "**LOQ**"
    },
    "EN": {
        "app_title": "🔬 LabT — Login",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "login_error": "Incorrect username or password.",
        "powered_by": "Powered by : BnB",
        "linear_title": "📈 Linearity",
        "sn_title": "📊 Signal-to-Noise Report (S/N)",
        "download_pdf": "📄 Download full PDF with graphics",
        "download_pdf_simple": "📄 Download PDF",
        "lod_label": "**LOD**",
        "loq_label": "**LOQ**"
    }
}

# ===============================
# Données utilisateurs
# ===============================
USER_FILE = "users.json"
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump({
            "admin": {"password": "admin", "access": ["linearity", "sn"]},
        }, f)

with open(USER_FILE, "r") as f:
    users = json.load(f)

# ===============================
# Fonctions utilitaires
# ===============================
def save_users(users_dict):
    with open(USER_FILE, "w") as f:
        json.dump(users_dict, f, indent=2)

def calculate_lod_loq(slope, noise):
    lod_signal = 3.3 * noise
    loq_signal = 10 * noise
    if slope and slope != 0:
        lod_conc = lod_signal / slope
        loq_conc = loq_signal / slope
    else:
        lod_conc, loq_conc = None, None
    return lod_signal, loq_signal, lod_conc, loq_conc

# ===============================
# Authentification
# ===============================
def login_page():
    lang = st.session_state.lang
    texts = TEXTS[lang]
    st.title(texts["app_title"])

    # Sélecteur de langue sur la page de connexion uniquement
    chosen = st.selectbox("Lang / Language", options=["FR", "EN"], index=0 if st.session_state.lang == "FR" else 1)
    st.session_state.lang = chosen
    texts = TEXTS[st.session_state.lang]

    username = st.text_input(texts["username"])
    password = st.text_input(texts["password"], type="password")
    if st.button(texts["login_btn"]):
        user = username.lower().strip()
        if user in users and users[user]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = user
            # Protection complète contre KeyError
            access_list = []
            if isinstance(users.get(user), dict):
                access_list = users[user].get("access", [])
            st.session_state.access = access_list

            # Ré-initialiser toutes les clés utilisées ailleurs
            for key in ["slope_lin", "lin_fig", "sn_result", "sn_img_annot", "lod_s", "lod_c", "loq_s", "loq_c", "sn_manual"]:
                if key not in st.session_state:
                    st.session_state[key] = None

            # ✅ Correction ciblée
            st.rerun()

        else:
            st.error(texts["login_error"])

    # Pied de page stylisé "Powered by : BnB"
    st.markdown(
        f"""
        <style>
        .footer {{
            position: relative;
            left: 0;
            bottom: 0;
            width: 100%;
            text-align: center;
            color: #6c757d;
            font-size:12px;
            font-style: italic;
            margin-top: 40px;
        }}
        </style>
        <div class="footer">{texts["powered_by"]}</div>
        """,
        unsafe_allow_html=True,
    )

# ===============================
# Déconnexion
# ===============================
def logout():
    if "logged_in" in st.session_state:
        del st.session_state["logged_in"]
    if "user" in st.session_state:
        del st.session_state["user"]
    if "access" in st.session_state:
        del st.session_state["access"]

    st.success("Vous avez été déconnecté.")
    st.rerun()  # ✅ Correction ciblée

# ===============================
# Main App minimal pour éviter NameError
# ===============================
def main_app():
    st.title("🏠 Tableau de bord principal")
    st.write(f"Connecté en tant que : {st.session_state.user}")
    st.info("Ici, vous pouvez intégrer vos modules Linéarité, S/N, etc.")

# ===============================
# Lancement
# ===============================
def run():
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    run()