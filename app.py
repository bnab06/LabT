# ==========================================
# app.py complet
# ==========================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
from scipy.signal import find_peaks
import json
import os
from datetime import datetime

# -----------------------------
# Initialisation de session
# -----------------------------
for key in ['users', 'current_user', 'role', 'unit', 'prev_page']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'users' else {}

# -----------------------------
# Fichier utilisateurs
# -----------------------------
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

# -----------------------------
# Login
# -----------------------------
def login_action(username, password):
    users = load_users()
    username_lower = username.lower()
    if username_lower in users and users[username_lower]['password'] == password:
        st.session_state.current_user = username_lower
        st.session_state.role = users[username_lower]['role']
        st.success(f"Connexion réussie ✅ / You are logged in as {username_lower}")
        st.experimental_rerun()
    else:
        st.error("Utilisateur ou mot de passe incorrect / Incorrect username or password")

def login_page():
    st.title("LabT Application / Application LabT")
    users = load_users()
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        login_action(username, password)

# -----------------------------
# Menu Admin
# -----------------------------
def admin_menu():
    st.header("Admin Panel / Panneau Admin")
    choice = st.selectbox("Choose action / Choisir action:", 
                          ["Add user / Ajouter utilisateur", 
                           "Delete user / Supprimer utilisateur",
                           "Modify user / Modifier utilisateur"])
    users = load_users()
    if choice.startswith("Add"):
        new_user = st.text_input("New username / Nouveau nom d'utilisateur")
        new_pass = st.text_input("Password / Mot de passe", type="password")
        role = st.selectbox("Role / Rôle", ["admin", "user"])
        if st.button("Add / Ajouter"):
            if new_user.lower() in users:
                st.error("User already exists / L'utilisateur existe déjà")
            else:
                users[new_user.lower()] = {"password": new_pass, "role": role}
                save_users(users)
                st.success("User added / Utilisateur ajouté")
    elif choice.startswith("Delete"):
        del_user = st.selectbox("Select user / Sélectionner un utilisateur", list(users.keys()))
        if st.button("Delete / Supprimer"):
            users.pop(del_user)
            save_users(users)
            st.success("User deleted / Utilisateur supprimé")
    elif choice.startswith("Modify"):
        mod_user = st.selectbox("Select user / Sélectionner un utilisateur", list(users.keys()))
        new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
        role = st.selectbox("Role / Rôle", ["admin", "user"])
        if st.button("Modify / Modifier"):
            users[mod_user]["password"] = new_pass
            users[mod_user]["role"] = role
            save_users(users)
            st.success("User modified / Utilisateur modifié")

# -----------------------------
# Menu User
# -----------------------------
def user_menu():
    st.header("User Panel / Panneau Utilisateur")
    if st.button("Change password / Changer mot de passe"):
        new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
        if st.button("Save / Enregistrer"):
            users = load_users()
            users[st.session_state.current_user]["password"] = new_pass
            save_users(users)
            st.success("Password updated / Mot de passe mis à jour")

# -----------------------------
# Choix calcul
# -----------------------------
def calculations_menu():
    st.header("Choose calculation / Choisir calcul")
    calc_choice = st.selectbox("Select / Sélectionner", 
                               ["Unknown calculation / Calcul inconnu", 
                                "S/N classic / S/N classique", 
                                "S/N USP"])
    st.session_state.prev_page = "calculations"
    return calc_choice

# -----------------------------
# Lecture CSV
# -----------------------------
def read_csv(file):
    try:
        df = pd.read_csv(file)
        if 'Time' not in df.columns or 'Signal' not in df.columns:
            st.error("CSV must include 'Time' and 'Signal' columns")
            return None
        return df
    except Exception as e:
        st.error(f"Error reading CSV / Erreur lecture CSV: {e}")
        return None

# -----------------------------
# Calcul S/N
# -----------------------------
def calc_sn(df, height_factor=5, use_slope=False):
    peaks, _ = find_peaks(df['Signal'], height=height_factor*np.std(df['Signal']))
    sn_values = df['Signal'][peaks].max() / np.std(df['Signal'])
    if use_slope:
        slope, intercept = np.polyfit(df['Time'], df['Signal'], 1)
        lod = (3 * np.std(df['Signal'])) / slope
        loq = (10 * np.std(df['Signal'])) / slope
        return sn_values, lod, loq
    return sn_values, None, None

# -----------------------------
# Export PDF
# -----------------------------
def export_pdf(calc_type, df, sn_val=None, lod=None, loq=None):
    if not st.session_state.unit:
        st.warning("Please enter the unit / Veuillez saisir l'unité")
        return
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="App: LabT", ln=1, align="C")
    pdf.cell(200, 10, txt=f"Calculation / Calcul: {calc_type}", ln=2)
    pdf.cell(200, 10, txt=f"S/N: {sn_val} {st.session_state.unit if sn_val else ''}", ln=3)
    if lod and loq:
        pdf.cell(200, 10, txt=f"LOD: {lod} {st.session_state.unit}", ln=4)
        pdf.cell(200, 10, txt=f"LOQ: {loq} {st.session_state.unit}", ln=5)
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    st.success(f"PDF generated: {filename}")

# -----------------------------
# Main App
# -----------------------------
def main():
    if st.session_state.current_user is None:
        login_page()
    else:
        st.sidebar.button("Logout / Déconnexion", on_click=lambda: st.session_state.update({'current_user': None, 'role': None}))
        st.session_state.unit = st.text_input("Unit / Unité", st.session_state.unit if st.session_state.unit else "")
        if st.session_state.role == "admin":
            admin_menu()
        else:
            user_menu()
        calc_choice = calculations_menu()
        file = st.file_uploader("Upload CSV", type=["csv"])
        if file:
            df = read_csv(file)
            if df is not None:
                sn_val, lod, loq = None, None, None
                if "S/N" in calc_choice:
                    use_slope = st.checkbox("Use calibration curve for LOD/LOQ / Utiliser courbe de linéarité")
                    sn_val, lod, loq = calc_sn(df, use_slope=use_slope)
                if st.button("Generate PDF / Générer PDF"):
                    export_pdf(calc_choice, df, sn_val, lod, loq)
                    
if __name__ == "__main__":
    main()