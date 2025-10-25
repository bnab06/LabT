# app.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import json
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
import cv2
import os

# -------------------------------------------
# Utils
# -------------------------------------------

def load_users():
    if not os.path.exists("users.json"):
        with open("users.json", "w") as f:
            json.dump({"admin": {"password": "admin123"}, "user": {"password": "user123"}}, f)
    with open("users.json", "r") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def linear_regression(x, y):
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs
    y_fit = slope * np.array(x) + intercept
    r2 = 1 - sum((y - y_fit)**2)/sum((y - np.mean(y))**2)
    return slope, intercept, r2

# -------------------------------------------
# App
# -------------------------------------------

def login():
    users = load_users()
    st.sidebar.title("Connexion")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.experimental_rerun()
        else:
            st.sidebar.error("Invalid credentials")

def change_password():
    users = load_users()
    st.sidebar.subheader("Changer le mot de passe")
    current = st.sidebar.text_input("Mot de passe actuel", type="password")
    new = st.sidebar.text_input("Nouveau mot de passe", type="password")
    if st.sidebar.button("Changer"):
        if st.session_state["user"] in users and users[st.session_state["user"]]["password"] == current:
            users[st.session_state["user"]]["password"] = new
            save_users(users)
            st.sidebar.success("Password changed")
        else:
            st.sidebar.error("Incorrect current password")

# -------------------------------------------
# Linéarité
# -------------------------------------------

def linear_panel():
    st.subheader("Courbe de linéarité")
    mode = st.radio("Choix de saisie:", ["CSV", "Saisie manuelle"])
    df = None
    if mode == "CSV":
        file = st.file_uploader("Importer CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        data = st.text_area("Données séparées par virgules\nEx: 1,2\n3,5\n...")
        if data:
            rows = [list(map(float, row.split(","))) for row in data.strip().split("\n")]
            df = pd.DataFrame(rows, columns=["X","Y"])
    if df is not None:
        slope, intercept, r2 = linear_regression(df["X"], df["Y"])
        st.write(f"Equation: Y = {slope:.4f} X + {intercept:.4f}, R² = {r2:.4f}")
        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode='markers', name='Data'))
        fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode='lines', name='Fit'))
        st.plotly_chart(fig)
        # Concentration ↔ signal
        choice = st.selectbox("Calcul:", ["Concentration ↔ Signal", "Signal ↔ Concentration"])
        val = st.number_input("Entrer valeur")
        unit = st.selectbox("Unité", ["µg/mL", "mg/mL"])
        if choice == "Concentration ↔ Signal":
            st.write("Signal estimé:", slope*val + intercept)
        else:
            st.write("Concentration estimée:", (val - intercept)/slope)
        # Export PDF
        if st.button("Exporter PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0,10,f"Rapport Linéarité - {st.session_state['user']}", ln=True)
            pdf.ln(10)
            pdf.cell(0,10,f"Equation: Y={slope:.4f}X+{intercept:.4f}", ln=True)
            pdf.cell(0,10,f"R²={r2:.4f}", ln=True)
            pdf.output("rapport_linearite.pdf")
            st.success("PDF généré: rapport_linearite.pdf")
        st.session_state["slope"] = slope

# -------------------------------------------
# S/N
# -------------------------------------------

def sn_panel():
    st.subheader("Calcul S/N")
    st.write("Importer chromatogramme CSV, PNG ou PDF")
    file = st.file_uploader("Fichier", type=["csv","png","pdf"])
    df = None
    if file:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith(".png"):
            img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_GRAYSCALE)
            st.image(img)
        elif file.name.endswith(".pdf"):
            images = convert_from_path(file)
            for img in images:
                st.image(img)
    if df is not None:
        # sliders pour zone
        start = st.slider("Start index", 0, len(df)-1, 0)
        end = st.slider("End index", 0, len(df)-1, len(df)-1)
        y_zone = df["Signal"].iloc[start:end+1]
        sn_classic = y_zone.max()/y_zone.std()
        st.write(f"S/N classique = {sn_classic:.4f}")
        # Formules consultables
        if st.button("Voir formule S/N"):
            st.latex(r"S/N_{classic} = \frac{Signal_{max}}{Noise_{std}}")

# -------------------------------------------
# Admin
# -------------------------------------------

def admin_panel():
    st.subheader("Gestion utilisateurs")
    users = load_users()
    if st.button("Ajouter user"):
        new_user = st.text_input("Nom")
        pwd = st.text_input("Mot de passe", type="password")
        if new_user:
            users[new_user] = {"password": pwd}
            save_users(users)
            st.success("Utilisateur ajouté")
    if st.button("Supprimer user"):
        del_user = st.selectbox("Choisir user", list(users.keys()))
        if del_user:
            users.pop(del_user)
            save_users(users)
            st.success("Utilisateur supprimé")

# -------------------------------------------
# Menu principal
# -------------------------------------------

def main():
    st.title("LabT - Powered by BnB")
    if "user" not in st.session_state:
        login()
    else:
        change_password()
        user = st.session_state["user"]
        if user == "admin":
            admin_panel()
        else:
            linear_panel()
            sn_panel()

if __name__ == "__main__":
    main()