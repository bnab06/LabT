# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import os
import cv2
import pytesseract
from pdf2image import convert_from_path
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# ---------------------------
# Gestion utilisateurs (JSON)
# ---------------------------

USER_FILE = "users.json"

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    else:
        return {"admin": {"password": "admin", "role": "admin"}}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

users = load_users()

# ---------------------------
# Authentification
# ---------------------------
def login():
    st.title("🔐 Connexion")
    username = st.text_input("Nom d’utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if username in users and users[username]["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = users[username].get("role", "user")
            st.success(f"Bienvenue {username} 👋")
            st.experimental_rerun()
        else:
            st.error("Nom d’utilisateur ou mot de passe incorrect")

# ---------------------------
# Profil utilisateur
# ---------------------------
def profil_page():
    st.subheader("👤 Profil utilisateur")
    st.markdown(f"Utilisateur connecté : **{st.session_state['username']}**")

    new_password = st.text_input("Nouveau mot de passe", type="password")
    if st.button("Changer le mot de passe"):
        if new_password.strip():
            users[st.session_state["username"]]["password"] = new_password
            save_users(users)
            st.success("Mot de passe mis à jour ✅")
        else:
            st.warning("Veuillez saisir un mot de passe valide.")

# ---------------------------
# Menu Admin
# ---------------------------
def admin_page():
    st.subheader("👑 Gestion des utilisateurs")

    choice = st.radio("Action :", ["Ajouter", "Modifier", "Supprimer"], horizontal=True)

    if choice == "Ajouter":
        new_user = st.text_input("Nom du nouvel utilisateur")
        new_pass = st.text_input("Mot de passe", type="password")
        role = st.selectbox("Rôle", ["user", "admin"])
        if st.button("Ajouter utilisateur"):
            if new_user not in users:
                users[new_user] = {"password": new_pass, "role": role}
                save_users(users)
                st.success(f"Utilisateur {new_user} ajouté ✅")
            else:
                st.warning("Utilisateur déjà existant.")

    elif choice == "Modifier":
        user_to_edit = st.selectbox("Choisir un utilisateur", list(users.keys()))
        new_pass = st.text_input("Nouveau mot de passe", type="password")
        role = st.selectbox("Nouveau rôle", ["user", "admin"])
        if st.button("Modifier utilisateur"):
            users[user_to_edit] = {"password": new_pass, "role": role}
            save_users(users)
            st.success(f"Utilisateur {user_to_edit} modifié ✅")

    elif choice == "Supprimer":
        user_to_delete = st.selectbox("Utilisateur à supprimer", list(users.keys()))
        if st.button("Supprimer"):
            if user_to_delete != "admin":
                del users[user_to_delete]
                save_users(users)
                st.success(f"Utilisateur {user_to_delete} supprimé ✅")
            else:
                st.error("Impossible de supprimer l’admin principal !")

# ---------------------------
# Digitizing chromatogramme
# ---------------------------
def digitizing_page():
    st.subheader("📈 Digitalisation d’un chromatogramme (image ou PDF)")

    file = st.file_uploader("Importer un chromatogramme (PNG, JPG, PDF)", type=["png", "jpg", "jpeg", "pdf"])
    if file:
        if file.name.endswith(".pdf"):
            pages = convert_from_path(file)
            image = np.array(pages[0])
        else:
            file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        st.image(image, caption="Chromatogramme importé", use_container_width=True)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        st.text_area("Résultat OCR :", text, height=200)

        st.download_button("Télécharger les données extraites", text, file_name="chrom_data.txt")

# ---------------------------
# Calculs analytiques
# ---------------------------
def calcul_page():
    st.subheader("🧪 Calculs S/N, LOD, LOQ, Linéarité")

    csv_file = st.file_uploader("Importer un fichier CSV (Time, Signal)", type=["csv"])
    if csv_file:
        df = pd.read_csv(csv_file)
        if "Time" not in df.columns or "Signal" not in df.columns:
            st.error("Le fichier doit contenir les colonnes Time et Signal.")
            return

        fig, ax = plt.subplots()
        ax.plot(df["Time"], df["Signal"])
        st.pyplot(fig)

        region = st.slider("Sélectionner la zone (en % du chromatogramme)", 0, 100, (20, 80))
        subset = df.iloc[int(len(df)*region[0]/100): int(len(df)*region[1]/100)]
        noise = np.std(subset["Signal"])
        signal = np.max(subset["Signal"])
        sn = signal / noise if noise != 0 else np.nan

        st.write(f"**S/N = {sn:.2f}**")
        lod = 3 * noise
        loq = 10 * noise
        st.write(f"**LOD = {lod:.3f}**, **LOQ = {loq:.3f}**")

        st.markdown("---")
        st.subheader("📊 Linéarité")
        mode = st.radio("Choisir la méthode :", ["Importer CSV", "Saisie manuelle"], horizontal=True)

        if mode == "Importer CSV":
            lin_file = st.file_uploader("Importer données linéarité (Conc, Réponse)", type=["csv"])
            if lin_file:
                df_lin = pd.read_csv(lin_file)
                X = df_lin.iloc[:, 0].values.reshape(-1, 1)
                y = df_lin.iloc[:, 1].values
        else:
            concs = st.text_input("Concentrations (séparées par des virgules)")
            reps = st.text_input("Réponses (séparées par des virgules)")
            if concs and reps:
                X = np.array([float(x) for x in concs.split(",")]).reshape(-1, 1)
                y = np.array([float(x) for x in reps.split(",")])

        if "X" in locals():
            model = LinearRegression().fit(X, y)
            slope = model.coef_[0]
            intercept = model.intercept_
            r2 = r2_score(y, model.predict(X))

            st.markdown(f"**Pente :** {slope:.6g}")
            st.markdown(f"**Ordonnée à l’origine :** {intercept:.6g}")
            st.markdown(f"**R² :** {r2:.5f}")

            plt.figure()
            plt.scatter(X, y, label="Données")
            plt.plot(X, model.predict(X), color='red', label="Régression linéaire")
            plt.legend()
            st.pyplot(plt)

# ---------------------------
# Interface principale
# ---------------------------
def main():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login()
        return

    st.sidebar.title("📚 Menu")
    menu = st.sidebar.radio("Navigation :", ["Calculs", "Digitalisation", "Profil", "Admin", "Déconnexion"])

    if menu == "Calculs":
        calcul_page()
    elif menu == "Digitalisation":
        digitizing_page()
    elif menu == "Profil":
        profil_page()
    elif menu == "Admin" and st.session_state["role"] == "admin":
        admin_page()
    elif menu == "Déconnexion":
        st.session_state.clear()
        st.experimental_rerun()

if __name__ == "__main__":
    main()