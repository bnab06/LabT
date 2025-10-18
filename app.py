import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io, os, json, datetime
from fpdf import FPDF
from PIL import Image
import pdfplumber

USERS_FILE = "users.json"

# --- INITIALISATION SESSION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.page = "login"
    st.session_state.calc_type = None

# --- CHARGER LES UTILISATEURS ---
if not os.path.exists(USERS_FILE):
    users = {"admin": {"password": "admin123"}, "bb": {"password": "bb123"}, "user": {"password": "user123"}}
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
else:
    with open(USERS_FILE, "r") as f:
        users = json.load(f)

# --- FONCTIONS ---
def login_page():
    st.markdown("<h1 style='color: #0055FF;'>LabT - Chromatogram Analyzer</h1>", unsafe_allow_html=True)
    st.subheader("Connexion")
    username = st.text_input("Nom utilisateur")
    password = st.text_input("Mot de passe", type="password")
    calc_choice = st.selectbox("Type de calcul automatique après connexion", 
                               ["Concentration inconnue", "Signal inconnu"])
    if st.button("Se connecter"):
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.calc_type = calc_choice
            st.session_state.page = "menu"
            st.success(f"Connecté en tant que {username} - {calc_choice}")
        else:
            st.error("Nom utilisateur ou mot de passe incorrect")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.page = "login"
    st.session_state.calc_type = None

# --- MENU PRINCIPAL ---
def menu_page():
    st.markdown(f"<h2 style='color: #0055FF;'>LabT - Connecté en tant que {st.session_state.username}</h2>", unsafe_allow_html=True)
    st.button("Déconnexion", on_click=logout)

    if st.session_state.username == "admin":
        st.info("Admin : gérer les utilisateurs")
        manage_users()
    else:
        st.info(f"Utilisateur normal : {st.session_state.calc_type}")
        page_choice = st.selectbox("Choisir une fonctionnalité", ["Linéarité", "S/N"])
        if page_choice == "Linéarité":
            linearity_page()
        elif page_choice == "S/N":
            sn_page()

# --- ADMIN USER MANAGEMENT ---
def manage_users():
    st.subheader("Gérer les utilisateurs")
    user_list = list(users.keys())
    st.write("Utilisateurs existants :", user_list)
    
    action = st.selectbox("Action", ["Ajouter", "Supprimer", "Modifier mot de passe"])
    username = st.text_input("Nom utilisateur")
    password = st.text_input("Mot de passe", type="password")
    
    if st.button("Valider action"):
        if action == "Ajouter":
            if username and password:
                users[username] = {"password": password}
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                st.success(f"Utilisateur {username} ajouté")
            else:
                st.error("Nom utilisateur et mot de passe requis")
        elif action == "Supprimer":
            if username in users:
                users.pop(username)
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                st.success(f"Utilisateur {username} supprimé")
            else:
                st.error("Utilisateur introuvable")
        elif action == "Modifier mot de passe":
            if username in users:
                users[username]["password"] = password
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                st.success(f"Mot de passe modifié pour {username}")
            else:
                st.error("Utilisateur introuvable")

# --- LINÉARITÉ ---
def linearity_page():
    st.subheader("Linéarité")
    mode = st.radio("Mode de saisie", ["Manuel", "CSV"])
    
    conc_unit = st.selectbox("Unité de concentration", ["µg/mL", "mg/mL"])
    
    if mode == "Manuel":
        c = st.text_input("Concentrations (séparées par virgule)")
        r = st.text_input("Réponses (aires ou absorbances, séparées par virgule)")
        if c and r:
            try:
                c_list = [float(x) for x in c.split(",")]
                r_list = [float(x) for x in r.split(",")]
                if len(c_list) != len(r_list):
                    st.error("Concentrations et réponses doivent avoir même longueur")
                    return
                df = pd.DataFrame({"Concentration": c_list, "Réponse": r_list})
                plot_linearity(df, conc_unit)
            except:
                st.error("Erreur dans la conversion des valeurs")
    else:
        uploaded_file = st.file_uploader("Télécharger CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            if df.shape[1] >= 2:
                df.columns = ["Concentration", "Réponse"]
                plot_linearity(df, conc_unit)
            else:
                st.error("CSV invalide")

def plot_linearity(df, conc_unit):
    st.write(df)
    fig = px.scatter(df, x="Concentration", y="Réponse", trendline="ols")
    st.plotly_chart(fig)
    # R2 automatique
    results = px.get_trendline_results(fig)
    r2 = results.iloc[0]["px_fit_results"].rsquared
    st.success(f"R² = {r2:.4f}")
    # Calcul concentration inconnue
    unknown = st.number_input("Valeur de réponse inconnue pour calcul concentration", value=0.0)
    if unknown != 0.0:
        slope = results.iloc[0]["px_fit_results"].params[1]
        intercept = results.iloc[0]["px_fit_results"].params[0]
        conc_calc = (unknown - intercept)/slope
        st.info(f"Concentration inconnue = {conc_calc:.4f} {conc_unit}")

# --- S/N, LOD, LOQ ---
def sn_page():
    st.subheader("Calcul S/N, LOD, LOQ")
    uploaded_file = st.file_uploader("Télécharger chromatogramme CSV", type=["csv","txt","pdf","png"])
    if uploaded_file:
        st.success("Fichier chargé - extraction des données non implémentée pour PDF/PNG")
        # Ici tu peux ajouter digitization ou OCR selon le fichier
        # Pour CSV : lecture et calcul S/N

# --- MAIN ---
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "menu":
    menu_page()