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

def logout():
    st.session_state.logged_in = False
    st.session_state.current_page = None
    st.session_state.username = ""
    st.session_state.role = ""
    st.experimental_rerun()

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
    users = load_users()
    selected_user = st.selectbox("Select user / Choisir un utilisateur :", list(users.keys()))
    password = st.text_input("Password / Mot de passe :", type="password")
    st.button("Login / Se connecter", on_click=login_action, args=(selected_user, password))

# -------------------------------
# Admin : gestion utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role, lang):
    if not username or (action not in ["Supprimer", "Delete"] and not password):
        st.warning("All fields must be filled / Tous les champs doivent être remplis !")
        return
    users = load_users()
    if action in ["Ajouter", "Add"]:
        if username in users:
            st.warning("User already exists / Utilisateur déjà existant.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("User added ✅ / Utilisateur ajouté ✅")
    elif action in ["Modifier", "Edit"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("User modified ✅ / Utilisateur modifié ✅")
    elif action in ["Supprimer", "Delete"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            del users[username]
            save_users(users)
            st.success("User deleted ✅ / Utilisateur supprimé ✅")

def manage_users():
    st.header("👥 User Management / Gestion des utilisateurs")
    st.write(f"You are logged in as / Vous êtes connecté en tant : **{st.session_state.username}**")
    lang = st.selectbox("Language / Langue", ["English", "Français"], index=0)
    action = st.selectbox("Action", ["Add", "Edit", "Delete"] if lang=="English" else ["Ajouter", "Modifier", "Supprimer"])
    username = st.text_input("Username / Nom d’utilisateur")
    password = st.text_input("Password / Mot de passe")
    role = st.selectbox("Role / Rôle", ["user", "admin"])
    st.button("Validate / Valider", on_click=validate_user_action, args=(action, username, password, role, lang))
    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# PDF helper
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
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download PDF / Télécharger PDF</a>', unsafe_allow_html=True)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Linearity Curve / Courbe de linéarité")
    st.write(f"You are logged in as / Vous êtes connecté en tant : **{st.session_state.username}**")
    conc_input = st.text_input("Known concentrations (comma separated) / Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Responses (comma separated) / Réponses (séparées par des virgules)", key="resp_input")
    unknown_type = st.selectbox("Unknown type / Type d'inconnu :", ["Concentration", "Signal"], key="unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue :", value=0.0, step=0.1, key="unknown_value")
    unit = st.selectbox("Concentration unit / Unité de concentration", ["µg/mL","mg/L","g/L"], index=0, key="unit")
    company_name = st.text_input("Company name for PDF / Nom de la compagnie pour le PDF :", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp):
                st.warning("Lists must have same length / Les listes doivent avoir la même taille.")
                return
            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"
            st.session_state.slope = slope
            st.session_state.unit = unit

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope*conc+intercept, mode="lines", name=f"Fit ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Linearity / Linéarité")
            st.plotly_chart(fig)
            st.success(f"Equation / Équation : {eq}")

            if slope != 0:
                if unknown_type=="Concentration":
                    result = (unknown_value - intercept)/slope
                    st.info(f"Unknown concentration = {result:.4f} {unit}")
                else:
                    result = slope*unknown_value + intercept
                    st.info(f"Unknown signal = {result:.4f}")

            def export_pdf_linearity():
                content_text = f"Linearity curve:\nEquation: {eq}\nUnknown type: {unknown_type}\nUnknown value: {unknown_value}\nResult: {result:.4f} {unit if unknown_type=='Concentration' else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)
            st.button("Export PDF / Exporter PDF", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs: {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# Signal/Noise
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise_std = df["signal"].std()
    sn_ratio = signal_peak / noise_std
    baseline = df.iloc[:max(1,int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp
    lod = 3 * noise_std
    loq = 10 * noise_std
    return sn_ratio, sn_usp, lod, loq, signal_peak, noise_std, noise_usp

def sn_page():
    st.header("📊 Signal/Noise / Rapport S/N")
    st.write(f"You are logged in as / Vous êtes connecté en tant : **{st.session_state.username}**")
    company_name = st.text_input("Company name for PDF / Nom de la compagnie pour le PDF :", value="", key="company_name_sn")
    uploaded_file = st.file_uploader("Upload chromatogram CSV / Téléverser un chromatogramme CSV", type=["csv"], key="sn_upload")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]
            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV must contain columns: Time and Signal / CSV doit contenir Time et Signal")
                return
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Time / Temps", yaxis_title="Signal", title="Chromatogram / Chromatogramme")
            st.plotly_chart(fig)

            sn_ratio, sn_usp, lod, loq, signal_peak, noise_std, noise_usp = calculate_sn(df)
            st.success(f"S/N = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (baseline noise = {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

            if st.session_state.slope != 0:
                sn_conc = sn_ratio / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope
                st.info(f"S/N in concentration = {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N in concentration = {sn_usp_conc:.4f} {st.session_state.unit}")

            def export_pdf_sn():
                content_text = f"""USP Signal to Noise Analysis:
Signal max: {signal_peak}
Noise: {noise_std:.4f}
S/N: {sn_ratio:.2f}
USP S/N: {sn_usp:.2f}
LOD: {lod:.4f}, LOQ: {loq:.4f}
S/N in concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit}
USP S/N in concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit}"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter PDF", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"Error reading CSV / Erreur de lecture CSV: {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# Menu principal
# -------------------------------
def main_menu():
    if st.session_state.role=="admin":
        manage_users()
    elif st.session_state.role=="user":
        choice = st.selectbox("Choose option / Choisir une option:", ["Linearity / Courbe de linéarité","S/N / Calcul S/N"])
        if choice.startswith("Linearity"):
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Unknown role / Rôle inconnu")

# -------------------------------
# Lancement
# -------------------------------
if not st.session_state.logged_in:
    login()
else:
    main_menu()