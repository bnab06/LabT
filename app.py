# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import json
import io
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from PIL import Image
from pdf2image import convert_from_bytes
import pytesseract
import cv2

# ===============================
# 🔹 USERS FILE & migration pour éviter KeyError "access"
# ===============================
USERS_FILE = "users.json"

def migrate_legacy_users_minimal():
    """
    Corrige automatiquement les anciens utilisateurs pour qu'ils aient les clés 'role' et 'access'.
    Ne touche pas aux modules ni à l'interface.
    """
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}

    updated = False
    for u, data in users.items():
        if not isinstance(data, dict):
            users[u] = {"password": "user", "role": "user", "access": ["linearity", "sn"]}
            updated = True
            continue
        if "role" not in data:
            data["role"] = "user"
            updated = True
        if "access" not in data:
            data["access"] = ["linearity", "sn"]
            updated = True

    # Assurer la présence de l'admin
    if "admin" not in users:
        users["admin"] = {"password": "admin", "role": "admin", "access": ["linearity", "sn"]}
        updated = True

    if updated:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
        print("users.json mis à jour automatiquement pour corriger les clés manquantes.")

# ===============================
# OUTILS GÉNÉRAUX
# ===============================

def t(txt):
    return txt  # future version bilingue

def pdf_to_png_bytes(uploaded_file):
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1, dpi=300)
        if pages:
            return pages[0].convert("RGB"), None
    except Exception as e_pdf2:
        pdf2_err = str(e_pdf2)
    try:
        import fitz
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count < 1:
            return None, "PDF vide."
        page = doc.load_page(0)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        return img, None
    except Exception as e_fitz:
        return None, f"Erreur conversion PDF : {e_fitz}"

# ===============================
# AUTHENTIFICATION
# ===============================

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}

    # 🔹 Correction automatique
    for u, data in users.items():
        if not isinstance(data, dict):
            users[u] = {"password": "user", "role": "user", "access": ["linearity", "sn"]}
        else:
            if "role" not in data:
                data["role"] = "user"
            if "access" not in data:
                data["access"] = ["linearity", "sn"]
    return users

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def login_page():
    st.title("🔐 Connexion")
    users = load_users()
    username = st.selectbox("Utilisateur", list(users.keys()))
    password = st.text_input("Mot de passe", type="password")

    if st.button("Connexion"):
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = users[username].get("role", "user")
            st.session_state["access"] = users[username].get("access", ["linearity", "sn"])
            st.success("Connexion réussie !")
            st.session_state["page"] = "menu"
            st.rerun()
        else:
            st.error("Identifiants invalides.")

# ===============================
# ADMIN
# ===============================

def admin_panel():
    st.subheader("👤 Gestion des utilisateurs")
    users = load_users()
    action = st.selectbox("Action", ["Ajouter utilisateur", "Modifier privilèges", "Supprimer utilisateur"])

    if action == "Ajouter utilisateur":
        new_user = st.text_input("Nom d'utilisateur")
        new_pass = st.text_input("Mot de passe")
        privileges = st.multiselect("Modules", ["linearity", "sn"])
        if st.button("Créer"):
            if new_user and new_pass:
                users[new_user] = {"password": new_pass, "role": "user", "access": privileges or ["linearity", "sn"]}
                save_users(users)
                st.success(f"Utilisateur '{new_user}' ajouté.")
            else:
                st.error("Remplir tous les champs.")

    elif action == "Modifier privilèges":
        user_to_edit = st.selectbox("Utilisateur", [u for u in users if users[u]["role"] != "admin"])
        if user_to_edit:
            new_priv = st.multiselect("Modules", ["linearity", "sn"], default=users[user_to_edit].get("access", ["linearity", "sn"]))
            if st.button("Sauvegarder"):
                users[user_to_edit]["access"] = new_priv
                save_users(users)
                st.success("Modifications enregistrées.")

    elif action == "Supprimer utilisateur":
        user_to_del = st.selectbox("Utilisateur à supprimer", [u for u in users if users[u]["role"] != "admin"])
        if st.button("Supprimer"):
            users.pop(user_to_del)
            save_users(users)
            st.warning(f"Utilisateur {user_to_del} supprimé.")

    if st.button("⬅️ Retour au menu principal"):
        st.session_state["page"] = "menu"
        st.rerun()

# ===============================
# MODULE S/N
# ===============================

def analyze_sn(image):
    """Analyse S/N sur image avec tous les sliders et entrées manuelles."""
    try:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    except Exception:
        return None, "Erreur: image invalide."

    # 🔹 Tout le code S/N original avec sliders, entrées manuelles, nuit et sensibilité
    # Exemple : calcul peak, baseline, bruit, S/N classique et USP, etc.
    # ⚠️ Ici tu gardes exactement ton code original, inchangé

    return {}, None  # le vrai code S/N reste dans ton fichier original

def sn_module():
    st.title("📈 Calcul du rapport Signal / Bruit (S/N)")
    # 🔹 Code S/N original complet avec sliders, entrées manuelles, nuit et sensibilité
    # ⚠️ Laisse tout exactement comme dans ton code initial

# ===============================
# MODULE LINÉARITÉ
# ===============================

def linearity_module():
    st.title("📊 Analyse de linéarité")
    # 🔹 Code Linéarité original avec CSV et entrées manuelles
    # ⚠️ Laisse tout exactement comme dans ton code initial

# ===============================
# FEEDBACK / EMAIL
# ===============================

def send_email(subject, body, sender_email, sender_pass, receiver_email):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True
    except Exception:
        return False

def feedback_module():
    st.title("💬 Feedback utilisateur")
    # 🔹 Code feedback original
    # ⚠️ Laisse tout exactement comme dans ton code initial

# ===============================
# APPLICATION PRINCIPALE MULTI-ONGLETS
# ===============================

def main_app():
    if "user" not in st.session_state:
        login_page()
        return

    user = st.session_state["user"]
    role = st.session_state["role"]
    access = st.session_state["access"]

    st.title(f"👋 Bonjour, {user} !")
    tab = st.radio("Choisir un module :", ["Accueil", "Linéarité", "S/N", "Feedback", "Admin", "Déconnexion"])

    if tab == "Accueil":
        st.title("Bienvenue dans LabT")
        st.info("Choisissez un module.")

    elif tab == "Linéarité" and "linearity" in access:
        linearity_module()

    elif tab == "S/N" and "sn" in access:
        sn_module()

    elif tab == "Feedback":
        feedback_module()

    elif tab == "Admin" and role == "admin":
        admin_panel()

    elif tab == "Déconnexion":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.success("Déconnecté.")
        st.rerun()

def run():
    st.set_page_config(page_title="LabT", layout="wide")
    main_app()

# ===============================
# EXÉCUTION
# ===============================

if __name__ == "__main__":
    migrate_legacy_users_minimal()  # 🔹 Corrige users.json sans toucher le reste
    run()