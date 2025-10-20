# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
import peakutils

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="auto")

# --------------------------
# UTILITAIRES
# --------------------------
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# Bilingue
LANG = {"FR": {
    "login": "Connexion",
    "username": "Nom d'utilisateur",
    "password": "Mot de passe",
    "admin_menu": "Menu Admin",
    "user_menu": "Menu Utilisateur",
    "change_pass": "Changer mot de passe",
    "logout": "Déconnexion",
    "linearity": "Linéarité",
    "sn": "S/N",
    "export_pdf": "Exporter PDF",
    "concentration": "Concentration",
    "signal": "Signal",
    "upload_csv": "Importer CSV",
    "manual_entry": "Saisie manuelle",
    "error_required": "Veuillez saisir le nom de l'entreprise."
}, "EN": {
    "login": "Login",
    "username": "Username",
    "password": "Password",
    "admin_menu": "Admin Menu",
    "user_menu": "User Menu",
    "change_pass": "Change Password",
    "logout": "Logout",
    "linearity": "Linearity",
    "sn": "S/N",
    "export_pdf": "Export PDF",
    "concentration": "Concentration",
    "signal": "Signal",
    "upload_csv": "Upload CSV",
    "manual_entry": "Manual entry",
    "error_required": "Please enter the company name."
}}

# --------------------------
# LOGIN / USERS
# --------------------------
def login_screen():
    st.title("LabT")
    users = load_users()
    username = st.text_input(LANG["FR"]["username"])
    password = st.text_input(LANG["FR"]["password"], type="password")
    if st.button(LANG["FR"]["login"]):
        if username.lower() in (u.lower() for u in users) and users[username]["password"] == password:
            st.session_state["user"] = username
            if users[username]["role"] == "admin":
                st.session_state["page"] = "admin_menu"
            else:
                st.session_state["page"] = "user_menu"
        else:
            st.error("Login incorrect")

# --------------------------
# ADMIN MENU
# --------------------------
def admin_menu():
    st.title("Admin")
    users = load_users()
    st.write("Liste des utilisateurs :")
    for u, info in users.items():
        st.write(f"- {u} ({info['role']})")
    if st.button(LANG["FR"]["logout"]):
        st.session_state.clear()
        st.experimental_rerun()

# --------------------------
# USER MENU
# --------------------------
def user_menu():
    st.title("Utilisateur")
    if st.button(LANG["FR"]["change_pass"]):
        change_password()
    if st.button(LANG["FR"]["linearity"]):
        page_linearity()
    if st.button(LANG["FR"]["sn"]):
        page_sn()
    if st.button(LANG["FR"]["logout"]):
        st.session_state.clear()
        st.experimental_rerun()

def change_password():
    st.subheader(LANG["FR"]["change_pass"])
    old = st.text_input("Ancien mot de passe", type="password")
    new = st.text_input("Nouveau mot de passe", type="password")
    if st.button("Valider"):
        users = load_users()
        user = st.session_state["user"]
        if users[user]["password"] == old:
            users[user]["password"] = new
            save_users(users)
            st.success("Mot de passe changé")
        else:
            st.error("Mot de passe incorrect")

# --------------------------
# LINEARITY
# --------------------------
def page_linearity():
    st.subheader(LANG["FR"]["linearity"])
    mode = st.radio("Mode", [LANG["FR"]["upload_csv"], LANG["FR"]["manual_entry"]])
    if mode == LANG["FR"]["upload_csv"]:
        file = st.file_uploader("CSV")
        if file:
            df = pd.read_csv(file)
            x = df["Concentration"].values
            y = df["Signal"].values
            slope, intercept = np.polyfit(x, y, 1)
            r2 = np.corrcoef(x, y)[0,1]**2
            st.write(f"Slope: {slope}, Intercept: {intercept}, R²: {r2}")
            plt.plot(x, y, 'o')
            plt.plot(x, slope*x + intercept)
            st.pyplot(plt)
    else:
        st.info("Saisie manuelle à compléter")

# --------------------------
# S/N
# --------------------------
def page_sn():
    st.subheader(LANG["FR"]["sn"])
    st.info("Calcul S/N à compléter avec choix de zone")

# --------------------------
# MAIN
# --------------------------
def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "login"
    if st.session_state["page"] == "login":
        login_screen()
    elif st.session_state["page"] == "admin_menu":
        admin_menu()
    elif st.session_state["page"] == "user_menu":
        user_menu()

if __name__ == "__main__":
    main()