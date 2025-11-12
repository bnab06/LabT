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
# default language: FR (will be selectable on login page)
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

# ===============================
# Textes bilingues (FR / EN technical-neutral)
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
        "download_pdf": "📄 Télécharger le PDF complet avec graphiques",
        "download_pdf_simple": "📄 Télécharger le PDF",
        "lod_label": "**LOD**",
        "loq_label": "**LOQ**"
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
        "download_pdf": "📄 Download full PDF with graphics",
        "download_pdf_simple": "📄 Download PDF",
        "lod_label": "**LOD**",
        "loq_label": "**LOQ**"
    }
}

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
    lang = st.session_state.lang
    texts = TEXTS[lang]
    st.title(texts["app_title"])

    # Sélecteur de langue sur la page de connexion uniquement
    chosen = st.selectbox("Lang / Language", options=["FR", "EN"], index=0 if st.session_state.lang == "FR" else 1)
    st.session_state.lang = chosen
    texts = TEXTS[st.session_state.lang]

    username = st.text_input(texts["username"])
    password = st.text_input(texts["password"], type="password")
    if st.button(texts["login_btn"]):
        user = username.lower().strip()
        # garde la logique d'origine : on vérifie l'utilisateur comme avant
        if user in users and users[user]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = user
            # protection minimale contre KeyError tout en gardant le comportement
            if isinstance(users.get(user), dict) and "access" in users.get(user, {}):
                st.session_state.access = users[user]["access"]
            else:
                st.session_state.access = []
            st.experimental_rerun()
        else:
            st.error(texts["login_error"])

    # Pied de page stylisé "Powered by : BnB"
    st.markdown(
        f"""
        <style>
        .footer {{
            position: relative;
            left: 0;
            bottom: 0;
            width: 100%;
            text-align: center;
            color: #6c757d;
            font-size:12px;
            font-style: italic;
            margin-top: 40px;
        }}
        </style>
        <div class="footer">{texts["powered_by"]}</div>
        """,
        unsafe_allow_html=True,
    )

def change_password():
    # Utilise les mêmes libellés selon la langue courante
    texts = TEXTS[st.session_state.lang]
    st.subheader("🔑 " + ("Modifier le mot de passe" if st.session_state.lang == "FR" else "Change password"))
    old = st.text_input("Mot de passe actuel" if st.session_state.lang == "FR" else "Current password", type="password")
    new = st.text_input("Nouveau mot de passe" if st.session_state.lang == "FR" else "New password", type="password")
    if st.button("Mettre à jour" if st.session_state.lang == "FR" else "Update"):
        u = st.session_state.user
        if users[u]["password"] == old:
            users[u]["password"] = new
            save_users(users)
            st.success("Mot de passe mis à jour ✅" if st.session_state.lang == "FR" else "Password updated ✅")
        else:
            st.error("Mot de passe actuel incorrect." if st.session_state.lang == "FR" else "Current password incorrect.")

# ===============================
# Module Linéarité
# ===============================
def linearity_module():
    texts = TEXTS[st.session_state.lang]
    st.header(texts["linear_title"])
    st.write("Entrer les données manuellement :" if st.session_state.lang == "FR" else "Enter data manually:")

    conc_str = st.text_area("Concentrations (séparées par des virgules)" if st.session_state.lang == "FR" else "Concentrations (comma separated)")
    signal_str = st.text_area("Signaux (séparés par des virgules)" if st.session_state.lang == "FR" else "Signals (comma separated)")
    unit = st.selectbox("Unité de concentration" if st.session_state.lang == "FR" else "Concentration unit", ["µg/mL", "mg/mL", "ng/mL"], index=0)

    slope = None
    intercept = None
    if st.button("Tracer la droite" if st.session_state.lang == "FR" else "Plot line"):
        try:
            x = np.array([float(i) for i in conc_str.split(",")])
            y = np.array([float(i) for i in signal_str.split(",")])
            if len(x) != len(y):
                st.error("Les deux listes doivent avoir la même longueur." if st.session_state.lang == "FR" else "Both lists must have the same length.")
            else:
                model = LinearRegression().fit(x.reshape(-1, 1), y)
                slope = model.coef_[0]
                intercept = model.intercept_
                st.session_state.slope_lin = slope
                st.success(f"Pente : {slope:.4f}" if st.session_state.lang == "FR" else f"Slope : {slope:.4f}")
                st.write(f"Équation : y = {slope:.4f}x + {intercept:.4f}" if st.session_state.lang == "FR" else f"Equation: y = {slope:.4f}x + {intercept:.4f}")

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
        return None, ("Aucun pic détecté." if st.session_state.lang == "FR" else "No peak detected.")
    peak_idx = peaks[np.argmax(signal[peaks])]
    noise = np.std(signal)
    height = signal[peak_idx]
    sn = height / noise if noise != 0 else None
    return {"Peak Retention": peak_idx, "S/N": sn, "Noise": noise}, None

def sn_module():
    texts = TEXTS[st.session_state.lang]
    st.header(texts["sn_title"])
    uploaded_file = st.file_uploader("Téléverser chromatogramme (PNG ou PDF)" if st.session_state.lang == "FR" else "Upload chromatogram (PNG or PDF)", type=["png", "pdf"])

    if uploaded_file:
        img = Image.open(uploaded_file).convert("RGB")
        res, err = analyze_sn(img)
        if err:
            st.error(err)
        else:
            st.success(f"S/N automatique : {res['S/N']:.2f}" if st.session_state.lang == "FR" else f"Automatic S/N: {res['S/N']:.2f}")

            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            h_img, w_img = cv_img.shape[:2]
            peak_idx = res["Peak Retention"]
            # mapping index to x position (approx.)
            x_pos = int(peak_idx * w_img / len(np.mean(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), axis=0)))
            y_pos = int(h_img * 0.3)

            cv2.circle(cv_img, (x_pos, y_pos), 8, (0, 0, 255), -1)
            retention_time_min = peak_idx / 100
            cv2.putText(cv_img, f"{retention_time_min:.2f} min", (x_pos + 10, y_pos - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            st.image(Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)),
                     caption=("Chromatogramme avec pic marqué" if st.session_state.lang == "FR" else "Chromatogram with annotated peak"), use_column_width=True)

            slope = st.session_state.slope_lin
            lod_s, loq_s, lod_c, loq_c = calculate_lod_loq(slope, res["Noise"])
            unit = st.selectbox("Unité de concentration" if st.session_state.lang == "FR" else "Concentration unit", ["µg/mL", "mg/mL", "ng/mL"], index=0)
            st.markdown(f"{texts['lod_label']} : {lod_s:.2f} (signal) | {lod_c:.4f} {unit}")
            st.markdown(f"{texts['loq_label']} : {loq_s:.2f} (signal) | {loq_c:.4f} {unit}")

            # Stocker résultats et image pour PDF avancé
            st.session_state.sn_result = res
            st.session_state.lod_s = lod_s
            st.session_state.loq_s = loq_s
            st.session_state.lod_c = lod_c
            st.session_state.loq_c = loq_c
            st.session_state.sn_img_annot = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

    if st.button("🧮 " + ("Calcul manuel S/N" if st.session_state.lang == "FR" else "Manual S/N calc")):
        st.markdown("### Entrée manuelle" if st.session_state.lang == "FR" else "### Manual entry")
        H = st.number_input("Hauteur du pic (H)" if st.session_state.lang == "FR" else "Peak height (H)")
        h = st.number_input("Bruit (h)" if st.session_state.lang == "FR" else "Noise (h)")
        if h > 0:
            sn_classique = H / h
            st.success(f"S/N classique = {sn_classique:.2f}" if st.session_state.lang == "FR" else f"S/N = {sn_classique:.2f}")
            # Stocker S/N manuel pour PDF
            st.session_state.sn_manual = sn_classique
        else:
            st.warning("Entrer un bruit > 0." if st.session_state.lang == "FR" else "Enter noise > 0.")

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
# PDF avancé complet (bilingue selon st.session_state.lang)
# ===============================
def generate_pdf_report_full(results, lin_fig=None, sn_img=None, filename="rapport_LabT.pdf"):
    lang = st.session_state.lang
    texts = TEXTS[lang]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Rapport LabT" if lang == "FR" else "LabT Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)
    if "user" in st.session_state and st.session_state.user:
        pdf.cell(0, 8, f"Utilisateur : {st.session_state.user}" if lang == "FR" else f"User: {st.session_state.user}", ln=True)
        pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, ("Résultats :" if lang == "FR" else "Results:"), ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.ln(2)

    # Écrire les résultats
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

    # Footer "Powered by : BnB"
    pdf.set_y(-20)
    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(108,117,125)  # grey color
    pdf.cell(0, 10, texts["powered_by"], align="C")

    pdf.output(filename)
    return filename

# Affichage du bouton PDF complet (si résultats présents)
if st.session_state.logged_in:
    results_pdf = {}
    if st.session_state.slope_lin is not None:
        results_pdf["Pente (Linéarité)" if st.session_state.lang == "FR" else "Slope (Linearity)"] = f"{st.session_state.slope_lin:.4f}"
    if "sn_result" in st.session_state:
        sn_res = st.session_state.sn_result
        sn_value = sn_res.get("S/N")
        results_pdf["S/N automatique" if st.session_state.lang == "FR" else "Automatic S/N"] = f"{sn_value:.2f}" if sn_value else "N/A"
        results_pdf["Peak Retention" if st.session_state.lang == "FR" else "Peak Retention"] = sn_res.get("Peak Retention", "N/A")
        results_pdf["Noise" if st.session_state.lang == "FR" else "Noise"] = f"{sn_res.get('Noise', 0):.2f}"
        if "lod_s" in st.session_state and "lod_c" in st.session_state:
            results_pdf["LOD (signal)"] = f"{st.session_state.lod_s:.2f}"
            results_pdf["LOQ (signal)"] = f"{st.session_state.loq_s:.2f}"
            results_pdf["LOD (concentration)"] = f"{st.session_state.lod_c:.4f}"
            results_pdf["LOQ (concentration)"] = f"{st.session_state.loq_c:.4f}"
    if "sn_manual" in st.session_state:
        results_pdf["S/N manuel" if st.session_state.lang == "FR" else "Manual S/N"] = f"{st.session_state.sn_manual:.2f}"

    if results_pdf:
        if st.button(TEXTS[st.session_state.lang]["download_pdf"]):
            pdf_file = generate_pdf_report_full(
                results_pdf,
                lin_fig=st.session_state.get("lin_fig"),
                sn_img=st.session_state.get("sn_img_annot")
            )
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label=TEXTS[st.session_state.lang]["download_pdf_simple"],
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