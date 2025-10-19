# ================================
# Partie 1 : imports et utilitaires
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import json
import os

# ================================
# Initialisation session_state
# ================================
if 'users' not in st.session_state:
    st.session_state.users = {}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if 'role' not in st.session_state:
    st.session_state.role = None

if 'language' not in st.session_state:
    st.session_state.language = 'English'  # default language

if 'unit' not in st.session_state:
    st.session_state.unit = ''

if 'slope' not in st.session_state:
    st.session_state.slope = None

# ================================
# Fonctions utilisateurs
# ================================
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            st.session_state.users = json.load(f)
    else:
        st.session_state.users = {}
    return st.session_state.users

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(st.session_state.users, f, indent=4)

def check_password(username, password):
    username_lower = username.lower()
    return username_lower in st.session_state.users and st.session_state.users[username_lower]['password'] == password

def add_user(username, password, role):
    username_lower = username.lower()
    st.session_state.users[username_lower] = {'password': password, 'role': role}
    save_users()

def remove_user(username):
    username_lower = username.lower()
    if username_lower in st.session_state.users:
        del st.session_state.users[username_lower]
        save_users()
# ================================
# Partie 2 : Login et menu principal
# ================================

def login_page():
    load_users()
    st.title("LabT Application")
    
    # Choix de la langue
    lang = st.selectbox("Language / Langue", ["English", "Français"], index=0 if st.session_state.language == "English" else 1)
    st.session_state.language = lang

    username = st.text_input("Username / Nom d'utilisateur:")
    password = st.text_input("Password / Mot de passe:", type="password")
    
    if st.button("Login / Connexion"):
        login_action(username, password)

def login_action(username, password):
    if check_password(username, password):
        st.session_state.logged_in = True
        st.session_state.current_user = username.lower()
        st.session_state.role = st.session_state.users[username.lower()]['role']
        st.success(f"Login successful ✅ / Connexion réussie ✅ as {st.session_state.current_user}")
        st.experimental_rerun()
    else:
        st.error("Invalid username or password / Nom d'utilisateur ou mot de passe invalide")

# ================================
# Menu principal selon rôle
# ================================
def main_menu():
    st.sidebar.title("Menu / Menu")
    
    if st.session_state.role == "admin":
        option = st.sidebar.selectbox(
            "Admin options / Options Admin",
            ["Manage Users / Gérer les utilisateurs"]
        )
        if option == "Manage Users / Gérer les utilisateurs":
            manage_users()
    
    elif st.session_state.role == "user":
        option = st.sidebar.selectbox(
            "User options / Options Utilisateur",
            ["Change Password / Modifier mot de passe", "Unknown calculation / Calcul inconnu", "S/N calculation / Calcul S/N"]
        )
        if option == "Change Password / Modifier mot de passe":
            change_password()
        elif option in ["Unknown calculation / Calcul inconnu", "S/N calculation / Calcul S/N"]:
            calculation_page(option)
# ================================
# Partie 3 : Gestion utilisateurs et calculs
# ================================

# Gestion utilisateurs (admin)
def manage_users():
    st.subheader("User Management / Gestion des utilisateurs")
    users = st.session_state.users

    new_user = st.text_input("New username / Nouveau nom d'utilisateur:")
    new_password = st.text_input("New password / Nouveau mot de passe:", type="password")
    new_role = st.selectbox("Role / Rôle:", ["user", "admin"])
    
    if st.button("Add / Ajouter"):
        if new_user.lower() in users:
            st.error("User already exists / L'utilisateur existe déjà")
        else:
            users[new_user.lower()] = {"password": new_password, "role": new_role}
            save_users()
            st.success(f"User {new_user} added / ajouté ✅")

    st.write("Existing users / Utilisateurs existants:")
    for uname, info in users.items():
        col1, col2, col3 = st.columns([2,1,1])
        col1.write(uname)
        col2.write(info["role"])
        if col3.button(f"Delete / Supprimer {uname}"):
            del users[uname]
            save_users()
            st.success(f"User {uname} deleted / supprimé ✅")
            st.experimental_rerun()

# Modifier mot de passe (user)
def change_password():
    st.subheader("Change Password / Modifier mot de passe")
    current_pwd = st.text_input("Current password / Mot de passe actuel:", type="password")
    new_pwd = st.text_input("New password / Nouveau mot de passe:", type="password")
    if st.button("Save / Enregistrer"):
        username = st.session_state.current_user
        if st.session_state.users[username]["password"] == current_pwd:
            st.session_state.users[username]["password"] = new_pwd
            save_users()
            st.success("Password updated ✅ / Mot de passe mis à jour ✅")
        else:
            st.error("Current password incorrect / Mot de passe actuel incorrect")

# Calcul inconnu ou S/N
def calculation_page(option):
    st.subheader(option)
    # Exemple simple pour récupérer CSV et unités
    uploaded_file = st.file_uploader("Upload CSV / Importer CSV", type=["csv"])
    if uploaded_file:
        import pandas as pd
        df = pd.read_csv(uploaded_file)
        st.write(df.head())
    
    unit = st.text_input("Unit / Unité:", value="mg/mL")
    st.session_state.unit = unit
    
    if st.button("Calculate / Calculer"):
        # Ici placer les calculs existants de l'application précédente
        try:
            result = perform_calculation(df, unit, option)
            st.success("Calculation done ✅ / Calcul terminé ✅")
            st.write(result)
        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs : {e}")
# ================================
# Partie 4 : Calculs avancés et export PDF
# ================================

from fpdf import FPDF
import numpy as np

def perform_calculation(df, unit, option):
    """
    Effectue les calculs selon le choix de l'utilisateur.
    - df : DataFrame du CSV importé
    - unit : unité de concentration ou signal
    - option : type de calcul ("Unknown calculation" ou "S/N")
    """
    result = {}
    if option in ["Unknown calculation", "Calcul inconnu"]:
        # Exemple: moyenne du signal
        result["Mean signal"] = df["Signal"].mean()
        result["Unit"] = unit
    elif option in ["S/N"]:
        # Calcul S/N classique
        signal = df["Signal"]
        noise = df["Signal"].rolling(window=5).std()  # bruit estimé sur 5 points
        sn_values = signal / noise
        result["S/N (classical)"] = sn_values.mean()
        
        # Optionnel: calcul LOD et LOQ avec pente si linéarité fournie
        if "Concentration" in df.columns:
            x = df["Concentration"].values
            y = df["Signal"].values
            slope, intercept = np.polyfit(x, y, 1)
            lod = (3 * np.std(y - (slope*x + intercept))) / slope
            loq = (10 * np.std(y - (slope*x + intercept))) / slope
            result["LOD"] = lod
            result["LOQ"] = loq
            result["Unit"] = unit
    return result

# Export PDF
def export_pdf(results, filename="report.pdf", company_name=""):
    if company_name.strip() == "":
        st.error("Please enter company name before generating report / Veuillez saisir le nom de l'entreprise avant de générer le rapport")
        return
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"App: LabT - Report", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Company / Société: {company_name}", ln=True)
    
    pdf.ln(5)
    for k, v in results.items():
        pdf.cell(0, 10, f"{k}: {v}", ln=True)
    
    pdf.output(filename)
    st.success(f"PDF generated ✅ / PDF généré: {filename}")