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
# Initialisation session_state
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = None
if "unit" not in st.session_state:
    st.session_state.unit = "µg/mL"
if "slope" not in st.session_state:
    st.session_state.slope = 0.0

# -------------------------------
# Gestion utilisateurs
# -------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "user": {"password": "user", "role": "user"}
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------------
# Connexion / Déconnexion
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
        st.session_state.current_page = "manage_users" if st.session_state.role=="admin" else "linearity"
        st.success(f"Login successful ✅ / Vous êtes connecté en tant que {selected_user}")
        st.experimental_rerun()
    else:
        st.error("Incorrect username or password ❌ / Nom d’utilisateur ou mot de passe incorrect ❌")

def login():
    st.title("🔬 LabT - Login / Connexion")
    selected_user = st.selectbox("Select user / Choisir un utilisateur", list(load_users().keys()))
    password = st.text_input("Password / Mot de passe", type="password")
    st.button("Login / Se connecter", on_click=login_action, args=(selected_user, password))

# -------------------------------
# Page Admin : gestion des utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Delete / Supprimer" and not password):
        st.warning("All fields must be filled / Tous les champs doivent être remplis")
        return
    users = load_users()
    if action in ["Add / Ajouter"]:
        if username in users:
            st.warning("User already exists / Utilisateur déjà existant")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("User added ✅ / Utilisateur ajouté ✅")
    elif action in ["Modify / Modifier"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("User modified ✅ / Utilisateur modifié ✅")
    elif action in ["Delete / Supprimer"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable")
        else:
            del users[username]
            save_users(users)
            st.success("User deleted ✅ / Utilisateur supprimé ✅")

def manage_users():
    st.header("👥 User Management / Gestion des utilisateurs")
    st.write(f"You are logged in as / Vous êtes connecté en tant : **{st.session_state.username}**")
    action = st.selectbox("Action", ["Add / Ajouter", "Modify / Modifier", "Delete / Supprimer"])
    username = st.text_input("Username / Nom d’utilisateur")
    password = st.text_input("Password / Mot de passe")
    role = st.selectbox("Role / Rôle", ["user", "admin"])
    st.button("Validate / Valider", on_click=validate_user_action, args=(action, username, password, role))
    st.button("Logout / Déconnexion", on_click=logout)

# -------------------------------
# PDF
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
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download / Télécharger PDF</a>', unsafe_allow_html=True)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Linearity / Courbe de linéarité")
    st.write(f"You are logged in as / Vous êtes connecté en tant : **{st.session_state.username}**")

    conc_input = st.text_input("Known concentrations (comma separated) / Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Responses (comma separated) / Réponses (séparées par des virgules)", key="resp_input")
    unknown_type = st.selectbox("Unknown type / Type d'inconnu", ["Concentration unknown", "Signal unknown", "Concentration inconnue", "Signal inconnu"], key="unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue", value=0.0, step=0.1)
    unit = st.selectbox("Unit / Unité", ["µg/mL", "mg/L", "g/L"], index=0, key="unit")
    company_name = st.text_input("Company for PDF / Nom de la compagnie pour le rapport PDF", value="", key="company_name")
# -------------------------------
# S/N et USP S/N
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()
    sn_classic = signal_peak / noise

    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp

    lod = 3 * noise
    loq = 10 * noise

    return sn_classic, sn_usp, lod, loq, signal_peak, noise, noise_usp

def sn_page():
    st.header("📊 Signal-to-Noise Analysis / Calcul du rapport signal/bruit (S/N)")
    st.write(f"You are logged in as / Vous êtes connecté en tant : **{st.session_state.username}**")
    company_name = st.text_input("Company for PDF / Nom de la compagnie pour le rapport PDF", value="", key="company_name_sn")
    uploaded_file = st.file_uploader("Upload a chromatogram CSV / Téléverser un chromatogramme (CSV)", type=["csv"], key="sn_upload")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]

            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV must contain columns: Time and Signal / CSV doit contenir les colonnes : Time et Signal")
                return

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Time / Temps", yaxis_title="Signal", title="Chromatogram / Chromatogramme")
            st.plotly_chart(fig)

            sn_classic, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)

            st.success(f"S/N (classic) = {sn_classic:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (baseline noise / bruit baseline = {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

            if st.session_state.slope != 0:
                sn_conc = sn_classic / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope
                st.info(f"S/N in concentration: {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N in concentration: {sn_usp_conc:.4f} {st.session_state.unit}")

            def export_pdf_sn():
                content_text = f"""Signal to Noise Analysis:
Signal max: {signal_peak}
Noise: {noise:.4f}
S/N ratio (classic): {sn_classic:.2f}
USP S/N: {sn_usp:.2f}
LOD: {lod:.4f}, LOQ: {loq:.4f}
S/N in concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit}
USP S/N in concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit}
"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter PDF", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"Error reading CSV / Erreur de lecture CSV: {e}")

    st.button("Logout / Déconnexion", on_click=logout)

# -------------------------------
# Menu principal
# -------------------------------
def main_menu():
    role = st.session_state.role
    if role == "admin":
        manage_users()
    elif role == "user":
        choice = st.selectbox("Select an option / Choisir une option", ["Linearity / Courbe de linéarité", "Signal-to-Noise / Calcul S/N"])
        if "Linearity" in choice or "Linéarité" in choice:
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Unknown role / Rôle inconnu")

# -------------------------------
# Lancement
# -------------------------------
if __name__ == "__main__":
    if not st.session_state.logged_in:
        login()
    else:
        main_menu()