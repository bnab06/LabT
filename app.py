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
        st.success(f"Connexion réussie ✅ Vous êtes connecté en tant que {selected_user}")
    else:
        st.error("Nom d’utilisateur ou mot de passe incorrect ❌")

def login():
    st.title("🔬 LabT - Connexion")
    selected_user = st.selectbox("Choisir un utilisateur :", list(load_users().keys()))
    password = st.text_input("Mot de passe :", type="password")
    st.button("Se connecter", on_click=login_action, args=(selected_user, password))

# -------------------------------
# Page admin : gestion des utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer" and not password):
        st.warning("Tous les champs doivent être remplis !")
        return
    users = load_users()
    if action == "Ajouter":
        if username in users:
            st.warning("Utilisateur déjà existant.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("Utilisateur ajouté ✅")
    elif action == "Modifier":
        if username not in users:
            st.warning("Utilisateur introuvable.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("Utilisateur modifié ✅")
    elif action == "Supprimer":
        if username not in users:
            st.warning("Utilisateur introuvable.")
        else:
            del users[username]
            save_users(users)
            st.success("Utilisateur supprimé ✅")

def manage_users():
    st.header("👥 Gestion des utilisateurs")
    st.write(f"Vous êtes connecté en tant que **{st.session_state.username}**")

    action = st.selectbox("Action :", ["Ajouter", "Modifier", "Supprimer"], key="action_admin")
    username = st.text_input("Nom d’utilisateur :", key="username_admin")
    password = st.text_input("Mot de passe :", key="password_admin")
    role = st.selectbox("Rôle :", ["user", "admin"], key="role_admin")
    st.button("Valider", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Déconnexion", on_click=logout)

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
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Télécharger le PDF</a>', unsafe_allow_html=True)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Courbe de linéarité")
    st.write(f"Vous êtes connecté en tant que **{st.session_state.username}**")

    conc_input = st.text_input("Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Réponses (séparées par des virgules)", key="resp_input")
    unknown_type = st.selectbox("Type d'inconnu :", ["Concentration inconnue", "Signal inconnu"], key="unknown_type")
    unknown_value = st.number_input("Valeur inconnue :", value=0.0, step=0.1, key="unknown_value")
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

            st.session_state.slope = slope
            st.session_state.unit = unit

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

            def export_pdf_linearity():
                content_text = f"Courbe de linéarité:\nÉquation: {eq}\nType inconnu: {unknown_type}\nValeur inconnue: {unknown_value}\nRésultat: {result:.4f} {unit if unknown_type=='Concentration inconnue' else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Exporter le rapport PDF", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Erreur dans les calculs : {e}")

    st.button("⬅️ Déconnexion", on_click=logout)

# -------------------------------
# S/N
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
    st.header("📊 Calcul du rapport signal/bruit (S/N)")
    st.write(f"Vous êtes connecté en tant que **{st.session_state.username}**")
    company_name = st.text_input("Nom de la compagnie pour le rapport PDF :", value="", key="company_name_sn")

    uploaded_file = st.file_uploader("Téléverser un chromatogramme (CSV)", type=["csv"], key="sn_upload")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]

            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV doit contenir les colonnes : Time et Signal")
                return

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Temps", yaxis_title="Signal", title="Chromatogramme")
            st.plotly_chart(fig)

            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)
            st.success(f"Rapport S/N = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (bruit baseline = {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

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
S/N en concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
USP S/N en concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Exporter le rapport PDF", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"Erreur de lecture CSV : {e}")

    st.button("⬅️ Déconnexion", on_click=logout)

# -------------------------------
# Menu principal
# -------------------------------
def main_menu():
    role = st.session_state.role
    if role == "admin":
        manage_users()
    elif role == "user":
        choice = st.selectbox("Choisir une option :", ["Courbe de linéarité", "Calcul S/N"])
        if choice == "Courbe de linéarité":
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Rôle inconnu.")

# -------------------------------
# Lancement
# -------------------------------
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login()
    else:
        main_menu()