import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import json
import os
import base64

# -------------------------------
# Fichier utilisateurs
# -------------------------------
USERS_FILE = "users.json"

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
# Initialisation session_state
# -------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'role' not in st.session_state:
    st.session_state.role = ''
if 'current_page' not in st.session_state:
    st.session_state.current_page = None
if 'unit' not in st.session_state:
    st.session_state.unit = ''
if 'slope' not in st.session_state:
    st.session_state.slope = NoneType
# -------------------------------
# Connexion et logout
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
    else:
        st.error("Nom d’utilisateur ou mot de passe incorrect ❌ / Incorrect username or password ❌")

def login():
    users_list = list(load_users().keys())
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", users_list, key="login_user")
    password = st.text_input("Password / Mot de passe:", type="password", key="login_pass")
    st.button("Login / Se connecter", on_click=login_action, args=(selected_user, password))
# -------------------------------
# Gestion des utilisateurs (admin)
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer / Delete" and not password):
        st.warning("Tous les champs doivent être remplis / All fields must be filled!")
        return
    users = load_users()
    if action in ["Ajouter / Add", "Add"]:
        if username in users:
            st.warning("Utilisateur déjà existant / User already exists.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("Utilisateur ajouté ✅ / User added ✅")
    elif action in ["Modifier / Edit", "Edit"]:
        if username not in users:
            st.warning("Utilisateur introuvable / User not found.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("Utilisateur modifié ✅ / User edited ✅")
    elif action in ["Supprimer / Delete", "Delete"]:
        if username not in users:
            st.warning("Utilisateur introuvable / User not found.")
        else:
            del users[username]
            save_users(users)
            st.success("Utilisateur supprimé ✅ / User deleted ✅")

def manage_users():
    st.header("👥 Gestion des utilisateurs / User Management")
    st.write(f"Vous êtes connecté en tant que / Logged in as **{st.session_state.username}**")

    action = st.selectbox(
        "Action:",
        ["Ajouter / Add", "Modifier / Edit", "Supprimer / Delete"],
        key="action_admin"
    )
    username = st.text_input("Nom d’utilisateur / Username:", key="username_admin")
    password = st.text_input("Mot de passe / Password:", key="password_admin")
    role = st.selectbox("Rôle / Role:", ["user", "admin"], key="role_admin")
    st.button("Valider / Confirm", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Déconnexion / Logout", on_click=logout)

# -------------------------------
# PDF
# -------------------------------
def generate_pdf(title, content_text, company=""):
    if not company:
        st.warning("Veuillez saisir le nom de l'entreprise / Please enter the company name")
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report / Rapport LabT", ln=True, align="C")
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
    if not pdf_file:
        return
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download PDF / Télécharger le PDF</a>',
        unsafe_allow_html=True
    )

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Courbe de linéarité / Linearity Curve")
    st.write(f"Vous êtes connecté en tant que / Logged in as **{st.session_state.username}**")

    conc_input = st.text_input("Concentrations (comma separated) / Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Responses (comma separated) / Réponses (séparées par des virgules)", key="resp_input")
    unknown_type = st.selectbox("Unknown type / Type d'inconnu:", ["Concentration inconnue / Unknown concentration", "Signal inconnu / Unknown signal"], key="unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue:", value=0.0, step=0.1, key="unknown_value")
    unit = st.selectbox("Unit / Unité:", ["µg/mL", "mg/L", "g/L"], index=0, key="unit")
    company_name = st.text_input("Company name for PDF / Nom de la compagnie pour le rapport PDF:", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("Les listes doivent avoir la même taille et ne pas être vides / Lists must be same length and not empty")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"

            st.session_state.slope = slope
            st.session_state.unit = unit

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept, mode="lines", name=f"Line / Droite ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Courbe de linéarité / Linearity Curve")
            st.plotly_chart(fig)
            st.success(f"Equation / Équation : {eq}")

            if slope != 0:
                if unknown_type.startswith("Concentration"):
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 Unknown concentration / Concentration inconnue = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 Unknown signal / Signal inconnu = {result:.4f} {unit}")

            def export_pdf_linearity():
                content_text = f"Linearity Curve / Courbe de linéarité:\nEquation / Équation: {eq}\nUnknown type / Type inconnu: {unknown_type}\nUnknown value / Valeur inconnue: {unknown_value} {unit}\nResult / Résultat: {result:.4f} {unit}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter le rapport PDF", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)
# ==========================
# 🧮 PARTIE 4 : S/N, LOD/LOQ
# ==========================

import io
from fpdf import FPDF

def sn_analysis(df, language, unit):
    try:
        # Vérification des colonnes
        time_col = [c for c in df.columns if 'time' in c.lower()]
        signal_col = [c for c in df.columns if 'signal' in c.lower()]
        if not time_col or not signal_col:
            raise ValueError("Missing Time/Signal columns")

        t = df[time_col[0]].to_numpy()
        y = df[signal_col[0]].to_numpy()

        # Calcul S/N classique
        baseline = np.std(y[:int(len(y) * 0.1)])
        peak = np.max(y)
        sn_classic = peak / baseline if baseline > 0 else np.nan

        # Calcul S/N USP : (2 * H) / (Hn - Hp)
        noise_section = y[:int(len(y) * 0.1)]
        usp_noise = np.std(noise_section)
        sn_usp = (2 * peak) / usp_noise if usp_noise > 0 else np.nan

        # LOD et LOQ avec pente (si dispo)
        slope = st.session_state.get("slope", None)
        lod = loq = None
        if slope and slope != 0:
            lod = 3.3 * usp_noise / slope
            loq = 10 * usp_noise / slope

        # Résumé affiché
        if language == "Français":
            st.subheader("Résultats S/N")
            st.write(f"S/N (classique) : {sn_classic:.2f}")
            st.write(f"S/N (USP) : {sn_usp:.2f}")
            if slope:
                st.write(f"**LOD :** {lod:.4f} {unit}")
                st.write(f"**LOQ :** {loq:.4f} {unit}")
        else:
            st.subheader("S/N Results")
            st.write(f"Classic S/N : {sn_classic:.2f}")
            st.write(f"USP S/N : {sn_usp:.2f}")
            if slope:
                st.write(f"**LOD :** {lod:.4f} {unit}")
                st.write(f"**LOQ :** {loq:.4f} {unit}")

        # Graphique du signal
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=y, mode="lines", name="Signal"))
        st.plotly_chart(fig, use_container_width=True)

        # Sauvegarde dans session
        st.session_state.sn_results = {
            "sn_classic": sn_classic,
            "sn_usp": sn_usp,
            "lod": lod,
            "loq": loq,
        }

    except Exception as e:
        msg = f"Erreur S/N : {e}" if language == "Français" else f"Error in S/N: {e}"
        st.error(msg)


def export_pdf_sn(df, language):
    """Création du rapport PDF S/N"""
    try:
        res = st.session_state.get("sn_results", {})
        sn_classic = res.get("sn_classic", "N/A")
        sn_usp = res.get("sn_usp", "N/A")
        lod = res.get("lod", "N/A")
        loq = res.get("loq", "N/A")
        unit = st.session_state.get("unit", "")
        company = st.session_state.get("company_name", "").strip()

        if not company:
            if language == "Français":
                st.warning("⚠️ Veuillez saisir le nom de l’entreprise avant d’exporter.")
            else:
                st.warning("⚠️ Please enter the company name before exporting.")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"App: LabT - {'Rapport S/N' if language == 'Français' else 'S/N Report'}", ln=True, align="C")
        pdf.ln(8)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, f"{'Entreprise' if language == 'Français' else 'Company'} : {company}", ln=True)
        pdf.cell(0, 10, f"{'Date' if language == 'Français' else 'Date'} : {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        pdf.ln(10)

        # Résultats
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Résultats / Results", ln=True)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, f"S/N (Classique / Classic): {sn_classic}", ln=True)
        pdf.cell(0, 8, f"S/N (USP): {sn_usp}", ln=True)
        pdf.cell(0, 8, f"LOD: {lod} {unit}", ln=True)
        pdf.cell(0, 8, f"LOQ: {loq} {unit}", ln=True)

        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        st.download_button(
            label="📄 Télécharger le rapport PDF" if language == "Français" else "📄 Download PDF Report",
            data=pdf_output.getvalue(),
            file_name="LabT_SN_Report.pdf",
            mime="application/pdf",
        )

    except Exception as e:
        msg = f"Erreur PDF : {e}" if language == "Français" else f"PDF Error: {e}"
        st.error(msg)


# ======================
# ⚙️ INTÉGRATION DU MODULE
# ======================

def sn_page():
    language = st.session_state.get("language", "English")
    unit = st.session_state.get("unit", "")

    st.title("🔍 Rapport S/N" if language == "Français" else "🔍 S/N Report")
    uploaded_file = st.file_uploader(
        "Importer un fichier CSV" if language == "Français" else "Upload CSV file", type=["csv"]
    )

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head())

            mode = st.selectbox(
                "Choisir le mode" if language == "Français" else "Choose mode",
                ["Classique + USP" if language == "Français" else "Classic + USP",
                 "Courbe + LOD/LOQ" if language == "Français" else "Linearity + LOD/LOQ"]
            )

            if "Courbe" in mode or "Linearity" in mode:
                st.session_state["slope"] = st.number_input(
                    "Pente de la courbe / Slope of line",
                    min_value=0.0001,
                    value=1.0,
                    format="%.4f"
                )

            if st.button("Calculer S/N" if language == "Français" else "Compute S/N"):
                sn_analysis(df, language, unit)

            if "sn_results" in st.session_state:
                if st.button("📄 Exporter PDF" if language == "Français" else "📄 Export PDF"):
                    export_pdf_sn(df, language)

        except Exception as e:
            msg = f"Erreur de lecture CSV : {e}" if language == "Français" else f"CSV read error: {e}"
            st.error(msg)
