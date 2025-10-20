# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import peakutils
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
import os

# ===================== CONFIGURATION =====================
st.set_page_config(page_title="LabT", layout="wide")

USERS_FILE = "users.json"

# ===================== FONCTIONS UTILISATEURS =====================
def load_users():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin123", "role": "admin"},
            "user1": {"password": "user123", "role": "user"},
            "user2": {"password": "user123", "role": "user"},
        }
        save_users(users)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def check_login(username, password):
    users = load_users()
    username = username.lower()
    if username in users and users[username]["password"] == password:
        return users[username]["role"]
    return None

# ===================== FONCTIONS ANALYSE =====================
def detect_peaks(signal, threshold=0.5, min_dist=10):
    try:
        indexes = peakutils.indexes(np.array(signal), thres=threshold, min_dist=min_dist)
        return indexes
    except Exception:
        return np.array([])

def calculate_sn(df, peak_zone, noise_zone):
    signal_peak = df[(df["Time"] >= peak_zone[0]) & (df["Time"] <= peak_zone[1])]["Signal"]
    signal_noise = df[(df["Time"] >= noise_zone[0]) & (df["Time"] <= noise_zone[1])]["Signal"]

    if len(signal_peak) == 0 or len(signal_noise) == 0:
        return None, None

    peak_height = signal_peak.max() - signal_peak.min()
    noise_std = np.std(signal_noise)
    sn_ratio = peak_height / (2 * noise_std) if noise_std != 0 else np.nan
    return sn_ratio, noise_std

def calculate_lod_loq(sn_ratio):
    if sn_ratio and sn_ratio != 0:
        lod = 3 / sn_ratio
        loq = 10 / sn_ratio
        return lod, loq
    return None, None

# ===================== INTERFACE PDF =====================
def generate_pdf(df, sn_ratio, lod, loq):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Rapport LabT / LabT Report", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, f"S/N Ratio : {sn_ratio:.2f}" if sn_ratio else "S/N Ratio : N/A", ln=True)
    pdf.cell(200, 10, f"LOD : {lod:.4f}" if lod else "LOD : N/A", ln=True)
    pdf.cell(200, 10, f"LOQ : {loq:.4f}" if loq else "LOQ : N/A", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, "Tableau des données / Data Table", ln=True)
    pdf.ln(5)

    for i, row in df.iterrows():
        pdf.cell(200, 8, f"{row['Time']:.2f}    {row['Signal']:.2f}", ln=True)

    output = "rapport_labt.pdf"
    pdf.output(output)
    return output

# ===================== INTERFACE PRINCIPALE =====================
def main():
    st.title("🧪 LabT — Signal / Bruit, LOD, LOQ")

    lang = st.sidebar.radio("Langue / Language", ["Français", "English"])
    users = load_users()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None

    if not st.session_state.logged_in:
        st.subheader("🔐 Connexion" if lang == "Français" else "🔐 Login")
        username = st.text_input("Nom d'utilisateur / Username").lower()
        password = st.text_input("Mot de passe / Password", type="password")
        if st.button("Se connecter / Login"):
            role = check_login(username, password)
            if role:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.success("Connecté avec succès" if lang == "Français" else "Logged in successfully")
                st.experimental_rerun()
            else:
                st.error("Identifiants incorrects" if lang == "Français" else "Invalid credentials")
        return

    # ===================== ADMIN =====================
    if st.session_state.role == "admin":
        st.sidebar.markdown("### 👤 Gestion utilisateurs / User Management")
        users = load_users()
        st.write("### Utilisateurs existants / Existing Users")
        st.table(pd.DataFrame(users).T)

        new_user = st.text_input("Nouvel utilisateur / New Username").lower()
        new_pass = st.text_input("Mot de passe / Password")
        new_role = st.selectbox("Rôle / Role", ["user", "admin"])
        if st.button("Ajouter / Add"):
            users[new_user] = {"password": new_pass, "role": new_role}
            save_users(users)
            st.success("Utilisateur ajouté !" if lang == "Français" else "User added!")
        if st.button("Se déconnecter / Logout"):
            st.session_state.logged_in = False
            st.experimental_rerun()
        return

    # ===================== UTILISATEUR =====================
    st.sidebar.header("⚙️ Menu")
    menu = st.sidebar.radio("Navigation", ["Analyse CSV", "Déconnexion / Logout"])

    if menu == "Déconnexion / Logout":
        st.session_state.logged_in = False
        st.experimental_rerun()
        return

    st.subheader("📊 Analyse des données" if lang == "Français" else "📊 Data Analysis")
    uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
        df.columns = [c.strip().capitalize() for c in df.columns]
        if "Time" not in df.columns or "Signal" not in df.columns:
            st.error("Le CSV doit contenir les colonnes 'Time' et 'Signal'.")
            return

        st.write(df.head())

        # Sélection des zones
        col1, col2 = st.columns(2)
        with col1:
            peak_start = st.number_input("Début pic / Peak start", value=float(df["Time"].min()))
            peak_end = st.number_input("Fin pic / Peak end", value=float(df["Time"].min()) + 1)
        with col2:
            noise_start = st.number_input("Début bruit / Noise start", value=float(df["Time"].min()))
            noise_end = st.number_input("Fin bruit / Noise end", value=float(df["Time"].min()) + 1)

        sn_ratio, noise_std = calculate_sn(df, (peak_start, peak_end), (noise_start, noise_end))
        lod, loq = calculate_lod_loq(sn_ratio)

        if sn_ratio:
            st.success(f"Rapport S/N : {sn_ratio:.2f}")
            st.info(f"LOD : {lod:.4f} | LOQ : {loq:.4f}")
        else:
            st.warning("Impossible de calculer le rapport S/N")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Signal"], mode="lines", name="Signal"))
        fig.add_vrect(x0=peak_start, x1=peak_end, fillcolor="red", opacity=0.2, line_width=0, annotation_text="Peak")
        fig.add_vrect(x0=noise_start, x1=noise_end, fillcolor="blue", opacity=0.1, line_width=0, annotation_text="Noise")
        st.plotly_chart(fig, use_container_width=True)

        if st.button("📄 Générer le rapport PDF"):
            pdf_file = generate_pdf(df, sn_ratio, lod, loq)
            with open(pdf_file, "rb") as f:
                st.download_button("Télécharger le PDF", f, file_name=pdf_file)

if __name__ == "__main__":
    main()