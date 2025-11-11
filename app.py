# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime
from PIL import Image
from pdf2image import convert_from_bytes
import cv2
import matplotlib.pyplot as plt
import os

# ===============================
# TRADUCTIONS BILINGUE
# ===============================
TRANSLATIONS = {
    "FR": {
        "Language / Langue": "Langue",
        "Connexion": "Connexion",
        "Utilisateur": "Utilisateur",
        "Mot de passe": "Mot de passe",
        "Connexion réussie !": "Connexion réussie !",
        "Identifiants invalides.": "Identifiants invalides.",
        "Bienvenue dans LabT": "Bienvenue dans LabT",
        "Choisissez un module ci-dessus.": "Choisissez un module ci-dessus.",
        "Déconnecté": "Déconnecté",
        "Signal plat ou OCR invalide": "Signal plat ou OCR invalide",
        "Importer une image ou un PDF du chromatogramme": "Importer une image ou un PDF du chromatogramme",
        "Temps de rétention": "Temps de rétention",
        "S/N Classique": "S/N Classique",
        "S/N USP": "S/N USP",
        "Importer un fichier CSV": "Importer un fichier CSV",
        "Message ou commentaire": "Message ou commentaire"
    },
    "EN": {
        "Language / Langue": "Language",
        "Connexion": "Login",
        "Utilisateur": "User",
        "Mot de passe": "Password",
        "Connexion réussie !": "Login successful!",
        "Identifiants invalides.": "Invalid credentials.",
        "Bienvenue dans LabT": "Welcome to LabT",
        "Choisissez un module ci-dessus.": "Choose a module above.",
        "Déconnecté": "Logged out",
        "Signal plat ou OCR invalide": "Flat signal or invalid OCR",
        "Importer une image ou un PDF du chromatogramme": "Upload image or PDF of chromatogram",
        "Temps de rétention": "Retention time",
        "S/N Classique": "Classic S/N",
        "S/N USP": "USP S/N",
        "Importer un fichier CSV": "Upload CSV file",
        "Message ou commentaire": "Message or comment"
    }
}

# ===============================
# LANGUE PAR DÉFAUT
# ===============================
LANG = "FR"

def t(txt, lang=None):
    if lang is None:
        lang = LANG
    return TRANSLATIONS.get(lang, {}).get(txt, txt)

# ===============================
# USERS FILE
# ===============================
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    users = {
        "admin":{"password":"admin","role":"admin","access":["linearity","sn"]},
        "user":{"password":"user","role":"user","access":["linearity","sn"]}
    }
    with open(USERS_FILE,"w") as f:
        json.dump(users,f,indent=4)

def load_users():
    with open(USERS_FILE,"r") as f:
        return json.load(f)
def save_users(users):
    with open(USERS_FILE,"w") as f:
        json.dump(users,f,indent=4)

# ===============================
# LOGIN
# ===============================
def login_page():
    st.title(t("Connexion"))
    users = load_users()
    username = st.selectbox(t("Utilisateur"), list(users.keys()))
    password = st.text_input(t("Mot de passe"), type="password")
    if st.button(t("Connexion")):
        if username in users and users[username]["password"]==password:
            st.session_state["user"]=username
            st.session_state["role"]=users[username]["role"]
            st.session_state["access"]=users[username]["access"]
            st.success(t("Connexion réussie !"))
            st.session_state["page"]="menu"
            st.rerun()
        else:
            st.error(t("Identifiants invalides."))

# ===============================
# ADMIN PANEL
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
        st.session_state["page"]="menu"
        st.rerun()

# ===============================
# PDF -> IMAGE
# ===============================
def pdf_to_png_bytes(uploaded_file):
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1, dpi=300)
        if pages:
            return pages[0].convert("RGB"), None
    except:
        import fitz
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count<1: return None,"PDF vide."
        page = doc.load_page(0)
        mat = fitz.Matrix(2.0,2.0)
        pix = page.get_pixmap(matrix=mat,alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        return img,None

# ===============================
# S/N MODULE AVEC SLIDERS & CALCUL MANUEL
# ===============================
def analyze_sn_manual(image, zone_start, zone_end, sensitivity):
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    profile = np.mean(gray, axis=0)
    x = np.arange(len(profile))
    y = profile
    # Appliquer zone sélectionnée
    y_zone = y[zone_start:zone_end]
    x_zone = x[zone_start:zone_end]
    peak_idx = np.argmax(y_zone)
    peak_height = y_zone[peak_idx]
    baseline = np.median(y_zone)
    noise = np.std(y_zone[:max(1,len(y_zone)//10)])
    sn_classic = (peak_height-baseline)/(noise if noise!=0 else 1)
    sn_classic *= sensitivity
    sn_usp = sn_classic/np.sqrt(2)
    retention_time = x_zone[peak_idx]
    return {"S/N Classique":sn_classic,"S/N USP":sn_usp,"Peak Retention":retention_time}

def sn_module():
    st.title("📈 Calcul du rapport Signal / Bruit (S/N)")
    uploaded_file = st.file_uploader(t("Importer une image ou un PDF du chromatogramme"), type=["png","jpg","jpeg","pdf"])
    if uploaded_file:
        if uploaded_file.type=="application/pdf":
            img, err = pdf_to_png_bytes(uploaded_file)
            if err: st.error(err); return
        else: img = Image.open(uploaded_file).convert("RGB")
        st.image(img, caption="Chromatogramme original", use_container_width=True)
        # Sliders zone et sensibilité
        max_x = img.width
        zone = st.slider("Zone d'analyse",0,max_x,(0,max_x))
        sensitivity = st.slider("Sensibilité",0.1,5.0,1.0)
        res = analyze_sn_manual(img, zone[0], zone[1], sensitivity)
        st.markdown(f"**S/N Classique :** {res['S/N Classique']:.4f}")
        st.markdown(f"**S/N USP :** {res['S/N USP']:.4f}")
        st.markdown(f"**Temps de rétention :** {res['Peak Retention']:.0f}")

# ===============================
# LINÉARITÉ MODULE AVEC GRAPHIQUE & CONCENTRATION INCONNUE
# ===============================
def linearity_module():
    st.title("📊 Analyse de linéarité")
    uploaded_file = st.file_uploader(t("Importer un fichier CSV"), type=["csv"])
    if not uploaded_file: st.info("Veuillez importer un fichier CSV contenant vos données de calibration."); return
    df = pd.read_csv(uploaded_file)
    st.dataframe(df)
    if "Concentration" in df.columns and "Réponse" in df.columns:
        x,y = df["Concentration"],df["Réponse"]
        coeffs = np.polyfit(x,y,1)
        slope,intercept = coeffs
        r = np.corrcoef(x,y)[0,1]
        st.markdown(f"**y = {slope:.4f}x + {intercept:.4f}**")
        st.markdown(f"**R² = {r**2:.4f}**")
        # Graphique
        plt.figure(figsize=(6,4))
        plt.scatter(x,y,label="Données")
        plt.plot(x,slope*x+intercept,color="red",label="Régression")
        plt.xlabel("Concentration"); plt.ylabel("Réponse"); plt.legend(); plt.grid(True)
        st.pyplot(plt)
        # Calcul concentration inconnue
        unknown_signal = st.number_input("Entrer signal inconnu",value=0.0)
        if unknown_signal>0:
            conc_unknown = (unknown_signal-intercept)/slope
            st.markdown(f"**Concentration estimée :** {conc_unknown:.4f}")
    else: st.error("Le fichier doit contenir les colonnes 'Concentration' et 'Réponse'.")

# ===============================
# FEEDBACK SIMPLE
# ===============================
def feedback_module():
    st.title("💬 Feedback utilisateur")
    msg = st.text_area(t("Message ou commentaire"))
    if st.button("Envoyer"):
        if msg: st.success("Message enregistré ✅")
        else: st.warning("Veuillez remplir le message.")

# ===============================
# APPLICATION PRINCIPALE
# ===============================
LANG = st.selectbox("Language / Langue", ["FR","EN"], index=0)

def main_app():
    if "user" not in st.session_state: login_page(); return
    user = st.session_state["user"]
    role = st.session_state["role"]
    access = st.session_state["access"]

    st.title(f"👋 {user}")
    module = st.selectbox("Module", ["Accueil","Linéarité","S/N","Feedback","Admin","Déconnexion"])

    if module=="Accueil":
        st.title(t("Bienvenue dans LabT"))
        st.info(t("Choisissez un module ci-dessus."))
    elif module=="Linéarité" and "linearity" in access:
        linearity_module()
    elif module=="S/N" and "sn" in access:
        sn_module()
    elif module=="Feedback":
        feedback_module()
    elif module=="Admin" and role=="admin":
        admin_panel()
    elif module=="Déconnexion":
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.success(t("Déconnecté"))
        st.rerun()

def run():
    st.set_page_config(page_title="LabT", layout="wide")
    main_app()

if __name__=="__main__":
    run()