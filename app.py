import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
from scipy import stats

# ---------- Initialisation session_state ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'unit' not in st.session_state:
    st.session_state.unit = ""
if 'slope' not in st.session_state:
    st.session_state.slope = None
if 'intercept' not in st.session_state:
    st.session_state.intercept = None
if 'linear_fit' not in st.session_state:
    st.session_state.linear_fit = False

# ---------- Utilitaires pour utilisateurs ----------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
# ---------- Login ----------
def login_action(username, password):
    users = load_users()
    user_lower = username.lower()
    if user_lower in users and users[user_lower]['password'] == password:
        st.session_state.logged_in = True
        st.session_state.user_role = users[user_lower]['role']
        st.session_state.username = user_lower
        st.success(f"Connexion réussie ✅ / You are logged in as {username}")
        st.experimental_rerun()
    else:
        st.error("Utilisateur ou mot de passe incorrect / Wrong username or password")

def login_page():
    st.title("LabT Application - Login")
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Se connecter"):
        login_action(username, password)

# ---------- Menu principal ----------
def main_menu():
    st.title("LabT Application")
    st.write(f"Logged in as: {st.session_state.username} ({st.session_state.user_role})")
    
    if st.session_state.user_role == "admin":
        option = st.selectbox("Choose action / Choisir action:",
                              ["Manage Users / Gérer utilisateurs"])
    else:
        option = st.selectbox("Choose action / Choisir action:",
                              ["Unknown Calculation / Calcul inconnu", 
                               "S/N Calculation / Calcul S/N"])
    return option
# ---------- Admin: gestion utilisateurs ----------
def admin_manage_users():
    users = load_users()
    st.subheader("Manage Users / Gérer utilisateurs")
    action = st.selectbox("Action:", ["Add / Ajouter", "Modify / Modifier", "Delete / Supprimer"])
    
    if action.startswith("Add"):
        new_user = st.text_input("Username / Nom d'utilisateur")
        password = st.text_input("Password / Mot de passe")
        role = st.selectbox("Role / Rôle", ["user", "admin"])
        if st.button("Add User / Ajouter"):
            users[new_user.lower()] = {"password": password, "role": role}
            save_users(users)
            st.success(f"User {new_user} added / ajouté ✅")
    
    elif action.startswith("Modify"):
        mod_user = st.selectbox("Select user / Choisir utilisateur", list(users.keys()))
        new_pass = st.text_input("New Password / Nouveau mot de passe")
        if st.button("Modify / Modifier"):
            users[mod_user]['password'] = new_pass
            save_users(users)
            st.success(f"User {mod_user} modified / modifié ✅")
    
    elif action.startswith("Delete"):
        del_user = st.selectbox("Select user / Choisir utilisateur", list(users.keys()))
        if st.button("Delete / Supprimer"):
            users.pop(del_user)
            save_users(users)
            st.success(f"User {del_user} deleted / supprimé ✅")

# ---------- Calculs ----------
def calc_unknown(df, unit=""):
    df['Concentration'] = df['Signal']  # Placeholder: remplacer par vraie formule
    st.session_state.unit = unit
    st.dataframe(df)

def calc_sn(df, use_linear=False):
    sn_classic = df['Signal'].max() / df['Signal'].std() if df['Signal'].std() != 0 else 0
    lod = loq = None
    if use_linear and st.session_state.slope is not None:
        std_y = df['Signal'].std()
        lod = 3.3 * std_y / st.session_state.slope
        loq = 10 * std_y / st.session_state.slope
    return sn_classic, lod, loq
# ---------- PDF Export ----------
def export_pdf(df, filename="report.pdf", company_name=""):
    if not company_name:
        st.error("Please enter company name / Veuillez entrer le nom de l'entreprise")
        return
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"App: LabT - Report", ln=True)
    pdf.cell(200, 10, txt=f"Company / Société: {company_name}", ln=True)
    pdf.cell(200, 10, txt=f"Generated on: {datetime.now()}", ln=True)
    for i, row in df.iterrows():
        pdf.cell(200, 10, txt=str(row.to_dict()), ln=True)
    pdf.output(filename)
    st.success(f"PDF saved / PDF enregistré: {filename}")

# ---------- Application principale ----------
if not st.session_state.logged_in:
    login_page()
else:
    choice = main_menu()
    if choice.startswith("Manage Users"):
        admin_manage_users()
    elif choice.startswith("Unknown Calculation"):
        uploaded_file = st.file_uploader("Upload CSV / Charger CSV", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            unit = st.text_input("Unit / Unité", "mg/mL")
            calc_unknown(df, unit)
            company_name = st.text_input("Company / Société")
            if st.button("Generate PDF / Générer PDF"):
                export_pdf(df, company_name=company_name)
    elif choice.startswith("S/N Calculation"):
        uploaded_file = st.file_uploader("Upload CSV / Charger CSV", type="csv")
        use_linear = st.checkbox("Use linear curve for LOD/LOQ / Utiliser la courbe de linéarité")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            if use_linear:
                x = df['Concentration']
                y = df['Signal']
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                st.session_state.slope = slope
                st.session_state.intercept = intercept
                st.session_state.linear_fit = True
            sn_value, lod, loq = calc_sn(df, use_linear)
            st.write(f"S/N: {sn_value:.2f}")
            if lod and loq:
                st.write(f"LOD: {lod:.4f} {st.session_state.unit}, LOQ: {loq:.4f} {st.session_state.unit}")
            company_name = st.text_input("Company / Société")
            if st.button("Generate PDF / Générer PDF"):
                export_pdf(df, company_name=company_name)