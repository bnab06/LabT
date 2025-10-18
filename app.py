import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from datetime import datetime
import json
import os

# ---------------------------
# Utilitaires
# ---------------------------

USERS_FILE = "users.json"
LOGO = "logo.png"  # optionnel, mettre un logo dans le dossier

# Initialisation du fichier users.json si inexistant
if not os.path.exists(USERS_FILE):
    default_users = {
        "admin": {"password": "bb", "role": "admin"},
        "bb": {"password": "bb", "role": "user"},
        "user": {"password": "user", "role": "user"}
    }
    with open(USERS_FILE, "w") as f:
        json.dump(default_users, f, indent=4)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def login_page():
    st.title("LabT")
    users = load_users()
    st.sidebar.subheader("Se connecter")
    username = st.sidebar.selectbox("Utilisateur", list(users.keys()))
    password = st.sidebar.text_input("Mot de passe", type="password")
    if st.sidebar.button("Login"):
        if username in users and password == users[username]["password"]:
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]
            st.session_state["page"] = "menu"
        else:
            st.sidebar.error("Identifiants incorrects")

# ---------------------------
# Menu principal
# ---------------------------
def menu_page():
    st.subheader(f"Connecté en tant que: {st.session_state['username']}")
    st.write("Choisir une fonction:")
    choice = st.selectbox("Menu", ["Linéarité", "S/N USP", "Déconnexion"])
    if choice == "Linéarité":
        st.session_state["page"] = "linearity"
    elif choice == "S/N USP":
        st.session_state["page"] = "sn"
    elif choice == "Déconnexion":
        st.session_state.clear()
        st.session_state["page"] = "login"

# ---------------------------
# Gestion utilisateurs (Admin)
# ---------------------------
def admin_page():
    st.subheader("Gestion des utilisateurs")
    users = load_users()
    st.write("Liste des utilisateurs existants:")
    selected_user = st.selectbox("Sélectionner un utilisateur", list(users.keys()))
    new_pass = st.text_input("Nouveau mot de passe")
    new_role = st.selectbox("Rôle", ["user", "admin"], index=0 if users[selected_user]["role"]=="user" else 1)
    if st.button("Modifier"):
        users[selected_user]["password"] = new_pass or users[selected_user]["password"]
        users[selected_user]["role"] = new_role
        save_users(users)
        st.success("Utilisateur modifié")
    if st.button("Supprimer"):
        if selected_user != "admin":
            users.pop(selected_user)
            save_users(users)
            st.success("Utilisateur supprimé")
        else:
            st.error("Impossible de supprimer l'admin")
    if st.button("Ajouter utilisateur"):
        new_user = st.text_input("Nom du nouvel utilisateur")
        new_pass2 = st.text_input("Mot de passe du nouvel utilisateur")
        if new_user and new_pass2 and new_user not in users:
            users[new_user] = {"password": new_pass2, "role": "user"}
            save_users(users)
            st.success("Utilisateur ajouté")

# ---------------------------
# Lecture CSV "smart"
# ---------------------------
def read_csv_smart(file):
    try:
        df = pd.read_csv(file, sep=None, engine='python')
        if df.shape[1] == 2:
            df.columns = ["Time", "Signal"]
        return df
    except Exception as e:
        st.error(f"Erreur lecture CSV: {e}")
        return None

# ---------------------------
# Linéarité
# ---------------------------
def linearity_page():
    st.subheader("Courbe de linéarité")
    # Entrée manuelle
    conc_str = st.text_input("Concentrations (séparées par des virgules)", value="10,20,30")
    resp_str = st.text_input("Réponse (aires ou absorbance)", value="100,200,300")
    unit_conc = st.selectbox("Unité de concentration", ["µg/mL", "mg/mL"], index=0)
    unit_resp = st.selectbox("Type de réponse", ["Aire", "Absorbance"])
    if st.button("Tracer la courbe"):
        try:
            c = np.array([float(x) for x in conc_str.split(",")])
            r = np.array([float(x) for x in resp_str.split(",")])
            df = pd.DataFrame({"Concentration": c, "Réponse": r})
            X = df[["Concentration"]]
            y = df["Réponse"]
            model = LinearRegression().fit(X, y)
            y_pred = model.predict(X)
            r2 = model.score(X, y)
            st.write(f"R² = {r2:.4f}")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Concentration"], y=df["Réponse"], mode='markers', name='Données'))
            fig.add_trace(go.Scatter(x=df["Concentration"], y=y_pred, mode='lines', name='Fit'))
            fig.update_layout(xaxis_title=f"Concentration ({unit_conc})", yaxis_title=f"Réponse ({unit_resp})")
            st.plotly_chart(fig)
            # Calcul concentration inconnue
            unknown_resp = st.number_input("Réponse inconnue")
            if unknown_resp:
                conc_unknown = (unknown_resp - model.intercept_) / model.coef_[0]
                st.success(f"Concentration inconnue: {conc_unknown:.4f} {unit_conc}")
        except Exception as e:
            st.error(f"Erreur calcul linéarité: {e}")

# ---------------------------
# S/N USP
# ---------------------------
def sn_page():
    st.subheader("Calcul S/N USP")
    uploaded_file = st.file_uploader("Upload CSV chromatogramme", type=["csv"])
    if uploaded_file:
        df = read_csv_smart(uploaded_file)
        if df is not None:
            start = st.number_input("Start Time", value=float(df['Time'].min()))
            end = st.number_input("End Time", value=float(df['Time'].max()))
            y = df.loc[(df["Time"]>=start) & (df["Time"]<=end), "Signal"]
            sn = np.max(y)/np.std(y)
            lod = 3 * np.std(y)
            loq = 10 * np.std(y)
            st.write(f"S/N: {sn:.4f}")
            st.write(f"LOD: {lod:.4f}")
            st.write(f"LOQ: {loq:.4f}")

# ---------------------------
# Main
# ---------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "login"

if st.session_state["page"] == "login":
    login_page()
elif st.session_state.get("role") == "admin" and st.session_state["page"]=="menu":
    admin_page()
elif st.session_state.get("page")=="menu":
    menu_page()
elif st.session_state["page"]=="linearity":
    linearity_page()
    if st.button("Retour au menu principal"):
        st.session_state["page"] = "menu"
elif st.session_state["page"]=="sn":
    sn_page()
    if st.button("Retour au menu principal"):
        st.session_state["page"] = "menu"