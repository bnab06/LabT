# ================================
# app.py - Partie 1
# Imports et configuration
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from pdf2image import convert_from_path
from PIL import Image
import os
from datetime import datetime

# Configuration page
st.set_page_config(
    page_title="LabT Analysis Platform",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------
# Fonctions utilitaires
# ----------------

def load_csv(file):
    """Charge un fichier CSV et retourne un DataFrame"""
    try:
        df = pd.read_csv(file)
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement du CSV : {e}")
        return None

def save_csv(df, filename):
    """Sauvegarde un DataFrame en CSV"""
    try:
        df.to_csv(filename, index=False)
        st.success(f"Fichier sauvegardé : {filename}")
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")

def create_pdf(title, content, filename="report.pdf"):
    """Crée un PDF simple avec FPDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(10)
    for line in content:
        pdf.multi_cell(0, 10, line)
    pdf.output(filename)
    st.success(f"PDF généré : {filename}")

# ----------------
# Session utilisateur
# ----------------

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None
# ================================
# app.py - Partie 2
# Traitement CSV et chromatogramme
# ================================

# ----------------
# Lecture de chromatogrammes
# ----------------

def extract_chrom_data(df, time_col="Time", signal_col="Signal"):
    """Extrait les colonnes temps et signal d'un DataFrame"""
    if time_col not in df.columns or signal_col not in df.columns:
        st.error(f"Colonnes attendues non trouvées : {time_col}, {signal_col}")
        return None, None
    return df[time_col].values, df[signal_col].values

def plot_chrom(time, signal, title="Chromatogramme"):
    """Affiche un chromatogramme avec matplotlib"""
    fig, ax = plt.subplots()
    ax.plot(time, signal, color="blue")
    ax.set_xlabel("Temps")
    ax.set_ylabel("Signal")
    ax.set_title(title)
    st.pyplot(fig)

# ----------------
# Traitement d'images / PDF de chromatogrammes
# ----------------

def load_chrom_image(file):
    """Charge une image et retourne un objet PIL"""
    try:
        img = Image.open(file)
        return img
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'image : {e}")
        return None

def pdf_to_images(pdf_file):
    """Convertit un PDF en images (liste de pages)"""
    try:
        pages = convert_from_path(pdf_file)
        return pages
    except Exception as e:
        st.error(f"Erreur lors de la conversion PDF : {e}")
        return None

# ----------------
# Extraction simple des données à partir d'image (option OCR si nécessaire)
# ----------------

def extract_signal_from_image(img):
    """
    Extraction simplifiée du signal à partir d'une image.
    Placeholder pour intégration OCR / analyse de graphique.
    """
    st.warning("Extraction du signal depuis image non implémentée. Fonction placeholder.")
    return None, None
# ================================
# app.py - Partie 3
# Calcul S/N, LOD, LOQ et export
# ================================

# ----------------
# Calcul du signal-to-noise
# ----------------
def calculate_sn(signal, noise_region=None):
    """
    Calcule le rapport signal sur bruit (S/N)
    signal : tableau numpy du pic
    noise_region : tuple (start_idx, end_idx) pour bruit de fond
    """
    if noise_region:
        noise = np.std(signal[noise_region[0]:noise_region[1]])
    else:
        # Si pas de région de bruit fournie, estimation sur tout le signal
        noise = np.std(signal)
    peak_height = np.max(signal) - np.min(signal)
    if noise == 0:
        st.warning("Bruit nul détecté, S/N infini")
        return np.inf
    return peak_height / noise

# ----------------
# Calcul LOD et LOQ
# ----------------
def calculate_lod_loq(signal, noise_region=None):
    sn = calculate_sn(signal, noise_region)
    # Formule classique : LOD = 3*noise, LOQ = 10*noise
    if noise_region:
        noise = np.std(signal[noise_region[0]:noise_region[1]])
    else:
        noise = np.std(signal)
    lod = 3 * noise
    loq = 10 * noise
    return lod, loq, sn

# ----------------
# Export CSV
# ----------------
def export_csv(data, filename="results.csv"):
    """
    Export d'un dictionnaire ou DataFrame en CSV
    """
    if isinstance(data, dict):
        df = pd.DataFrame([data])
    else:
        df = data
    df.to_csv(filename, index=False)
    st.success(f"Fichier CSV sauvegardé : {filename}")

# ----------------
# Export PDF
# ----------------
def export_pdf_plot(fig, filename="results.pdf"):
    """
    Sauvegarde un graphique matplotlib en PDF
    """
    try:
        fig.savefig(filename)
        st.success(f"PDF sauvegardé : {filename}")
    except Exception as e:
        st.error(f"Erreur export PDF : {e}")
# ================================
# app.py - Partie 4
# Interface moderne sans sidebar
# ================================

# ----------------
# Fonction principale
# ----------------
def main():
    st.set_page_config(page_title="LabT", layout="wide")
    st.title("LabT - Analyse de chromatogrammes")

    # ----------------
    # Connexion / Authentification simple
    # ----------------
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None

    if not st.session_state.logged_in:
        st.subheader("Connexion")
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            if username == "admin" and password == "admin":
                st.session_state.logged_in = True
                st.session_state.user = "admin"
            elif username == "user" and password == "user":
                st.session_state.logged_in = True
                st.session_state.user = "user"
            else:
                st.error("Utilisateur ou mot de passe invalide")
        return

    st.sidebar.success(f"Connecté en tant que : {st.session_state.user}")

    # ----------------
    # Panels utilisateur/admin
    # ----------------
    panel_options = ["Analyse", "Admin"] if st.session_state.user == "admin" else ["Analyse"]
    panel = st.radio("Menu", panel_options)

    if panel == "Analyse":
        analysis_panel()
    elif panel == "Admin":
        admin_panel()

# ----------------
# Panel Analyse
# ----------------
def analysis_panel():
    st.header("Analyse chromatogramme")

    uploaded_file = st.file_uploader("Importer CSV ou PDF", type=["csv","pdf"])
    if uploaded_file:
        # Lecture CSV
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
            # Calcul exemple S/N
            if 'Signal' in df.columns:
                lod, loq, sn = calculate_lod_loq(df['Signal'].values)
                st.write(f"S/N: {sn:.2f}, LOD: {lod:.2f}, LOQ: {loq:.2f}")
                export_csv({"S/N": sn, "LOD": lod, "LOQ": loq})
        # Lecture PDF
        elif uploaded_file.name.endswith(".pdf"):
            images = pdf2image.convert_from_bytes(uploaded_file.read())
            st.image(images, width=600)
            st.info("Extraction de données PDF non implémentée ici")

# ----------------
# Panel Admin
# ----------------
def admin_panel():
    st.header("Panel Admin")
    st.write("Gestion utilisateurs et paramètres avancés")
    st.button("Déconnexion", on_click=logout)

# ----------------
# Déconnexion
# ----------------
def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.experimental_rerun()

# ----------------
# Lancement de l'application
# ----------------
if __name__ == "__main__":
    main()
