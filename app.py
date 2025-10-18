import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from fpdf import FPDF
import os
import json
from datetime import datetime

# -------------------- USERS --------------------
USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    users = {"admin": {"password": "admin123"}, "bb": {"password": "bb123"}, "user": {"password": "user123"}}
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

with open(USERS_FILE, "r") as f:
    users = json.load(f)

# -------------------- SESSION --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.page = "login"

# -------------------- LOGIN --------------------
def login_page():
    st.title("LabT - Chromatogram Analyzer")
    st.subheader("Connexion")
    username = st.text_input("Nom utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "menu"
            st.experimental_rerun()
        else:
            st.error("Nom utilisateur ou mot de passe incorrect")

# -------------------- LOGOUT --------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.page = "login"
    st.experimental_rerun()

# -------------------- ADMIN --------------------
def admin_page():
    st.header("Gestion des utilisateurs")
    with st.form("user_form"):
        action = st.selectbox("Action", ["Ajouter", "Supprimer", "Modifier"])
        user = st.text_input("Nom utilisateur")
        pwd = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Valider")
        if submitted:
            if action == "Ajouter":
                if user not in users and user and pwd:
                    users[user] = {"password": pwd}
                    with open(USERS_FILE, "w") as f:
                        json.dump(users, f)
                    st.success(f"Utilisateur {user} ajouté")
                else:
                    st.error("Utilisateur existe ou champs vides")
            elif action == "Supprimer":
                if user in users:
                    users.pop(user)
                    with open(USERS_FILE, "w") as f:
                        json.dump(users, f)
                    st.success(f"Utilisateur {user} supprimé")
                else:
                    st.error("Utilisateur non trouvé")
            elif action == "Modifier":
                if user in users and pwd:
                    users[user]["password"] = pwd
                    with open(USERS_FILE, "w") as f:
                        json.dump(users, f)
                    st.success(f"Mot de passe de {user} modifié")
                else:
                    st.error("Utilisateur non trouvé ou mot de passe vide")

# -------------------- LINÉARITÉ --------------------
def linearity_page():
    st.header("Courbe de linéarité")
    # Choix de l’unité
    conc_unit = st.selectbox("Unité de concentration", ["µg/mL", "mg/mL"])
    y_label = st.text_input("Nom de l’axe Y", "Réponse")
    method = st.radio("Entrée des données", ["Manuelle", "CSV"])

    if method == "Manuelle":
        conc_input = st.text_area("Concentrations (séparées par virgule)")
        response_input = st.text_area("Réponses (séparées par virgule)")
        if st.button("Calculer la linéarité"):
            try:
                c = [float(x.strip()) for x in conc_input.split(",")]
                r = [float(x.strip()) for x in response_input.split(",")]
                df = pd.DataFrame({"Concentration": c, "Réponse": r})
                X = np.array(c).reshape(-1,1)
                y = np.array(r)
                model = LinearRegression().fit(X, y)
                y_pred = model.predict(X)
                r2 = model.score(X, y)
                st.write(f"R² = {r2:.4f}")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=c, y=r, mode="markers", name="Données"))
                fig.add_trace(go.Scatter(x=c, y=y_pred, mode="lines", name="Régression"))
                fig.update_layout(xaxis_title=f"Concentration ({conc_unit})", yaxis_title=y_label)
                st.plotly_chart(fig)
                # Concentration inconnue
                unknown = st.number_input("Entrer une réponse inconnue pour calculer la concentration")
                if unknown:
                    conc_unknown = (unknown - model.intercept_)/model.coef_[0]
                    st.success(f"Concentration inconnue = {conc_unknown:.4f} {conc_unit}")
            except Exception as e:
                st.error(f"Erreur: {e}")

    else:
        uploaded_file = st.file_uploader("Télécharger un CSV", type=["csv"])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            try:
                X = np.array(df.iloc[:,0]).reshape(-1,1)
                y = np.array(df.iloc[:,1])
                model = LinearRegression().fit(X, y)
                y_pred = model.predict(X)
                r2 = model.score(X, y)
                st.write(f"R² = {r2:.4f}")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df.iloc[:,0], y=df.iloc[:,1], mode="markers", name="Données"))
                fig.add_trace(go.Scatter(x=df.iloc[:,0], y=y_pred, mode="lines", name="Régression"))
                fig.update_layout(xaxis_title=f"Concentration ({conc_unit})", yaxis_title=y_label)
                st.plotly_chart(fig)
                unknown = st.number_input("Entrer une réponse inconnue pour calculer la concentration")
                if unknown:
                    conc_unknown = (unknown - model.intercept_)/model.coef_[0]
                    st.success(f"Concentration inconnue = {conc_unknown:.4f} {conc_unit}")
            except Exception as e:
                st.error(f"Erreur: {e}")

# -------------------- S/N --------------------
def sn_page():
    st.header("Calcul S/N, LOD, LOQ")
    uploaded_file = st.file_uploader("Télécharger CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head())
            st.info("Calcul S/N à implémenter ici")
        except Exception as e:
            st.error(f"Erreur: {e}")

# -------------------- MENU --------------------
def menu_page():
    st.title(f"LabT - Connecté en tant que {st.session_state.username}")
    st.button("Déconnexion", on_click=logout)
    if st.session_state.username == "admin":
        admin_page()
    else:
        page = st.selectbox("Choisissez l’action", ["Linéarité", "S/N"])
        if page == "Linéarité":
            linearity_page()
        elif page == "S/N":
            sn_page()

# -------------------- MAIN --------------------
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "menu":
    menu_page()