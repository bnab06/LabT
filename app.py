# -*- coding: utf-8 -*-
# =======================================================
# LabT - Analyse Chromatographique (v6.0)
# Linéarité + S/N + OCR + Gestion utilisateurs
# =======================================================

import streamlit as st
import json
import os
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import cv2

# -------------------- CONFIG --------------------
st.set_page_config(page_title="LabT", layout="wide")

USERS_FILE = "users.json"
FEEDBACK_FILE = "feedback.json"

# -------------------- FICHIERS INITIAUX --------------------
def ensure_files():
    """Crée les fichiers JSON par défaut si absents"""
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "password": "admin",
                "role": "admin",
                "access": ["linearity", "sn"]
            }
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f, indent=4)

    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w") as f:
            json.dump([], f)

ensure_files()

# -------------------- UTILITAIRES --------------------
def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------- LOGIN --------------------
def login_page():
    st.title("🔬 Bienvenue sur LabT")

    users = load_users()
    usernames = list(users.keys())

    if not usernames:
        st.error("Aucun utilisateur trouvé. Contactez l’administrateur.")
        return

    username = st.selectbox("👤 Utilisateur", usernames)
    password = st.text_input("🔑 Mot de passe", type="password")

    if st.button("Connexion"):
        if username in users and password == users[username]["password"]:
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]
            st.session_state["access"] = users[username].get("access", [])
            st.success(f"Bienvenue, {username} !")
            st.rerun()
        else:
            st.error("Nom d’utilisateur ou mot de passe invalide.")

# -------------------- DÉCONNEXION --------------------
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Déconnecté.")
    st.rerun()

# -------------------- MODULE LINÉARITÉ --------------------
def linearity_module():
    st.header("📈 Linéarité")

    uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df)

        if "Concentration" in df.columns and "Réponse" in df.columns:
            x = df["Concentration"]
            y = df["Réponse"]
            coef = np.polyfit(x, y, 1)
            poly = np.poly1d(coef)
            r = np.corrcoef(x, y)[0, 1]

            st.write(f"**Équation :** y = {coef[0]:.4f}x + {coef[1]:.4f}")
            st.write(f"**Coefficient de corrélation (R) :** {r:.4f}")

            fig, ax = plt.subplots()
            ax.scatter(x, y)
            ax.plot(x, poly(x), color="red")
            ax.set_xlabel("Concentration")
            ax.set_ylabel("Réponse")
            st.pyplot(fig)
        else:
            st.warning("Colonnes attendues : 'Concentration' et 'Réponse'.")

# -------------------- MODULE S/N --------------------
def sn_module():
    st.header("📊 Calcul du rapport Signal / Bruit (S/N)")

    uploaded = st.file_uploader("Importer chromatogramme (image ou PDF)", type=["png", "jpg", "jpeg", "pdf"])
    if not uploaded:
        return

    # Conversion PDF → image si nécessaire
    if uploaded.type == "application/pdf":
        pages = convert_from_bytes(uploaded.read())
        image = pages[0]
    else:
        image = Image.open(uploaded)

    st.image(image, caption="Chromatogramme importé", use_container_width=True)

    # OCR pour info
    ocr_text = pytesseract.image_to_string(image)
    if len(ocr_text.strip()) < 10:
        st.warning("OCR non exploitable — analyse graphique utilisée.")
    else:
        st.caption("🧠 OCR terminé.")

    # Conversion en niveaux de gris
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

    # Projection verticale
    y_projection = np.sum(gray, axis=1)
    inverted = np.max(y_projection) - y_projection  # inversion pour pics positifs
    inverted = (inverted - np.min(inverted)) / (np.max(inverted) - np.min(inverted) + 1e-9)

    # Détection du pic principal
    peaks, _ = find_peaks(inverted, distance=10, prominence=0.05)
    if len(peaks) == 0:
        st.error("Aucun pic détecté automatiquement.")
        return

    main_peak = peaks[np.argmax(inverted[peaks])]
    st.success(f"✅ Pic principal détecté à la ligne Y = {main_peak}")

    # Calcul du bruit (écart-type hors zone pic)
    zone_exclue = range(max(0, main_peak - 10), min(len(inverted), main_peak + 10))
    noise_zone = np.delete(inverted, zone_exclue)
    noise = np.std(noise_zone) if len(noise_zone) > 0 else 1
    signal = np.max(inverted)
    sn_classic = signal / noise if noise != 0 else np.inf

    st.markdown(f"**S/N Classique :** {sn_classic:.2f}")
    st.markdown(f"**Position du pic principal :** {main_peak}")

# -------------------- MODULE FEEDBACK --------------------
def feedback_module():
    st.header("🗣️ Feedback utilisateur")
    fb = st.text_area("Laissez un commentaire ou un signalement")

    if st.button("Envoyer"):
        if fb.strip():
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = {"user": st.session_state["username"], "text": fb, "date": now}
            data = []
            if os.path.exists(FEEDBACK_FILE):
                data = json.load(open(FEEDBACK_FILE))
            data.append(entry)
            json.dump(data, open(FEEDBACK_FILE, "w"), indent=4)
            st.success("Merci pour votre retour !")
        else:
            st.warning("Veuillez écrire un message avant d’envoyer.")

# -------------------- MODULE ADMIN --------------------
def admin_panel():
    st.header("⚙️ Panneau Administrateur")

    users = load_users()
    user_list = [u for u in users.keys() if u != "admin"]

    action = st.selectbox("Action", ["Ajouter utilisateur", "Supprimer utilisateur", "Modifier privilèges"])

    if action == "Ajouter utilisateur":
        new_user = st.text_input("Nom d’utilisateur")
        new_pass = st.text_input("Mot de passe", type="password")
        if st.button("Ajouter"):
            if new_user in users:
                st.error("Cet utilisateur existe déjà.")
            else:
                users[new_user] = {"password": new_pass, "role": "user", "access": ["linearity", "sn"]}
                save_users(users)
                st.success(f"Utilisateur {new_user} ajouté ✅")

    elif action == "Supprimer utilisateur":
        to_delete = st.selectbox("Utilisateur à supprimer", user_list)
        if st.button("Supprimer"):
            del users[to_delete]
            save_users(users)
            st.warning(f"Utilisateur {to_delete} supprimé 🗑️")

    elif action == "Modifier privilèges":
        target = st.selectbox("Utilisateur", user_list)
        user_access = users[target].get("access", [])
        lin = st.checkbox("Linéarité", "linearity" in user_access)
        sn = st.checkbox("S/N", "sn" in user_access)
        if st.button("Enregistrer"):
            users[target]["access"] = []
            if lin:
                users[target]["access"].append("linearity")
            if sn:
                users[target]["access"].append("sn")
            save_users(users)
            st.success("Privilèges mis à jour ✅")

# -------------------- APPLICATION PRINCIPALE --------------------
def main_app():
    if "username" not in st.session_state:
        login_page()
        return

    username = st.session_state["username"]
    role = st.session_state["role"]

    st.sidebar.image("logo.png", use_container_width=True)
    st.sidebar.markdown(f"👋 Bonjour, **{username}** ({role})")

    options = []
    if "linearity" in st.session_state["access"]:
        options.append("Linéarité")
    if "sn" in st.session_state["access"]:
        options.append("S/N")
    if role == "admin":
        options.append("Admin")
    options += ["Feedback", "Déconnexion"]

    menu = st.sidebar.selectbox("📘 Module", options)

    if menu == "Linéarité":
        linearity_module()
    elif menu == "S/N":
        sn_module()
    elif menu == "Admin":
        admin_panel()
    elif menu == "Feedback":
        feedback_module()
    elif menu == "Déconnexion":
        logout()

# -------------------- LANCEMENT --------------------
def run():
    main_app()

if __name__ == "__main__":
    run()