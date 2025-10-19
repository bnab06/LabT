import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import os
from fpdf import FPDF
from datetime import datetime
import base64

# -------------------------------
# Configuration et fichiers
# -------------------------------
USERS_FILE = "users.json"

if "language" not in st.session_state:
    st.session_state.language = "EN"  # default language

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
# Connexion / Déconnexion
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
        st.success(f"{'Connexion réussie' if st.session_state.language=='FR' else 'Login successful'} ✅ / You are logged in as {selected_user}")
        st.experimental_rerun()
    else:
        st.error(f"{'Nom d’utilisateur ou mot de passe incorrect' if st.session_state.language=='FR' else 'Username or password incorrect'} ❌")

def login():
    st.title("🔬 LabT - Connexion / Login")
    selected_user = st.selectbox(
        "Choisir un utilisateur / Select user:",
        list(load_users().keys())
    )
    password = st.text_input(
        "Mot de passe / Password:", type="password"
    )
    st.button("Se connecter / Login", on_click=login_action, args=(selected_user, password))

# -------------------------------
# PDF Génération
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
    st.markdown(
        f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download PDF / Télécharger PDF</a>',
        unsafe_allow_html=True
    )

# -------------------------------
# Page Admin / Gestion utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer" and not password):
        st.warning(f"{'Tous les champs doivent être remplis !' if st.session_state.language=='FR' else 'All fields must be filled!'}")
        return
    users = load_users()
    if action == "Ajouter":
        if username in users:
            st.warning(f"{'Utilisateur déjà existant.' if st.session_state.language=='FR' else 'User already exists.'}")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success(f"{'Utilisateur ajouté ✅' if st.session_state.language=='FR' else 'User added ✅'}")
    elif action == "Modifier":
        if username not in users:
            st.warning(f"{'Utilisateur introuvable.' if st.session_state.language=='FR' else 'User not found.'}")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success(f"{'Utilisateur modifié ✅' if st.session_state.language=='FR' else 'User modified ✅'}")
    elif action == "Supprimer":
        if username not in users:
            st.warning(f"{'Utilisateur introuvable.' if st.session_state.language=='FR' else 'User not found.'}")
        else:
            del users[username]
            save_users(users)
            st.success(f"{'Utilisateur supprimé ✅' if st.session_state.language=='FR' else 'User deleted ✅'}")

def manage_users():
    st.header(f"{'👥 Gestion des utilisateurs' if st.session_state.language=='FR' else '👥 User Management'}")
    st.write(f"{'Vous êtes connecté en tant que' if st.session_state.language=='FR' else 'You are logged in as'} **{st.session_state.username}**")

    actions = [("Ajouter", "Add"), ("Modifier", "Modify"), ("Supprimer", "Delete")]
    action = st.selectbox(
        f"{'Action' if st.session_state.language=='FR' else 'Action'}",
        [f"{a[0]} / {a[1]}" for a in actions],
        key="action_admin"
    )
    action_fr = action.split(" / ")[0]  # keep FR action for logic
    username = st.text_input(f"{'Nom d’utilisateur' if st.session_state.language=='FR' else 'Username'}", key="username_admin")
    password = st.text_input(f"{'Mot de passe' if st.session_state.language=='FR' else 'Password'}", key="password_admin")
    role = st.selectbox(f"{'Rôle' if st.session_state.language=='FR' else 'Role'}", ["user", "admin"], key="role_admin")
    st.button(f"{'Valider' if st.session_state.language=='FR' else 'Validate'}", on_click=validate_user_action, args=(action_fr, username, password, role))
    st.button(f"⬅️ {'Déconnexion' if st.session_state.language=='FR' else 'Logout'}", on_click=logout)
# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header(f"📈 {'Courbe de linéarité' if st.session_state.language=='FR' else 'Linearity Curve'}")
    st.write(f"{'Vous êtes connecté en tant que' if st.session_state.language=='FR' else 'You are logged in as'} **{st.session_state.username}**")

    if "unit" not in st.session_state:
        st.session_state.unit = "µg/mL"  # default

    conc_input = st.text_input(f"{'Concentrations connues (séparées par des virgules)' if st.session_state.language=='FR' else 'Known concentrations (comma separated)'}", key="conc_input")
    resp_input = st.text_input(f"{'Réponses (séparées par des virgules)' if st.session_state.language=='FR' else 'Responses (comma separated)'}", key="resp_input")
    unknown_type = st.selectbox(
        f"{'Type d\'inconnu' if st.session_state.language=='FR' else 'Unknown type'}",
        [f"{'Concentration inconnue' if st.session_state.language=='FR' else 'Unknown concentration'}",
         f"{'Signal inconnu' if st.session_state.language=='FR' else 'Unknown signal'}"],
        key="unknown_type"
    )
    unknown_value = st.number_input(
        f"{'Valeur inconnue' if st.session_state.language=='FR' else 'Unknown value'}",
        value=0.0, step=0.1, key="unknown_value"
    )
    unit = st.selectbox(
        f"{'Unité' if st.session_state.language=='FR' else 'Unit'}",
        ["µg/mL", "mg/L", "g/L"], index=0, key="unit"
    )
    company_name = st.text_input(f"{'Nom de la compagnie pour le rapport PDF' if st.session_state.language=='FR' else 'Company name for PDF report'}", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning(f"{'Les listes doivent avoir la même taille et ne pas être vides.' if st.session_state.language=='FR' else 'Lists must have same length and cannot be empty.'}")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"

            st.session_state.slope = slope
            st.session_state.unit = unit

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept, mode="lines", name=f"Droite ({eq})"))
            fig.update_layout(
                xaxis_title=f"{'Concentration' if st.session_state.language=='FR' else 'Concentration'} ({unit})",
                yaxis_title=f"{'Signal' if st.session_state.language=='FR' else 'Signal'}",
                title=f"{'Courbe de linéarité' if st.session_state.language=='FR' else 'Linearity Curve'}"
            )
            st.plotly_chart(fig)
            st.success(f"Équation : {eq}")

            if slope != 0:
                if "Concentration" in unknown_type or "inconnue" in unknown_type:
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 {'Concentration inconnue' if st.session_state.language=='FR' else 'Unknown concentration'} = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 {'Signal inconnu' if st.session_state.language=='FR' else 'Unknown signal'} = {result:.4f}")

            def export_pdf_linearity():
                content_text = f"Linearity Curve:\nEquation: {eq}\nUnknown type: {unknown_type}\nUnknown value: {unknown_value}\nResult: {result:.4f} {unit if 'Concentration' in unknown_type or 'inconnue' in unknown_type else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button(f"{'Exporter le rapport PDF' if st.session_state.language=='FR' else 'Export PDF Report'}", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"{'Erreur dans les calculs' if st.session_state.language=='FR' else 'Error in calculation'}: {e}")

    st.button(f"⬅️ {'Déconnexion' if st.session_state.language=='FR' else 'Logout'}", on_click=logout)

# -------------------------------
# Calcul S/N
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()
    sn_ratio = signal_peak / noise if noise != 0 else np.nan

    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp if noise_usp != 0 else np.nan

    lod = 3 * noise
    loq = 10 * noise

    return sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp

def sn_page():
    st.header(f"📊 {'Calcul du rapport signal/bruit (S/N)' if st.session_state.language=='FR' else 'Signal-to-Noise Ratio (S/N)'}")
    st.write(f"{'Vous êtes connecté en tant que' if st.session_state.language=='FR' else 'You are logged in as'} **{st.session_state.username}**")
    company_name = st.text_input(f"{'Nom de la compagnie pour le rapport PDF' if st.session_state.language=='FR' else 'Company name for PDF report'}", value="", key="company_name_sn")

    uploaded_file = st.file_uploader(f"{'Téléverser un chromatogramme (CSV)' if st.session_state.language=='FR' else 'Upload chromatogram (CSV)'}", type=["csv"], key="sn_upload")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]
            if "time" not in df.columns or "signal" not in df.columns:
                st.error(f"{'CSV doit contenir les colonnes : Time et Signal' if st.session_state.language=='FR' else 'CSV must contain columns: Time and Signal'}")
                return

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Time", yaxis_title="Signal", title="Chromatogram")
            st.plotly_chart(fig)

            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)
            st.success(f"S/N = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (baseline noise = {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

            # Convert to concentration if slope exists
            if 'slope' in st.session_state and st.session_state.slope != 0:
                sn_conc = sn_ratio / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope
                st.info(f"S/N en concentration: {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N en concentration: {sn_usp_conc:.4f} {st.session_state.unit}")

            def export_pdf_sn():
                content_text = f"""USP Signal to Noise Analysis:
Signal max: {signal_peak}
Noise: {noise:.4f}
S/N ratio: {sn_ratio:.2f}
USP S/N: {sn_usp:.2f}
LOD: {lod:.4f}, LOQ: {loq:.4f}
S/N in concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
USP S/N in concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button(f"{'Exporter le rapport PDF' if st.session_state.language=='FR' else 'Export PDF Report'}", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"{'Erreur de lecture CSV' if st.session_state.language=='FR' else 'Error reading CSV'}: {e}")

    st.button(f"⬅️ {'Déconnexion' if st.session_state.language=='FR' else 'Logout'}", on_click=logout)
def main_menu():
    # Language selection
    st.sidebar.selectbox("Language / Langue", ["EN", "FR"], index=0, key="language")

    role = st.session_state.role
    if role ==