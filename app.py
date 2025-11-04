# app.py - Partie 1

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from pdf2image import convert_from_bytes
from skimage.color import rgb2gray
from skimage import io
from scipy.signal import find_peaks
import json
from datetime import datetime

# --- Session state initialisation ---
if "login_status" not in st.session_state:
    st.session_state["login_status"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""

# --- Chargement des utilisateurs depuis JSON ---
def load_users():
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        return users
    except FileNotFoundError:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# --- Page de connexion ---
def login_page():
    st.title("LabT Login / Connexion")
    st.caption("Powered by BnB")
    
    users = load_users()
    
    username_input = st.text_input("Username / Nom d'utilisateur").lower()
    password_input = st.text_input("Password / Mot de passe", type="password")
    
    if st.button("Login / Se connecter"):
        if username_input in users and users[username_input]["password"] == password_input:
            st.session_state["login_status"] = True
            st.session_state["username"] = username_input
            st.session_state["role"] = users[username_input]["role"]
            st.experimental_rerun()
        else:
            st.error("Invalid credentials / Identifiants invalides")
    
def logout():
    st.session_state["login_status"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.experimental_rerun()

# --- Navigation principale ---
def main_app():
    if not st.session_state["login_status"]:
        login_page()
        return
    
    st.write(f"Logged in as: {st.session_state['username']} ({st.session_state['role']})")
    if st.session_state["role"] == "admin":
        admin_panel()
    else:
        user_panel()
# app.py - Partie 2

# --- Panel Admin ---
def admin_panel():
    st.subheader("Admin Panel - Gestion des utilisateurs")
    users = load_users()

    new_user = st.text_input("Ajouter un utilisateur / Add user")
    new_password = st.text_input("Mot de passe / Password", type="password")
    new_role = st.selectbox("Rôle / Role", ["admin", "user"], key="admin_role_select")
    
    if st.button("Ajouter / Add"):
        if new_user and new_password:
            users[new_user.lower()] = {"password": new_password, "role": new_role}
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté")
        else:
            st.warning("Veuillez saisir un nom et mot de passe")
    
    st.subheader("Liste des utilisateurs / Users")
    for u, info in users.items():
        st.write(f"{u} - {info['role']}")
        if st.button(f"Supprimer {u}", key=f"del_{u}"):
            users.pop(u)
            save_users(users)
            st.experimental_rerun()
# app.py - Partie 3

# --- Panel Linéarité ---
def linearity_panel():
    st.subheader("Linéarité / Linearity")
    uploaded_csv = st.file_uploader("Importer CSV (concentration, signal)")
    unit = st.selectbox("Unité concentration / Unit", ["µg/mL", "mg/mL"], index=0)

    if uploaded_csv:
        df = pd.read_csv(uploaded_csv)
        x = df['concentration']
        y = df['signal']
        slope, intercept = np.polyfit(x, y, 1)
        st.session_state["linearity_slope"] = slope

        # Plot linéarité
        plt.figure()
        plt.plot(x, y, 'o', label="Data")
        plt.plot(x, slope*x+intercept, '-', label="Fit")
        plt.xlabel(f"Concentration ({unit})")
        plt.ylabel("Signal")
        plt.title("Courbe de linéarité")
        plt.legend()
        st.pyplot(plt.gcf())

        # Concentration ou signal inconnu
        y_unknown = st.number_input("Signal inconnu / Unknown signal")
        x_unknown = st.number_input("Concentration inconnue / Unknown concentration")
        if y_unknown:
            conc_calc = (y_unknown - intercept)/slope
            st.write(f"Concentration inconnue calculée: {conc_calc:.3f} {unit}")
        if x_unknown:
            signal_calc = slope * x_unknown + intercept
            st.write(f"Signal inconnu calculé: {signal_calc:.3f}")

# --- Panel S/N (voir code précédent fourni) ---
def sn_panel_robust():
    st.subheader("Calcul S/N / S/N Calculation")
    uploaded_file = st.file_uploader("Importer PDF ou PNG du chromatogramme")

    slope_manual = st.number_input("Pente manuelle (optionnel) / Manual slope", value=0.0)

    if uploaded_file:
        try:
            if uploaded_file.name.lower().endswith(".pdf"):
                images = convert_from_bytes(uploaded_file.read())
                img = images[0]
            else:
                img = io.imread(uploaded_file)

            st.image(img, caption="Chromatogramme original", use_column_width=True)
            img_gray = rgb2gray(np.array(img)) if img.ndim==3 else np.array(img)
            y_signal = img_gray.mean(axis=1)
            peaks, _ = find_peaks(y_signal, height=np.max(y_signal)*0.05)
            if len(peaks)==0:
                st.warning("Aucun pic détecté automatiquement")
            else:
                main_peak = peaks[np.argmax(y_signal[peaks])]
                H = y_signal[main_peak]
                h = H/2
                st.write(f"Hauteur pic principal H={H:.3f}")
                fig, ax = plt.subplots()
                ax.imshow(img)
                ax.plot([img.shape[1]//2], [main_peak], 'ro')
                st.pyplot(fig)

                threshold = st.slider("Sensibilité / Threshold", min_value=0.0, max_value=1.0, value=0.1)
                h_input = st.number_input("h (bruit) / noise", value=h)
                H_input = st.number_input("H (pic principal) / peak", value=H)
                slope = slope_manual if slope_manual !=0 else st.session_state.get("linearity_slope",1.0)
                sn_classic = H_input/h_input
                st.write(f"S/N classique: {sn_classic:.2f}")
                unit = st.selectbox("Unité concentration / Unit", ["µg/mL","mg/mL"])
                lod = 3*h_input/slope
                loq = 10*h_input/slope
                st.write(f"LOD={lod:.3f} {unit}, LOQ={loq:.3f} {unit}")
                if st.button("Afficher formules / Show formulas"):
                    st.latex(r"S/N = \frac{H}{h}")
                    st.latex(r"LOD = \frac{3 \cdot h}{pente}")
                    st.latex(r"LOQ = \frac{10 \cdot h}{pente}")
        except Exception as e:
            st.error(f"Erreur traitement image / Image processing error: {e}")

# --- Changer mot de passe ---
def change_password():
    st.subheader("Changer mot de passe / Change password")
    users = load_users()
    old = st.text_input("Ancien mot de passe / Old password", type="password")
    new = st.text_input("Nouveau mot de passe / New password", type="password")
    if st.button("Valider / Submit"):
        username = st.session_state["username"]
        if users[username]["password"] == old:
            users[username]["password"] = new
            save_users(users)
            st.success("Mot de passe changé")
        else:
            st.error("Ancien mot de passe incorrect")

# --- Feedback ---
def feedback_panel():
    st.subheader("Feedback / Suggestions")
    feedback_text = st.text_area("Envoyer vos commentaires / Send feedback")
    if st.button("Envoyer / Submit"):
        with open("feedback.json","a") as f:
            json.dump({"user":st.session_state["username"],"feedback":feedback_text,"date":str(datetime.now())}, f)
            f.write("\n")
        st.success("Feedback envoyé")
