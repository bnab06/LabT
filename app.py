# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
from scipy.stats import linregress
from scipy.signal import find_peaks
import json
from fpdf import FPDF
from PIL import Image
import io
import base64
import cv2
import fitz  # PyMuPDF for PDF
import tempfile
import os

st.set_page_config(page_title="LabT - Analyse Chromatographique", layout="wide")

# ------------------ AUTHENTIFICATION ------------------ #
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        users = {"admin": {"password": "admin123", "role": "admin"}}
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def login():
    st.sidebar.title("🔐 Connexion")
    username = st.sidebar.text_input("Utilisateur")
    password = st.sidebar.text_input("Mot de passe", type="password")
    if st.sidebar.button("Connexion"):
        users = load_users()
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = users[username]["role"]
            st.experimental_rerun()
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect.")

def logout():
    if "user" in st.session_state:
        if st.sidebar.button("🚪 Déconnexion"):
            del st.session_state["user"]
            st.experimental_rerun()

# ------------------ ADMINISTRATION ------------------ #
def admin_panel():
    st.title("👤 Gestion des utilisateurs")
    users = load_users()

    action = st.selectbox("Action", ["Ajouter", "Modifier", "Supprimer"])
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["user", "admin"])

    if st.button("Valider"):
        if action == "Ajouter":
            if username in users:
                st.warning("Utilisateur déjà existant.")
            else:
                users[username] = {"password": password, "role": role}
                save_users(users)
                st.success("Utilisateur ajouté avec succès.")
        elif action == "Modifier":
            if username not in users:
                st.warning("Utilisateur introuvable.")
            else:
                users[username] = {"password": password, "role": role}
                save_users(users)
                st.success("Utilisateur modifié.")
        elif action == "Supprimer":
            if username in users:
                del users[username]
                save_users(users)
                st.success("Utilisateur supprimé.")

# ------------------ CHANGER MOT DE PASSE ------------------ #
def profil_page():
    st.title("👤 Profil utilisateur")
    users = load_users()
    current_user = st.session_state["user"]
    new_password = st.text_input("Nouveau mot de passe", type="password")
    if st.button("Changer le mot de passe"):
        users[current_user]["password"] = new_password
        save_users(users)
        st.success("Mot de passe changé avec succès ✅")

# ------------------ LINÉARITÉ ------------------ #
def linearity_page():
    st.title("📈 Linéarité")

    option = st.radio("Mode d'entrée", ["Importer CSV", "Saisie manuelle"])
    if option == "Importer CSV":
        file = st.file_uploader("Importer fichier CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        data = st.text_area("Entrer les données (x,y) séparées par des virgules", "1,2\n2,4\n3,6")
        try:
            df = pd.read_csv(io.StringIO(data), header=None, names=["x", "y"])
        except:
            st.warning("Format incorrect.")
            return

    if 'df' in locals():
        st.write(df)
        slope, intercept, r_value, _, _ = linregress(df["x"], df["y"])
        st.success(f"**Équation : y = {slope:.4f}x + {intercept:.4f}**")
        st.info(f"**R² = {r_value**2:.5f}**")

        plt.figure()
        plt.scatter(df["x"], df["y"])
        plt.plot(df["x"], slope * df["x"] + intercept, color='red')
        st.pyplot(plt)

        st.session_state["slope_linearite"] = slope
        st.download_button("📤 Exporter pente vers S/N", str(slope), file_name="pente_linearite.txt")

# ------------------ DIGITALISATION ------------------ #
def extract_data_from_image(image):
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    ys, xs = np.where(edges > 0)
    if len(xs) < 10:
        return None
    df = pd.DataFrame({"Time": xs, "Signal": ys})
    df = df.sort_values("Time").reset_index(drop=True)
    return df

def digitizing_page():
    st.title("🧠 Digitalisation de chromatogramme")
    uploaded = st.file_uploader("Importer une image ou un PDF", type=["png", "jpg", "jpeg", "pdf"])
    if uploaded:
        if uploaded.type == "application/pdf":
            pdf_bytes = uploaded.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(uploaded)

        st.image(img, caption="Chromatogramme importé", use_container_width=True)
        df = extract_data_from_image(img)
        if df is not None:
            st.write("✅ Données extraites automatiquement :")
            st.dataframe(df.head())
            st.session_state["digitized_data"] = df
        else:
            st.warning("Impossible d'extraire les données. Vérifiez la qualité de l'image.")

# ------------------ SIGNAL / BRUIT ------------------ #
def sn_page():
    st.title("📊 Calcul du rapport S/N")

    uploaded = st.file_uploader("Importer un fichier chromatogramme", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
    elif "digitized_data" in st.session_state:
        df = st.session_state["digitized_data"]
        st.info("✅ Données importées depuis la digitalisation")
    else:
        st.warning("Veuillez importer ou digitaliser un chromatogramme.")
        return

    col1, col2 = st.columns(2)
    with col1:
        start = st.slider("Début de la zone d'analyse", 0, len(df)-2, 0)
    with col2:
        end = st.slider("Fin de la zone d'analyse", start+1, len(df)-1, len(df)-1)

    zone = df.iloc[start:end]
    signal_max = zone["Signal"].max()
    noise = np.std(zone["Signal"])
    sn_ratio = signal_max / noise if noise != 0 else 0

    st.metric("Signal / Bruit", f"{sn_ratio:.2f}")

    plt.figure()
    plt.plot(df["Time"], df["Signal"], label="Chromatogramme")
    plt.axvspan(df["Time"].iloc[start], df["Time"].iloc[end], color='orange', alpha=0.3, label="Zone analysée")
    plt.legend()
    st.pyplot(plt)

    slope = st.session_state.get("slope_linearite", None)
    if slope:
        lod = 3.3 * noise / slope
        loq = 10 * noise / slope
        st.success(f"**LOD = {lod:.5f}**, **LOQ = {loq:.5f}** (en concentration)")

# ------------------ RAPPORT PDF ------------------ #
def generate_pdf(company, username, sn_ratio, slope=None, lod=None, loq=None):
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, company, ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Utilisateur : {username}", ln=True)
    pdf.cell(200, 10, f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, f"S/N = {sn_ratio:.2f}", ln=True)
    if slope:
        pdf.cell(200, 10, f"Pente = {slope:.5f}", ln=True)
    if lod and loq:
        pdf.cell(200, 10, f"LOD = {lod:.5f}, LOQ = {loq:.5f}", ln=True)
    pdf.output(buffer)
    return buffer.getvalue()

# ------------------ MAIN ------------------ #
def main():
    if "user" not in st.session_state:
        login()
        return

    logout()

    menu = st.sidebar.radio(
        "Menu",
        ["Linéarité", "Signal/Bruit", "Digitalisation", "Profil", "Administration"] 
        if st.session_state["role"] == "admin" else 
        ["Linéarité", "Signal/Bruit", "Digitalisation", "Profil"]
    )

    if menu == "Linéarité":
        linearity_page()
    elif menu == "Signal/Bruit":
        sn_page()
    elif menu == "Digitalisation":
        digitizing_page()
    elif menu == "Profil":
        profil_page()
    elif menu == "Administration":
        admin_panel()

if __name__ == "__main__":
    main()