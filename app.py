# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
from datetime import datetime
import base64

st.set_page_config(page_title="LabT", layout="wide")

# ---------------------- USERS ----------------------
USERS_FILE = "users.json"

import json
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"admin": "admin123", "bb": "bb123", "user": "user123"}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# ---------------------- LOGIN ----------------------
def login():
    st.title("LabT - Connexion")
    users = load_users()
    username = st.selectbox("Utilisateur", list(users.keys()))
    password = st.text_input("Mot de passe", type="password")
    login_btn = st.button("Se connecter")
    if login_btn:
        if username in users and password == users[username]:
            st.session_state["user"] = username
            st.success(f"Connecté en tant que {username}")
            st.session_state["page"] = "home"
        else:
            st.error("Identifiants incorrects")

# ---------------------- LOGOUT ----------------------
def logout():
    st.session_state.pop("user", None)
    st.session_state["page"] = "login"
    st.experimental_rerun()

# ---------------------- USER MANAGEMENT ----------------------
def manage_users():
    st.subheader("Gestion des utilisateurs (Admin)")
    users = load_users()
    st.write("Utilisateurs existants :", list(users.keys()))
    
    with st.form("add_user_form"):
        new_user = st.text_input("Nom utilisateur")
        new_pass = st.text_input("Mot de passe", type="password")
        add_btn = st.form_submit_button("Ajouter")
        if add_btn and new_user and new_pass:
            users[new_user] = new_pass
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté.")

    with st.form("delete_user_form"):
        del_user = st.selectbox("Supprimer utilisateur", list(users.keys()))
        del_btn = st.form_submit_button("Supprimer")
        if del_btn:
            if del_user in users:
                users.pop(del_user)
                save_users(users)
                st.success(f"Utilisateur {del_user} supprimé.")

# ---------------------- CHROMATOGRAMME ----------------------
def load_chromatogram(file):
    ext = file.name.split(".")[-1].lower()
    if ext == "csv":
        try:
            df = pd.read_csv(file)
            if "Time" not in df.columns or "Signal" not in df.columns:
                df.columns = ["Time", "Signal"]
            return df
        except:
            st.error("Erreur CSV : vérifiez le format")
            return None
    else:
        st.warning("Extraction graphique pour PDF/PNG non implémentée. Affichez l'image seulement.")
        return None

def sn_page():
    st.subheader("Calcul S/N, LOD, LOQ")
    uploaded_file = st.file_uploader("Charger chromatogramme CSV/PNG/PDF", type=["csv","png","pdf"])
    if uploaded_file:
        df = load_chromatogram(uploaded_file)
        if df is not None:
            st.line_chart(df.set_index("Time")["Signal"])
            start = st.number_input("Start Time", value=float(df['Time'].min()))
            end = st.number_input("End Time", value=float(df['Time'].max()))
            if st.button("Calculer S/N, LOD, LOQ"):
                y = df[(df['Time']>=start)&(df['Time']<=end)]["Signal"].values
                if len(y)==0:
                    st.error("Pas de données dans la zone sélectionnée")
                else:
                    noise = np.std(y)
                    peak = np.max(y)
                    sn = peak / noise
                    lod = 3*noise
                    loq = 10*noise
                    st.write(f"S/N: {sn:.2f}, LOD: {lod:.2f}, LOQ: {loq:.2f}")

# ---------------------- LINEARITY ----------------------
def linearity_page():
    st.subheader("Courbe de linéarité")
    conc_str = st.text_area("Concentrations (séparées par virgule)")
    resp_str = st.text_area("Réponses (séparées par virgule)")
    unit_conc = st.selectbox("Unité concentration", ["µg/mL","mg/mL"])
    unit_resp = st.selectbox("Réponse", ["Aire","Absorbance"])
    unknown_type = st.radio("Calcul automatique", ["Concentration inconnue","Signal inconnu"])
    unknown_val = st.number_input("Valeur inconnue (à calculer automatiquement)")

    if st.button("Calculer linéarité"):
        try:
            c = [float(x.strip()) for x in conc_str.split(",")]
            r = [float(x.strip()) for x in resp_str.split(",")]
            if len(c)!=len(r):
                st.error("Concentrations et réponses de longueurs différentes")
                return
            df = pd.DataFrame({"Concentration": c, "Réponse": r})
            # Regression linéaire
            m, b = np.polyfit(df["Concentration"], df["Réponse"],1)
            y_fit = m*np.array(c)+b
            r2 = np.corrcoef(df["Réponse"], y_fit)[0,1]**2
            st.write(f"Équation: y = {m:.3f}x + {b:.3f}, R² = {r2:.3f}")
            # Plot
            plt.figure()
            plt.scatter(c,r,label="Points")
            plt.plot(c,y_fit,color="red",label="Fit")
            plt.xlabel(f"Concentration ({unit_conc})")
            plt.ylabel(f"Réponse ({unit_resp})")
            plt.legend()
            st.pyplot(plt)
            # Calcul automatique
            if unknown_val>0:
                if unknown_type=="Concentration inconnue":
                    conc_calc = (unknown_val - b)/m
                    st.success(f"Concentration inconnue: {conc_calc:.3f} {unit_conc}")
                else:
                    signal_calc = m*unknown_val+b
                    st.success(f"Signal inconnu: {signal_calc:.3f} {unit_resp}")
        except Exception as e:
            st.error(f"Erreur: {e}")

    # Export PDF
    if st.button("Exporter PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial","B",16)
        pdf.cell(0,10,"LabT - Rapport Linéarité",ln=True,align="C")
        pdf.set_font("Arial","",12)
        pdf.cell(0,10,f"Utilisateur: {st.session_state.get('user','')}",ln=True)
        pdf.cell(0,10,f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
        pdf.cell(0,10,f"Équation: y = {m:.3f}x + {b:.3f}, R² = {r2:.3f}",ln=True)
        pdf.output("rapport_linearite.pdf")
        st.success("PDF généré: rapport_linearite.pdf")

# ---------------------- MAIN ----------------------
def main_menu():
    if "user" not in st.session_state:
        st.session_state["page"] = "login"

    page = st.session_state.get("page","login")
    if page=="login":
        login()
    else:
        st.sidebar.button("Déconnexion", on_click=logout)
        user = st.session_state["user"]
        st.title(f"LabT - Bienvenue {user}")
        if user=="admin":
            manage_users()
        else:
            choix = st.radio("Choisir une fonction", ["Linéarité","S/N"])
            if choix=="Linéarité":
                linearity_page()
            else:
                sn_page()
        if st.button("Retour au menu principal"):
            st.experimental_rerun()

if __name__=="__main__":
    main_menu()