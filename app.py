import streamlit as st
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
from pdf2image import convert_from_path
import cv2
import io

# -----------------------------
# Initialisation users
# -----------------------------
USERS_FILE = Path("users.json")
if not USERS_FILE.exists():
    users = {
        "admin": {"password": "adminpass", "role": "admin"},
        "user": {"password": "userpass", "role": "user"}
    }
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
else:
    with open(USERS_FILE, "r") as f:
        users = json.load(f)

# -----------------------------
# Session state
# -----------------------------
if "username" not in st.session_state:
    st.session_state["username"] = None

# -----------------------------
# Login
# -----------------------------
def login():
    st.title("Connexion")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if username in users and users[username]["password"] == password:
            st.session_state["username"] = username
            st.success(f"Bienvenue {username} !")
            st.experimental_rerun()
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect")

# -----------------------------
# Admin gestion users
# -----------------------------
def admin_panel():
    st.subheader("Gestion des utilisateurs (Admin)")
    for user in list(users.keys()):
        st.write(f"- {user} ({users[user]['role']})")
    st.write("Ajouter / modifier / supprimer un utilisateur :")
    new_user = st.text_input("Nom d'utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["user", "admin"])
    col1, col2, col3 = st.columns(3)
    if col1.button("Ajouter / Modifier"):
        users[new_user] = {"password": new_pass, "role": role}
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
        st.success(f"{new_user} ajouté / modifié")
    if col2.button("Supprimer"):
        if new_user in users:
            del users[new_user]
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=4)
            st.success(f"{new_user} supprimé")
        else:
            st.error("Utilisateur non trouvé")

# -----------------------------
# Digitalization
# -----------------------------
def digitalization():
    st.subheader("Digitalization (PDF / Image / OCR)")
    file = st.file_uploader("Importer PDF ou Image", type=["pdf", "png", "jpg", "jpeg"])
    if file:
        if file.type == "application/pdf":
            images = convert_from_path(file, dpi=200)
            st.image(images[0], caption="Première page du PDF", use_column_width=True)
            text = ""
            for img in images:
                text += pytesseract.image_to_string(img)
            st.text_area("Texte extrait via OCR", text, height=300)
        else:
            img = np.array(plt.imread(file))
            st.image(img, caption="Image importée", use_column_width=True)
            text = pytesseract.image_to_string(img)
            st.text_area("Texte extrait via OCR", text, height=300)

# -----------------------------
# Chromatogramme S/N
# -----------------------------
def chromatogram_analysis():
    st.subheader("Analyse Chromatogramme")
    uploaded_file = st.file_uploader("Importer CSV chromatogramme", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write(df.head())
        x = df[df.columns[0]].values
        y = df[df.columns[1]].values
        fig, ax = plt.subplots()
        ax.plot(x, y)
        ax.set_xlabel("Temps")
        ax.set_ylabel("Signal")
        st.pyplot(fig)
        # S/N simple
        signal = np.max(y)
        noise = np.std(y)
        st.write(f"Signal: {signal:.3f}")
        st.write(f"Noise: {noise:.3f}")
        st.write(f"S/N: {signal/noise:.3f}")

# -----------------------------
# Page principale
# -----------------------------
def main():
    if st.session_state["username"] is None:
        login()
        return

    st.title("LabT - Application principale")
    st.write(f"Connecté en tant que {st.session_state['username']}")

    if users[st.session_state["username"]]["role"] == "admin":
        admin_panel()

    digitalization()
    chromatogram_analysis()

if __name__ == "__main__":
    main()