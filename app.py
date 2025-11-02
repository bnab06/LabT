# -*- coding: utf-8 -*-
import streamlit as st
from PIL import Image
import numpy as np
import cv2
import json
import io

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="LabT", layout="wide")

# -------------------------------
# USERS DATA (JSON)
# -------------------------------
USERS_FILE = "users.json"

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------------
# LOGIN PAGE
# -------------------------------
def login_page():
    st.title("LabT - Login")
    st.caption("Powered by BnB")
    
    users = load_users()
    
    username = st.text_input("Username").lower()
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username in users and password == users[username]["password"]:
            st.session_state["user"] = username
            st.session_state["role"] = users[username]["role"]
        else:
            st.error("Invalid credentials / Identifiants invalides")

# -------------------------------
# PDF → PNG
# -------------------------------
def pdf_to_png(file):
    from pdf2image import convert_from_bytes
    images = convert_from_bytes(file.read())
    img_byte_arr = io.BytesIO()
    images[0].save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# -------------------------------
# LINÉARITÉ PANEL
# -------------------------------
def linearity_panel():
    st.header("Linéarité")
    
    uploaded_csv = st.file_uploader("Upload CSV (conc, signal)", type="csv")
    concentrations = []
    signals = []
    
    if uploaded_csv:
        import pandas as pd
        df = pd.read_csv(uploaded_csv)
        concentrations = df['Concentration'].tolist()
        signals = df['Signal'].tolist()
    
    manual_input = st.text_area("Ou saisir manuellement les valeurs séparées par des virgules")
    if manual_input:
        lines = manual_input.split("\n")
        for line in lines:
            parts = line.split(",")
            if len(parts) >=2:
                concentrations.append(float(parts[0]))
                signals.append(float(parts[1]))
    
    if concentrations and signals:
        st.write("Concentrations:", concentrations)
        st.write("Signals:", signals)
        # Calcul automatique signal inconnu et concentration inconnue
        slope, intercept = np.polyfit(concentrations, signals, 1)
        st.write(f"Pente droite de linéarité: {slope:.4f}")
        st.write(f"Signal inconnu pour concentration X: {slope*0+intercept:.4f} (exemple)")
        # Exporter pente vers S/N
        st.session_state["slope"] = slope

# -------------------------------
# S/N ROBUSTE
# -------------------------------
def calculate_sn_robust(img, threshold=50, noise_start=0, noise_end=None):
    img_np = np.array(img.convert("L"))  # niveau de gris
    H = np.max(img_np)
    coords = np.where(img_np == H)
    peak_x, peak_y = coords[1][0], coords[0][0]
    
    # inversion
    img_inv = 255 - img_np
    
    if noise_end is None:
        noise_end = img_inv.shape[0]//5
    noise_region = img_inv[noise_start:noise_end, :]
    h = np.std(noise_region)
    
    sn_ratio = H / h if h != 0 else None
    
    # Image affichage
    img_disp = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
    cv2.circle(img_disp, (peak_x, peak_y), 5, (0,0,255), -1)
    
    return sn_ratio, H, h, img_disp, peak_x, peak_y

def sn_panel_robust():
    st.header("S/N Calculation")
    
    uploaded_file = st.file_uploader("Upload PNG ou PDF", type=["png","pdf"])
    if uploaded_file:
        img_path = uploaded_file
        if uploaded_file.name.endswith(".pdf"):
            img_path = pdf_to_png(uploaded_file)
        img = Image.open(img_path)
        
        threshold = st.slider("Threshold (0-255)", 0, 255, 50)
        noise_start = st.slider("Début zone bruit (px)", 0, img.height-1, 0)
        noise_end = st.slider("Fin zone bruit (px)", 1, img.height, img.height//5)
        
        sn, H, h, img_proc, px, py = calculate_sn_robust(img, threshold, noise_start, noise_end)
        
        st.write(f"**S/N ratio**: {sn:.2f} | **H**: {H} | **h**: {h}")
        st.image(img_proc, caption="Image traitée (pic rouge)", use_column_width=True)
# -------------------------------
# ADMIN PANEL
# -------------------------------
def admin_panel():
    st.header("Admin Panel - Gestion des utilisateurs")
    users = load_users()

    selected_user = st.selectbox("Sélectionner un utilisateur", list(users.keys()))
    if selected_user:
        role = st.selectbox("Rôle", ["admin", "user"], index=0 if users[selected_user]["role"]=="admin" else 1)
        access_linearity = st.checkbox("Accès Linéarité", value=users[selected_user].get("access_linearity", True))
        access_sn = st.checkbox("Accès S/N", value=users[selected_user].get("access_sn", True))
        
        if st.button("Mettre à jour l'utilisateur"):
            users[selected_user]["role"] = role
            users[selected_user]["access_linearity"] = access_linearity
            users[selected_user]["access_sn"] = access_sn
            save_users(users)
            st.success("Utilisateur mis à jour !")
    
    # Ajouter un nouvel utilisateur
    st.subheader("Ajouter un utilisateur")
    new_user = st.text_input("Nom d'utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    new_role = st.selectbox("Rôle", ["admin","user"])
    if st.button("Ajouter utilisateur"):
        if new_user in users:
            st.warning("Utilisateur déjà existant")
        else:
            users[new_user] = {"password": new_pass, "role": new_role, "access_linearity": True, "access_sn": True}
            save_users(users)
            st.success("Utilisateur ajouté !")

# -------------------------------
# FEEDBACK PANEL (DISCRET)
# -------------------------------
def feedback_panel():
    st.subheader("Feed-back (discret)")
    
    feedback = st.text_area("Envoyer vos commentaires")
    if st.button("Envoyer"):
        if "feedback_list" not in st.session_state:
            st.session_state["feedback_list"] = []
        st.session_state["feedback_list"].append({"user": st.session_state["user"], "message": feedback, "response": ""})
        st.success("Feedback envoyé !")
    
    # Admin peut lire et répondre
    if st.session_state.get("role") == "admin":
        st.markdown("**Feed-back utilisateurs**")
        for i, fb in enumerate(st.session_state.get("feedback_list", [])):
            st.write(f"**De**: {fb['user']}")
            st.write(f"**Message**: {fb['message']}")
            reply = st.text_input(f"Répondre à {fb['user']}", value=fb.get("response",""), key=f"reply_{i}")
            if st.button(f"Envoyer réponse {i}"):
                st.session_state["feedback_list"][i]["response"] = reply
                st.success("Réponse envoyée !")
    
    # Users peuvent voir toutes les réponses
    if st.session_state.get("role") == "user":
        st.markdown("**Réponses admin**")
        for fb in st.session_state.get("feedback_list", []):
            if fb.get("response"):
                st.write(f"**Réponse à {fb['user']}**: {fb['response']}")

# -------------------------------
# CHANGE PASSWORD (DISCRET)
# -------------------------------
def change_password_panel():
    st.subheader("Modifier mot de passe")
    old = st.text_input("Ancien mot de passe", type="password")
    new = st.text_input("Nouveau mot de passe", type="password")
    if st.button("Modifier"):
        users = load_users()
        username = st.session_state["user"]
        if old == users[username]["password"]:
            users[username]["password"] = new
            save_users(users)
            st.success("Mot de passe modifié !")
        else:
            st.error("Ancien mot de passe incorrect")

# -------------------------------
# MAIN APP
# -------------------------------
def main_app():
    if "user" not in st.session_state:
        login_page()
        return

    st.title("LabT - Application")
    st.write(f"Connecté en tant que {st.session_state['user']} ({st.session_state['role']})")

    # Menu horizontal
    menu = st.radio("Choisir le volet", ["Linéarité", "S/N"], horizontal=True)
    if menu == "Linéarité":
        if st.session_state.get("role") == "admin" and not st.session_state.get("access_linearity", True):
            st.warning("Accès refusé à Linéarité")
        else:
            linearity_panel()
    elif menu == "S/N":
        if st.session_state.get("role") == "admin" and not st.session_state.get("access_sn", True):
            st.warning("Accès refusé à S/N")
        else:
            sn_panel_robust()
    
    # Discret : mot de passe
    if st.checkbox("Changer mot de passe", key="pwd_discret"):
        change_password_panel()
    
    # Discret : feed-back
    if st.checkbox("Feed-back", key="fb_discret"):
        feedback_panel()
    
    # Admin panel
    if st.session_state.get("role") == "admin":
        st.checkbox("Admin Panel", key="admin_discret", on_change=admin_panel)

# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    main_app()