import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import easyocr
from PIL import Image
import io
import json
from datetime import datetime

# ------------------ USERS ------------------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

users = load_users()

# ------------------ LOGIN ------------------
def login():
    st.title("LabT - Login")
    st.info("Sélectionnez votre utilisateur et entrez le mot de passe.")
    user = st.selectbox("Utilisateur", list(users.keys()))
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if user in users and users[user] == pwd:
            st.session_state['user'] = user
            st.success(f"Connecté en tant que {user}")
            st.session_state['menu'] = "main"
        else:
            st.error("Utilisateur ou mot de passe incorrect")

# ------------------ LOGOUT ------------------
def logout():
    if st.button("Déconnexion"):
        st.session_state['user'] = None
        st.session_state['menu'] = "login"

# ------------------ OCR ------------------
reader = easyocr.Reader(['en'])

def extract_data_from_image(uploaded_file):
    img = Image.open(uploaded_file)
    results = reader.readtext(np.array(img), detail=0)
    data = []
    for line in results:
        try:
            # extraire les nombres séparés par espaces ou virgules
            for val in line.replace(',', ' ').split():
                data.append(float(val))
        except:
            continue
    if len(data) % 2 != 0:
        data = data[:-1]  # supprimer le dernier si impair
    df = pd.DataFrame({"Time": data[::2], "Signal": data[1::2]})
    return df

# ------------------ CHROMATOGRAM ------------------
def load_chromatogram(uploaded_file):
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        if df.shape[1] < 2:
            st.error("CSV invalide, besoin d'au moins 2 colonnes")
            return None
        df.columns = ["Time", "Signal"]
    else:
        df = extract_data_from_image(uploaded_file)
    return df

def plot_chromatogram(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Signal"], mode="lines", name="Signal"))
    st.plotly_chart(fig, use_container_width=True)

# ------------------ S/N, LOD, LOQ ------------------
def calculate_sn(df, start, end):
    zone = df[(df["Time"] >= start) & (df["Time"] <= end)]
    if zone.empty:
        return None, None, None, None
    y = zone["Signal"].values
    sn = np.max(y)/np.std(y)
    lod = 3*sn
    loq = 10*sn
    return sn, lod, loq, zone

# ------------------ LINEARITY ------------------
def linearity_page():
    st.subheader("Courbe de linéarité")
    method = st.radio("Méthode de saisie", ["Entrée manuelle", "Importer CSV"])
    
    conc_unit = st.selectbox("Unité concentration", ["µg/mL", "mg/mL"])
    
    if method == "Entrée manuelle":
        c_input = st.text_area("Concentrations séparées par virgule")
        r_input = st.text_area("Réponses (aires ou absorbances) séparées par virgule")
        if st.button("Tracer la courbe"):
            try:
                c = np.array([float(x) for x in c_input.split(",")])
                r = np.array([float(x) for x in r_input.split(",")])
                if len(c) != len(r):
                    st.error("Concentration et réponse doivent avoir le même nombre de points")
                    return
                df = pd.DataFrame({"Concentration": c, "Réponse": r})
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["Concentration"], y=df["Réponse"], mode="markers+lines"))
                st.plotly_chart(fig, use_container_width=True)
                # régression linéaire
                m, b = np.polyfit(df["Concentration"], df["Réponse"], 1)
                r2 = np.corrcoef(df["Concentration"], df["Réponse"])[0,1]**2
                st.write(f"Équation: y = {m:.4f}x + {b:.4f}, R² = {r2:.4f}")
                
                # concentration inconnue
                unknown = st.number_input("Entrer le signal inconnu", value=0.0)
                if unknown > 0:
                    conc_calc = (unknown - b)/m
                    st.success(f"Concentration inconnue ≈ {conc_calc:.4f} {conc_unit}")
                
                # Export PDF
                if st.button("Exporter rapport PDF"):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, "Rapport Linéarité LabT", 0, 1, "C")
                    pdf.set_font("Arial", "", 12)
                    pdf.cell(0, 10, f"Utilisateur: {st.session_state['user']}", 0, 1)
                    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
                    pdf.cell(0, 10, f"Équation: y = {m:.4f}x + {b:.4f}, R² = {r2:.4f}", 0, 1)
                    pdf.cell(0, 10, f"Concentration inconnue ≈ {conc_calc:.4f} {conc_unit}", 0, 1)
                    pdf.output("rapport_linearite.pdf")
                    st.success("PDF généré: rapport_linearite.pdf")
            except Exception as e:
                st.error(f"Erreur: {e}")
    else:
        uploaded_file = st.file_uploader("Choisir un fichier CSV", type=["csv"])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            if df.shape[1] < 2:
                st.error("CSV invalide")
                return
            df.columns = ["Concentration","Réponse"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Concentration"], y=df["Réponse"], mode="markers+lines"))
            st.plotly_chart(fig, use_container_width=True)
            m, b = np.polyfit(df["Concentration"], df["Réponse"],1)
            r2 = np.corrcoef(df["Concentration"], df["Réponse"])[0,1]**2
            st.write(f"Équation: y = {m:.4f}x + {b:.4f}, R² = {r2:.4f}")

# ------------------ MAIN ------------------
def main():
    if 'menu' not in st.session_state:
        st.session_state['menu'] = "login"
    if 'user' not in st.session_state:
        st.session_state['user'] = None

    if st.session_state['menu'] == "login":
        login()
    elif st.session_state['menu'] == "main":
        st.title("LabT - Page principale")
        st.write(f"Connecté en tant que: {st.session_state['user']}")
        logout()
        
        action = st.selectbox("Choisir l'action", ["S/N USP", "Linéarité"])
        if action == "S/N USP":
            uploaded_file = st.file_uploader("Charger chromatogramme CSV, PNG ou JPG", type=["csv","png","jpg"])
            if uploaded_file is not None:
                df = load_chromatogram(uploaded_file)
                if df is not None:
                    plot_chromatogram(df)
                    start = st.number_input("Start Time", value=float(df["Time"].min()))
                    end = st.number_input("End Time", value=float(df["Time"].max()))
                    if st.button("Calculer S/N"):
                        sn, lod, loq, zone = calculate_sn(df, start, end)
                        if sn is not None:
                            st.write(f"S/N: {sn:.4f}, LOD: {lod:.4f}, LOQ: {loq:.4f}")
                        else:
                            st.error("Zone vide ou invalide")
        elif action == "Linéarité":
            linearity_page()

if __name__ == "__main__":
    main()