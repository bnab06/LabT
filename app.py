# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import cv2
import io
import json
import os
from datetime import datetime
from PIL import Image
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile

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
def save_users(users_dict):
    with open(USER_FILE, "w") as f:
        json.dump(users_dict, f, indent=2)

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
    st.title("🔬 LabT — Connexion")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        user = username.lower().strip()
        if user in users and users[user]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.access = users[user]["access"]
            st.experimental_rerun()
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect.")

def change_password():
    st.subheader("🔑 Modifier le mot de passe")
    old = st.text_input("Mot de passe actuel", type="password")
    new = st.text_input("Nouveau mot de passe", type="password")
    if st.button("Mettre à jour"):
        u = st.session_state.user
        if users[u]["password"] == old:
            users[u]["password"] = new
            save_users(users)
            st.success("Mot de passe mis à jour ✅")
        else:
            st.error("Mot de passe actuel incorrect.")

# ===============================
# Module Linéarité
# ===============================
def linearity_module():
    st.header("📈 Linéarité")
    st.write("Entrer les données manuellement :")

    conc_str = st.text_area("Concentrations (séparées par des virgules)")
    signal_str = st.text_area("Signaux (séparés par des virgules)")
    unit = st.selectbox("Unité de concentration", ["µg/mL", "mg/mL", "ng/mL"], index=0)

    slope = None
    intercept = None
    if st.button("Tracer la droite"):
        try:
            x = np.array([float(i) for i in conc_str.split(",")])
            y = np.array([float(i) for i in signal_str.split(",")])
            if len(x) != len(y):
                st.error("Les deux listes doivent avoir la même longueur.")
            else:
                model = LinearRegression().fit(x.reshape(-1, 1), y)
                slope = model.coef_[0]
                intercept = model.intercept_
                st.session_state.slope_lin = slope
                st.success(f"Pente : {slope:.4f}")
                st.write(f"Équation : y = {slope:.4f}x + {intercept:.4f}")

                fig, ax = plt.subplots()
                ax.scatter(x, y, color="blue")
                ax.plot(x, model.predict(x.reshape(-1, 1)), color="red")
                ax.set_xlabel(f"Concentration ({unit})")
                ax.set_ylabel("Signal")
                st.pyplot(fig)

                # Stocker figure pour PDF avancé
                st.session_state.lin_fig = fig
        except Exception as e:
            st.error(f"Erreur : {e}")
    return slope, intercept

# ===============================
# Module S/N
# ===============================
def analyze_sn(img):
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    signal = np.mean(gray, axis=0)
    peaks, _ = find_peaks(signal, height=np.max(signal)*0.5)
    if len(peaks) == 0:
        return None, "Aucun pic détecté."
    peak_idx = peaks[np.argmax(signal[peaks])]
    noise = np.std(signal)
    height = signal[peak_idx]
    sn = height / noise if noise != 0 else None
    return {"Peak Retention": peak_idx, "S/N": sn, "Noise": noise}, None

def sn_module():
    st.header("📊 Rapport Signal/Bruit (S/N)")
    uploaded_file = st.file_uploader("Téléverser chromatogramme (PNG ou PDF)", type=["png", "pdf"])

    if uploaded_file:
        img = Image.open(uploaded_file).convert("RGB")
        res, err = analyze_sn(img)
        if err:
            st.error(err)
        else:
            st.success(f"S/N automatique : {res['S/N']:.2f}")

            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            h_img, w_img = cv_img.shape[:2]
            peak_idx = res["Peak Retention"]
            x_pos = int(peak_idx * w_img / len(np.mean(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), axis=0)))
            y_pos = int(h_img * 0.3)

            cv2.circle(cv_img, (x_pos, y_pos), 8, (0, 0, 255), -1)
            retention_time_min = peak_idx / 100
            cv2.putText(cv_img, f"{retention_time_min:.2f} min", (x_pos + 10, y_pos - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            st.image(Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)),
                     caption="Chromatogramme avec pic marqué", use_column_width=True)

            slope = st.session_state.slope_lin
            lod_s, loq_s, lod_c, loq_c = calculate_lod_loq(slope, res["Noise"])
            unit = st.selectbox("Unité de concentration", ["µg/mL", "mg/mL", "ng/mL"], index=0)
            st.markdown(f"**LOD** : {lod_s:.2f} (signal) | {lod_c:.4f} {unit}")
            st.markdown(f"**LOQ** : {loq_s:.2f} (signal) | {loq_c:.4f} {unit}")

            # Stocker résultats et image pour PDF avancé
            st.session_state.sn_result = res
            st.session_state.lod_s = lod_s
            st.session_state.loq_s = loq_s
            st.session_state.lod_c = lod_c
            st.session_state.loq_c = loq_c
            st.session_state.sn_img_annot = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

    if st.button("🧮 Calcul manuel S/N"):
        st.markdown("### Entrée manuelle")
        H = st.number_input("Hauteur du pic (H)")
        h = st.number_input("Bruit (h)")
        if h > 0:
            sn_classique = H / h
            st.success(f"S/N classique = {sn_classique:.2f}")
            # Stocker S/N manuel pour PDF
            st.session_state.sn_manual = sn_classique
        else:
            st.warning("Entrer un bruit > 0.")

# ===============================
# Topbar et interface
# ===============================
def topbar():
    st.markdown(f"""
        <style>
        .topbar {{
            background-color: #002B5B;
            color: white;
            padding: 10px 20px;
            font-size: 20px;
            font-weight: 600;
            border-radius: 0px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .username {{
            font-size: 14px;
            font-weight: 400;
        }}
        </style>
        <div class="topbar">
            <div>🧪 LabT — Analytical Suite</div>
            <div class="username">👤 Utilisateur : {st.session_state.user}</div>
        </div>
    """, unsafe_allow_html=True)

def main_app():
    topbar()
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Aller à :", ["Linéarité", "S/N", "Mot de passe", "Déconnexion"])
    if page == "Linéarité":
        linearity_module()
    elif page == "S/N":
        sn_module()
    elif page == "Mot de passe":
        change_password()
    elif page == "Déconnexion":
        st.session_state.logged_in = False
        st.experimental_rerun()

# ===============================
# PDF avancé complet
# ===============================
def generate_pdf_report_full(results, lin_fig=None, sn_img=None, filename="rapport_LabT.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Rapport LabT", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)
    if "user" in st.session_state:
        pdf.cell(0, 8, f"Utilisateur : {st.session_state.user}", ln=True)
        pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "Résultats :", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.ln(2)
    for key, value in results.items():
        pdf.cell(0, 8, f"{key} : {value}", ln=True)
    pdf.ln(5)
    # Graphique Linéarité
    if lin_fig:
        tmpfile = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        lin_fig.savefig(tmpfile.name, bbox_inches="tight")
        pdf.image(tmpfile.name, w=180)
        tmpfile.close()
        pdf.ln(5)
    # Chromatogramme annoté
    if sn_img:
        tmpfile = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        sn_img.save(tmpfile.name)
        pdf.image(tmpfile.name, w=180)
        tmpfile.close()
        pdf.ln(5)
    pdf.output(filename)
    return filename

# Affichage du bouton PDF complet
if st.session_state.logged_in:
    results_pdf = {}
    if st.session_state.slope_lin is not None:
        results_pdf["Pente (Linéarité)"] = f"{st.session_state.slope_lin:.4f}"
    if "sn_result" in st.session_state:
        sn_res = st.session_state.sn_result
        results_pdf["S/N automatique"] = f"{sn_res.get('S/N', 'N/A'):.2f}" if sn_res.get("S/N") else "N/A"
        results_pdf["Peak Retention"] = sn_res.get("Peak Retention", "N/A")
        results_pdf["Noise"] = f"{sn_res.get('Noise', 0):.2f}"
        if "lod_s" in st.session_state and "lod_c" in st.session_state:
            results_pdf["LOD (signal)"] = f"{st.session_state.lod_s:.2f}"
            results_pdf["LOQ (signal)"] = f"{st.session_state.loq_s:.2f}"
            results_pdf["LOD (concentration)"] = f"{st.session_state.lod_c:.4f}"
            results_pdf["LOQ (concentration)"] = f"{st.session_state.loq_c:.4f}"
    if "sn_manual" in st.session_state:
        results_pdf["S/N manuel"] = f"{st.session_state.sn_manual:.2f}"

    if results_pdf:
        if st.button("📄 Télécharger PDF complet avec graphiques"):
            pdf_file = generate_pdf_report_full(
                results_pdf,
                lin_fig=st.session_state.get("lin_fig"),
                sn_img=st.session_state.get("sn_img_annot")
            )
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="Télécharger le PDF",
                    data=f,
                    file_name=pdf_file,
                    mime="application/pdf"
                )

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