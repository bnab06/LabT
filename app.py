import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import json
import os

# ----------------- Utilisateurs -----------------
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# ----------------- Login -----------------
if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.title("LabT - Connexion")
    users = load_users()
    usernames = list(users.keys())
    selected_user = st.selectbox("Choisir un utilisateur", usernames)
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if password == users[selected_user]["password"]:
            st.session_state.user = selected_user
            st.session_state.role = users[selected_user]["role"]
            st.success(f"Connecté en tant que {selected_user}")
            st.experimental_rerun()
        else:
            st.error("Mot de passe incorrect")

def logout():
    st.session_state.user = None
    st.experimental_rerun()

# ----------------- Menu Principal -----------------
def main_menu():
    st.title(f"LabT - Connecté : {st.session_state.user}")
    st.button("Se déconnecter", on_click=logout)

    if st.session_state.role == "admin":
        st.subheader("Gestion des utilisateurs")
        manage_users()
    else:
        menu_choice = st.selectbox("Choisir l'option", ["Linéarité", "Signal/Concentration inconnu", "S/N USP"])
        if menu_choice == "Linéarité":
            linearity_page()
        elif menu_choice == "Signal/Concentration inconnu":
            unknown_page()
        elif menu_choice == "S/N USP":
            sn_page()

# ----------------- Gestion utilisateurs -----------------
def manage_users():
    users = load_users()
    st.write("Ajouter un utilisateur")
    new_user = st.text_input("Nom utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    if st.button("Ajouter"):
        if new_user and new_pass:
            users[new_user] = {"password": new_pass, "role": "user"}
            save_users(users)
            st.success("Utilisateur ajouté")
        else:
            st.error("Remplir tous les champs")
    st.write("Supprimer un utilisateur existant")
    del_user = st.selectbox("Sélectionner un utilisateur", list(users.keys()))
    if st.button("Supprimer"):
        if del_user != "admin":
            users.pop(del_user)
            save_users(users)
            st.success(f"Utilisateur {del_user} supprimé")
        else:
            st.error("Impossible de supprimer l'admin")

# ----------------- Linéarité -----------------
def linearity_page():
    st.header("Linéarité")
    conc_input = st.text_input("Concentrations (séparées par des virgules)")
    response_input = st.text_input("Réponses (séparées par des virgules)")
    unknown_choice = st.selectbox("Calculer", ["Concentration inconnue", "Signal inconnu"])
    unit = st.selectbox("Unité", ["µg/mL", "mg/mL"])
    unknown_value = st.number_input("Valeur inconnue")

    if st.button("Calculer"):
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",")])
            resp = np.array([float(x.strip()) for x in response_input.split(",")])
            m, b = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(resp, m*conc + b)[0,1]**2
            fig = px.scatter(x=conc, y=resp, labels={"x":"Concentration", "y":"Réponse"}, title="Courbe de linéarité")
            fig.add_traces(px.line(x=conc, y=m*conc + b).data)
            st.plotly_chart(fig)

            st.write(f"Équation : y = {m:.4f}x + {b:.4f}")
            st.write(f"R² = {r2:.4f}")

            if unknown_choice=="Concentration inconnue":
                conc_unknown = (unknown_value - b)/m
                st.success(f"Concentration inconnue = {conc_unknown:.4f} {unit}")
                result_text = f"Concentration inconnue = {conc_unknown:.4f} {unit}"
            else:
                signal_unknown = m*unknown_value + b
                st.success(f"Signal inconnu = {signal_unknown:.4f}")
                result_text = f"Signal inconnu = {signal_unknown:.4f}"

            # PDF export
            if st.button("Exporter PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "Rapport Linéarité - LabT", ln=True, align="C")
                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 10, f"Utilisateur: {st.session_state.user}", ln=True)
                pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
                pdf.ln(5)
                pdf.cell(0, 10, f"Équation : y = {m:.4f}x + {b:.4f}", ln=True)
                pdf.cell(0, 10, f"R² = {r2:.4f}", ln=True)
                pdf.cell(0, 10, result_text, ln=True)
                fig.write_image("temp_linearity.png")
                pdf.image("temp_linearity.png", x=10, w=180)
                pdf_file = f"Rapport_Linéarité_{st.session_state.user}.pdf"
                pdf.output(pdf_file)
                st.download_button("Télécharger PDF", data=open(pdf_file, "rb").read(), file_name=pdf_file)

        except Exception as e:
            st.error(f"Erreur: {e}")

# ----------------- Signal/concentration inconnu -----------------
def unknown_page():
    st.header("Calcul automatique inconnu")
    # Même logique que linéarité_page mais séparée si nécessaire
    st.info("Fonction calcul automatique inconnu ici")

# ----------------- S/N USP -----------------
def sn_page():
    st.header("Signal/Noise USP")
    uploaded_file = st.file_uploader("Charger CSV (Time, Signal)", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            if df.shape[1]<2:
                st.error("CSV doit avoir au moins deux colonnes (Time, Signal)")
                return
            st.plotly_chart(px.line(df, x=df.columns[0], y=df.columns[1], labels={"x":"Time","y":"Signal"}))
            st.success("Fichier chargé")
        except Exception as e:
            st.error(f"Erreur: {e}")

# ----------------- Lancement -----------------
if st.session_state.user is None:
    login()
else:
    main_menu()