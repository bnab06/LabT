# app.py
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime

st.set_page_config(page_title="LabT", layout="wide")

# --- Users ---
USERS = {
    "admin": "admin123",
    "bb": "bb123",
    "user": "user123"
}

# --- Session state ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = "login"

# --- Functions ---
def login(user, pwd):
    if USERS.get(user) == pwd:
        st.session_state.logged_in = True
        st.session_state.user = user
        st.session_state.page = "main"
        st.success(f"Connecté en tant que {user}")
    else:
        st.error("Identifiants incorrects")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "login"

def calculate_sn(df, start, end):
    zone = df[(df['Time'] >= start) & (df['Time'] <= end)]
    y = zone['Signal'].values
    peak_height = np.max(y)
    noise = np.std(y)
    sn = peak_height / noise if noise != 0 else np.nan
    lod = 3 * noise
    loq = 10 * noise
    return sn, lod, loq, zone

def linearity(c, r):
    c = np.array(c)
    r = np.array(r)
    A = np.vstack([c, np.ones(len(c))]).T
    m, b = np.linalg.lstsq(A, r, rcond=None)[0]
    y_fit = m * c + b
    residuals = r - y_fit
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((r - np.mean(r))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot !=0 else np.nan
    return m, b, r2

# --- Pages ---
if st.session_state.page == "login":
    st.title("LabT - Connexion")
    user = st.selectbox("Utilisateur", list(USERS.keys()))
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        login(user, pwd)

elif st.session_state.page == "main":
    st.title("LabT - Menu Principal")
    st.write(f"Connecté en tant que **{st.session_state.user}**")
    if st.session_state.user == "admin":
        st.subheader("Gestion des utilisateurs")
        new_user = st.text_input("Nom utilisateur")
        new_pwd = st.text_input("Mot de passe", type="password")
        if st.button("Ajouter utilisateur"):
            if new_user and new_pwd:
                USERS[new_user] = new_pwd
                st.success(f"Utilisateur {new_user} ajouté")
            else:
                st.error("Remplir nom et mot de passe")
    else:
        menu = st.selectbox("Choisir un calcul", ["S/N USP", "Linéarité", "Tutoriel CSV"])
        if menu == "S/N USP":
            st.subheader("Calcul S/N, LOD, LOQ")
            uploaded_file = st.file_uploader("Uploader CSV (Time,Signal)", type="csv")
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    if df.shape[1] == 2:
                        df.columns = ["Time","Signal"]
                        st.success("CSV chargé")
                        start = st.number_input("Start Time", value=float(df['Time'].min()))
                        end = st.number_input("End Time", value=float(df['Time'].max()))
                        if st.button("Calculer S/N"):
                            sn, lod, loq, zone = calculate_sn(df, start, end)
                            st.write(f"S/N: {sn:.2f}, LOD: {lod:.2f}, LOQ: {loq:.2f}")
                            st.line_chart(zone.set_index("Time")["Signal"])
                    else:
                        st.error("CSV doit contenir exactement 2 colonnes")
                except Exception as e:
                    st.error(f"Erreur: {e}")
        elif menu == "Linéarité":
            st.subheader("Courbe de linéarité")
            unit = st.selectbox("Unité de concentration", ["µg/mL","mg/mL"])
            resp_unit = st.selectbox("Type de réponse", ["Aire","Absorbance"])
            c_str = st.text_input(f"Concentrations ({unit}) séparées par virgule")
            r_str = st.text_input(f"Réponses ({resp_unit}) séparées par virgule")
            if st.button("Tracer courbe"):
                try:
                    c = [float(x.strip()) for x in c_str.split(",")]
                    r = [float(x.strip()) for x in r_str.split(",")]
                    m, b, r2 = linearity(c, r)
                    st.write(f"y = {m:.4f}*x + {b:.4f}, R² = {r2:.4f}")
                    df_lin = pd.DataFrame({"Concentration":c, "Réponse":r})
                    st.line_chart(df_lin.set_index("Concentration"))
                    # Concentration inconnue
                    unknown = st.number_input("Entrer signal inconnu", value=0.0)
                    if unknown>0:
                        conc_unknown = (unknown - b)/m
                        st.write(f"Concentration inconnue: {conc_unknown:.4f} {unit}")
                except Exception as e:
                    st.error(f"Erreur: {e}")
        elif menu == "Tutoriel CSV":
            st.subheader("Préparer un CSV à partir d'un PDF ou PNG")
            st.markdown("""
**Pourquoi ?**  
Le calcul S/N nécessite un CSV avec 2 colonnes : `Time` et `Signal`.

**Étapes recommandées :**
1. Ouvrez [WebPlotDigitizer](https://apps.automeris.io/wpd/)
2. Importez votre PDF ou PNG.
3. Sélectionnez l'axe X (Time) et Y (Signal).
4. Exportez en CSV.
5. Uploadez le CSV dans S/N USP.
            """)
    if st.button("Déconnexion"):
        logout()