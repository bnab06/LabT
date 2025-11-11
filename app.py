# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import json
from datetime import datetime
from scipy.signal import find_peaks
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import smtplib
from email.mime.text import MIMEText

# -----------------------------
# CONFIG GLOBALE
# -----------------------------
st.set_page_config(page_title="LabT", layout="wide")
USERS_FILE = "users.json"

# -----------------------------
# GESTION UTILISATEURS
# -----------------------------
def ensure_files():
    """Crée le fichier users.json si manquant."""
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin", "access": ["Linéarité", "S/N"]},
            "user": {"password": "user", "role": "user", "access": ["S/N"]}
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -----------------------------
# LOGIN / LOGOUT
# -----------------------------
def login_page():
    st.title("🔐 Connexion")
    users = load_users()

    username = st.text_input("Utilisateur")
    password = st.text_input("Mot de passe", type="password")
    login_btn = st.button("Se connecter")

    if login_btn:
        if username in users and password == users[username]["password"]:
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]
            st.session_state["access"] = users[username]["access"]
            st.success(f"Bienvenue {username} !")
            st.experimental_rerun()
        else:
            st.error("Utilisateur ou mot de passe invalide.")

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Déconnecté avec succès.")
    st.experimental_rerun()

# -----------------------------
# MODULE S/N
# -----------------------------
def sn_module():
    st.header("📊 Calcul du rapport S/N")

    uploaded = st.file_uploader("Charger un chromatogramme (image ou PDF)", type=["png", "jpg", "jpeg", "pdf"])
    if not uploaded:
        return

    # Extraction OCR / Image
    if uploaded.type == "application/pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.read())
            images = convert_from_path(tmp.name)
            img = images[0]
    else:
        img = Image.open(uploaded)

    # OCR
    text = pytesseract.image_to_string(img)
    data = []
    for line in text.splitlines():
        parts = line.replace(",", ".").split()
        vals = [v for v in parts if v.replace('.', '', 1).isdigit()]
        if len(vals) >= 2:
            data.append(vals[:2])

    if not data:
        st.error("❌ Impossible d’extraire les données du chromatogramme.")
        return

    df = pd.DataFrame(data, columns=["X", "Y"]).astype(float)

    # Corriger X artificiel si plat
    if len(df["X"].unique()) <= 1:
        st.warning("Signal plat ou OCR invalide : axe X artificiel généré.")
        df["X"] = np.arange(len(df))

    # Détection automatique du pic principal
    peaks, _ = find_peaks(df["Y"], height=np.median(df["Y"]) * 1.2)
    if len(peaks) == 0:
        idx = df["Y"].idxmax()
        peak_x = df.loc[idx, "X"]
        peak_y = df.loc[idx, "Y"]
        st.warning("Aucun pic détecté par seuil — pic le plus haut utilisé.")
    else:
        idx = peaks[np.argmax(df.loc[peaks, 'Y'])]
        peak_x = df.loc[idx, "X"]
        peak_y = df.loc[idx, "Y"]

    # Calcul bruit et S/N
    noise_region = df["Y"].iloc[:max(10, len(df)//10)]
    noise_std = np.std(noise_region)
    if noise_std == 0:
        noise_std = 1e-9

    sn_classic = peak_y / noise_std
    sn_usp = (peak_y - np.mean(noise_region)) / (2 * noise_std)

    # Affichage
    st.write(f"**S/N Classique :** {sn_classic:.4f}")
    st.write(f"**S/N USP :** {sn_usp:.4f}")
    st.write(f"**Temps de rétention du pic :** {peak_x:.4f}")

    # Tracé du chromatogramme
    st.line_chart(df.set_index("X"))

# -----------------------------
# MODULE LINÉARITÉ
# -----------------------------
def linearity_module():
    st.header("📈 Évaluation de la linéarité")
    st.info("Module en développement.")

# -----------------------------
# MODULE ADMIN
# -----------------------------
def admin_module():
    st.header("⚙️ Administration")
    users = load_users()
    selected_user = st.selectbox("Sélectionner un utilisateur", list(users.keys()))
    st.write(f"Rôle : {users[selected_user]['role']}")
    st.write(f"Accès : {', '.join(users[selected_user]['access'])}")

# -----------------------------
# MODULE FEEDBACK
# -----------------------------
def feedback_module():
    st.header("💬 Feedback")
    msg = st.text_area("Votre message :")
    if st.button("Envoyer"):
        st.success("Merci pour votre retour ! (email désactivé sur Streamlit Cloud)")

# -----------------------------
# APPLICATION PRINCIPALE
# -----------------------------
def main_app():
    username = st.session_state.get("username", None)
    role = st.session_state.get("role", None)

    # ✅ Affichage logo ou texte si manquant
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
    else:
        st.sidebar.markdown("### 🧪 LabT")

    st.sidebar.markdown(f"👋 Bonjour, **{username}** ({role})")

    # Menu déroulant des modules
    module = st.sidebar.selectbox("📂 Module", ["Linéarité", "S/N", "Feedback", "Admin", "Déconnexion"])

    if module == "Déconnexion":
        logout()
    elif module == "S/N":
        sn_module()
    elif module == "Linéarité":
        linearity_module()
    elif module == "Admin":
        admin_module()
    elif module == "Feedback":
        feedback_module()

# -----------------------------
# LANCEMENT
# -----------------------------
def run():
    ensure_files()
    if "username" not in st.session_state:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    run()