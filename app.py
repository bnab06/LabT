# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import json
import os
from scipy.signal import find_peaks
from fpdf import FPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes

# ----------------------------------------
# CONFIGURATION DE BASE
# ----------------------------------------
st.set_page_config(page_title="LabT", layout="wide")
USERS_FILE = "users.json"


# ----------------------------------------
# GESTION UTILISATEURS
# ----------------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"admin": {"password": "admin"}}, f)
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
            if not isinstance(users, dict):
                raise ValueError
            return users
    except Exception:
        with open(USERS_FILE, "w") as f:
            json.dump({"admin": {"password": "admin"}}, f)
        return {"admin": {"password": "admin"}}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


# ----------------------------------------
# CALCULS S/N, LOD, LOQ
# ----------------------------------------
def usp_sn_analysis(df, height_factor=0.1):
    signal = df.iloc[:, 1].values
    peaks, _ = find_peaks(signal, height=np.max(signal) * height_factor, distance=5)

    if len(peaks) == 0:
        st.warning("Aucun pic détecté. Ajuste le facteur de hauteur.")
        return None, None

    baseline = np.delete(signal, peaks)
    noise = np.std(baseline)
    sn_ratios = [signal[p] / noise for p in peaks]

    df_result = pd.DataFrame({
        "Peak #": np.arange(1, len(peaks) + 1),
        "Time": df.iloc[peaks, 0],
        "Signal": signal[peaks],
        "S/N": sn_ratios
    })

    mean_sn = np.mean(sn_ratios)
    lod = 3 * noise
    loq = 10 * noise

    return df_result, mean_sn, lod, loq


# ----------------------------------------
# DIGITALIZATION (extraction signal depuis image/PDF)
# ----------------------------------------
def extract_from_image(uploaded_file):
    image = Image.open(uploaded_file)
    text = pytesseract.image_to_string(image)
    return text


def extract_from_pdf(uploaded_file):
    images = convert_from_bytes(uploaded_file.read())
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
    return text


# ----------------------------------------
# PDF REPORT
# ----------------------------------------
def generate_pdf_report(df_result, mean_sn, lod, loq):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Rapport LabT", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Moyenne S/N: {mean_sn:.2f}", ln=True)
    pdf.cell(200, 10, f"LOD: {lod:.4f}", ln=True)
    pdf.cell(200, 10, f"LOQ: {loq:.4f}", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", "B", 10)
    for _, row in df_result.iterrows():
        pdf.cell(40, 8, f"Peak {int(row['Peak #'])}", 0, 0)
        pdf.cell(40, 8, f"Time: {row['Time']:.2f}", 0, 0)
        pdf.cell(40, 8, f"S/N: {row['S/N']:.2f}", 0, 1)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer


# ----------------------------------------
# INTERFACE PRINCIPALE
# ----------------------------------------
def main():
    users = load_users()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    # ------------------------
    # LOGIN DIRECT SUR PAGE
    # ------------------------
    if not st.session_state.logged_in:
        st.title("🧪 LabT - Connexion")
        username = st.text_input("Nom d’utilisateur")
        password = st.text_input("Mot de passe", type="password")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Se connecter"):
                if username in users and users[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Nom d’utilisateur ou mot de passe incorrect.")

        with col2:
            if st.button("Quitter"):
                st.stop()

        return

    # ------------------------
    # CONTENU APRÈS LOGIN
    # ------------------------
    st.sidebar.title(f"👋 Bonjour, {st.session_state.username}")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    choix = st.sidebar.radio("📂 Menu :", [
        "Accueil",
        "Calculs S/N, LOD, LOQ",
        "Digitalization (extraction image/PDF)",
        "Admin (gestion utilisateurs)"
    ])

    # --- ACCUEIL ---
    if choix == "Accueil":
        st.title("🧪 LabT - Application de laboratoire")
        st.write("Bienvenue dans **LabT**. Sélectionnez une fonction dans le menu à gauche.")

    # --- CALCULS S/N ---
    elif choix == "Calculs S/N, LOD, LOQ":
        st.title("📈 Calculs S/N, LOD, LOQ")

        uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])
        height_factor = st.slider("Facteur de hauteur (sensibilité)", 0.01, 0.5, 0.1, 0.01)

        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head())

            result = usp_sn_analysis(df, height_factor)
            if result:
                df_result, mean_sn, lod, loq = result
                st.success(f"S/N moyen: {mean_sn:.2f} | LOD: {lod:.4f} | LOQ: {loq:.4f}")
                st.dataframe(df_result)

                csv = df_result.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Télécharger CSV", csv, "resultats_labt.csv", "text/csv")

                pdf_buf = generate_pdf_report(df_result, mean_sn, lod, loq)
                st.download_button("📄 Télécharger PDF", pdf_buf, "rapport_labt.pdf", "application/pdf")

    # --- DIGITALIZATION ---
    elif choix == "Digitalization (extraction image/PDF)":
        st.title("🧩 Extraction du signal à partir d’une image ou d’un PDF")

        file = st.file_uploader("Importer un chromatogramme (image ou PDF)", type=["jpg", "png", "jpeg", "pdf"])
        if file:
            if file.type == "application/pdf":
                text = extract_from_pdf(file)
            else:
                text = extract_from_image(file)

            st.text_area("Texte extrait :", text, height=300)
            st.success("Extraction terminée ✅")

    # --- ADMIN ---
    elif choix == "Admin (gestion utilisateurs)":
        if st.session_state.username != "admin":
            st.error("Accès réservé à l’administrateur.")
            return

        st.title("🧑‍💼 Gestion des utilisateurs")

        new_user = st.text_input("Nom du nouvel utilisateur")
        new_pass = st.text_input("Mot de passe", type="password")
        if st.button("Ajouter utilisateur"):
            if new_user and new_pass:
                users[new_user] = {"password": new_pass}
                save_users(users)
                st.success(f"Utilisateur '{new_user}' ajouté.")
            else:
                st.warning("Veuillez remplir les deux champs.")

        user_to_del = st.selectbox("Supprimer un utilisateur", list(users.keys()))
        if st.button("Supprimer utilisateur"):
            if user_to_del != "admin":
                del users[user_to_del]
                save_users(users)
                st.success(f"Utilisateur '{user_to_del}' supprimé.")
            else:
                st.error("Impossible de supprimer l’administrateur.")


if __name__ == "__main__":
    main()