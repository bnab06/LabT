import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image
import cv2
from fpdf import FPDF
import json
from pdf2image import convert_from_bytes

# ===============================
# INITIALISATION SESSION
# ===============================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "feedback_list" not in st.session_state:
    st.session_state["feedback_list"] = []
if "slope_linearity" not in st.session_state:
    st.session_state["slope_linearity"] = 1.0

# ===============================
# UTILITIES
# ===============================
def load_users():
    try:
        with open("users.json","r") as f:
            return json.load(f)
    except:
        return {"admin":{"password":"admin","role":"admin"}, "user":{"password":"user","role":"user"}}

users_db = load_users()

# ===============================
# PAGE DE LOGIN
# ===============================
def login_page():
    st.title("LabT Application")
    st.subheader("Login / Connexion")
    st.caption("Powered by: BnB")

    username = st.text_input("Username / Nom d'utilisateur").strip().lower()
    password = st.text_input("Password / Mot de passe", type="password")

    if st.button("Login / Se connecter"):
        if username in users_db and users_db[username]["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = users_db[username]["role"]
            st.success(f"Welcome {username} / Bienvenue {username}")
        else:
            st.error("Invalid credentials / Identifiants invalides")

def logout():
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.experimental_rerun()
# ===============================
# LINEARITE
# ===============================
def linearity_panel():
    st.subheader("Linearity / Linéarité")

    # --- Upload CSV ---
    csv_file = st.file_uploader("Upload linearity CSV", type=["csv"])
    if csv_file:
        try:
            df = pd.read_csv(csv_file)
            st.write(df)
            x = df['Concentration']
            y = df['Signal']
            slope, intercept = np.polyfit(x, y, 1)
            st.session_state["slope_linearity"] = slope
            st.line_chart({"Concentration": x, "Signal": slope*x + intercept})
            st.write(f"Slope / Pente: {slope:.4f}")
        except:
            st.error("Error reading CSV / Erreur lecture CSV")

    # --- Manual input ---
    conc_input = st.text_input("Concentrations (comma separated) / Concentrations séparées par des virgules")
    signal_input = st.text_input("Signals (comma separated) / Signaux séparés par des virgules")
    if conc_input and signal_input:
        try:
            x = np.array([float(v) for v in conc_input.split(",")])
            y = np.array([float(v) for v in signal_input.split(",")])
            slope, intercept = np.polyfit(x, y, 1)
            st.session_state["slope_linearity"] = slope
            st.line_chart({"Concentration": x, "Signal": slope*x + intercept})
            st.write(f"Slope / Pente: {slope:.4f}")
        except:
            st.error("Invalid manual input / Valeurs invalides")

    # --- Signal <-> Concentration unknowns ---
    st.write("Calculate unknown / Calcul concentration <-> signal")
    unknown_signal = st.number_input("Unknown signal / Signal inconnu")
    unknown_conc = st.number_input("Unknown concentration / Concentration inconnue")
    if st.button("Compute concentration from signal / Calculer concentration à partir du signal"):
        if slope != 0:
            conc = (unknown_signal - intercept)/slope
            st.write(f"Estimated concentration / Concentration estimée: {conc:.4f}")
    if st.button("Compute signal from concentration / Calculer signal à partir de la concentration"):
        sig = slope*unknown_conc + intercept
        st.write(f"Estimated signal / Signal estimé: {sig:.4f}")

    # --- Unit dropdown ---
    unit = st.selectbox("Unit / Unité", ["mg/mL","µg/mL","ppm"])
# ===============================
# SIGNAL-TO-NOISE & FEEDBACK
# ===============================
def sn_panel():
    st.subheader("Signal-to-Noise / Rapport Signal sur Bruit")

    # --- Upload image ---
    uploaded_image = st.file_uploader("Upload chromatogram image / Importer chromatogramme", type=["png","jpg","jpeg","pdf"])
    img = None
    if uploaded_image:
        if uploaded_image.name.endswith(".pdf"):
            pages = convert_from_bytes(uploaded_image.read())
            img = pages[0]
        else:
            img = Image.open(uploaded_image)

        img_gray = img.convert("L")
        img_array = np.array(img_gray)
        img_inv = 255 - img_array  # inversion
        st.image(Image.fromarray(img_inv), caption="Processed image / Image traitée", use_column_width=True)

        # Find peak
        peak_idx = np.argmax(img_inv)
        peak_val = img_inv.flatten()[peak_idx]
        peak_coords = np.unravel_index(peak_idx, img_inv.shape)
        st.write(f"Peak max / Pic principal: {peak_val}, position: {peak_coords}")

        # Red dot
        img_marked = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
        cv2.circle(img_marked, (peak_coords[1], peak_coords[0]), 5, (0,0,255), -1)
        st.image(Image.fromarray(img_marked), caption="Peak marked / Pic marqué", use_column_width=True)

    # Manual S/N
    st.write("Manual S/N calculation / Calcul manuel")
    H = st.number_input("Peak height H / Hauteur pic H", value=0.0)
    h = st.number_input("Noise height h / Hauteur bruit h", value=0.0)
    s_n_manual = H/h if h!=0 else 0
    st.write(f"S/N = H/h : {s_n_manual:.2f}")

    # LOQ/LOD
    unit = st.selectbox("Unit for LOQ/LOD / Unité pour LOQ/LOD", ["mg/mL","µg/mL","ppm"])
    slope = st.session_state.get("slope_linearity", 1.0)
    LOQ = 10*h/slope if slope!=0 else 0
    LOD = 3.3*h/slope if slope!=0 else 0
    st.write(f"LOQ: {LOQ:.5f} {unit}, LOD: {LOD:.5f} {unit}")

# Feedback
def feedback_panel():
    st.subheader("Feedback / Retours utilisateurs")
    user_name = st.session_state.get("username","anonymous")
    feedback_text = st.text_area("Your feedback / Votre retour")
    if st.button("Send / Envoyer"):
        fb = {"user":user_name,"text":feedback_text,"response":""}
        st.session_state["feedback_list"].append(fb)
        st.success("Feedback sent / Retour envoyé")

    st.write("All feedbacks / Tous les retours :")
    for fb in st.session_state["feedback_list"]:
        st.markdown(f"**{fb['user']}**: {fb['text']}")
        if fb['response']:
            st.markdown(f"Admin response: {fb['response']}")

# Admin feedback
def admin_feedback_panel():
    st.subheader("Admin feedback management / Gestion des retours")
    if st.session_state.get("role") != "admin":
        st.warning("Admin only / Réservé à l'admin")
        return
    for idx, fb in enumerate(st.session_state["feedback_list"]):
        st.markdown(f"**{fb['user']}**: {fb['text']}")
        resp = st.text_input(f"Response to {fb['user']}", value=fb['response'], key=f"resp{idx}")
        if st.button(f"Save response {idx}"):
            st.session_state["feedback_list"][idx]["response"] = resp
            st.success("Response saved / Réponse sauvegardée")

# ===============================
# MAIN APP
# ===============================
def main_app():
    if not st.session_state["logged_in"]:
        login_page()
    else:
        st.sidebar.button("Logout / Déconnexion", on_click=logout)
        role = st.session_state["role"]
        st.write(f"Logged in as {st.session_state['username']} ({role})")
        
        linearity_panel()
        sn_panel()
        feedback_panel()
        if role=="admin":
            admin_feedback_panel()

# Run
main_app()