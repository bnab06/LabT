import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import json
import matplotlib.pyplot as plt

# Initialisation de session_state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "unit" not in st.session_state:
    st.session_state.unit = ""
# Chargement des utilisateurs depuis un fichier JSON
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# Action de login insensible à la casse
def login_action(selected_user, password):
    users = load_users()
    selected_user_lower = selected_user.lower()
    matched_user = None
    for user in users:
        if user.lower() == selected_user_lower:
            matched_user = user
            break

    if matched_user and users[matched_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = matched_user
        st.session_state.role = users[matched_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"Connexion réussie ✅ / You are logged in as {matched_user}")
        st.experimental_rerun()
    else:
        st.error("Nom d’utilisateur ou mot de passe incorrect ❌ / Wrong username or password")

# Page login
def login_page():
    st.title("LabT App / Application LabT")
    users = load_users()
    selected_user = st.selectbox(
        "Choisir un utilisateur / Choose user:", 
        sorted(list(users.keys()), key=lambda x: x.lower()), 
        key="login_user"
    )
    password = st.text_input("Mot de passe / Password:", type="password", key="login_pass")
    if st.button("Se connecter / Login"):
        login_action(selected_user, password)

# Navigation
if not st.session_state.logged_in:
    login_page()
def main_menu():
    st.title("LabT App / Application LabT")
    if st.session_state.role == "admin":
        menu_options = [
            "Gérer les utilisateurs / Manage Users",
            "Linéarité / Linearity",
            "Calcul S/N classique / Classical S/N",
            "Calcul S/N USP / USP S/N",
        ]
    else:
        menu_options = [
            "Linéarité / Linearity",
            "Calcul S/N classique / Classical S/N",
            "Calcul S/N USP / USP S/N",
        ]

    choice = st.selectbox("Menu principal / Main menu:", menu_options, key="main_menu")

    if choice.startswith("Gérer les utilisateurs") or choice.startswith("Manage Users"):
        manage_users_page()
    elif choice.startswith("Linéarité") or choice.startswith("Linearity"):
        linearity_page()
    elif choice.startswith("Calcul S/N classique") or choice.startswith("Classical S/N"):
        sn_classical_page()
    elif choice.startswith("Calcul S/N USP") or choice.startswith("USP S/N"):
        sn_usp_page()
def manage_users_page():
    st.subheader("Gestion des utilisateurs / User Management")
    users = load_users()

    action = st.radio("Action / Action:", ["Ajouter / Add", "Supprimer / Delete"])
    
    if action.startswith("Ajouter") or action.startswith("Add"):
        new_user = st.text_input("Nom d'utilisateur / Username:")
        new_pass = st.text_input("Mot de passe / Password:", type="password")
        role = st.selectbox("Rôle / Role:", ["admin", "user"])
        if st.button("Valider / Submit"):
            if new_user:
                users[new_user] = {"password": new_pass, "role": role}
                save_users(users)
                st.success("Utilisateur ajouté ✅ / User added")
            else:
                st.error("Veuillez saisir un nom d'utilisateur / Please enter a username")
    
    elif action.startswith("Supprimer") or action.startswith("Delete"):
        user_to_delete = st.selectbox("Sélectionner l'utilisateur / Select user:", list(users.keys()))
        if st.button("Supprimer / Delete"):
            if user_to_delete in users:
                del users[user_to_delete]
                save_users(users)
                st.success("Utilisateur supprimé ✅ / User deleted")

def linearity_page():
    st.subheader("Courbe de linéarité / Linearity curve")
    st.info("Ici vous pouvez importer vos données CSV et tracer la courbe / Import CSV to plot curve")
    uploaded_file = st.file_uploader("Importer CSV / Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())
        # Option pour tracer la courbe de linéarité
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.iloc[:,0], y=df.iloc[:,1], mode='lines+markers'))
        st.plotly_chart(fig)
        st.session_state.slope, st.session_state.intercept = np.polyfit(df.iloc[:,0], df.iloc[:,1], 1)

def sn_classical_page():
    st.subheader("S/N classique / Classical S/N")
    st.info("Calcul S/N basé sur le bruit de fond")
    # Ici ajouter calculs classiques de S/N

def sn_usp_page():
    st.subheader("S/N USP / USP S/N")
    st.info("Calcul S/N selon USP, possibilité d'utiliser la courbe de linéarité")
    # Ici ajouter calculs USP et LOD/LOQ
    use_linearity = st.checkbox("Utiliser la courbe de linéarité / Use linearity curve")
    if use_linearity:
        st.write(f"Slope utilisée: {st.session_state.slope if 'slope' in st.session_state else 'N/A'}")

def export_pdf():
    st.subheader("Exporter le rapport / Export PDF")
    company_name = st.text_input("Nom de l'entreprise / Company name:")
    if not company_name:
        st.error("Veuillez saisir le nom de l'entreprise avant d'exporter / Please enter company name")
        return
    if st.button("Générer PDF / Generate PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"App: LabT", ln=True)
        pdf.cell(0, 10, f"Entreprise / Company: {company_name}", ln=True)
        pdf.output("rapport_labt.pdf")
        st.success("PDF généré avec succès ✅ / PDF generated successfully")