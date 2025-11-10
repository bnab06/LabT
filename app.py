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
#          OUTILS GÉNÉRAUX
# ===============================

def t(txt):
    return txt  # (future version bilingue)

# --- Conversion PDF → Image (auto) ---
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
#          AUTHENTIFICATION
# ===============================

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "admin": {"password": "admin", "role": "admin", "access": ["linearity", "sn"]},
            "user": {"password": "user", "role": "user", "access": ["linearity", "sn"]}
        }

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
            st.session_state["role"] = users[username]["role"]
            st.session_state["access"] = users[username]["access"]
            st.success("Connexion réussie !")
            st.session_state["page"] = "menu"
            st.rerun()
        else:
            st.error("Identifiants invalides.")

# ===============================
#          PAGE ADMIN
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
                users[new_user] = {"password": new_pass, "role": "user", "access": privileges}
                save_users(users)
                st.success(f"Utilisateur '{new_user}' ajouté.")
            else:
                st.error("Remplir tous les champs.")

    elif action == "Modifier privilèges":
        user_to_edit = st.selectbox("Utilisateur", [u for u in users if users[u]["role"] != "admin"])
        if user_to_edit:
            new_priv = st.multiselect("Modules", ["linearity", "sn"], default=users[user_to_edit]["access"])
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
#      DÉTECTION + CALCUL S/N
# ===============================

def analyze_sn(image):
    """Analyse S/N sur image (non modifiée, OCR automatique ou graphique)."""
    try:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    except Exception:
        return None, "Erreur: image invalide."

    # Extraction du profil horizontal (somme verticale)
    profile = np.mean(gray, axis=0)
    x = np.arange(len(profile))
    y = profile

    if len(np.unique(x)) <= 1:
        return None, "Signal plat ou OCR invalide : axe X artificiel utilisé."

    # Recherche du pic principal (max Y)
    peak_idx = np.argmax(y)
    peak_height = y[peak_idx]
    retention_time = x[peak_idx]

    # Estimation du bruit (partie basse du signal)
    baseline = np.median(y)
    noise = np.std(y[:len(y)//10]) if len(y) > 10 else 1

    sn_classic = (peak_height - baseline) / (noise if noise != 0 else 1)
    sn_usp = sn_classic / np.sqrt(2)

    return {
        "S/N Classique": sn_classic,
        "S/N USP": sn_usp,
        "Peak Retention (X)": retention_time
    }, None

def sn_module():
    st.title("📈 Calcul du rapport Signal / Bruit (S/N)")

    uploaded_file = st.file_uploader("Importer une image ou un PDF du chromatogramme", type=["png", "jpg", "jpeg", "pdf"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            img, err = pdf_to_png_bytes(uploaded_file)
            if err:
                st.error(err)
                return
        else:
            img = Image.open(uploaded_file).convert("RGB")

        st.image(img, caption="Chromatogramme original", use_container_width=True)

        res, err = analyze_sn(img)
        if err:
            st.warning(err)
        elif res:
            st.markdown(f"**S/N Classique :** {res['S/N Classique']:.4f}")
            st.markdown(f"**S/N USP :** {res['S/N USP']:.4f}")
            st.markdown(f"**Temps de rétention :** {res['Peak Retention (X)']:.4f}")

# ===============================
#         MODULE LINÉARITÉ
# ===============================

def linearity_module():
    st.title("📊 Analyse de linéarité")

    uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])
    if not uploaded_file:
        st.info("Veuillez importer un fichier CSV contenant vos données de calibration.")
        return

    df = pd.read_csv(uploaded_file)
    st.dataframe(df)

    if "Concentration" in df.columns and "Réponse" in df.columns:
        x, y = df["Concentration"], df["Réponse"]
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs
        r = np.corrcoef(x, y)[0, 1]
        st.markdown(f"**y = {slope:.4f}x + {intercept:.4f}**")
        st.markdown(f"**R² = {r**2:.4f}**")
    else:
        st.error("Le fichier doit contenir les colonnes 'Concentration' et 'Réponse'.")

# ===============================
#      FEEDBACK + EMAIL
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
    except Exception as e:
        return False

def feedback_module():
    st.title("💬 Feedback utilisateur")
    email = st.text_input("Votre adresse email")
    msg = st.text_area("Message ou commentaire")

    if st.button("Envoyer"):
        if email and msg:
            ok = send_email(
                "Feedback LabT",
                f"De: {email}\n\n{msg}",
                "labtchem6@gmail.com",  # expéditeur
                "motdepasse_app",       # mot de passe d'application Gmail
                "labtchem6@gmail.com"   # destinataire
            )
            if ok:
                st.success("Message envoyé avec succès ✅")
            else:
                st.error("Échec d'envoi.")
        else:
            st.warning("Veuillez remplir les champs.")

# ===============================
#           APPLICATION
# ===============================

def main_app():
    if "user" not in st.session_state:
        login_page()
        return

    user = st.session_state["user"]
    role = st.session_state["role"]
    access = st.session_state["access"]

    st.sidebar.title(f"👋 Bonjour, {user} !")
    module = st.sidebar.selectbox("Module", ["Accueil", "Linéarité", "S/N", "Feedback", "Admin", "Déconnexion"])

    if module == "Accueil":
        st.title("Bienvenue dans LabT")
        st.info("Choisissez un module dans le menu à gauche.")

    elif module == "Linéarité" and "linearity" in access:
        linearity_module()

    elif module == "S/N" and "sn" in access:
        sn_module()

    elif module == "Feedback":
        feedback_module()

    elif module == "Admin" and role == "admin":
        admin_panel()

    elif module == "Déconnexion":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.success("Déconnecté.")
        st.rerun()

def run():
    st.set_page_config(page_title="LabT", layout="wide")
    main_app()

if __name__ == "__main__":
    run()