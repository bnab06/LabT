# -------------------------------
# PARTIE 1 : Imports et Gestion Utilisateurs / Login
# -------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import os
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
    st.experimental_rerun()

def login_action(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"Connexion réussie ✅ / You are logged in as {selected_user}")
        st.experimental_rerun()
    else:
        st.error("Nom d’utilisateur ou mot de passe incorrect ❌ / Invalid username or password")

def login():
    st.title("🔬 LabT - Login / Connexion")
    
    # Menu de langue (par défaut anglais)
    if "lang" not in st.session_state:
        st.session_state.lang = "English"
    
    lang = st.selectbox("Select language / Choisir langue:", ["English", "Français"], key="lang_selectbox")
    st.session_state.lang = lang

    users_list = list(load_users().keys())
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", users_list, key="login_user_selectbox")
    password = st.text_input("Password / Mot de passe :", type="password", key="login_password_input")
    st.button("Login / Connexion", on_click=login_action, args=(selected_user, password), key="login_button")
# -------------------------------
# PARTIE 2 : Gestion Utilisateurs & Linéarité
# -------------------------------

# -------------------------------
# Page admin : gestion des utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer / Delete" and not password):
        st.warning("Tous les champs doivent être remplis ! / All fields must be filled!")
        return
    users = load_users()
    if action in ["Ajouter / Add", "Add"]:
        if username in users:
            st.warning("Utilisateur déjà existant / User already exists.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("Utilisateur ajouté ✅ / User added ✅")
    elif action in ["Modifier / Modify", "Modify"]:
        if username not in users:
            st.warning("Utilisateur introuvable / User not found.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("Utilisateur modifié ✅ / User modified ✅")
    elif action in ["Supprimer / Delete", "Delete"]:
        if username not in users:
            st.warning("Utilisateur introuvable / User not found.")
        else:
            del users[username]
            save_users(users)
            st.success("Utilisateur supprimé ✅ / User deleted ✅")

def manage_users():
    st.header("👥 Gestion des utilisateurs / User Management")
    st.write(f"Vous êtes connecté en tant que / You are logged in as **{st.session_state.username}**")

    action = st.selectbox("Action / Action:", ["Ajouter / Add", "Modifier / Modify", "Supprimer / Delete"], key="admin_action_selectbox")
    username = st.text_input("Nom d’utilisateur / Username:", key="admin_username_input")
    password = st.text_input("Mot de passe / Password:", key="admin_password_input")
    role = st.selectbox("Rôle / Role:", ["user", "admin"], key="admin_role_selectbox")
    st.button("Valider / Submit", on_click=validate_user_action, args=(action, username, password, role), key="admin_validate_button")
    st.button("⬅️ Déconnexion / Logout", on_click=logout, key="admin_logout_button")


# -------------------------------
# PDF texte uniquement
# -------------------------------
def generate_pdf(title, content_text, company=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report / Rapport LabT", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Company / Société: {company}", ln=True)
    pdf.cell(0, 10, f"User / Utilisateur: {st.session_state.username}", ln=True)
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
# Linéarité / Linearity
# -------------------------------
def linearity_page():
    st.header("📈 Courbe de linéarité / Linearity Curve")
    st.write(f"Vous êtes connecté en tant que / You are logged in as **{st.session_state.username}**")

    # Inputs
    conc_input = st.text_input("Concentrations connues (séparées par des virgules) / Known concentrations (comma-separated)", key="linearity_conc_input")
    resp_input = st.text_input("Réponses (séparées par des virgules) / Responses (comma-separated)", key="linearity_resp_input")
    unknown_type = st.selectbox("Type d'inconnu / Unknown type:", ["Concentration inconnue / Unknown concentration", "Signal inconnu / Unknown signal"], key="linearity_unknown_type")
    unknown_value = st.number_input("Valeur inconnue / Unknown value:", value=0.0, step=0.1, key="linearity_unknown_value")
    
    if "unit" not in st.session_state:
        st.session_state.unit = "µg/mL"
    unit = st.selectbox("Unité / Unit:", ["µg/mL", "mg/L", "g/L"], index=0, key="linearity_unit_selectbox")
    st.session_state.unit = unit

    company_name = st.text_input("Nom de la compagnie pour le rapport PDF / Company name for PDF report:", value="", key="linearity_company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("Les listes doivent avoir la même taille et ne pas être vides / Lists must have the same size and cannot be empty.")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"

            st.session_state.slope = slope
            st.session_state.unit = unit

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept, mode="lines", name=f"Droite / Line ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Courbe de linéarité / Linearity curve")
            st.plotly_chart(fig)
            st.success(f"Équation / Equation : {eq}")

            # Calcul de l'inconnu
            if slope != 0:
                if "Unknown concentration" in unknown_type:
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 Concentration inconnue / Unknown concentration = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 Signal inconnu / Unknown signal = {result:.4f}")

            # Export PDF
            def export_pdf_linearity():
                if not company_name:
                    st.warning("Veuillez saisir le nom de la compagnie / Please enter company name")
                    return
                content_text = f"Courbe de linéarité / Linearity curve:\nÉquation / Equation: {eq}\nType inconnu / Unknown type: {unknown_type}\nValeur inconnue / Unknown value: {unknown_value}\nRésultat / Result: {result:.4f} {unit if 'Concentration' in unknown_type else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Exporter le rapport PDF / Export PDF", on_click=export_pdf_linearity, key="linearity_export_pdf_button")

        except Exception as e:
            st.error(f"Erreur dans les calculs / Error in calculation: {e}")

    st.button("⬅️ Déconnexion / Logout", on_click=logout, key="linearity_logout_button")
# -------------------------------
# PARTIE 3 : S/N et Menu Principal
# -------------------------------

# -------------------------------
# Calcul S/N
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()
    sn_ratio = signal_peak / noise

    # USP S/N : bruit baseline (10% initial)
    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp

    lod = 3 * noise
    loq = 10 * noise

    return sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp


def sn_page():
    st.header("📊 Calcul du rapport signal/bruit (S/N) / Signal to Noise Calculation")
    st.write(f"Vous êtes connecté en tant que / You are logged in as **{st.session_state.username}**")

    company_name = st.text_input("Nom de la compagnie pour le rapport PDF / Company name for PDF report:", value="", key="sn_company_name")
    uploaded_file = st.file_uploader("Téléverser un chromatogramme CSV / Upload CSV chromatogram:", type=["csv"], key="sn_file_uploader")

    linearity_for_sn = st.checkbox("Utiliser une courbe de linéarité pour calculer LOD/LOQ en concentration / Use linearity curve to calculate LOD/LOQ in concentration", key="sn_linearity_checkbox")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]

            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV doit contenir les colonnes : Time et Signal / CSV must contain 'Time' and 'Signal' columns")
                return

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Temps / Time", yaxis_title="Signal", title="Chromatogramme / Chromatogram")
            st.plotly_chart(fig)

            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)
            st.success(f"S/N classique / Classic S/N = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (bruit baseline / baseline noise = {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

            # Conversion en concentration si slope disponible
            if 'slope' in st.session_state and st.session_state.slope != 0:
                sn_conc = sn_ratio / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope

                if linearity_for_sn:
                    lod_conc = (3 * noise) / st.session_state.slope
                    loq_conc = (10 * noise) / st.session_state.slope
                    st.info(f"LOD en concentration = {lod_conc:.4f} {st.session_state.unit}")
                    st.info(f"LOQ en concentration = {loq_conc:.4f} {st.session_state.unit}")

                st.info(f"S/N en concentration / S/N in concentration: {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N en concentration / USP S/N in concentration: {sn_usp_conc:.4f} {st.session_state.unit}")

            # Export PDF
            def export_pdf_sn():
                if not company_name:
                    st.warning("Veuillez saisir le nom de la compagnie / Please enter company name")
                    return
                content_text = f"""USP Signal to Noise Analysis / Analyse S/N USP:
Signal max / Max signal: {signal_peak}
Noise / Bruit: {noise:.4f}
S/N ratio classique / Classic S/N: {sn_ratio:.2f}
USP S/N: {sn_usp:.2f}
LOD: {lod:.4f}, LOQ: {loq:.4f}
S/N en concentration / S/N in concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
USP S/N en concentration / USP S/N in concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Exporter le rapport PDF / Export PDF", on_click=export_pdf_sn, key="sn_export_pdf_button")

        except Exception as e:
            st.error(f"Erreur de lecture CSV / Error reading CSV: {e}")

    st.button("⬅️ Déconnexion / Logout", on_click=logout, key="sn_logout_button")


# -------------------------------
# Menu principal
# -------------------------------
def main_menu():
    role = st.session_state.role
    if role == "admin":
        manage_users()
    elif role == "user":
        choice = st.selectbox("Choisir une option / Select an option:", ["Courbe de linéarité / Linearity curve", "Calcul S/N / Signal to Noise"])
        if choice == "Courbe de linéarité / Linearity curve":
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Rôle inconnu / Unknown role")


# -------------------------------
# Lancement de l'app
# -------------------------------
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login()
    else:
        main_menu()