# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
import os
from datetime import datetime
from PIL import Image, ImageDraw
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression
from fpdf import FPDF

# ===============================
# Initialisation session
# ===============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "access" not in st.session_state:
    st.session_state.access = []
if "lin_slope" not in st.session_state:
    st.session_state.lin_slope = None
if "lin_intercept" not in st.session_state:
    st.session_state.lin_intercept = None
if "sn_result" not in st.session_state:
    st.session_state.sn_result = {}
if "sn_img_annot" not in st.session_state:
    st.session_state.sn_img_annot = None
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
        "linear_title": "📈 Linéarité",
        "sn_title": "📊 Rapport Signal/Bruit (S/N)",
        "download_pdf": "📄 Télécharger le PDF complet",
        "download_pdf_simple": "📄 Télécharger PDF",
        "lod_label": "**LOD**",
        "loq_label": "**LOQ**",
        "change_pass": "Changer le mot de passe",
        "new_pass": "Nouveau mot de passe",
        "save_pass": "Enregistrer"
    },
    "EN": {
        "app_title": "🔬 LabT — Login",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "login_error": "Incorrect username or password.",
        "powered_by": "Powered by : BnB",
        "linear_title": "📈 Linearity",
        "sn_title": "📊 Signal-to-Noise Report (S/N)",
        "download_pdf": "📄 Download full PDF",
        "download_pdf_simple": "📄 Download PDF",
        "lod_label": "**LOD**",
        "loq_label": "**LOQ**",
        "change_pass": "Change Password",
        "new_pass": "New Password",
        "save_pass": "Save"
    }
}

# ===============================
# Données utilisateurs
# ===============================
USER_FILE = "users.json"
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump({
            "admin": {"password": "admin", "access": ["admin"]},
            "user": {"password": "user", "access": ["linearity", "sn"]},
        }, f, indent=2)

with open(USER_FILE, "r") as f:
    users = json.load(f)

def save_users(users_dict):
    with open(USER_FILE, "w") as f:
        json.dump(users_dict, f, indent=2)

# ===============================
# Authentification
# ===============================
def login_page():
    lang = st.session_state.lang
    texts = TEXTS[lang]
    st.title(texts["app_title"])

    chosen = st.selectbox("Lang / Language", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1)
    st.session_state.lang = chosen
    texts = TEXTS[st.session_state.lang]

    username = st.text_input(texts["username"])
    password = st.text_input(texts["password"], type="password")
    if st.button(texts["login_btn"]):
        user = username.lower().strip()
        if user in users and users[user]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.access = users[user].get("access", [])
            st.rerun()
        else:
            st.error(texts["login_error"])

    st.markdown(f"""
    <style>
    .footer {{
        position: relative;
        left:0;
        bottom:0;
        width:100%;
        text-align:center;
        color:#6c757d;
        font-size:12px;
        font-style:italic;
        margin-top:40px;
    }}
    </style>
    <div class="footer">{texts['powered_by']}</div>
    """, unsafe_allow_html=True)

# ===============================
# Changement mot de passe
# ===============================
def change_password():
    texts = TEXTS[st.session_state.lang]
    st.subheader(texts["change_pass"])
    new_pass = st.text_input(texts["new_pass"], type="password")
    if st.button(texts["save_pass"]):
        users[st.session_state.user]["password"] = new_pass
        save_users(users)
        st.success("Mot de passe mis à jour !" if st.session_state.lang=="FR" else "Password updated!")

# ===============================
# Module Linéarité
# ===============================
def linearity_module():
    texts = TEXTS[st.session_state.lang]
    st.subheader(texts["linear_title"])
    mode = st.radio("Mode / Mode", ["CSV", "Saisie manuelle"])
    slope, intercept = None, None

    if mode=="CSV":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            x = df.iloc[:,0].values.reshape(-1,1)
            y = df.iloc[:,1].values
            reg = LinearRegression().fit(x,y)
            slope = reg.coef_[0]
            intercept = reg.intercept_
            st.session_state.lin_slope = slope
            st.session_state.lin_intercept = intercept
            st.write(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}")

    if mode=="Saisie manuelle":
        conc_input = st.text_input("Concentrations (séparées par des virgules)")
        sig_input = st.text_input("Signal (séparé par des virgules)")
        if st.button("Calculer Linéarité"):
            try:
                x = np.array([float(v) for v in conc_input.split(",")]).reshape(-1,1)
                y = np.array([float(v) for v in sig_input.split(",")])
                reg = LinearRegression().fit(x,y)
                slope = reg.coef_[0]
                intercept = reg.intercept_
                st.session_state.lin_slope = slope
                st.session_state.lin_intercept = intercept
                st.success(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}")
            except:
                st.error("Erreur dans les valeurs saisies")

# ===============================
# Module S/N
# ===============================
def sn_module():
    texts = TEXTS[st.session_state.lang]
    st.subheader(texts["sn_title"])
    unit = st.selectbox("Unité de concentration", ["µg/mL","mg/mL","ng/mL"], index=0)

    # --- Image upload pour S/N ---
    uploaded_file = st.file_uploader("Upload chromatogram image", type=["png","jpg","jpeg","tif"])
    if uploaded_file:
        img = Image.open(uploaded_file)
        img_gray = img.convert("L")
        arr = np.array(img_gray)
        y_signal = arr.max(axis=0)
        # Sélection zone
        start = st.number_input("Start pixel", 0, int(len(y_signal)-1), 0)
        end = st.number_input("End pixel", 0, int(len(y_signal)-1), len(y_signal)-1)
        zone_signal = y_signal[start:end+1]
        peaks,_ = find_peaks(zone_signal)
        if len(peaks)>0:
            peak_idx = peaks[np.argmax(zone_signal[peaks])]
            global_peak = start + peak_idx
            draw = ImageDraw.Draw(img)
            draw.ellipse((global_peak-5, arr[:,global_peak].max()-5, global_peak+5, arr[:,global_peak].max()+5), fill="red")
            draw.text((global_peak+5, arr[:,global_peak].max()-15), f"{global_peak} px", fill="red")
            st.image(img, caption="Pic annoté")
            st.session_state.sn_img_annot = img
            # calcul S/N classique
            signal = zone_signal[peak_idx]
            noise = np.std(np.concatenate([zone_signal[:peak_idx], zone_signal[peak_idx+1:]]))
            st.session_state.sn_result = {"signal":signal,"noise":noise,"sn":signal/noise if noise>0 else None}
            # LOD/LOQ
            slope = st.session_state.lin_slope if st.session_state.lin_slope else 1
            lod_s = 3.3*noise
            loq_s = 10*noise
            lod_c = lod_s/slope
            loq_c = loq_s/slope
            st.session_state.sn_result.update({"lod_s":lod_s,"loq_s":loq_s,"lod_c":lod_c,"loq_c":loq_c})

    # --- Calcul manuel S/N ---
    st.markdown("---")
    st.subheader("Calcul manuel S/N")
    H = st.number_input("Hauteur pic H", value=0.0)
    h = st.number_input("Bruit h", value=0.0)
    if st.button("Calculer S/N manuel"):
        if h>0:
            sn_manual = H/h
            st.success(f"S/N manuel = {sn_manual:.2f}")
        else:
            st.error("Erreur: h doit être >0")

# ===============================
# PDF export
# ===============================
def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,"LabT Report",ln=True)
    # Linéarité
    pdf.set_font("Arial","",12)
    slope = st.session_state.lin_slope
    intercept = st.session_state.lin_intercept
    if slope:
        pdf.cell(0,8,f"Slope: {slope:.4f}, Intercept: {intercept:.4f}",ln=True)
    # S/N
    sn_res = st.session_state.sn_result
    if sn_res:
        pdf.cell(0,8,f"S/N: {sn_res.get('sn',None):.2f}",ln=True)
        pdf.cell(0,8,f"LOD signal: {sn_res.get('lod_s',None):.2f}",ln=True)
        pdf.cell(0,8,f"LOQ signal: {sn_res.get('loq_s',None):.2f}",ln=True)
        pdf.cell(0,8,f"LOD concentration: {sn_res.get('lod_c',None):.2f}",ln=True)
        pdf.cell(0,8,f"LOQ concentration: {sn_res.get('loq_c',None):.2f}",ln=True)
    # Image annotée
    if st.session_state.sn_img_annot:
        buf = io.BytesIO()
        st.session_state.sn_img_annot.save(buf, format="PNG")
        buf.seek(0)
        pdf.image(buf, x=10, w=180)
    # Sauvegarde
    pdf_file = f"LabT_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(pdf_file)
    st.success(f"PDF généré: {pdf_file}")

# ===============================
# Topbar et Main App
# ===============================
def main_app():
    texts = TEXTS[st.session_state.lang]
    st.title("LabT Main App")
    if "admin" in st.session_state.access:
        st.subheader("Admin - Gestion utilisateurs")
        # Ajout / suppression / privilèges
        user_to_add = st.text_input("Nouvel utilisateur")
        pass_to_add = st.text_input("Mot de passe", type="password")
        add_btn = st.button("Ajouter utilisateur")
        if add_btn and user_to_add and pass_to_add:
            users[user_to_add] = {"password": pass_to_add, "access":[]}
            save_users(users)
            st.success("Utilisateur ajouté")
        # Liste des utilisateurs
        for u in users:
            st.write(f"{u} - accès: {users[u].get('access',[])}")
            if u!="admin":
                if st.button(f"Supprimer {u}"):
                    del users[u]
                    save_users(users)
                    st.experimental_rerun()
    else:
        change_password()
        linearity_module()
        sn_module()
        if st.button(texts["download_pdf"]):
            generate_pdf()

# ===============================
# Lancement
# ===============================
def run():
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__=="__main__":
    run()