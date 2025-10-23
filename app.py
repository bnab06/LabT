import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO
import json
from datetime import datetime
from scipy import stats

# ----------------- Traduction FR/EN -----------------
def T(fr, en):
    return fr if st.session_state.lang == "FR" else en

# ----------------- Initialisation -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "lang" not in st.session_state:
    st.session_state.lang = "FR"  # par défaut

# ----------------- Utilisateurs -----------------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"admin": {"password":"admin", "role":"admin"}}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ----------------- Login -----------------
def login_form():
    st.title(T("Connexion", "Login"))
    col1, col2 = st.columns(2)
    username = col1.text_input(T("Utilisateur", "Username"))
    password = col2.text_input(T("Mot de passe", "Password"), type="password")
    if st.button(T("Se connecter", "Login")):
        users = load_users()
        if username.lower() in [u.lower() for u in users.keys()] and password == users.get(username, {}).get("password", ""):
            st.session_state.logged_in = True
            st.session_state.username = username
        else:
            st.error(T("Utilisateur ou mot de passe invalide", "Invalid username or password"))

# ----------------- Logout -----------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.experimental_rerun()

# ----------------- Changer mot de passe -----------------
def change_password():
    st.subheader(T("Changer mot de passe", "Change password"))
    old_pw = st.text_input(T("Ancien mot de passe", "Old password"), type="password")
    new_pw = st.text_input(T("Nouveau mot de passe", "New password"), type="password")
    if st.button(T("Valider", "Submit")):
        users = load_users()
        if old_pw == users.get(st.session_state.username, {}).get("password", ""):
            users[st.session_state.username]["password"] = new_pw
            save_users(users)
            st.success(T("Mot de passe changé", "Password changed"))
        else:
            st.error(T("Ancien mot de passe incorrect", "Old password incorrect"))

# ----------------- Linéarité -----------------
def linearity_tab():
    st.header(T("Linéarité", "Linearity"))
    input_type = st.radio(T("Méthode de saisie", "Input method"), [T("CSV", "CSV"), T("Saisie manuelle", "Manual input")])
    
    x = y = None
    if input_type == T("CSV", "CSV"):
        file = st.file_uploader(T("Importer CSV", "Upload CSV"), type=["csv"])
        if file:
            df = pd.read_csv(file)
            if df.shape[1] < 2:
                st.warning(T("CSV doit contenir au moins deux colonnes", "CSV must have at least two columns"))
                return
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
    else:
        x_str = st.text_input(T("Entrer les concentrations séparées par des virgules", "Enter concentrations separated by commas"))
        y_str = st.text_input(T("Entrer les signaux séparés par des virgules", "Enter signals separated by commas"))
        try:
            x = np.array([float(v) for v in x_str.split(",")])
            y = np.array([float(v) for v in y_str.split(",")])
        except:
            if x_str or y_str:
                st.error(T("Erreur de saisie", "Input error"))

    if x is not None and y is not None:
        slope, intercept, r_value, _, _ = stats.linregress(x, y)
        st.write(T(f"R² = {r_value**2:.4f}", f"R² = {r_value**2:.4f}"))
        fig, ax = plt.subplots()
        ax.scatter(x, y, label=T("Points expérimentaux", "Data points"))
        ax.plot(x, slope*x + intercept, color='red', label=T("Ajustement linéaire", "Linear fit"))
        ax.set_xlabel(T("Concentration", "Concentration"))
        ax.set_ylabel(T("Signal", "Signal"))
        ax.legend()
        st.pyplot(fig)

        # Concentration ou signal inconnu
        unknown_choice = st.selectbox(T("Calculer la concentration ou signal inconnu?", "Calculate unknown concentration or signal?"),
                                      [T("Concentration inconnue", "Unknown concentration"), T("Signal inconnu", "Unknown signal")])
        if unknown_choice == T("Concentration inconnue", "Unknown concentration"):
            signal_val = st.number_input(T("Entrer le signal", "Enter signal"))
            conc_val = (signal_val - intercept)/slope
            st.write(T(f"Concentration inconnue = {conc_val:.4f}", f"Unknown concentration = {conc_val:.4f}"))
        else:
            conc_val = st.number_input(T("Entrer la concentration", "Enter concentration"))
            signal_val = slope*conc_val + intercept
            st.write(T(f"Signal inconnu = {signal_val:.4f}", f"Unknown signal = {signal_val:.4f}"))

        # Export PDF
        if st.button(T("Exporter rapport PDF", "Export PDF report")):
            company = st.text_input(T("Nom de la compagnie", "Company name"))
            unit = st.selectbox(T("Unité de concentration", "Concentration unit"), ["ug/ml","mg/ml"])
            if not company:
                st.warning(T("Veuillez saisir le nom de la compagnie", "Please enter company name"))
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(0,10,T(f"Rapport Linéarité - {company}", f"Linearity Report - {company}"), ln=True)
                pdf.cell(0,10,T(f"R² = {r_value**2:.4f}", f"R² = {r_value**2:.4f}"), ln=True)
                img_buffer = BytesIO()
                fig.savefig(img_buffer, format='png')
                pdf.image(img_buffer, x=10, y=40, w=180)
                pdf_output = BytesIO()
                pdf.output(pdf_output)
                st.download_button(T("Télécharger PDF", "Download PDF"), pdf_output.getvalue(), file_name="linearity_report.pdf")

# ----------------- S/N -----------------
def sn_tab():
    st.header(T("S/N", "Signal to Noise"))
    uploaded_file = st.file_uploader(T("Importer CSV, PNG ou PDF", "Upload CSV, PNG or PDF"), type=["csv","png","pdf"])
    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()
        st.success(T("Fichier chargé", "File loaded"))
        if file_type == "csv":
            df = pd.read_csv(uploaded_file)
            if df.shape[1] < 2:
                st.warning(T("CSV doit contenir au moins deux colonnes", "CSV must have at least two columns"))
                return
            st.dataframe(df.head())
            time = df.iloc[:,0].values
            signal = df.iloc[:,1].values
            st.subheader(T("Sélectionner la zone pour le calcul S/N", "Select zone for S/N calculation"))
            start_idx = st.slider(T("Index début", "Start index"), 0, len(signal)-2, 0)
            end_idx = st.slider(T("Index fin", "End index"), 1, len(signal)-1, len(signal)-1)
            zone_signal = signal[start_idx:end_idx+1]
            zone_time = time[start_idx:end_idx+1]
            fig, ax = plt.subplots()
            ax.plot(time, signal, label=T("Signal", "Signal"))
            ax.plot(zone_time, zone_signal, color='red', label=T("Zone sélectionnée", "Selected zone"))
            ax.set_xlabel(T("Temps", "Time"))
            ax.set_ylabel(T("Signal", "Signal"))
            ax.legend()
            st.pyplot(fig)
            noise = np.std(zone_signal)
            signal_max = np.max(zone_signal)
            sn_classic = signal_max / noise
            sn_usp = 1.5 * signal_max / noise
            st.write(T(f"S/N classique : {sn_classic:.2f}", f"Classic S/N : {sn_classic:.2f}"))
            st.write(T(f"S/N USP : {sn_usp:.2f}", f"USP S/N : {sn_usp:.2f}"))
            if st.button(T("Exporter rapport PDF", "Export PDF report")):
                company = st.text_input(T("Nom de la compagnie", "Company name"))
                if not company:
                    st.warning(T("Veuillez saisir le nom de la compagnie", "Please enter company name"))
                else:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0,10,T(f"Rapport S/N - {company}", f"S/N report - {company}"), ln=True)
                    pdf.cell(0,10,T(f"S/N classique: {sn_classic:.2f}", f"Classic S/N: {sn_classic:.2f}"), ln=True)
                    pdf.cell(0,10,T(f"S/N USP: {sn_usp:.2f}", f"USP S/N: {sn_usp:.2f}"), ln=True)
                    img_buffer = BytesIO()
                    fig.savefig(img_buffer, format='png')
                    pdf.image(img_buffer, x=10, y=60, w=180)
                    pdf_output = BytesIO()
                    pdf.output(pdf_output)
                    st.download_button(T("Télécharger PDF", "Download PDF"), pdf_output.getvalue(), file_name="sn_report.pdf")
        else:
            st.image(uploaded_file)
            st.info(T("Aperçu PDF/PNG non implémenté pour calcul automatique", "PDF/PNG preview only, calculation not implemented"))

# ----------------- Menu principal -----------------
def main():
    if not st.session_state.logged_in:
        login_form()
        return
    st.title(T("Application LabT", "LabT Application"))
    st.sidebar.radio(T("Langue", "Language"), ["FR","EN"], index=0, key="lang")  # si sidebar minimal
    st.button(T("Déconnexion", "Logout"), on_click=logout)

    menu = st.selectbox(T("Menu", "Menu"), [T("Linéarité", "Linearity"), T("S/N", "Signal/Noise"), T("Changer mot de passe", "Change Password")])
    if menu == T("Linéarité", "Linearity"):
        linearity_tab()
    elif menu == T("S/N", "Signal/Noise"):
        sn_tab()
    elif menu == T("Changer mot de passe", "Change Password"):
        change_password()

if __name__ == "__main__":
    main()