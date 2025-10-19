# app_part1.py

import streamlit as st
import json
from pathlib import Path

# ----------------------------
# Initialisation session_state
# ----------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = ''
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'lang' not in st.session_state:
    st.session_state.lang = 'English'  # Anglais par défaut

# ----------------------------
# Gestion des utilisateurs (JSON)
# ----------------------------
USERS_FILE = Path("users.json")

def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ----------------------------
# Connexion
# ----------------------------
def login_action(username_input, password_input):
    users = load_users()
    username_lower = username_input.lower()
    if username_lower in users:
        user_data = users[username_lower]
        if user_data["password"] == password_input:
            st.session_state.logged_in = True
            st.session_state.username = username_lower
            st.session_state.role = user_data.get("role", "user")
            st.experimental_rerun()
        else:
            st.error("Incorrect password / Mot de passe incorrect")
    else:
        st.error("User not found / Utilisateur non trouvé")

def login_page():
    st.title("App: LabT / Application LabT")
    st.selectbox("Language / Langue", ["English", "Français"], key="lang")

    username_input = st.text_input("Username / Nom d'utilisateur")
    password_input = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        login_action(username_input, password_input)

# ----------------------------
# Menu après connexion
# ----------------------------
def main_menu():
    st.sidebar.title("Menu")
    if st.session_state.lang == "English":
        menu_items = {
            "Unknown calculation": "Unknown calculation",
            "Linearity": "Linearity",
            "Signal-to-Noise": "Signal-to-Noise",
        }
        if st.session_state.role == "admin":
            menu_items["Manage Users"] = "Manage Users"
    else:
        menu_items = {
            "Calcul inconnu": "Calcul inconnu",
            "Linéarité": "Linéarité",
            "S/N": "S/N",
        }
        if st.session_state.role == "admin":
            menu_items["Gérer les utilisateurs"] = "Gérer les utilisateurs"

    st.session_state.selected_option = st.sidebar.selectbox(
        "Choose an option / Choisir une option", list(menu_items.keys())
    )

# ----------------------------
# App principale
# ----------------------------
def run_app():
    if not st.session_state.logged_in:
        login_page()
    else:
        st.success(f"Login successful ✅ / Vous êtes connecté en tant que {st.session_state.role}")
        main_menu()

if __name__ == "__main__":
    run_app()
# app_part2.py

import streamlit as st
from app_part1 import load_users, save_users

def manage_users():
    st.header("Manage Users / Gérer les utilisateurs")
    users = load_users()

    # Affichage des utilisateurs existants
    st.subheader("Existing Users / Utilisateurs existants")
    for u, data in users.items():
        st.write(f"- {u} ({data.get('role','user')})")

    # Ajouter un utilisateur
    st.subheader("Add User / Ajouter un utilisateur")
    new_user = st.text_input("Username / Nom d'utilisateur", key="add_user")
    new_password = st.text_input("Password / Mot de passe", key="add_pass", type="password")
    new_role = st.selectbox("Role / Rôle", ["user", "admin"], key="add_role")
    if st.button("Add / Ajouter"):
        if new_user.strip() == "" or new_password.strip() == "":
            st.error("Username and password cannot be empty / Nom et mot de passe obligatoires")
        else:
            uname_lower = new_user.lower()
            if uname_lower in users:
                st.error("User already exists / L'utilisateur existe déjà")
            else:
                users[uname_lower] = {"password": new_password, "role": new_role}
                save_users(users)
                st.success(f"User {new_user} added successfully / ajouté avec succès")
                st.experimental_rerun()

    # Modifier le mot de passe d’un utilisateur
    st.subheader("Modify Password / Modifier le mot de passe")
    mod_user = st.selectbox("Select user / Choisir utilisateur", list(users.keys()), key="mod_user")
    new_mod_password = st.text_input("New password / Nouveau mot de passe", key="mod_pass", type="password")
    if st.button("Update / Mettre à jour"):
        if new_mod_password.strip() == "":
            st.error("Password cannot be empty / Mot de passe obligatoire")
        else:
            users[mod_user]["password"] = new_mod_password
            save_users(users)
            st.success(f"Password for {mod_user} updated successfully / mis à jour")
            st.experimental_rerun()

    # Supprimer un utilisateur
    st.subheader("Delete User / Supprimer un utilisateur")
    del_user = st.selectbox("Select user / Choisir utilisateur à supprimer", list(users.keys()), key="del_user")
    if st.button("Delete / Supprimer"):
        if del_user == st.session_state.username:
            st.error("You cannot delete your own account / Impossible de supprimer son compte")
        else:
            users.pop(del_user)
            save_users(users)
            st.success(f"User {del_user} deleted successfully / supprimé avec succès")
            st.experimental_rerun()


def user_profile():
    st.header("User Profile / Profil utilisateur")
    st.write(f"Username / Nom d'utilisateur: {st.session_state.username}")
    st.write(f"Role / Rôle: {st.session_state.role}")
    
    st.subheader("Change Password / Changer le mot de passe")
    old_pass = st.text_input("Current password / Mot de passe actuel", type="password", key="old_pass")
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password", key="new_pass")
    if st.button("Update Password / Mettre à jour"):
        users = load_users()
        user_data = users.get(st.session_state.username)
        if not user_data or user_data["password"] != old_pass:
            st.error("Incorrect current password / Mot de passe actuel incorrect")
        else:
            user_data["password"] = new_pass
            users[st.session_state.username] = user_data
            save_users(users)
            st.success("Password updated successfully / Mot de passe mis à jour")
            st.experimental_rerun()
# app_part3.py

import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
from app_part2 import load_users

def unknown_calculation():
    st.header("Unknown Calculation / Calcul inconnu")

    # Vérification de l'unité
    if "unit" not in st.session_state:
        st.session_state.unit = ""

    st.session_state.unit = st.text_input("Unit / Unité", st.session_state.unit, key="unit_input")

    st.subheader("Input data / Données d'entrée")
    conc = st.number_input(f"Concentration ({st.session_state.unit})", min_value=0.0, step=0.01)
    signal = st.number_input("Signal / Signal", min_value=0.0, step=0.01)

    if st.button("Calculate / Calculer"):
        if st.session_state.unit.strip() == "":
            st.error("Unit must be specified / L'unité doit être spécifiée")
            return

        sn_ratio = signal / conc if conc != 0 else None
        st.success(f"Signal/Concentration: {sn_ratio:.4f} {st.session_state.unit if sn_ratio else ''}")

def linearity_analysis():
    st.header("Linearity Analysis / Analyse de linéarité")

    uploaded_file = st.file_uploader("Upload CSV / Télécharger CSV", type=["csv"])
    use_curve = st.checkbox("Use linear curve for S/N / Utiliser courbe pour S/N", value=True)

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "Concentration" not in df.columns or "Signal" not in df.columns:
            st.error("CSV must contain 'Concentration' and 'Signal' columns / le CSV doit contenir 'Concentration' et 'Signal'")
            return
        st.write(df.head())

        if use_curve:
            # Simple linear regression
            slope, intercept = np.polyfit(df["Concentration"], df["Signal"], 1)
            st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée à l'origine: {intercept:.4f}")
            st.session_state.slope = slope
            st.session_state.intercept = intercept
        else:
            st.session_state.slope = None

def export_pdf():
    st.header("Export PDF / Exporter PDF")
    
    company_name = st.text_input("Company Name / Nom de l’entreprise")
    if st.button("Generate PDF / Générer PDF"):
        if company_name.strip() == "":
            st.error("Company name must be specified / Le nom de l’entreprise est obligatoire")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"App: LabT", ln=True)
        pdf.cell(0, 10, f"Company / Entreprise: {company_name}", ln=True)

        if "slope" in st.session_state and st.session_state.slope is not None:
            pdf.cell(0, 10, f"Slope / Pente: {st.session_state.slope:.4f}", ln=True)

        # Exemple : ajout du calcul inconnu
        if "unit" in st.session_state and st.session_state.unit != "":
            pdf.cell(0, 10, f"Unknown Calculation Unit / Unité calcul inconnu: {st.session_state.unit}", ln=True)

        pdf.output("report.pdf")
        st.success("PDF generated successfully / PDF généré avec succès")
# app_part4.py

import streamlit as st
from app_part1 import load_users, save_users  # assume this part handles JSON user storage
from app_part3 import unknown_calculation, linearity_analysis, export_pdf

def login_page():
    st.title("LabT Application")

    users = load_users()
    user_list = [u.lower() for u in users.keys()]
    
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", user_list)
    password = st.text_input("Password / Mot de passe", type="password")
    
    if st.button("Login / Connexion"):
        login_action(selected_user, password)

def login_action(selected_user, password):
    users = load_users()
    selected_user_lower = selected_user.lower()
    if selected_user_lower in [u.lower() for u in users.keys()] and password == users[selected_user]["password"]:
        st.session_state["logged_in"] = True
        st.session_state["user"] = selected_user_lower
        st.session_state["role"] = users[selected_user]["role"]
        st.experimental_rerun()
    else:
        st.error("Invalid credentials / Identifiants invalides")

def admin_panel():
    st.header("Admin Panel / Panneau Admin")
    action = st.selectbox("Action:", ["Add / Ajouter", "Delete / Supprimer", "Modify / Modifier"])
    
    users = load_users()
    
    if action == "Add / Ajouter":
        new_user = st.text_input("New username / Nouvel utilisateur")
        new_pass = st.text_input("Password / Mot de passe", type="password")
        role = st.selectbox("Role:", ["admin", "user"])
        if st.button("Add / Ajouter"):
            users[new_user] = {"password": new_pass, "role": role}
            save_users(users)
            st.success("User added / Utilisateur ajouté")
    
    elif action == "Delete / Supprimer":
        del_user = st.selectbox("Select user / Sélectionner un utilisateur", list(users.keys()))
        if st.button("Delete / Supprimer"):
            users.pop(del_user, None)
            save_users(users)
            st.success("User deleted / Utilisateur supprimé")
    
    elif action == "Modify / Modifier":
        mod_user = st.selectbox("Select user / Sélectionner un utilisateur", list(users.keys()))
        new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
        new_role = st.selectbox("New role / Nouveau rôle", ["admin", "user"])
        if st.button("Modify / Modifier"):
            users[mod_user] = {"password": new_pass, "role": new_role}
            save_users(users)
            st.success("User modified / Utilisateur modifié")

def user_panel():
    st.header("User Panel / Panneau Utilisateur")
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
    if st.button("Change Password / Changer mot de passe"):
        users = load_users()
        users[st.session_state.user]["password"] = new_pass
        save_users(users)
        st.success("Password updated / Mot de passe mis à jour")

def main_app():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_page()
    else:
        st.sidebar.title("Menu")
        role = st.session_state["role"]
        options = []
        if role == "admin":
            options = ["User Management / Gestion utilisateurs"]
        options += [
            "Unknown Calculation / Calcul inconnu",
            "Linearity / Linéarité",
            "Export PDF"
        ]
        choice = st.sidebar.selectbox("Select / Sélectionner", options)

        if role == "admin" and choice.startswith("User Management"):
            admin_panel()
        elif choice.startswith("Unknown Calculation"):
            unknown_calculation()
        elif choice.startswith("Linearity"):
            linearity_analysis()
        elif choice.startswith("Export PDF"):
            export_pdf()

if __name__ == "__main__":
    main_app()