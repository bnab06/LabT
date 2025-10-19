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
        st.success(f"Connexion réussie ✅ / You are logged in as {selected_user}")
    else:
        st.error("Nom d’utilisateur ou mot de passe incorrect ❌ / Incorrect username or password")

def login():
    st.title("🔬 LabT - Login / Connexion")
    selected_user = st.selectbox("Choose a user / Choisir un utilisateur :", list(load_users().keys()))
    password = st.text_input("Password / Mot de passe :", type="password")
    st.button("Login / Se connecter", on_click=login_action, args=(selected_user, password))

# -------------------------------
# Page admin : gestion des utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer" and not password):
        st.warning("All fields must be filled! / Tous les champs doivent être remplis !")
        return
    users = load_users()
    if action == "Ajouter":
        if username in users:
            st.warning("User already exists / Utilisateur déjà existant.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("User added ✅ / Utilisateur ajouté ✅")
    elif action == "Modifier":
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("User modified ✅ / Utilisateur modifié ✅")
    elif action == "Supprimer":
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            del users[username]
            save_users(users)
            st.success("User deleted ✅ / Utilisateur supprimé ✅")

def manage_users():
    st.header("👥 User Management / Gestion des utilisateurs")
    st.write(f"You are logged in as / Vous êtes connecté en tant que **{st.session_state.username}**")

    action = st.selectbox("Action / Action :", ["Ajouter", "Modifier", "Supprimer"], key="action_admin")
    username = st.text_input("Username / Nom d’utilisateur :", key="username_admin")
    password = st.text_input("Password / Mot de passe :", key="password_admin")
    role = st.selectbox("Role / Rôle :", ["user", "admin"], key="role_admin")
    st.button("Validate / Valider", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# PDF texte uniquement
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
    pdf.cell(0, 10, f"Log: LabT", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 8, content_text)

    pdf_file = f"{title}_{st.session_state.username}.pdf"
    pdf.output(pdf_file)
    return pdf_file

def offer_pdf_actions(pdf_file):
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download PDF / Télécharger le PDF</a>', unsafe_allow_html=True)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Linearity / Courbe de linéarité")
    st.write(f"You are logged in as / Vous êtes connecté en tant que **{st.session_state.username}**")

    conc_input = st.text_input("Known concentrations (comma-separated) / Concentrations connues :", key="conc_input")
    resp_input = st.text_input("Responses (comma-separated) / Réponses :", key="resp_input")
    unknown_type = st.selectbox("Unknown type / Type d'inconnu :", ["Concentration", "Signal"], key="unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue :", value=0.0, step=0.1, key="unknown_value")
    unit = st.selectbox("Unit / Unité :", ["µg/mL", "mg/L", "g/L"], index=0, key="unit")
    company_name = st.text_input("Company name for PDF / Nom de la compagnie :", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("Lists must be the same size and not empty / Les listes doivent avoir la même taille et ne pas être vides.")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"

            st.session_state.slope = slope
            st.session_state.unit = unit

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept, mode="lines", name=f"Line ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Linearity Curve")
            st.plotly_chart(fig)
            st.success(f"Equation / Équation : {eq}")

            if slope != 0:
                if unknown_type == "Concentration":
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 Unknown concentration = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 Unknown signal = {result:.4f}")

            def export_pdf_linearity():
                content_text = f"Linearity Curve:\nEquation: {eq}\nUnknown type: {unknown_type}\nUnknown value: {unknown_value}\nResult: {result:.4f} {unit if unknown_type=='Concentration' else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter PDF", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)
# -------------------------------
# Calcul S/N
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()

    # USP S/N : bruit de baseline (10% du début)
    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp

    lod = 3 * noise
    loq = 10 * noise

    return sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp

def sn_page():
    st.header("📊 Signal-to-Noise / Rapport signal/bruit (S/N)")
    st.write(f"You are logged in as / Vous êtes connecté en tant que **{st.session_state.username}**")
    company_name = st.text_input("Company name for PDF / Nom de la compagnie :", value="", key="company_name_sn")

    uploaded_file = st.file_uploader("Upload a chromatogram (CSV) / Téléverser un chromatogramme (CSV)", type=["csv"], key="sn_upload")

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

            sn_ratio = df["signal"].max() / df["signal"].std()
            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)

            st.success(f"S/N = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (baseline noise = bruit baseline {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

            if 'slope' in st.session_state and st.session_state.slope != 0:
                sn_conc = sn_ratio / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope
                st.info(f"S/N in concentration = {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N in concentration = {sn_usp_conc:.4f} {st.session_state.unit}")

            def export_pdf_sn():
                content_text = f"""USP Signal-to-Noise Analysis:
Signal peak: {signal_peak}
Noise: {noise:.4f}
S/N ratio: {sn_ratio:.2f}
USP S/N: {sn_usp:.2f}
LOD: {lod:.4f}, LOQ: {loq:.4f}
S/N in concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
USP S/N in concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter PDF", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"CSV read error / Erreur de lecture CSV : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# Menu principal
# -------------------------------
def main_menu():
    role = st.session_state.role
    if role == "admin":
        manage_users()
    elif role == "user":
        choice = st.selectbox("Choose an option / Choisir une option :", ["Linearity / Courbe de linéarité", "Signal-to-Noise / Calcul S/N"])
        if choice.startswith("Linearity"):
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Unknown role / Rôle inconnu")
# -------------------------------
# Lancement de l'application
# -------------------------------
if __name__ == "__main__":
    # Initialisation session_state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "role" not in st.session_state:
        st.session_state.role = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = None
    if "slope" not in st.session_state:
        st.session_state.slope = None
    if "unit" not in st.session_state:
        st.session_state.unit = "µg/mL"

    # Choix langue (anglais par défaut)
    if "lang" not in st.session_state:
        st.session_state.lang = "EN"
    lang = st.session_state.lang
    st.selectbox("Language / Langue", ["EN", "FR"], index=0 if lang=="EN" else 1, key="lang")

    # Navigation automatique après login
    if not st.session_state.logged_in:
        login()
    else:
        # Redirige vers la page courante si définie
        if st.session_state.current_page == "manage_users":
            manage_users()
        elif st.session_state.current_page == "linearity":
            linearity_page()
        elif st.session_state.current_page == "sn":
            sn_page()
        else:
            main_menu()