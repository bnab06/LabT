import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import base64
import os

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
# Connexion et session
# -------------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

def login_action(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.success(f"Connexion réussie ✅ / You are logged in as {selected_user}")
    else:
        st.error("Nom d’utilisateur ou mot de passe incorrect ❌ / Wrong username or password")

def login():
    st.title("🔬 LabT - Connexion / Login")
    # Choisir utilisateur
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", list(load_users().keys()), key="login_user")
    password = st.text_input("Password / Mot de passe:", type="password", key="login_password")
    st.button("Login / Se connecter", on_click=login_action, args=(selected_user, password))
# -------------------------------
# Page admin : gestion des utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer / Delete" and not password):
        st.warning("Tous les champs doivent être remplis / All fields are required")
        return
    users = load_users()
    if action in ["Ajouter / Add"]:
        if username in users:
            st.warning("Utilisateur déjà existant / User already exists")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("Utilisateur ajouté ✅ / User added")
    elif action in ["Modifier / Modify"]:
        if username not in users:
            st.warning("Utilisateur introuvable / User not found")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("Utilisateur modifié ✅ / User modified")
    elif action in ["Supprimer / Delete"]:
        if username not in users:
            st.warning("Utilisateur introuvable / User not found")
        else:
            del users[username]
            save_users(users)
            st.success("Utilisateur supprimé ✅ / User deleted")

def manage_users():
    st.header("👥 Gestion des utilisateurs / User Management")
    st.write(f"You are logged in as / Vous êtes connecté en tant que **{st.session_state.username}**")
    
    action = st.selectbox("Action / Action:", ["Ajouter / Add", "Modifier / Modify", "Supprimer / Delete"], key="admin_action")
    username = st.text_input("Nom d’utilisateur / Username:", key="admin_username")
    password = st.text_input("Mot de passe / Password:", key="admin_password")
    role = st.selectbox("Rôle / Role:", ["user", "admin"], key="admin_role")
    st.button("Valider / Validate", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Déconnexion / Logout", on_click=logout)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Courbe de linéarité / Linearity curve")
    st.write(f"You are logged in as / Vous êtes connecté en tant que **{st.session_state.username}**")

    # Initialisation unit pour éviter l'erreur Streamlit
    if "unit" not in st.session_state:
        st.session_state.unit = "µg/mL"

    conc_input = st.text_input("Concentrations known / Concentrations connues (comma separated)", key="conc_input")
    resp_input = st.text_input("Responses / Réponses (comma separated)", key="resp_input")
    unknown_type = st.selectbox("Unknown type / Type inconnu:", ["Concentration unknown", "Signal unknown"], key="unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue:", value=0.0, step=0.1, key="unknown_value")
    st.session_state.unit = st.selectbox("Unit / Unité:", ["µg/mL", "mg/L", "g/L"], index=0, key="unit_selector")
    company_name = st.text_input("Company name for PDF report / Nom de la compagnie:", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("Lists must have same length and not be empty / Les listes doivent avoir la même taille et ne pas être vides")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"
            st.session_state.slope = slope

            # Graph
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope*conc + intercept, mode="lines", name=f"Line ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({st.session_state.unit})", yaxis_title="Signal", title="Linearity / Linéarité")
            st.plotly_chart(fig)
            st.success(f"Equation / Équation : {eq}")

            # Calculate unknown
            if slope != 0:
                if unknown_type == "Concentration unknown":
                    result = (unknown_value - intercept)/slope
                    st.info(f"🔹 Unknown concentration = {result:.4f} {st.session_state.unit}")
                else:
                    result = slope*unknown_value + intercept
                    st.info(f"🔹 Unknown signal = {result:.4f}")

            # Export PDF
            def export_pdf_linearity():
                if not company_name:
                    st.warning("Please enter company name before exporting / Veuillez saisir le nom de la compagnie")
                    return
                content_text = f"Linearity curve / Courbe de linéarité:\nEquation: {eq}\nUnknown type: {unknown_type}\nUnknown value: {unknown_value}\nResult: {result:.4f} {st.session_state.unit if unknown_type=='Concentration unknown' else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter PDF", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)
# -------------------------------
# S/N calculation
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()
    sn_ratio = signal_peak / noise

    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp

    lod = 3 * noise
    loq = 10 * noise

    return sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp

def sn_page():
    st.header("📊 Signal/Noise (S/N) calculation / Calcul du rapport signal/bruit")
    st.write(f"You are logged in as / Vous êtes connecté en tant que **{st.session_state.username}**")
    company_name = st.text_input("Company name for PDF report / Nom de la compagnie:", value="", key="company_name_sn")

    uploaded_file = st.file_uploader("Upload chromatogram (CSV) / Téléverser un chromatogramme (CSV)", type=["csv"], key="sn_upload")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]

            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV must contain columns: Time and Signal / CSV doit contenir les colonnes : Time et Signal")
                return

            # Plot
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Time / Temps", yaxis_title="Signal", title="Chromatogram / Chromatogramme")
            st.plotly_chart(fig)

            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)
            st.success(f"S/N ratio = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (baseline noise / bruit baseline = {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

            # S/N in concentration if linearity available
            if 'slope' in st.session_state and st.session_state.slope != 0:
                sn_conc = sn_ratio / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope
                st.info(f"S/N in concentration: {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N in concentration: {sn_usp_conc:.4f} {st.session_state.unit}")

            # Export PDF
            def export_pdf_sn():
                if not company_name:
                    st.warning("Please enter company name before exporting / Veuillez saisir le nom de la compagnie")
                    return
                content_text = f"""USP Signal to Noise Analysis / Analyse USP S/N:
Signal max: {signal_peak}
Noise: {noise:.4f}
S/N ratio: {sn_ratio:.2f}
USP S/N: {sn_usp:.2f}
LOD: {lod:.4f}, LOQ: {loq:.4f}
S/N in concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
USP S/N in concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter PDF", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"Error reading CSV / Erreur de lecture CSV : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# Main menu
# -------------------------------
def main_menu():
    role = st.session_state.role
    if role == "admin":
        manage_users()
    elif role == "user":
        choice = st.selectbox("Choose an option / Choisir une option:", ["Linearity / Courbe de linéarité", "S/N calculation / Calcul S/N"])
        if choice.startswith("Linearity"):
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Unknown role / Rôle inconnu")

# -------------------------------
# App launch
# -------------------------------
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login()
    else:
        main_menu()