# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from sklearn.linear_model import LinearRegression
from fpdf import FPDF
import matplotlib.pyplot as plt
import io

# ===============================
# Initialisation session
# ===============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "access" not in st.session_state:
    st.session_state.access = []
if "slope_lin" not in st.session_state:
    st.session_state.slope_lin = None
if "lin_fig" not in st.session_state:
    st.session_state.lin_fig = None
if "sn_result" not in st.session_state:
    st.session_state.sn_result = {}
if "lod_s" not in st.session_state:
    st.session_state.lod_s = None
if "loq_s" not in st.session_state:
    st.session_state.loq_s = None
if "lod_c" not in st.session_state:
    st.session_state.lod_c = None
if "loq_c" not in st.session_state:
    st.session_state.loq_c = None
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

# ===============================
# Textes bilingues
# ===============================
TEXTS = {
    "FR": {
        "app_title": "🔬 LabT — Connexion",
        "username": "Nom d'utilisateur",
        "password": "Mot de passe",
        "login_btn": "Connexion",
        "login_error": "Nom d'utilisateur ou mot de passe incorrect.",
        "powered_by": "Powered by : BnB",
    },
    "EN": {
        "app_title": "🔬 LabT — Login",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "login_error": "Incorrect username or password.",
        "powered_by": "Powered by : BnB",
    }
}

# ===============================
# Données utilisateurs
# ===============================
USER_FILE = "users.json"
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump({
            "admin": {"password": "admin", "access": ["linearity", "sn"]},
        }, f)

with open(USER_FILE, "r") as f:
    users = json.load(f)

# ===============================
# Fonctions utilitaires
# ===============================
def calculate_lod_loq(slope, noise):
    lod_signal = 3.3 * noise
    loq_signal = 10 * noise
    if slope and slope != 0:
        lod_conc = lod_signal / slope
        loq_conc = loq_signal / slope
    else:
        lod_conc, loq_conc = None, None
    return lod_signal, loq_signal, lod_conc, loq_conc

# ===============================
# Authentification
# ===============================
def login_page():
    lang = st.session_state.lang
    texts = TEXTS[lang]
    st.title(texts["app_title"])

    chosen = st.selectbox("Lang / Language", options=["FR", "EN"], index=0 if st.session_state.lang=="FR" else 1)
    st.session_state.lang = chosen
    texts = TEXTS[st.session_state.lang]

    username = st.text_input(texts["username"])
    password = st.text_input(texts["password"], type="password")
    if st.button(texts["login_btn"]):
        user = username.lower().strip()
        if user in users and users[user]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.access = users.get(user, {}).get("access", [])
            st.rerun()
        else:
            st.error(texts["login_error"])

    st.markdown(f"""
        <style>
        .footer {{
            text-align: center;
            color: #6c757d;
            font-size:12px;
            font-style: italic;
            margin-top: 40px;
        }}
        </style>
        <div class="footer">{texts["powered_by"]}</div>
    """, unsafe_allow_html=True)

# ===============================
# Déconnexion
# ===============================
def logout():
    for key in ["logged_in","user","access"]:
        if key in st.session_state:
            del st.session_state[key]
    st.success("Vous avez été déconnecté.")
    st.rerun()

# ===============================
# Module Linéarité
# ===============================
def linearity_module():
    st.header("📈 Module Linéarité")
    uploaded_file = st.file_uploader("Importer un CSV pour linéarité", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "x" in df.columns and "y" in df.columns:
            X = df["x"].values.reshape(-1,1)
            Y = df["y"].values
            model = LinearRegression()
            model.fit(X,Y)
            slope = model.coef_[0]
            intercept = model.intercept_
            st.session_state.slope_lin = slope

            fig, ax = plt.subplots()
            ax.scatter(df["x"], df["y"], label="Données")
            ax.plot(df["x"], model.predict(X), color="red", label="Régression")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.legend()
            st.pyplot(fig)
            st.session_state.lin_fig = fig

            st.write(f"Pente : {slope:.4f}, Intercept : {intercept:.4f}")
        else:
            st.warning("Le CSV doit contenir 'x' et 'y'.")

# ===============================
# Module S/N + LOD/LOQ
# ===============================
def sn_module():
    st.header("📊 Module Signal/Bruit (S/N)")
    uploaded_file = st.file_uploader("Importer un CSV pour S/N", type=["csv"], key="sn_upload")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "signal" in df.columns and "noise" in df.columns:
            signal = df["signal"].values
            noise = df["noise"].values
            sn_ratio = np.mean(signal)/np.std(noise)
            st.session_state.sn_result["S/N"] = sn_ratio
            st.write(f"S/N moyen : {sn_ratio:.4f}")

            slope = st.session_state.slope_lin
            if slope:
                lod_s, loq_s, lod_c, loq_c = calculate_lod_loq(slope,np.std(noise))
                st.session_state.lod_s = lod_s
                st.session_state.loq_s = loq_s
                st.session_state.lod_c = lod_c
                st.session_state.loq_c = loq_c
                st.write(f"LOD signal : {lod_s:.4f}, LOQ signal : {loq_s:.4f}")
                st.write(f"LOD conc : {lod_c:.4f}, LOQ conc : {loq_c:.4f}")
        else:
            st.warning("Le CSV doit contenir 'signal' et 'noise'.")

# ===============================
# Génération PDF
# ===============================
def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Rapport LabT", ln=True, align="C")

    if st.session_state.lin_fig:
        pdf.set_font("Arial","",12)
        pdf.cell(0,10,"Module Linéarité", ln=True)
        img_bytes = io.BytesIO()
        st.session_state.lin_fig.savefig(img_bytes, format="png")
        pdf.image(img_bytes, x=10, w=180)

    if st.session_state.sn_result:
        pdf.set_font("Arial","",12)
        pdf.cell(0,10,"Module S/N", ln=True)
        pdf.cell(0,10,f"S/N moyen : {st.session_state.sn_result.get('S/N','N/A'):.4f}", ln=True)
        pdf.cell(0,10,f"LOD signal : {st.session_state.lod_s:.4f} , LOQ signal : {st.session_state.loq_s:.4f}", ln=True)
        pdf.cell(0,10,f"LOD conc : {st.session_state.lod_c:.4f} , LOQ conc : {st.session_state.loq_c:.4f}", ln=True)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    st.download_button("📄 Télécharger le PDF", data=pdf_bytes, file_name="rapport_labt.pdf", mime="application/pdf")

# ===============================
# Main App
# ===============================
def main_app():
    if st.button("Déconnexion"):
        logout()

    if "linearity" in st.session_state.access:
        linearity_module()
    if "sn" in st.session_state.access:
        sn_module()

    if st.session_state.lin_fig or st.session_state.sn_result:
        generate_pdf()

# ===============================
# Lancement
# ===============================
def run():
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    run()