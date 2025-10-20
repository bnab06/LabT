import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from scipy.signal import find_peaks
import json
from datetime import datetime

# -------- Session State Initialization --------
if "unit" not in st.session_state:
    st.session_state.unit = ""
if "slope" not in st.session_state:
    st.session_state.slope = None
if "users" not in st.session_state:
    st.session_state.users = {}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "role" not in st.session_state:
    st.session_state.role = ""

# -------- User Management --------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"admin": {"password": "admin", "role": "admin"}}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

if not st.session_state.users:
    st.session_state.users = load_users()

# -------- Authentication --------
def login_action(username, password):
    users = st.session_state.users
    uname_lower = username.lower()
    if uname_lower in (u.lower() for u in users.keys()):
        real_user = [u for u in users.keys() if u.lower() == uname_lower][0]
        if password == users[real_user]["password"]:
            st.session_state.logged_in = True
            st.session_state.current_user = real_user
            st.session_state.role = users[real_user]["role"]
            st.success(f"Login successful ✅ / Connexion réussie ✅\nYou are logged in as {real_user}")
            st.experimental_rerun()
        else:
            st.error("Incorrect password / Mot de passe incorrect")
    else:
        st.error("User not found / Utilisateur non trouvé")

def login_page():
    st.title("LabT Login / Connexion LabT")
    username = st.text_input("Username / Nom d'utilisateur:")
    password = st.text_input("Password / Mot de passe:", type="password")
    if st.button("Login / Se connecter"):
        login_action(username, password)

# -------- Main Menu --------
def main_menu():
    st.title("LabT Application")

    # Language selection
    lang = st.selectbox("Language / Langue:", ["English", "Français"])

    if st.session_state.role == "admin":
        menu_options = ["Manage Users / Gérer les utilisateurs"]
    else:
        menu_options = ["Unknown calculation / Calcul inconnu", "S/N calculation / Calcul S/N"]

    selected_option = st.selectbox("Select an option / Choisir une option:", menu_options)

    if selected_option in ["Manage Users / Gérer les utilisateurs"]:
        manage_users_page()
    elif selected_option in ["Unknown calculation / Calcul inconnu"]:
        unknown_calc_page()
    elif selected_option in ["S/N calculation / Calcul S/N"]:
        sn_calc_page()

# -------- User Management Page --------
def manage_users_page():
    st.subheader("User Management / Gestion des utilisateurs")
    users = st.session_state.users

    st.write("Existing users / Utilisateurs existants:", list(users.keys()))
    action = st.radio("Action:", ["Add / Ajouter", "Delete / Supprimer", "Modify / Modifier"])

    if action in ["Add / Ajouter"]:
        new_user = st.text_input("New username / Nouveau nom d'utilisateur:")
        new_pass = st.text_input("Password / Mot de passe:")
        role = st.selectbox("Role:", ["admin", "user"])
        if st.button("Confirm / Confirmer"):
            if new_user:
                users[new_user] = {"password": new_pass, "role": role}
                save_users(users)
                st.success(f"User {new_user} added / Utilisateur ajouté")
            else:
                st.error("Username required / Nom requis")

    elif action in ["Delete / Supprimer"]:
        del_user = st.selectbox("Select user to delete / Choisir utilisateur à supprimer:", list(users.keys()))
        if st.button("Delete / Supprimer"):
            if del_user in users:
                users.pop(del_user)
                save_users(users)
                st.success(f"User {del_user} deleted / Utilisateur supprimé")

    elif action in ["Modify / Modifier"]:
        mod_user = st.selectbox("Select user to modify / Choisir utilisateur:", list(users.keys()))
        new_pass = st.text_input("New password / Nouveau mot de passe:")
        if st.button("Modify / Modifier"):
            if mod_user in users:
                if new_pass:
                    users[mod_user]["password"] = new_pass
                    save_users(users)
                    st.success(f"Password updated for {mod_user} / Mot de passe mis à jour")

# -------- Unknown Calculation Page --------
def unknown_calc_page():
    st.subheader("Unknown Calculation / Calcul Inconnu")
    conc = st.number_input("Enter concentration / Entrer la concentration:")
    signal = st.number_input("Enter signal / Entrer le signal:")

    st.session_state.unit = st.text_input("Unit / Unité:", value=st.session_state.unit)

    if st.button("Calculate / Calculer"):
        try:
            result = signal / conc if conc != 0 else None
            st.write(f"Result / Résultat: {result:.4f} {st.session_state.unit}" if result else "Cannot calculate / Impossible à calculer")
        except Exception as e:
            st.error(f"Error / Erreur: {str(e)}")

# -------- S/N Calculation Page --------
def sn_calc_page():
    st.subheader("S/N Calculation / Calcul S/N")
    df = st.file_uploader("Upload CSV:", type=["csv"])
    use_linear_curve = st.checkbox("Use linearity curve for LOD/LOQ / Utiliser courbe linéaire pour LOD/LOQ")

    if df:
        try:
            data = pd.read_csv(df)
            x = data.iloc[:,0].values
            y = data.iloc[:,1].values
            st.line_chart(data)

            # Simple S/N calculation
            peaks, _ = find_peaks(y)
            noise = np.std(y)
            signal_val = np.mean(y[peaks]) if len(peaks) else np.max(y)
            sn = signal_val / noise if noise else None

            lod = loq = None
            if use_linear_curve:
                coeffs = np.polyfit(x, y, 1)
                slope = coeffs[0]
                st.session_state.slope = slope
                lod = 3 * noise / slope if slope else None
                loq = 10 * noise / slope if slope else None

            st.write(f"S/N: {sn:.4f}" if sn else "Cannot calculate / Impossible à calculer")
            st.write(f"LOD: {lod:.4f} / LOQ: {loq:.4f}" if lod and loq else "")

        except Exception as e:
            st.error(f"Error reading CSV / Erreur CSV: {str(e)}")

# -------- Main App Execution --------
if not st.session_state.logged_in:
    login_page()
else:
    main_menu()