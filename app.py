# app.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageOps
import cv2
import json
from io import BytesIO
from datetime import datetime
from pdf2image import convert_from_bytes
import matplotlib.pyplot as plt

st.set_page_config(page_title="LabT Application", layout="wide")

# --- Initialize session state ---
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "linearity_slope" not in st.session_state:
    st.session_state["linearity_slope"] = None
if "feedback_list" not in st.session_state:
    st.session_state["feedback_list"] = []

# --- Load users from JSON ---
def load_users():
    try:
        with open("users.json","r") as f:
            return json.load(f)
    except:
        return {"admin": {"password": "admin", "role": "admin"},
                "user": {"password": "user", "role": "user"}}

users_db = load_users()
# --- Login page ---
def login_page():
    st.title("LabT Login / Connexion")
    st.markdown("Powered by BnB")

    username = st.text_input("Username / Nom d'utilisateur").lower()
    password = st.text_input("Password / Mot de passe", type="password")

    if st.button("Login / Se connecter"):
        if username in users_db and users_db[username]["password"] == password:
            st.session_state["username"] = username
            st.session_state["role"] = users_db[username]["role"]
            st.experimental_rerun()
        else:
            st.error("Invalid credentials / Identifiants invalides")

# --- Admin user management ---
def admin_panel():
    st.header("User Management / Gestion des utilisateurs")
    for u in users_db:
        st.write(f"{u} - Role: {users_db[u]['role']}")
    st.markdown("Add, remove or modify users here / Ajouter, supprimer ou modifier des utilisateurs")
# --- Linearity Panel ---
def linearity_panel():
    st.header("Linearity / Linéarité")
    uploaded_csv = st.file_uploader("Upload CSV / Importer CSV", type=["csv"])
    conc_manual = st.text_input("Manual concentrations / Concentrations manuelles (comma separated)")
    signal_manual = st.text_input("Manual signals / Signaux manuels (comma separated)")
    conc_unit = st.selectbox("Concentration unit / Unité de concentration", ["mg/mL", "µg/mL", "ng/mL"])

    if uploaded_csv:
        df = pd.read_csv(uploaded_csv)
        concentrations = df.iloc[:,0].values
        signals = df.iloc[:,1].values
    else:
        if conc_manual and signal_manual:
            concentrations = np.array([float(x) for x in conc_manual.split(",")])
            signals = np.array([float(x) for x in signal_manual.split(",")])
        else:
            return

    # --- Linear fit ---
    slope, intercept = np.polyfit(concentrations, signals, 1)
    st.session_state["linearity_slope"] = slope
    st.write(f"Linear fit: y = {slope:.4f} x + {intercept:.4f}")

    # --- Plot ---
    fig, ax = plt.subplots()
    ax.plot(concentrations, signals, 'o', color='black', label="Data")
    ax.plot(concentrations, slope*concentrations + intercept, '-', color='black', label="Fit")
    ax.set_xlabel(f"Concentration ({conc_unit})")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    # --- Calculate unknown ---
    conc_unknown = st.number_input("Signal unknown / Signal inconnu", value=0.0)
    if st.button("Calculate concentration / Calculer concentration"):
        conc_calc = (conc_unknown - intercept)/slope
        st.write(f"Concentration: {conc_calc:.4f} {conc_unit}")


# --- S/N Panel ---
def sn_panel():
    st.header("Signal-to-Noise / Rapport Signal sur Bruit (S/N)")

    uploaded_file = st.file_uploader("Upload chromatogram / Importer chromatogramme", type=["png","jpg","jpeg","pdf"])
    if uploaded_file:
        # PDF to PNG if necessary
        if uploaded_file.type == "application/pdf":
            try:
                pages = convert_from_bytes(uploaded_file.read())
                img = pages[0].convert("L")
            except:
                st.error("PDF conversion failed. Install poppler and check PATH.")
                return
        else:
            img = Image.open(uploaded_file).convert("L")

        img = ImageOps.invert(img)  # line baseline at bottom
        st.image(img, caption="Processed chromatogram / Chromatogramme traité", use_column_width=True)

        img_array = np.array(img)
        h, w = img_array.shape

        # --- Noise slider ---
        st.subheader("Select noise region / Sélectionner la zone de bruit")
        start_col, end_col = st.slider("Noise region (pixels)", 0, w, (0, w//10))
        noise_region = img_array[:, start_col:end_col]
        noise_std = np.std(noise_region)
        st.write(f"Noise Std / Écart type du bruit: {noise_std:.2f}")

        # --- Detect main peak ---
        max_val = np.max(img_array)
        max_pos = np.unravel_index(np.argmax(img_array), img_array.shape)
        st.write(f"Peak height / Hauteur du pic principal: {max_val}")
        st.write(f"Peak position / Temps de rétention (pixels): {max_pos[1]}")

        img_mark = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        cv2.circle(img_mark, (max_pos[1], max_pos[0]), radius=5, color=(0,0,255), thickness=-1)
        st.image(img_mark, caption="Peak marked / Pic marqué", use_column_width=True)

        # --- Manual/USP S/N ---
        st.subheader("Manual / USP S/N / LOQ / LOD calculations")
        H_input = st.number_input("H (peak height) / Hauteur du pic", value=float(max_val))
        h_input = st.number_input("h (noise height) / Bruit", value=float(noise_std))
        slope_option = st.radio("Choose slope / Choisir la pente", ["Use linearity slope / Utiliser la pente linéarité", "Manual / Manuel"], horizontal=True)

        if slope_option == "Use linearity slope / Utiliser la pente linéarité":
            slope = st.session_state.get("linearity_slope", None)
            if slope is None:
                st.warning("Linearity slope not available / Pente non disponible")
        else:
            slope = st.number_input("Enter slope / Entrer la pente", value=1.0)

        if st.button("Calculate S/N, LOD, LOQ"):
            S_N = H_input / h_input if h_input > 0 else 0
            LOD = 3 * h_input / slope if slope else None
            LOQ = 10 * h_input / slope if slope else None
            st.write(f"S/N: {S_N:.2f}")
            if LOD: st.write(f"LOD: {LOD:.4f}")
            if LOQ: st.write(f"LOQ: {LOQ:.4f}")

    # --- Feedback / Commentaires ---
    st.subheader("Feedback / Commentaires")
    feedback_text = st.text_area("Send feedback / Envoyer vos commentaires", "")
    if st.button("Submit / Envoyer"):
        st.session_state["feedback_list"].append({"user": st.session_state.get("username","unknown"), "text": feedback_text, "reply": ""})
        st.success("Feedback submitted / Commentaire envoyé")

    if st.session_state.get("role") == "admin":
        st.subheader("Admin feedback management / Gestion des commentaires")
        for i, fb in enumerate(st.session_state.get("feedback_list", [])):
            st.write(f"{i+1}. {fb['user']}: {fb['text']}")
            reply_text = st.text_input(f"Reply to feedback #{i+1} / Répondre", value=fb.get("reply",""))
            if st.button(f"Send reply #{i+1}"):
                st.session_state["feedback_list"][i]["reply"] = reply_text
                st.success(f"Reply sent / Réponse envoyée")
    else:
        st.subheader("Replies / Réponses")
        for fb in st.session_state.get("feedback_list", []):
            if fb.get("reply"):
                st.write(f"{fb['user']}: {fb['text']}")
                st.info(f"Admin reply: {fb['reply']}")
def main_app():
    if not st.session_state["username"]:
        login_page()
        return

    st.title(f"Welcome {st.session_state['username']} / Bienvenue")

    # --- Horizontal menu for Linearity / S/N ---
    choice = st.selectbox("Select module / Choisir le module", ["Linearity / Linéarité", "S/N"], index=0)

    if choice.startswith("Linearity"):
        linearity_panel()
    else:
        sn_panel()

    # --- Admin panel access ---
    if st.session_state.get("role") == "admin":
        admin_panel()

if __name__ == "__main__":
    main_app()