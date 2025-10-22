# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import io
import base64

# =====================
# CONFIGURATION GÉNÉRALE
# =====================
st.set_page_config(page_title="LabT", layout="wide")

# Charger les utilisateurs
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {"admin": {"password": "admin", "role": "admin", "company": ""}}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

users = load_users()

# =====================
# FONCTIONS DIVERS
# =====================

def login(username, password):
    username = username.strip().lower()  # insensible à la casse
    for user, data in users.items():
        if user.lower() == username and data["password"] == password:
            return user, data["role"]
    return None, None

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def change_password(username):
    st.subheader("🔒 Change password / Changer le mot de passe")
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
    confirm_pass = st.text_input("Confirm password / Confirmer le mot de passe", type="password")
    if st.button("✅ Save / Enregistrer"):
        if new_pass and new_pass == confirm_pass:
            users[username]["password"] = new_pass
            save_users(users)
            st.success("Password updated successfully / Mot de passe mis à jour ✅")
        else:
            st.error("Passwords do not match / Les mots de passe ne correspondent pas ❌")

# =====================
# ADMIN PAGE
# =====================
def admin_page(username):
    st.title("👨‍💼 Admin - Gestion des utilisateurs")

    st.subheader("Liste des utilisateurs")
    df = pd.DataFrame([
        {"Username": u, "Role": users[u]["role"], "Company": users[u].get("company", "")}
        for u in users
    ])
    st.dataframe(df, use_container_width=True)

    st.subheader("Ajouter un utilisateur")
    new_user = st.text_input("Nom d'utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    new_role = st.selectbox("Rôle", ["user", "admin"])
    new_company = st.text_input("Nom de la compagnie (optionnel)")

    if st.button("Ajouter"):
        if new_user.lower() in [u.lower() for u in users.keys()]:
            st.warning("Utilisateur déjà existant ⚠️")
        elif not new_user or not new_pass:
            st.error("Nom et mot de passe requis ❌")
        else:
            users[new_user] = {"password": new_pass, "role": new_role, "company": new_company}
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté ✅")
            st.rerun()

    st.subheader("Supprimer un utilisateur")
    del_user = st.selectbox("Choisir un utilisateur", [u for u in users if u != "admin"])
    if st.button("Supprimer"):
        users.pop(del_user)
        save_users(users)
        st.success(f"Utilisateur {del_user} supprimé ✅")
        st.rerun()

    if st.button("🚪 Logout / Déconnexion"):
        logout()

# =====================
# USER PAGE
# =====================
def user_page(username):
    st.title("🧪 LabT - Outils analytiques")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📈 Linéarité"):
            st.session_state.page = "linearity"
            st.rerun()
    with col2:
        if st.button("📊 Signal / Bruit (S/N)"):
            st.session_state.page = "sn"
            st.rerun()

    st.divider()
    if st.button("🔒 Change Password / Changer le mot de passe"):
        st.session_state.page = "change_pw"
        st.rerun()

    if st.button("🚪 Logout / Déconnexion"):
        logout()

# =====================
# PAGE LINEARITÉ (simplifiée ici)
# =====================
def page_linearity():
    st.header("📈 Linéarité")
    st.info("Import CSV ou saisie manuelle")

    choice = st.radio("Méthode :", ["Importer CSV", "Saisie manuelle"])

    if choice == "Importer CSV":
        uploaded_file = st.file_uploader("Importer fichier CSV", type=["csv"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.write(df)
                fig, ax = plt.subplots()
                ax.plot(df.iloc[:, 0], df.iloc[:, 1], "o-")
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Erreur lecture CSV : {e}")
    else:
        st.write("Saisie manuelle (en construction)")

    if st.button("⬅️ Retour menu"):
        st.session_state.page = "menu"
        st.rerun()

# =====================
# PAGE SIGNAL / BRUIT
# =====================
def page_sn():
    st.header("📊 Signal / Bruit (S/N)")
    st.info("Importer un chromatogramme CSV, PNG ou PDF")

    uploaded_file = st.file_uploader("Importer chromatogramme", type=["csv", "png", "pdf"])
    if uploaded_file:
        st.success(f"Fichier importé : {uploaded_file.name}")
        # traitement CSV simple
        if uploaded_file.name.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df.iloc[:, 0], y=df.iloc[:, 1], mode="lines"))
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Erreur lecture CSV : {e}")
        else:
            st.image(uploaded_file, use_column_width=True)

    if st.button("⬅️ Retour menu"):
        st.session_state.page = "menu"
        st.rerun()

# =====================
# MAIN
# =====================
def login_screen():
    st.title("🔐 Connexion / Login")

    username = st.text_input("Nom d'utilisateur / Username")
    password = st.text_input("Mot de passe / Password", type="password")

    if st.button("Se connecter / Login"):
        user, role = login(username, password)
        if user:
            st.session_state.username = user
            st.session_state.role = role
            st.session_state.page = "menu"
            st.rerun()
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect ❌ / Wrong username or password ❌")

def main():
    if "page" not in st.session_state:
        st.session_state.page = "login"

    if st.session_state.page == "login":
        login_screen()
    elif st.session_state.page == "menu":
        if st.session_state.role == "admin":
            admin_page(st.session_state.username)
        else:
            user_page(st.session_state.username)
    elif st.session_state.page == "linearity":
        page_linearity()
    elif st.session_state.page == "sn":
        page_sn()
    elif st.session_state.page == "change_pw":
        change_password(st.session_state.username)
        if st.button("⬅️ Retour menu"):
            st.session_state.page = "menu"
            st.rerun()

if __name__ == "__main__":
    main()