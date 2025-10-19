# app.py — Partie 1 / 4
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
import io
import base64

# ===================== CONFIG =====================
st.set_page_config(page_title="LabT", page_icon="🧪", layout="wide")

# ===================== SESSION INIT =====================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "unit" not in st.session_state:
    st.session_state.unit = ""
if "slope" not in st.session_state:
    st.session_state.slope = None
if "sn_conc" not in st.session_state:
    st.session_state.sn_conc = None

# ===================== USER MANAGEMENT =====================
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"admin": {"password": "admin"}}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

# ===================== LOGIN LOGIC =====================
def login_action():
    st.session_state.authenticated = True
    st.experimental_rerun()

def logout():
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.experimental_rerun()

def login():
    st.title("🔐 Connexion à LabT")
    users = load_users()
    selected_user = st.selectbox("👤 Choisir un utilisateur :", list(users.keys()))
    password = st.text_input("🔑 Mot de passe :", type="password")

    if st.button("Se connecter"):
        if selected_user in users and password == users[selected_user]["password"]:
            st.session_state.authenticated = True
            st.session_state.current_user = selected_user
            st.success(f"Connexion réussie ✅ / You are logged in as {selected_user}")
            st.experimental_rerun()
        else:
            st.error("❌ Nom d'utilisateur ou mot de passe incorrect.")

    st.markdown("---")
    st.caption("💡 Utilisateur par défaut : admin / Mot de passe : admin")
# app.py — Partie 2 / 4

def main_interface():
    st.title("🧮 Calculs et Analyses - LabT")

    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            logout()

    uploaded_file = st.file_uploader("📂 Importer un fichier CSV (Time, Signal)", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine="python")
            df.columns = [c.strip().capitalize() for c in df.columns]
            if not {"Time", "Signal"}.issubset(df.columns):
                st.error("❌ Le fichier CSV doit contenir les colonnes 'Time' et 'Signal'")
                return

            st.success("✅ Fichier importé avec succès.")
            st.dataframe(df.head())

            # Affichage graphique
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Time"], y=df["Signal"], mode='lines', name="Signal"))
            fig.update_layout(title="Chromatogramme", xaxis_title="Time", yaxis_title="Signal")
            st.plotly_chart(fig, use_container_width=True)

            # Sauvegarde pour usage ultérieur
            st.session_state.df = df

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")
# app.py — Partie 3 / 4

def calculate_sn(df, height_factor=0.5, noise_window=10):
    """Calcule le rapport Signal/Bruit."""
    try:
        signal_max = df["Signal"].max()
        baseline = df["Signal"].rolling(window=noise_window, min_periods=1).mean()
        noise = df["Signal"].std()
        sn_ratio = signal_max / noise if noise != 0 else np.nan
        return sn_ratio, signal_max, noise
    except Exception:
        return np.nan, np.nan, np.nan

def linearity_curve(df, concentrations, signals):
    """Trace et calcule la pente de la courbe de linéarité."""
    try:
        slope, intercept = np.polyfit(concentrations, signals, 1)
        st.session_state.slope = slope
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=concentrations, y=signals, mode='markers', name='Données'))
        fig.add_trace(go.Scatter(x=concentrations,
                                 y=slope * np.array(concentrations) + intercept,
                                 mode='lines', name=f'Droite: y = {slope:.4f}x + {intercept:.2f}'))
        fig.update_layout(title="Courbe de linéarité", xaxis_title="Concentration", yaxis_title="Signal")
        st.plotly_chart(fig, use_container_width=True)
        return slope
    except Exception as e:
        st.error(f"Erreur dans la courbe de linéarité : {e}")
        return None

def lod_loq_from_slope(slope, noise):
    """Calcule LOD et LOQ à partir de la pente et du bruit."""
    if slope and slope != 0:
        lod = 3.3 * noise / slope
        loq = 10 * noise / slope
        return lod, loq
    return None, None

def analyse_section():
    st.header("📈 Analyse et calculs")
    if "df" not in st.session_state:
        st.warning("⚠️ Importez un fichier CSV avant de continuer.")
        return

    df = st.session_state.df
    st.subheader("🔹 Paramètres de calcul")
    height_factor = st.number_input("Facteur de hauteur (height factor)", 0.1, 10.0, 0.5, 0.1)
    noise_window = st.number_input("Fenêtre de bruit", 3, 100, 10, 1)
    st.session_state.unit = st.text_input("Unité (ex: µg/mL)", value=st.session_state.unit)

    sn, signal_max, noise = calculate_sn(df, height_factor, noise_window)

    if not np.isnan(sn):
        st.success(f"S/N = {sn:.3f}")
        st.write(f"Signal max = {signal_max:.2f} / Bruit = {noise:.2f}")
    else:
        st.error("Erreur dans le calcul du rapport signal/bruit.")

    # Option : faire une courbe de linéarité
    do_linearity = st.checkbox("Faire une courbe de linéarité (pour LOD/LOQ)", value=False)

    if do_linearity:
        st.info("Entrez les concentrations et signaux pour la courbe de linéarité :")
        concentrations = st.text_area("Concentrations (séparées par des virgules)")
        signals = st.text_area("Signaux correspondants (séparés par des virgules)")

        if concentrations and signals:
            try:
                conc = [float(x.strip()) for x in concentrations.split(",")]
                sig = [float(x.strip()) for x in signals.split(",")]
                slope = linearity_curve(df, conc, sig)

                if slope:
                    lod, loq = lod_loq_from_slope(slope, noise)
                    if lod and loq:
                        st.success(f"✅ LOD = {lod:.4f} {st.session_state.unit}")
                        st.success(f"✅ LOQ = {loq:.4f} {st.session_state.unit}")
                        st.session_state.slope = slope
                    else:
                        st.warning("Impossible de calculer LOD/LOQ (vérifiez les données).")
            except Exception as e:
                st.error(f"Erreur dans la saisie des données : {e}")
# app.py — Partie 4 / 4

def export_pdf_sn(company_name, sn, noise, signal_max, slope=None, lod=None, loq=None):
    """Exporte un rapport PDF complet."""
    if not company_name.strip():
        st.warning("⚠️ Entrez le nom de l’entreprise avant d’exporter le rapport.")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Rapport d'analyse - {company_name}", ln=True, align="C")

    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(0, 10, f"S/N = {sn:.3f}", ln=True)
    pdf.cell(0, 10, f"Signal max = {signal_max:.3f}", ln=True)
    pdf.cell(0, 10, f"Bruit = {noise:.3f}", ln=True)

    if slope:
        pdf.cell(0, 10, f"Pente de la droite = {slope:.4f}", ln=True)
    if lod and loq:
        pdf.cell(0, 10, f"LOD = {lod:.4f} {st.session_state.unit}", ln=True)
        pdf.cell(0, 10, f"LOQ = {loq:.4f} {st.session_state.unit}", ln=True)

    buffer = io.BytesIO()
    pdf.output(buffer)
    b64 = base64.b64encode(buffer.getvalue()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="rapport_labt.pdf">📄 Télécharger le rapport PDF</a>'
    st.markdown(href, unsafe_allow_html=True)

def main():
    if not st.session_state.authenticated:
        login()
        return

    main_interface()
    analyse_section()

    st.markdown("---")
    st.subheader("📤 Export du rapport")
    company = st.text_input("Nom de l’entreprise")
    if st.button("Générer le rapport PDF"):
        if "df" not in st.session_state:
            st.error("⚠️ Importez un fichier avant d’exporter.")
        else:
            sn, signal_max, noise = calculate_sn(st.session_state.df)
            lod, loq = (None, None)
            if st.session_state.slope and noise:
                lod, loq = lod_loq_from_slope(st.session_state.slope, noise)
            export_pdf_sn(company, sn, noise, signal_max,
                          st.session_state.slope, lod, loq)

if __name__ == "__main__":
    main()