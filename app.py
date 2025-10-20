# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import os

# --------------------------
# USERS
# --------------------------
if "users" not in st.session_state:
    st.session_state["users"] = {
        "admin": {"password": "adminpass", "role": "admin"},
        "user": {"password": "userpass", "role": "user"}
    }

# Convert usernames to lowercase for case-insensitive login
users_lower = {k.lower(): v for k, v in st.session_state["users"].items()}

# --------------------------
# LOGIN SCREEN
# --------------------------
def login_screen():
    st.title("LabT Login")
    username = st.text_input("Nom d’utilisateur / Username")
    password = st.text_input("Mot de passe / Password", type="password")
    
    if st.button("Se connecter / Login"):
        user_data = users_lower.get(username.lower())
        if user_data and user_data["password"] == password:
            st.session_state["username"] = username.lower()
            st.session_state["role"] = user_data["role"]
            st.experimental_rerun()
        else:
            st.error("Nom d’utilisateur ou mot de passe incorrect / Wrong username or password")

# --------------------------
# ADMIN SCREEN
# --------------------------
def admin_screen():
    st.title("Admin Panel")
    st.write("Gérer les utilisateurs / Manage users")
    
    users = st.session_state["users"]
    st.write("Liste des utilisateurs existants / Existing users:")
    st.table([{k:v["role"]} for k,v in users.items()])
    
    new_user = st.text_input("Nouvel utilisateur / New user")
    new_pass = st.text_input("Mot de passe / Password", type="password")
    new_role = st.selectbox("Rôle / Role", ["user", "admin"])
    
    if st.button("Ajouter / Add user"):
        if new_user:
            st.session_state["users"][new_user] = {"password": new_pass, "role": new_role}
            st.success("Utilisateur ajouté / User added")
            st.experimental_rerun()

# --------------------------
# USER SCREEN
# --------------------------
def user_screen():
    st.title("Utilisateur / User Panel")
    st.write(f"Bonjour, {st.session_state['username']}")
    
    # Change password
    st.subheader("Changer mot de passe / Change password")
    new_pass = st.text_input("Nouveau mot de passe / New password", type="password")
    if st.button("Mettre à jour / Update password"):
        if new_pass:
            st.session_state["users"][st.session_state["username"]]["password"] = new_pass
            st.success("Mot de passe mis à jour / Password updated")
    
    # Linéarité
    st.subheader("Linéarité / Linearity")
    lin_choice = st.radio("Choisir méthode / Select method", ["CSV", "Saisie manuelle / Manual input"])
    
    if lin_choice == "CSV":
        lin_file = st.file_uploader("Téléverser fichier CSV / Upload CSV", type=["csv"])
        if lin_file:
            df_lin = pd.read_csv(lin_file)
            if 'Concentration' in df_lin.columns and 'Signal' in df_lin.columns:
                x = df_lin['Concentration'].values
                y = df_lin['Signal'].values
                slope, intercept = np.polyfit(x, y, 1)
                r2 = np.corrcoef(x, y)[0,1]**2
                st.write(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}, R²: {r2:.4f}")
                fig, ax = plt.subplots()
                ax.scatter(x, y, label="Points")
                ax.plot(x, slope*x + intercept, color="red", label="Fit")
                ax.set_xlabel("Concentration")
                ax.set_ylabel("Signal")
                ax.legend()
                st.pyplot(fig)
    
    elif lin_choice == "Saisie manuelle / Manual input":
        num_points = st.number_input("Nombre de points / Number of points", min_value=2, step=1)
        x = []
        y = []
        for i in range(int(num_points)):
            c = st.number_input(f"Concentration {i+1}", value=0.0)
            s = st.number_input(f"Signal {i+1}", value=0.0)
            x.append(c)
            y.append(s)
        if st.button("Calculer / Calculate"):
            slope, intercept = np.polyfit(x, y, 1)
            r2 = np.corrcoef(x, y)[0,1]**2
            st.write(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}, R²: {r2:.4f}")
            fig, ax = plt.subplots()
            ax.scatter(x, y, label="Points")
            ax.plot(x, np.array(x)*slope + intercept, color="red", label="Fit")
            ax.set_xlabel("Concentration")
            ax.set_ylabel("Signal")
            ax.legend()
            st.pyplot(fig)
    
    # S/N classique
    st.subheader("S/N")
    sn_file = st.file_uploader("Téléverser chromatogramme CSV / Upload CSV", type=["csv"])
    if sn_file:
        df_sn = pd.read_csv(sn_file)
        if 'Signal' in df_sn.columns:
            yvals = df_sn['Signal'].values
            noise_std = np.std(yvals[:10])  # simple exemple, première zone
            peak_val = np.max(yvals)
            sn_val = peak_val / noise_std
            st.write(f"S/N: {sn_val:.2f}")

# --------------------------
# MAIN
# --------------------------
def main():
    if "username" not in st.session_state:
        login_screen()
    elif st.session_state.get("role") == "admin":
        admin_screen()
    else:
        user_screen()

if __name__ == "__main__":
    main()