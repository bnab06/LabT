import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import os
from fpdf import FPDF
from datetime import datetime
import base64

USERS_FILE = "users.json"

# -------------------------------
# Gestion des utilisateurs
# -------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "bb": {"password": "bb", "role": "user"},
            "user": {"password": "user", "role": "user"},
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------------
# Session & Login
# -------------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.current_page = None

def login_action(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"Login successful ✅ / You are logged in as {selected_user}")
    else:
        st.error("Username or password incorrect ❌")

def login():
    st.title("🔬 LabT - Login / Connexion")
    selected_user = st.selectbox("Select user / Choisir utilisateur :", list(load_users().keys()))
    password = st.text_input("Password / Mot de passe :", type="password")
    st.button("Login / Connexion", on_click=login_action, args=(selected_user, password))

# -------------------------------
# Admin page
# -------------------------------
def validate_user_action(action, username, password, role, lang="EN"):
    if not username or (action != "Supprimer / Delete" and not password):
        st.warning("All fields must be filled / Tous les champs doivent être remplis !")
        return
    users = load_users()
    if action in ["Ajouter / Add", "Add"]:
        if username in users:
            st.warning("User already exists / Utilisateur déjà existant.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("User added ✅ / Utilisateur ajouté ✅")
    elif action in ["Modifier / Edit", "Edit"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("User updated ✅ / Utilisateur modifié ✅")
    elif action in ["Supprimer / Delete", "Delete"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            del users[username]
            save_users(users)
            st.success("User deleted ✅ / Utilisateur supprimé ✅")

def manage_users():
    st.header("👥 User Management / Gestion des utilisateurs")
    st.write(f"You are logged in as / Vous êtes connecté en tant que **{st.session_state.username}**")
    action = st.selectbox("Action:", ["Ajouter / Add", "Modifier / Edit", "Supprimer / Delete"], key="action_admin")
    username = st.text_input("Username / Nom d’utilisateur:", key="username_admin")
    password = st.text_input("Password / Mot de passe:", key="password_admin")
    role = st.selectbox("Role / Rôle:", ["user", "admin"], key="role_admin")
    st.button("Submit / Valider", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# PDF utilities
# -------------------------------
def generate_pdf(title, content_text, company=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Company: {company}", ln=True)
    pdf.cell(0, 10, f"User: {st.session_state.username}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"App: LabT", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 8, content_text)
    pdf_file = f"{title}_{st.session_state.username}.pdf"
    pdf.output(pdf_file)
    return pdf_file

def offer_pdf_actions(pdf_file):
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download PDF</a>', unsafe_allow_html=True)

-------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Courbe de linéarité")
    st.write(f"Vous êtes connecté en tant que **{st.session_state.username}**")

    conc_input = st.text_input("Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Réponses (séparées par des virgules)", key="resp_input")
    unknown_type = st.selectbox("Type d'inconnu :", ["Concentration inconnue", "Signal inconnu"], key="unknown_type")
    unknown_value = st.number_input("Valeur inconnue :", value=0.0, step=0.1, key="unknown_value")

    # Initialisation de st.session_state.unit si elle n'existe pas encore
    if "unit" not in st.session_state:
        st.session_state.unit = "µg/mL"

    unit = st.selectbox("Unité :", ["µg/mL", "mg/L", "g/L"], index=0, key="unit")
    
    company_name = st.text_input("Nom de la compagnie pour le rapport PDF :", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("Les listes doivent avoir la même taille et ne pas être vides.")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"

            # Stocker la pente dans session_state pour le S/N
            st.session_state.slope = slope
            st.session_state.unit = unit  # ne fait rien si elle existe déjà

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept, mode="lines", name=f"Droite ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Courbe de linéarité")
            st.plotly_chart(fig)
            st.success(f"Équation : {eq}")

            if slope != 0:
                if unknown_type == "Concentration inconnue":
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 Concentration inconnue = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 Signal inconnu = {result:.4f}")

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)