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
# Connexion et session
# -------------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.current_page = None

def login_action(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"Login successful ✅ / Vous êtes connecté en tant que {selected_user}")
        st.experimental_rerun()
    else:
        st.error("Incorrect username or password ❌ / Nom d’utilisateur ou mot de passe incorrect ❌")

def login():
    st.title("🔬 LabT - Login / Connexion")
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", list(load_users().keys()), key="login_user")
    password = st.text_input("Password / Mot de passe:", type="password", key="login_pass")
    st.button("Login / Se connecter", on_click=login_action, args=(selected_user, password))

# -------------------------------
# Page admin : gestion utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Delete / Supprimer" and not password):
        st.warning("All fields must be filled! / Tous les champs doivent être remplis !")
        return
    users = load_users()
    if action in ["Add / Ajouter", "Modify / Modifier"]:
        if action == "Add / Ajouter" and username in users:
            st.warning("User already exists / Utilisateur déjà existant.")
            return
        if action == "Modify / Modifier" and username not in users:
            st.warning("User not found / Utilisateur introuvable.")
            return
        users[username] = {"password": password, "role": role}
        save_users(users)
        st.success("Action completed ✅ / Action terminée ✅")
    elif action == "Delete / Supprimer":
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
            return
        del users[username]
        save_users(users)
        st.success("User deleted ✅ / Utilisateur supprimé ✅")

def manage_users():
    st.header("👥 Admin Panel / Gestion des utilisateurs")
    st.write(f"Logged in as / Connecté en tant que **{st.session_state.username}**")
    
    action = st.selectbox("Action:", ["Add / Ajouter", "Modify / Modifier", "Delete / Supprimer"], key="admin_action")
    username = st.text_input("Username / Nom d’utilisateur:", key="admin_username")
    password = st.text_input("Password / Mot de passe:", key="admin_password")
    role = st.selectbox("Role / Rôle:", ["user", "admin"], key="admin_role")
    st.button("Submit / Valider", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Logout / Déconnexion", on_click=logout)
# -------------------------------
# PDF generator
# -------------------------------
def generate_pdf(title, content_text, company=""):
    if not company:
        st.warning("Please enter company name before generating the report / Veuillez saisir le nom de la compagnie")
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report / Rapport LabT", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Company / Compagnie: {company}", ln=True)
    pdf.cell(0, 10, f"User / Utilisateur: {st.session_state.username}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, "App: LabT", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 8, content_text)
    pdf_file = f"{title}_{st.session_state.username}.pdf"
    pdf.output(pdf_file)
    return pdf_file

def offer_pdf_actions(pdf_file):
    if not pdf_file:
        return
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download / Télécharger PDF</a>', unsafe_allow_html=True)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Linearity Curve / Courbe de linéarité")
    st.write(f"Logged in as / Connecté en tant que **{st.session_state.username}**")

    conc_input = st.text_input("Known concentrations (comma-separated) / Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Responses (comma-separated) / Réponses (séparées par des virgules)", key="resp_input")
    unknown_type = st.selectbox("Unknown type / Type d'inconnu:", ["Concentration", "Signal"], key="unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue:", value=0.0, step=0.1, key="unknown_value")
    unit = st.selectbox("Unit / Unité:", ["µg/mL", "mg/L", "g/L"], index=0, key="unit")
    company_name = st.text_input("Company name for report / Nom de la compagnie pour le rapport PDF:", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("Lists must be same length and not empty / Les listes doivent avoir la même taille et ne pas être vides.")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R²={r2:.4f})"

            st.session_state.slope = slope
            st.session_state.unit = unit

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope*conc+intercept, mode="lines", name=f"Fit ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Linearity Curve / Courbe de linéarité")
            st.plotly_chart(fig)
            st.success(f"Equation / Équation : {eq}")

            # Calculate unknown
            if slope != 0:
                if unknown_type == "Concentration":
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 Unknown concentration / Concentration inconnue = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 Unknown signal / Signal inconnu = {result:.4f}")

            def export_pdf_linearity():
                content_text = f"Linearity Curve / Courbe de linéarité:\nEquation: {eq}\nUnknown type: {unknown_type}\nUnknown value: {unknown_value}\nResult: {result:.4f} {unit if unknown_type=='Concentration' else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter le rapport PDF", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)
# -------------------------------
# Signal-to-noise calculation
# -------------------------------
def calculate_sn(signal, noise):
    if noise == 0:
        return np.nan
    return signal / noise

def sn_page():
    st.header("🔊 Signal-to-Noise / Rapport S/N")
    st.write(f"Logged in as / Connecté en tant que **{st.session_state.username}**")

    # Inputs
    signal_values = st.text_input("Signal values (comma-separated) / Valeurs du signal (séparées par des virgules)", key="sn_signal")
    noise_values = st.text_input("Noise values (comma-separated) / Valeurs du bruit (séparées par des virgules)", key="sn_noise")
    use_linearity_curve = st.checkbox("Use linearity slope for LOD/LOQ / Utiliser la pente de la linéarité pour LOD/LOQ", key="use_linearity")
    company_name = st.text_input("Company name for report / Nom de la compagnie pour le rapport PDF:", value="", key="sn_company_name")

    if signal_values and noise_values:
        try:
            signals = np.array([float(x.strip()) for x in signal_values.split(",")])
            noises = np.array([float(x.strip()) for x in noise_values.split(",")])
            if len(signals) != len(noises):
                st.warning("Signal and noise lists must be the same length / Les listes signal et bruit doivent avoir la même taille.")
                return

            sn_values = [calculate_sn(s, n) for s, n in zip(signals, noises)]
            avg_sn = np.nanmean(sn_values)

            st.write(f"Average S/N / S/N moyen: {avg_sn:.4f}")

            # LOQ/LOD
            if use_linearity_curve and hasattr(st.session_state, "slope") and st.session_state.slope != 0:
                slope = st.session_state.slope
                lod_conc = 3 * np.nanstd(noises) / slope
                loq_conc = 10 * np.nanstd(noises) / slope
                st.info(f"LOD (Concentration) = {lod_conc:.4f} {st.session_state.unit}")
                st.info(f"LOQ (Concentration) = {loq_conc:.4f} {st.session_state.unit}")

            def export_pdf_sn():
                content_text = f"S/N Values:\nSignals: {signals}\nNoises: {noises}\nS/N mean: {avg_sn:.4f}"
                if use_linearity_curve and hasattr(st.session_state, "slope"):
                    content_text += f"\nLOD: {lod_conc:.4f} {st.session_state.unit}\nLOQ: {loq_conc:.4f} {st.session_state.unit}"
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter le rapport PDF", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"Error / Erreur : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# Menu principal / Main app
# -------------------------------
def main_app():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
        pages = {
            "Linearity / Linéarité": linearity_page,
            "S/N / S/N": sn_page,
        }
        if st.session_state.role == "admin":
            pages["Admin Panel / Gestion utilisateurs"] = manage_users

        st.sidebar.title("Navigation / Menu")
        page_choice = st.sidebar.selectbox("Go to / Aller à:", list(pages.keys()))
        pages[page_choice]()

# -------------------------------
# Run the app
# -------------------------------
if __name__ == "__main__":
    main_app()