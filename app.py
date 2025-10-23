import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import json
from io import BytesIO
from pathlib import Path

# -------------------- USERS --------------------
USERS_FILE = "users.json"

def load_users():
    if Path(USERS_FILE).exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    else:
        return {"admin": "admin123"}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------- LOGIN --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

def login_area():
    st.title("Login / Connexion")
    username = st.text_input("Utilisateur / Username").lower()
    password = st.text_input("Mot de passe / Password", type="password")
    if st.button("Se connecter / Login"):
        users = load_users()
        if username in users and users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Bienvenue {username}!")
        else:
            st.error("Utilisateur ou mot de passe invalide / Invalid username or password")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.experimental_rerun()

# -------------------- CHANGE PASSWORD (discret) --------------------
def change_password(username, new_pass):
    users = load_users()
    users[username] = new_pass
    save_users(users)

# -------------------- APPLICATION --------------------
def linearity_tab():
    st.header("Linéarité / Linearity")
    input_type = st.radio("Mode saisie / Input type", ["CSV", "Manuel / Manual"])
    if input_type.startswith("CSV"):
        file = st.file_uploader("Importer CSV / Upload CSV", type=["csv"])
        if file is not None:
            df = pd.read_csv(file)
            if df.shape[1] < 2:
                st.error("Le CSV doit contenir au moins deux colonnes / CSV must have at least 2 columns")
                return
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
    else:
        x_str = st.text_area("Valeurs X (séparées par des virgules)")
        y_str = st.text_area("Valeurs Y (séparées par des virgules)")
        try:
            x = np.array([float(i) for i in x_str.split(",")])
            y = np.array([float(i) for i in y_str.split(",")])
        except:
            st.warning("Veuillez entrer des nombres valides / Enter valid numbers")
            return
    
    # Calcul linéarité
    try:
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        intercept = coeffs[1]
        y_fit = slope*x + intercept
        r2 = np.corrcoef(y, y_fit)[0,1]**2
        st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée à l'origine: {intercept:.4f}")
        st.write(f"R²: {r2:.4f}")
        fig, ax = plt.subplots()
        ax.scatter(x, y)
        ax.plot(x, y_fit, color='red')
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Erreur calcul linéarité / Linearity calculation error: {e}")
        return

    # Concentration / Signal inconnu
    choice = st.selectbox("Calculer / Calculate", ["Concentration inconnue / Unknown concentration", "Signal inconnu / Unknown signal"])
    if choice.startswith("Concentration"):
        signal = st.number_input("Entrer signal / Enter signal", value=float(y[0]))
        conc = (signal - intercept)/slope
        st.write(f"Concentration estimée / Estimated concentration: {conc:.4f}")
    else:
        conc = st.number_input("Entrer concentration / Enter concentration", value=float(x[0]))
        signal = slope*conc + intercept
        st.write(f"Signal estimé / Estimated signal: {signal:.4f}")

    # Export PDF
    company = st.text_input("Nom de la compagnie / Company name")
    unit = st.selectbox("Unité / Unit", ["µg/mL", "mg/mL"], index=0)
    if st.button("Exporter PDF / Export PDF"):
        if company == "":
            st.warning("Veuillez saisir le nom de la compagnie / Enter company name")
        else:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Rapport Linéarité / Linearity Report - {company}", ln=True)
            pdf.cell(0, 10, f"Slope / Pente: {slope:.4f}", ln=True)
            pdf.cell(0, 10, f"Intercept / Ordonnée à l'origine: {intercept:.4f}", ln=True)
            pdf.cell(0, 10, f"R²: {r2:.4f}", ln=True)
            buffer = BytesIO()
            pdf.output(buffer)
            st.download_button("Télécharger PDF / Download PDF", buffer.getvalue(), file_name="linearity_report.pdf")

# -------------------- S/N --------------------
def sn_tab():
    st.header("S/N")
    file_type = st.radio("Type de fichier / File type", ["CSV", "PNG", "PDF"])
    uploaded_file = st.file_uploader("Importer fichier / Upload file", type=["csv","png","pdf"])
    if uploaded_file:
        st.write("Fichier chargé / File loaded")
        st.write(uploaded_file.name)
        # Ici tu pourrais afficher l’aperçu chromatogramme selon le type

# -------------------- ADMIN --------------------
def admin_tab():
    st.header("Admin - Gestion utilisateurs / Manage Users")
    users = load_users()
    add_user = st.text_input("Ajouter utilisateur / Add user")
    add_pass = st.text_input("Mot de passe / Password", type="password")
    if st.button("Ajouter / Add"):
        users[add_user.lower()] = add_pass
        save_users(users)
        st.success(f"Utilisateur {add_user} ajouté / added")
    
    del_user = st.text_input("Supprimer utilisateur / Delete user")
    if st.button("Supprimer / Delete"):
        users.pop(del_user.lower(), None)
        save_users(users)
        st.success(f"Utilisateur {del_user} supprimé / deleted")

# -------------------- MAIN --------------------
if not st.session_state.logged_in:
    login_area()
else:
    st.sidebar.write(f"Connecté: {st.session_state.username}")
    if st.sidebar.button("Se déconnecter / Logout"):
        logout()

    if st.session_state.username == "admin":
        admin_tab()
    else:
        # Changer mot de passe discret
        with st.expander("Changer mot de passe / Change my password", expanded=False):
            new_pass = st.text_input("Nouveau mot de passe / New password", type="password")
            if st.button("Confirmer / Confirm", key="change_pass_user"):
                change_password(st.session_state.username, new_pass)
                st.success("Mot de passe changé / Password changed")
        
        # Menu principal utilisateur
        tabs = st.tabs(["Linéarité / Linearity", "S/N"])
        with tabs[0]:
            linearity_tab()
        with tabs[1]:
            sn_tab()