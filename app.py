# ---------------- Partie 1 ----------------
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime

# ---------------- Configuration ----------------
st.set_page_config(page_title="App: LabT", layout="wide")

# Initialisation de session_state pour éviter les erreurs
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

# ---------------- Fonctions utilitaires ----------------
def load_users():
    """Charge les utilisateurs depuis un fichier JSON"""
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    """Sauvegarde les utilisateurs dans un fichier JSON"""
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    """Fonction simplifiée de hash pour exemple"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
# ---------------- Partie 2 ----------------
# ---------------- Page de connexion ----------------
def login_page():
    st.title("App: LabT / Connexion")

    users = load_users()
    usernames = list(users.keys())

    # Sélection de l'utilisateur
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", usernames, key="select_user")

    # Mot de passe
    password = st.text_input("Password / Mot de passe:", type="password", key="password_input")

    # Bouton connexion
    if st.button("Login / Connexion"):
        login_action(selected_user, password)

def login_action(username, password):
    users = load_users()
    username_lower = username.lower()
    if username_lower in [u.lower() for u in users.keys()]:
        stored_user = [u for u in users.keys() if u.lower() == username_lower][0]
        if hash_password(password) == users[stored_user]["password"]:
            st.session_state.logged_in = True
            st.session_state.user_role = users[stored_user]["role"]
            st.session_state.username = stored_user
            st.success(f"Login successful ✅ / Vous êtes connecté en tant que {st.session_state.user_role}")
            st.experimental_rerun()
        else:
            st.error("Incorrect password / Mot de passe incorrect")
    else:
        st.error("User not found / Utilisateur non trouvé")

# ---------------- Menu principal ----------------
def main_menu():
    st.title("App: LabT")

    if st.session_state.user_role == "admin":
        option = st.selectbox("Select option / Choisir une option:", ["User management / Gestion utilisateurs"])
        if option.startswith("User management"):
            user_management()
    else:
        option = st.selectbox("Select option / Choisir une option:", ["Unknown calculation / Calcul inconnu", "S/N analysis / Analyse S/N"])
        if option.startswith("Unknown"):
            unknown_calculation()
        elif option.startswith("S/N"):
            sn_analysis()

# ---------------- Gestion utilisateurs (admin) ----------------
def user_management():
    st.header("User Management / Gestion des utilisateurs")
    users = load_users()

    # Ajouter un utilisateur
    st.subheader("Add user / Ajouter un utilisateur")
    new_username = st.text_input("Username / Nom d'utilisateur", key="new_user")
    new_password = st.text_input("Password / Mot de passe", type="password", key="new_pass")
    role = st.selectbox("Role / Rôle", ["user", "admin"], key="new_role")
    if st.button("Add / Ajouter"):
        if new_username and new_password:
            if new_username.lower() not in [u.lower() for u in users.keys()]:
                users[new_username] = {"password": hash_password(new_password), "role": role}
                save_users(users)
                st.success(f"User {new_username} added / ajouté ✅")
            else:
                st.error("User already exists / Utilisateur déjà existant")
# ---------------- Partie 3 ----------------
# ---------------- Calcul inconnu ----------------
def unknown_calculation():
    st.header("Unknown calculation / Calcul inconnu")
    
    conc_values = st.text_area("Enter concentrations / Entrez les concentrations (séparées par ,):", key="conc_input")
    signal_values = st.text_area("Enter signals / Entrez les signaux (séparés par ,):", key="signal_input")
    unit = st.text_input("Unit of concentration / Unité de concentration:", value="mg/mL", key="unit_input")
    
    if st.button("Calculate / Calculer"):
        try:
            conc_list = [float(x.strip()) for x in conc_values.split(",")]
            signal_list = [float(x.strip()) for x in signal_values.split(",")]
            if len(conc_list) != len(signal_list):
                st.error("Concentration and signal lists must have the same length / Les listes doivent avoir la même taille")
                return
            # Exemple de calcul linéaire simple (y = mx + b)
            m, b = np.polyfit(conc_list, signal_list, 1)
            st.session_state.slope = m
            st.session_state.intercept = b
            st.success(f"Slope / Pente: {m:.4f}, Intercept / Ordonnée à l'origine: {b:.4f}")
        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs: {e}")

# ---------------- Analyse S/N ----------------
def sn_analysis():
    st.header("S/N analysis / Analyse S/N")
    use_linear_curve = st.checkbox("Use linearity curve for LOD/LOQ / Utiliser la courbe de linéarité", value=True)
    
    # Entrer signal et bruit
    signal = st.number_input("Signal:", min_value=0.0, key="sn_signal")
    noise = st.number_input("Noise:", min_value=0.0, key="sn_noise")
    
    if st.button("Calculate S/N / Calculer S/N"):
        try:
            sn_classic = signal / noise if noise != 0 else None
            st.write(f"Classic S/N: {sn_classic:.4f}" if sn_classic else "Undefined / Indéfini")
            
            if use_linear_curve and "slope" in st.session_state and st.session_state.slope:
                # Calcul LOD et LOQ en concentration
                lod = 3.3 * noise / st.session_state.slope
                loq = 10 * noise / st.session_state.slope
                st.write(f"LOD: {lod:.4f}, LOQ: {loq:.4f} {st.session_state.unit if 'unit' in st.session_state else ''}")
        except Exception as e:
            st.error(f"Error in S/N calculation / Erreur S/N: {e}")

# ---------------- Préparation du PDF ----------------
def export_pdf(filename="LabT_report.pdf"):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(0, 10, txt="App: LabT Report", ln=True)
    pdf.ln(5)
    
    if "slope" in st.session_state:
        pdf.cell(0, 10, txt=f"Slope / Pente: {st.session_state.slope:.4f}", ln=True)
    if "intercept" in st.session_state:
        pdf.cell(0, 10, txt=f"Intercept / Ordonnée: {st.session_state.intercept:.4f}", ln=True)
    if "unit" in st.session_state:
        pdf.cell(0, 10, txt=f"Unit / Unité: {st.session_state.unit}", ln=True)
    
    pdf.output(filename)
    st.success(f"PDF saved / PDF sauvegardé: {filename}")
# ---------------- Partie 4 ----------------
# ---------------- Helpers ----------------
def load_users(filename="users.json"):
    import json, os
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_users(users, filename="users.json"):
    import json
    with open(filename, "w") as f:
        json.dump(users, f, indent=4)

# ---------------- Initialisation session_state ----------------
if "slope" not in st.session_state:
    st.session_state.slope = None
if "intercept" not in st.session_state:
    st.session_state.intercept = None
if "unit" not in st.session_state:
    st.session_state.unit = ""

# ---------------- Menu principal ----------------
def main_menu():
    st.title("LabT App")
    option = st.selectbox("Select option / Choisir option:", 
                          ["Unknown calculation / Calcul inconnu", 
                           "S/N analysis / Analyse S/N", 
                           "Export PDF"])
    
    if option.startswith("Unknown"):
        unknown_calculation()
    elif option.startswith("S/N"):
        sn_analysis()
    elif option.startswith("Export"):
        export_pdf()

# ---------------- Application ----------------
def app():
    users = load_users()
    st.sidebar.title("Login / Connexion")
    selected_user = st.sidebar.selectbox("Choose user / Choisir un utilisateur:", list(users.keys()))
    password = st.sidebar.text_input("Password / Mot de passe:", type="password")
    
    if st.sidebar.button("Login / Connexion"):
        if selected_user.lower() in (u.lower() for u in users.keys()) and password == users[selected_user]:
            st.success(f"Login successful ✅ / Vous êtes connecté en tant que {selected_user}")
            main_menu()
        else:
            st.error("Invalid credentials / Identifiants invalides")

# ---------------- Lancer l’app ----------------
if __name__ == "__main__":
    app()