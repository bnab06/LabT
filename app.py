import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import json
import os

# -----------------------------
# Gestion des utilisateurs
# -----------------------------
USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    # Créer un fichier users par défaut
    default_users = {
        "admin": {"password": "adminpass", "role": "admin"},
        "user1": {"password": "user1pass", "role": "user"}
    }
    with open(USERS_FILE, "w") as f:
        json.dump(default_users, f, indent=4)

with open(USERS_FILE, "r") as f:
    USERS = json.load(f)

# Session pour user
if "user" not in st.session_state:
    st.session_state["user"] = None

# -----------------------------
# Login
# -----------------------------
def login():
    st.title("Connexion")
    username = st.text_input("Utilisateur", key="login_user")
    password = st.text_input("Mot de passe", type="password", key="login_pass")
    if st.button("Se connecter"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state["user"] = username
            st.success(f"Connecté en tant que {username}")
        else:
            st.error("Utilisateur ou mot de passe invalide")

# -----------------------------
# Changer mot de passe (users)
# -----------------------------
def change_password():
    st.subheader("Changer le mot de passe")
    old_pass = st.text_input("Ancien mot de passe", type="password", key="old_pass")
    new_pass = st.text_input("Nouveau mot de passe", type="password", key="new_pass")
    confirm_pass = st.text_input("Confirmer nouveau mot de passe", type="password", key="confirm_pass")

    if st.button("Valider changement", key="change_pass_btn"):
        username = st.session_state["user"]
        if USERS[username]["password"] != old_pass:
            st.error("Ancien mot de passe incorrect")
        elif new_pass != confirm_pass:
            st.error("Les nouveaux mots de passe ne correspondent pas")
        else:
            USERS[username]["password"] = new_pass
            with open(USERS_FILE, "w") as f:
                json.dump(USERS, f, indent=4)
            st.success("Mot de passe changé avec succès")

# -----------------------------
# Application principale
# -----------------------------
def linearity_tab():
    st.header("Linéarité")
    input_type = st.radio("Choisir le type de saisie:", ["CSV", "Saisie manuelle"])
    
    if input_type == "CSV":
        file = st.file_uploader("Importer CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            st.dataframe(df)
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
    else:
        x_text = st.text_input("Valeurs de concentration (séparées par des virgules)")
        y_text = st.text_input("Valeurs de signal (séparées par des virgules)")
        if x_text and y_text:
            x = np.array([float(i) for i in x_text.split(",")])
            y = np.array([float(i) for i in y_text.split(",")])

    if 'x' in locals() and 'y' in locals():
        # Régression linéaire
        A = np.vstack([x, np.ones(len(x))]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)[0]
        r2 = np.corrcoef(x, y)[0,1]**2

        st.write(f"Pente: {m:.4f}")
        st.write(f"Ordonnée à l'origine: {c:.4f}")
        st.write(f"R²: {r2:.4f}")

        # Plot
        fig, ax = plt.subplots()
        ax.scatter(x, y, label="Données")
        ax.plot(x, m*x + c, color='red', label="Fit linéaire")
        ax.set_xlabel("Concentration (µg/mL)")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)

        # Calcul concentration ou signal inconnu
        val_unknown = st.number_input("Entrer signal ou concentration inconnue")
        mode = st.radio("Calculer:", ["Concentration", "Signal"])
        if mode == "Concentration":
            conc = (val_unknown - c)/m
            st.write(f"Concentration inconnue: {conc:.4f} µg/mL")
        else:
            signal = m*val_unknown + c
            st.write(f"Signal correspondant: {signal:.4f}")

        # Export PDF
        company = st.text_input("Nom de la compagnie pour le rapport PDF", "Ma compagnie")
        if st.button("Exporter rapport linéarité"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, f"Rapport de linéarité - {company}", ln=True, align='C')
            pdf.ln(10)
            pdf.cell(200, 10, f"Pente: {m:.4f}", ln=True)
            pdf.cell(200, 10, f"Ordonnée à l'origine: {c:.4f}", ln=True)
            pdf.cell(200, 10, f"R²: {r2:.4f}", ln=True)
            pdf.output("rapport_linearity.pdf")
            st.success("Rapport PDF généré: rapport_linearity.pdf")

def sn_tab():
    st.header("Signal / Bruit (S/N)")
    input_type = st.radio("Importer:", ["CSV", "Image (png/pdf)"])
    st.info("Zone de sélection et calcul S/N à implémenter selon vos besoins")

# -----------------------------
# Menu Admin
# -----------------------------
def admin_tab():
    st.header("Gestion des utilisateurs (Admin)")
    st.info("Ajouter, supprimer ou modifier un utilisateur")
    # Exemple simple
    new_user = st.text_input("Nom utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["user", "admin"])
    if st.button("Ajouter utilisateur"):
        if new_user in USERS:
            st.error("Utilisateur existe déjà")
        else:
            USERS[new_user] = {"password": new_pass, "role": role}
            with open(USERS_FILE, "w") as f:
                json.dump(USERS, f, indent=4)
            st.success(f"Utilisateur {new_user} ajouté")

# -----------------------------
# Main
# -----------------------------
if st.session_state["user"] is None:
    login()
else:
    user_role = USERS[st.session_state["user"]]["role"]
    st.write(f"Connecté en tant que {st.session_state['user']} ({user_role})")
    
    if user_role == "admin":
        admin_tab()
    else:
        change_password()
        # Onglets Linéarité / S/N
        tabs = st.tabs(["Linéarité", "S/N"])
        with tabs[0]:
            linearity_tab()
        with tabs[1]:
            sn_tab()