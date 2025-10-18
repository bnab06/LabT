# app_fast.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import camelot
from datetime import datetime
from io import BytesIO
import json

USERS_FILE = "users.json"

# ---------- Users ----------
def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

users = load_users()

# ---------- Login ----------
def login():
    st.title("LabT - Login")
    user = st.selectbox("Utilisateur", list(users.keys()))
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if password == users[user]:
            st.session_state["user"] = user
            st.session_state["logged_in"] = True
            st.success(f"Connecté en tant que {user}")
        else:
            st.error("Mot de passe incorrect")

def logout():
    if st.button("Déconnecter"):
        st.session_state.clear()
        st.experimental_rerun()

# ---------- S/N Calculation ----------
def sn_from_csv(df, start, end):
    df_zone = df[(df["Time"] >= start) & (df["Time"] <= end)]
    y = df_zone["Signal"].values
    sn = np.max(y)/np.std(y)
    lod = 3*np.std(y)
    loq = 10*np.std(y)
    return sn, lod, loq

def sn_from_png(uploaded_file):
    img = mpimg.imread(uploaded_file)
    st.image(img, caption="Chromatogramme chargé")
    st.info("Extraction graphique approximative non implémentée pour PNG. Convertir en CSV pour calcul réel.")
    return None, None, None

def sn_from_pdf(uploaded_file):
    tables = camelot.read_pdf(uploaded_file, pages='all')
    if len(tables) == 0:
        st.error("Aucune table détectée dans le PDF")
        return None, None, None
    df = tables[0].df
    df = df.apply(pd.to_numeric, errors='coerce')
    start, end = df.iloc[0,0], df.iloc[-1,0]
    return sn_from_csv(df, start, end)

def sn_page():
    st.header("Calcul S/N, LOD, LOQ")
    uploaded_file = st.file_uploader("Charger CSV, PNG ou PDF", type=["csv","png","pdf"])
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            start = st.number_input("Début zone (Time)", value=float(df["Time"].min()))
            end = st.number_input("Fin zone (Time)", value=float(df["Time"].max()))
            if st.button("Calculer S/N"):
                sn, lod, loq = sn_from_csv(df, start, end)
                st.success(f"S/N = {sn:.2f}, LOD = {lod:.2f}, LOQ = {loq:.2f}")
        elif uploaded_file.name.endswith(".png"):
            if st.button("Calculer S/N"):
                sn_from_png(uploaded_file)
        else:  # PDF
            if st.button("Calculer S/N"):
                sn_from_pdf(uploaded_file)

# ---------- Linéarité ----------
def linearity_page():
    st.header("Courbe de Linéarité")
    method = st.radio("Méthode", ["Manuelle","CSV"])
    if method == "Manuelle":
        c = st.text_input("Concentrations (séparées par virgule)", "1,2,3")
        r = st.text_input("Réponses (aires ou absorbances, séparées par virgule)", "10,20,30")
        try:
            c = [float(x.strip()) for x in c.split(",")]
            r = [float(x.strip()) for x in r.split(",")]
            df = pd.DataFrame({"Concentration": c, "Réponse": r})
        except:
            st.error("Erreur dans la conversion des valeurs")
            return
    else:
        uploaded_file = st.file_uploader("Charger CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
        else:
            return

    fig, ax = plt.subplots()
    ax.plot(df["Concentration"], df["Réponse"], marker='o')
    ax.set_xlabel("Concentration (µg/mL)")
    ax.set_ylabel("Réponse")
    st.pyplot(fig)

    coeff = np.polyfit(df["Concentration"], df["Réponse"], 1)
    r2 = np.corrcoef(df["Concentration"], df["Réponse"])[0,1]**2
    st.info(f"R² = {r2:.4f}")

    unknown_signal = st.number_input("Signal inconnu")
    if unknown_signal:
        conc_unknown = (unknown_signal - coeff[1])/coeff[0]
        st.success(f"Concentration inconnue ≈ {conc_unknown:.4f} µg/mL")

# ---------- Admin ----------
def admin_page():
    st.header("Admin - Gestion des utilisateurs")
    new_user = st.text_input("Nom")
    new_pass = st.text_input("Mot de passe", type="password")
    if st.button("Ajouter"):
        if new_user and new_pass:
            users[new_user] = new_pass
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté")
    del_user = st.selectbox("Supprimer utilisateur", list(users.keys()))
    if st.button("Supprimer"):
        if del_user in users:
            users.pop(del_user)
            save_users(users)
            st.success(f"Utilisateur {del_user} supprimé")

# ---------- Main ----------
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        login()
    else:
        st.sidebar.markdown(f"Connecté en tant que: {st.session_state.get('user')}")
        logout()
        user = st.session_state.get("user")
        if user=="admin":
            admin_page()
        else:
            choice = st.radio("Choisir une action", ["S/N","Linéarité"])
            if choice=="S/N":
                sn_page()
            else:
                linearity_page()

if __name__=="__main__":
    main()