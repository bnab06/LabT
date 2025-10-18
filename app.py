import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from fpdf import FPDF
from PIL import Image
import io
import datetime
import json
import os

# --------------------------
# Load users
# --------------------------
USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    st.error("Fichier users.json manquant.")
    st.stop()

with open(USERS_FILE) as f:
    users = json.load(f)

# --------------------------
# Session state
# --------------------------
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.page = "menu"

# --------------------------
# Login function
# --------------------------
def login():
    st.title("LabT – Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.login = True
            st.session_state.user = username
            st.session_state.role = users[username]["role"]
            st.session_state.page = "menu"
            st.success(f"Connecté en tant que {username}")
        else:
            st.error("Identifiants incorrects")

# --------------------------
# Logout
# --------------------------
def logout():
    st.session_state.login = False
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.page = "login"

# --------------------------
# Main menu
# --------------------------
def menu():
    st.markdown(f"### Connecté en tant que: {st.session_state.user}")
    st.title("LabT – Menu Principal")
    choice = st.selectbox("Choisir une fonctionnalité", ["--Sélectionner--","Signal/Noise USP", "Linéarité", "Gérer les utilisateurs (Admin)"])
    if choice == "Signal/Noise USP":
        st.session_state.page = "sn"
    elif choice == "Linéarité":
        st.session_state.page = "linearite"
    elif choice == "Gérer les utilisateurs (Admin)":
        if st.session_state.role == "admin":
            st.session_state.page = "admin"
        else:
            st.warning("Accès réservé à l'admin")

# --------------------------
# S/N USP, LOD, LOQ
# --------------------------
def sn_page():
    st.title("S/N USP, LOD, LOQ")
    uploaded_file = st.file_uploader("Uploader un fichier CSV/PNG/PDF", type=["csv","png","pdf"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(".png") or uploaded_file.name.endswith(".pdf"):
                # OCR / image processing option skipped for rapid setup
                st.warning("Extraction graphique non implémentée pour PDF/PNG. Convertir en CSV pour l'instant.")
                return
            else:
                st.error("Format non supporté.")
                return

            st.dataframe(df.head())
            start = st.number_input("Début (temps)", min_value=float(df.iloc[:,0].min()), max_value=float(df.iloc[:,0].max()), value=float(df.iloc[:,0].min()))
            end = st.number_input("Fin (temps)", min_value=float(df.iloc[:,0].min()), max_value=float(df.iloc[:,0].max()), value=float(df.iloc[:,0].max()))
            if st.button("Calculer S/N, LOD, LOQ"):
                y = df.iloc[:,1][(df.iloc[:,0]>=start) & (df.iloc[:,0]<=end)]
                noise = np.std(y[:5])
                peak = np.max(y)
                sn = peak / noise
                lod = 3 * noise
                loq = 10 * noise
                st.write(f"Signal/Noise (USP): {sn:.2f}")
                st.write(f"LOD: {lod:.2f}")
                st.write(f"LOQ: {loq:.2f}")
        except Exception as e:
            st.error(f"Erreur: {e}")

    if st.button("Retour au menu principal"):
        st.session_state.page = "menu"

# --------------------------
# Linéarité
# --------------------------
def linearite_page():
    st.title("Linéarité")
    option = st.radio("Mode d'entrée", ["Manuelle","CSV"])
    concentrations = []
    responses = []
    if option == "Manuelle":
        conc_input = st.text_input("Entrer les concentrations séparées par des virgules (ex: 1,2,3)")
        resp_input = st.text_input("Entrer les réponses correspondantes séparées par des virgules")
        conc_unit = st.selectbox("Unité de concentration", ["µg/mL","mg/mL"])
        resp_unit = st.selectbox("Nom axe Y", ["Aire","Absorbance"])
        if st.button("Tracer courbe"):
            try:
                concentrations = [float(x.strip()) for x in conc_input.split(",")]
                responses = [float(x.strip()) for x in resp_input.split(",")]
                if len(concentrations) != len(responses):
                    st.error("Le nombre de concentrations et réponses doit être identique.")
                    return
                df = pd.DataFrame({"Concentration": concentrations, "Réponse": responses})
                X = np.array(concentrations).reshape(-1,1)
                y = np.array(responses)
                model = LinearRegression().fit(X,y)
                r2 = model.score(X,y)
                st.write(f"R² = {r2:.4f}")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=concentrations, y=responses, mode="markers", name="Points"))
                fig.add_trace(go.Scatter(x=concentrations, y=model.predict(X), mode="lines", name="Régression"))
                fig.update_layout(xaxis_title=f"Concentration ({conc_unit})", yaxis_title=f"{resp_unit}")
                st.plotly_chart(fig)
                unknown = st.number_input("Entrer une réponse inconnue pour estimer la concentration")
                if st.button("Calculer concentration inconnue"):
                    conc_unknown = (unknown - model.intercept_)/model.coef_[0]
                    st.write(f"Concentration inconnue estimée: {conc_unknown:.4f} {conc_unit}")
                    if st.button("Exporter rapport PDF"):
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial","B",16)
                        pdf.cell(0,10,"LabT - Rapport Linéarité",ln=True)
                        pdf.set_font("Arial","",12)
                        pdf.ln(10)
                        pdf.cell(0,10,f"Utilisateur: {st.session_state.user}",ln=True)
                        pdf.cell(0,10,f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
                        pdf.ln(5)
                        pdf.cell(0,10,f"R² = {r2:.4f}",ln=True)
                        pdf.cell(0,10,f"Concentration inconnue estimée: {conc_unknown:.4f} {conc_unit}",ln=True)
                        pdf.output("rapport_linearite.pdf")
                        st.success("Rapport PDF généré: rapport_linearite.pdf")
            except Exception as e:
                st.error(f"Erreur: {e}")
    elif option == "CSV":
        uploaded_csv = st.file_uploader("Uploader CSV avec deux colonnes: Concentration, Réponse", type="csv")
        if uploaded_csv is not None:
            try:
                df = pd.read_csv(uploaded_csv)
                st.dataframe(df.head())
                X = df.iloc[:,0].values.reshape(-1,1)
                y = df.iloc[:,1].values
                model = LinearRegression().fit(X,y)
                r2 = model.score(X,y)
                st.write(f"R² = {r2:.4f}")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df.iloc[:,0], y=df.iloc[:,1], mode="markers", name="Points"))
                fig.add_trace(go.Scatter(x=df.iloc[:,0], y=model.predict(X), mode="lines", name="Régression"))
                fig.update_layout(xaxis_title="Concentration", yaxis_title="Réponse")
                st.plotly_chart(fig)
            except Exception as e:
                st.error(f"Erreur: {e}")

    if st.button("Retour au menu principal"):
        st.session_state.page = "menu"

# --------------------------
# Admin
# --------------------------
def admin_page():
    st.title("Gérer les utilisateurs")
    st.write(users)
    st.write("L'admin peut uniquement consulter la liste des utilisateurs.")
    if st.button("Retour au menu principal"):
        st.session_state.page = "menu"

# --------------------------
# Page dispatcher
# --------------------------
if not st.session_state.login:
    login()
else:
    st.sidebar.button("Déconnexion", on_click=logout)
    if st.session_state.page == "menu":
        menu()
    elif st.session_state.page == "sn":
        sn_page()
    elif st.session_state.page == "linearite":
        linearite_page()
    elif st.session_state.page == "admin":
        admin_page()