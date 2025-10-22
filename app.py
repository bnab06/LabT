# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="LabT", layout="wide")

# --- Gestion de session utilisateur ---
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

# --- Simu base de données utilisateurs ---
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}

# --- Connexion ---
def login_area():
    st.sidebar.title("🔐 Connexion")
    username = st.sidebar.text_input("Utilisateur")
    password = st.sidebar.text_input("Mot de passe", type="password")
    if st.sidebar.button("Se connecter"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.user = username
            st.session_state.role = USERS[username]["role"]
            st.sidebar.success(f"Bienvenue {username}")
            st.rerun()
        else:
            st.sidebar.error("Utilisateur ou mot de passe invalide")

# --- Déconnexion ---
def logout():
    if st.sidebar.button("Se déconnecter"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()

# --- Vérification login ---
def require_login():
    if not st.session_state.user:
        st.stop()

# --- Génération du PDF rapport ---
def generate_report(title, company, results_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt=company, ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, txt=title, ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for line in results_text.split("\n"):
        pdf.multi_cell(0, 10, line)
    filename = f"{title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# --- Page Linéarité ---
def page_linearite():
    st.title("📈 Linéarité")

    mode = st.radio("Choisissez la méthode :", ["Importer un fichier CSV", "Saisie manuelle"])
    company = st.text_input("Nom de la compagnie", "Votre compagnie ici")
    unit = st.selectbox("Unité de concentration :", ["µg/mL", "mg/mL", "ng/mL"], index=0)

    if mode == "Importer un fichier CSV":
        file = st.file_uploader("Importer le fichier CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            st.dataframe(df)

    else:
        st.write("Saisissez vos données séparées par des virgules.")
        x_input = st.text_input("Concentrations", "1,2,3,4,5")
        y_input = st.text_input("Signaux", "10,20,30,40,50")
        try:
            x = np.array([float(i) for i in x_input.split(",")])
            y = np.array([float(i) for i in y_input.split(",")])
            df = pd.DataFrame({"Concentration": x, "Signal": y})
        except:
            st.error("⚠️ Vérifiez vos données.")
            return

    if "df" in locals() and len(df) > 1:
        try:
            slope, intercept = np.polyfit(df.iloc[:, 0], df.iloc[:, 1], 1)
            r2 = np.corrcoef(df.iloc[:, 0], df.iloc[:, 1])[0, 1] ** 2
        except np.linalg.LinAlgError:
            st.error("❌ Erreur lors du calcul de la régression linéaire.")
            return

        st.session_state.linear_slope = slope
        st.session_state.linear_intercept = intercept

        st.success(f"Pente : {slope:.4f} | Intercept : {intercept:.4f} | R² : {r2:.4f}")

        fig, ax = plt.subplots()
        ax.scatter(df.iloc[:, 0], df.iloc[:, 1], label="Points")
        ax.plot(df.iloc[:, 0], slope * df.iloc[:, 0] + intercept, color="red", label="Régression")
        ax.set_xlabel(f"Concentration ({unit})")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig, use_container_width=True)

        # Calcul concentration inconnue
        st.subheader("Calculer une concentration inconnue :")
        signal_inconnu = st.number_input("Signal inconnu", value=0.0)
        if signal_inconnu:
            conc = (signal_inconnu - intercept) / slope
            st.write(f"👉 Concentration estimée : **{conc:.4f} {unit}**")

        if st.button("Exporter le rapport PDF"):
            results = f"""
Rapport de linéarité
Entreprise : {company}
Date : {datetime.now().strftime('%d/%m/%Y')}
Pente : {slope:.4f}
Intercept : {intercept:.4f}
R² : {r2:.4f}
"""
            file = generate_report("Rapport_Linéarité", company, results)
            with open(file, "rb") as f:
                st.download_button("📄 Télécharger le rapport", f, file_name=file)

# --- Page S/N ---
def page_sn():
    st.title("📊 Rapport Signal / Bruit (S/N)")

    company = st.text_input("Nom de la compagnie", "Votre compagnie ici")

    st.write("Choisissez votre mode d’importation :")
    mode = st.radio("", ["Importer un CSV", "Importer une image (PDF/PNG)"])

    slope = st.session_state.get("linear_slope", None)
    if slope:
        st.info(f"Pente importée depuis la linéarité : {slope:.4f}")

    if mode == "Importer un CSV":
        file = st.file_uploader("Importer le chromatogramme CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            if len(df.columns) >= 2:
                x, y = df.iloc[:, 0], df.iloc[:, 1]
                fig, ax = plt.subplots()
                ax.plot(x, y)
                ax.set_xlabel("Temps (min)")
                ax.set_ylabel("Signal")
                st.pyplot(fig, use_container_width=True)

                zone_min = st.number_input("Zone min", value=float(x.min()))
                zone_max = st.number_input("Zone max", value=float(x.max()))
                zone = df[(x >= zone_min) & (x <= zone_max)]

                if len(zone) > 1:
                    signal = np.max(zone.iloc[:, 1])
                    bruit = np.std(zone.iloc[:, 1])
                    sn_classique = signal / bruit if bruit != 0 else np.nan
                    sn_usp = (2 * signal) / bruit if bruit != 0 else np.nan

                    st.success(f"S/N classique : {sn_classique:.2f}")
                    st.info(f"S/N USP : {sn_usp:.2f}")

                    if slope:
                        lod = (3 * bruit) / slope
                        loq = (10 * bruit) / slope
                        st.write(f"LOD : **{lod:.4f}** {unit}")
                        st.write(f"LOQ : **{loq:.4f}** {unit}")

    elif mode == "Importer une image (PDF/PNG)":
        st.warning("📄 Cette fonctionnalité sera bientôt disponible.")

# --- Page Admin ---
def page_admin():
    st.title("👤 Gestion des utilisateurs")
    st.write("Ajouter, modifier ou supprimer un utilisateur.")
    st.warning("Module d’administration en construction...")

# --- Application principale ---
if not st.session_state.user:
    login_area()
else:
    st.sidebar.success(f"Connecté : {st.session_state.user}")
    logout()
    page = st.sidebar.radio("Menu principal", ["Linéarité", "S/N"] + (["Admin"] if st.session_state.role == "admin" else []))

    if page == "Linéarité":
        page_linearite()
    elif page == "S/N":
        page_sn()
    elif page == "Admin" and st.session_state.role == "admin":
        page_admin()