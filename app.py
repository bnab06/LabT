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
# 🔹 SWITCH DE LANGUE DYNAMIQUE
# ===============================
if "lang" not in st.session_state:
    st.session_state["lang"] = "FR"

def toggle_language():
    st.session_state["lang"] = "EN" if st.session_state["lang"] == "FR" else "FR"

st.button("🌐 EN/FR", on_click=toggle_language)

def t(txt_fr, txt_en=None):
    if st.session_state.get("lang", "FR") == "FR" or txt_en is None:
        return txt_fr
    return txt_en

# ===============================
# 🔹 USERS FILE & migration
# ===============================
USERS_FILE = "users.json"

def migrate_legacy_users_minimal():
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

    if "admin" not in users:
        users["admin"] = {"password": "admin", "role": "admin", "access": ["linearity", "sn"]}
        updated = True

    if updated:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)

# ===============================
# 🔹 OUTILS GÉNÉRAUX
# ===============================
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
            return None, t("PDF vide.", "Empty PDF.")
        page = doc.load_page(0)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        return img, None
    except Exception as e_fitz:
        return None, t(f"Erreur conversion PDF : {e_fitz}", f"PDF conversion error: {e_fitz}")

# ===============================
# 🔹 AUTHENTIFICATION
# ===============================
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}
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
    st.title(t("🔐 Connexion", "🔐 Login"))
    users = load_users()
    username = st.selectbox(t("Utilisateur", "User"), list(users.keys()))
    password = st.text_input(t("Mot de passe", "Password"), type="password")
    if st.button(t("Connexion", "Login")):
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = users[username].get("role", "user")
            st.session_state["access"] = users[username].get("access", ["linearity", "sn"])
            st.success(t("Connexion réussie !", "Login successful!"))
            st.session_state["page"] = "menu"
            st.rerun()
        else:
            st.error(t("Identifiants invalides.", "Invalid credentials."))

# ===============================
# 🔹 PAGE ADMIN
# ===============================
def admin_panel():
    st.subheader(t("👤 Gestion des utilisateurs", "👤 User Management"))
    users = load_users()
    action = st.selectbox(t("Action", "Action"), [
        t("Ajouter utilisateur", "Add User"),
        t("Modifier privilèges", "Edit Privileges"),
        t("Supprimer utilisateur", "Delete User")
    ])
    if action == t("Ajouter utilisateur", "Add User"):
        new_user = st.text_input(t("Nom d'utilisateur", "Username"))
        new_pass = st.text_input(t("Mot de passe", "Password"))
        privileges = st.multiselect(t("Modules", "Modules"), ["linearity", "sn"])
        if st.button(t("Créer", "Create")):
            if new_user and new_pass:
                users[new_user] = {"password": new_pass, "role": "user", "access": privileges or ["linearity","sn"]}
                save_users(users)
                st.success(t(f"Utilisateur '{new_user}' ajouté.", f"User '{new_user}' added."))
            else:
                st.error(t("Remplir tous les champs.", "Fill all fields."))
    elif action == t("Modifier privilèges", "Edit Privileges"):
        user_to_edit = st.selectbox(t("Utilisateur", "User"), [u for u in users if users[u]["role"] != "admin"])
        if user_to_edit:
            new_priv = st.multiselect(t("Modules", "Modules"), ["linearity", "sn"], default=users[user_to_edit].get("access", ["linearity","sn"]))
            if st.button(t("Sauvegarder", "Save")):
                users[user_to_edit]["access"] = new_priv
                save_users(users)
                st.success(t("Modifications enregistrées.", "Changes saved."))
    elif action == t("Supprimer utilisateur", "Delete User"):
        user_to_del = st.selectbox(t("Utilisateur à supprimer", "User to delete"), [u for u in users if users[u]["role"] != "admin"])
        if st.button(t("Supprimer", "Delete")):
            users.pop(user_to_del)
            save_users(users)
            st.warning(t(f"Utilisateur {user_to_del} supprimé.", f"User {user_to_del} deleted."))
    if st.button(t("⬅️ Retour au menu principal", "⬅️ Back to main menu")):
        st.session_state["page"] = "menu"
        st.rerun()

# ===============================
# 🔹 MODULE S/N
# ===============================
def sn_module():
    st.title(t("📈 Calcul du rapport Signal / Bruit (S/N)", "📈 Signal / Noise ratio"))
    uploaded_file = st.file_uploader(t("Importer une image ou un PDF du chromatogramme", "Upload chromatogram image or PDF"), type=["png","jpg","jpeg","pdf"])
    if not uploaded_file:
        st.info(t("Veuillez importer un fichier.", "Please upload a file."))
        return
    if uploaded_file.type == "application/pdf":
        img, err = pdf_to_png_bytes(uploaded_file)
        if err:
            st.error(err)
            return
    else:
        img = Image.open(uploaded_file).convert("RGB")
    st.image(img, caption=t("Chromatogramme original", "Original chromatogram"), use_container_width=True)

    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    profile = np.mean(gray, axis=0)
    x = np.arange(len(profile))
    y = profile

    st.subheader(t("Zone du bruit et du pic", "Noise and peak region"))
    start_idx = st.slider(t("Début de la zone à analyser", "Start index of region"), 0, len(x)-2, 0)
    end_idx = st.slider(t("Fin de la zone à analyser", "End index of region"), 1, len(x)-1, len(x)-1)
    if start_idx >= end_idx:
        st.warning(t("La zone est invalide.", "Invalid region."))
        return
    y_region = y[start_idx:end_idx]
    x_region = x[start_idx:end_idx]

    peak_idx_rel = np.argmax(y_region)
    peak_height = y_region[peak_idx_rel]
    peak_retention = x_region[peak_idx_rel]

    noise = np.std(y_region[:max(1,len(y_region)//10)])
    baseline = np.median(y_region)
    sn_classic = (peak_height - baseline)/(noise if noise!=0 else 1)
    sn_usp = sn_classic / np.sqrt(2)

    st.markdown(f"**{t('S/N Classique','S/N Classic')} :** {sn_classic:.4f}")
    st.markdown(f"**{t('S/N USP','USP S/N')} :** {sn_usp:.4f}")
    st.markdown(f"**{t('Temps de rétention','Peak Retention')} :** {peak_retention:.4f}")

# ===============================
# 🔹 MODULE LINÉARITÉ
# ===============================
def linearity_module():
    st.title(t("📊 Analyse de linéarité", "📊 Linearity Analysis"))
    mode = st.radio(t("Mode de saisie", "Input mode"), [t("Importer CSV","CSV Upload"), t("Entrée manuelle","Manual Entry")])
    if mode == t("Importer CSV","CSV Upload"):
        uploaded_file = st.file_uploader(t("Importer un fichier CSV", "Upload CSV file"), type=["csv"])
        if not uploaded_file:
            st.info(t("Veuillez importer un fichier CSV contenant vos données de calibration.", "Please upload a CSV file with calibration data."))
            return
        df = pd.read_csv(uploaded_file)
    else:
        st.info(t("Saisissez vos données de calibration", "Enter your calibration data"))
        n_points = st.number_input(t("Nombre de points", "Number of points"), min_value=2, max_value=50, value=5, step=1)
        conc_list = []
        resp_list = []
        for i in range(int(n_points)):
            col1, col2 = st.columns(2)
            conc = col1.number_input(f"{t('Concentration','Concentration')} {i+1}", value=0.0)
            resp = col2.number_input(f"{t('Réponse','Response')} {i+1}", value=0.0)
            conc_list.append(conc)
            resp_list.append(resp)
        df = pd.DataFrame({"Concentration": conc_list, "Réponse": resp_list})

    st.dataframe(df)
    if "Concentration" in df.columns and "Réponse" in df.columns:
        x, y = df["Concentration"], df["Réponse"]
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs
        r = np.corrcoef(x, y)[0,1]
        st.markdown(f"**y = {slope:.4f}x + {intercept:.4f}**")
        st.markdown(f"**R² = {r**2:.4f}**")
    else:
        st.error(t("Le fichier doit contenir les colonnes 'Concentration' et 'Réponse'.", "CSV must contain 'Concentration' and 'Response' columns."))

# ===============================
# 🔹 MODULE FEEDBACK
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
    st.title(t("💬 Feedback utilisateur", "💬 User Feedback"))
    email = st.text_input(t("Votre adresse email", "Your email"))
    msg = st.text_area(t("Message ou commentaire", "Message or comment"))
    if st.button(t("Envoyer", "Send")):
        if email and msg:
            ok = send_email(
                "Feedback LabT",
                f"De: {email}\n\n{msg}",
                "labtchem6@gmail.com",
                "motdepasse_app",
                "labtchem6@gmail.com"
            )
            if ok:
                st.success(t("Message envoyé avec succès ✅", "Message sent successfully ✅"))
            else:
                st.error(t("Échec d'envoi.", "Sending failed."))
        else:
            st.warning(t("Veuillez remplir les champs.", "Please fill in all fields."))

# ===============================
# 🔹 APPLICATION PRINCIPALE
# ===============================
def main_app():
    if "user" not in st.session_state:
        login_page()
        return
    user = st.session_state["user"]
    role = st.session_state["role"]
    access = st.session_state["access"]
    st.title(t(f"👋 Bonjour, {user} !", f"👋 Hello, {user}!"))
    module = st.radio(t("Module", "Module"), [
        t("Accueil","Home"),
        t("Linéarité","Linearity"),
        t("S/N","S/N"),
        t("Feedback","Feedback"),
        t("Admin","Admin"),
        t("Déconnexion","Logout")
    ])
    if module == t("Accueil","Home"):
        st.title(t("Bienvenue dans LabT", "Welcome to LabT"))
        st.info(t("Choisissez un module.", "Select a module."))
    elif module == t("Linéarité","Linearity") and "linearity" in access:
        linearity_module()
    elif module == t("S/N","S/N") and "sn" in access:
        sn_module()
    elif module == t("Feedback","Feedback"):
        feedback_module()
    elif module == t("Admin","Admin") and role == "admin":
        admin_panel()
    elif module == t("Déconnexion","Logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.success(t("Déconnecté.", "Logged out."))
        st.rerun()

def run():
    st.set_page_config(page_title="LabT", layout="wide")
    migrate_legacy_users_minimal()
    main_app()

if __name__ == "__main__":
    run()