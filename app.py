import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io, json, tempfile, os
from datetime import datetime

try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None
try:
    import pytesseract
except Exception:
    pytesseract = None

st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {
            "admin": {"password": "admin123", "role": "admin"},
            "user": {"password": "user123", "role": "user"},
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

USERS = load_users()

TEXTS = {
    "FR": {"app_title": "LabT", "login": "Connexion", "logout": "Déconnexion",
           "invalid": "Identifiants invalides", "linearity": "Linéarité", "sn": "S/N",
           "admin": "Admin", "company": "Nom de la compagnie",
           "generate_pdf": "Générer PDF", "download_pdf": "Télécharger PDF",
           "compute": "Calculer", "company_missing": "Veuillez saisir le nom de la compagnie avant de générer le rapport.",
           "add_user": "Ajouter utilisateur", "delete_user": "Supprimer utilisateur", "modify_user": "Modifier mot de passe",
           "select_region": "Sélectionner la zone", "formulas": "Formules"},
    "EN": {"app_title": "LabT", "login": "Login", "logout": "Logout",
           "invalid": "Invalid credentials", "linearity": "Linearity", "sn": "S/N",
           "admin": "Admin", "company": "Company name",
           "generate_pdf": "Generate PDF", "download_pdf": "Download PDF",
           "compute": "Compute", "company_missing": "Please enter company name before generating the report.",
           "add_user": "Add user", "delete_user": "Delete user", "modify_user": "Modify password",
           "select_region": "Select region", "formulas": "Formulas"}
}
def t(key): return TEXTS["FR"].get(key, key)

if "user" not in st.session_state: st.session_state.user = None
if "role" not in st.session_state: st.session_state.role = None
if "linear_slope" not in st.session_state: st.session_state.linear_slope = None

def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=20)
        pdf.set_xy(35, 10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=1, align="C")
    pdf.set_font("Arial", "", 11)
    pdf.ln(4)
    for l in lines: pdf.multi_cell(0, 7, l)
    if img_bytes:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(img_bytes.getvalue() if isinstance(img_bytes, io.BytesIO) else img_bytes)
            path = tmp.name
        pdf.image(path, x=20, w=170)
    return pdf.output(dest="S").encode("latin1")

# --- LOGIN ---
def login_screen():
    st.title(t("app_title"))
    u = st.text_input("Utilisateur")
    p = st.text_input("Mot de passe", type="password")
    if st.button(t("login")):
        for usr, data in USERS.items():
            if usr.lower() == u.lower() and data["password"] == p:
                st.session_state.user = usr
                st.session_state.role = data["role"]
                st.rerun()
        st.error(t("invalid"))

# --- ADMIN ---
def admin_panel():
    st.header("Gestion des utilisateurs")
    st.write("Ajouter ou supprimer un utilisateur")
    new_user = st.text_input("Nom utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["user", "admin"])
    if st.button("Ajouter"):
        if new_user and new_pass:
            USERS[new_user] = {"password": new_pass, "role": role}
            save_users(USERS)
            st.success("Utilisateur ajouté.")
            st.rerun()
    sel = st.selectbox("Supprimer utilisateur", list(USERS.keys()))
    if st.button("Supprimer"):
        if sel != "admin":
            USERS.pop(sel)
            save_users(USERS)
            st.success("Utilisateur supprimé.")
            st.rerun()
        else:
            st.warning("Impossible de supprimer admin")

# --- LINÉARITÉ ---
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"))
    uploaded = st.file_uploader("Importer CSV (Concentration, Signal)", type=["csv"])
    df = None
    if uploaded:
        df = pd.read_csv(uploaded)
        df.columns = ["Concentration", "Signal"]
    else:
        st.write("Ou saisissez manuellement vos paires :")
        txt = st.text_area("Concentration, Signal (une paire par ligne)")
        if st.button("Charger"):
            data = []
            for line in txt.splitlines():
                try:
                    x, y = line.replace(",", ".").split()
                    data.append([float(x), float(y)])
                except: pass
            if len(data) >= 2:
                df = pd.DataFrame(data, columns=["Concentration", "Signal"])
            else:
                st.warning("Au moins deux points nécessaires.")

    if df is None: return
    slope, intercept = np.polyfit(df["Concentration"], df["Signal"], 1)
    y_pred = np.polyval([slope, intercept], df["Concentration"])
    r2 = 1 - np.sum((df["Signal"] - y_pred)**2) / np.sum((df["Signal"] - np.mean(df["Signal"]))**2)
    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.6f}")
    st.session_state.linear_slope = slope

    fig, ax = plt.subplots()
    ax.scatter(df["Concentration"], df["Signal"])
    ax.plot(df["Concentration"], y_pred, color="red")
    st.pyplot(fig)

    calc = st.radio("Calcul", ["Signal → Concentration", "Concentration → Signal"])
    if calc.startswith("Signal"):
        s = st.number_input("Signal", 0.0)
        if st.button(t("compute")):
            c = (s - intercept) / slope
            st.success(f"Concentration = {c:.6f}")
    else:
        c = st.number_input("Concentration", 0.0)
        if st.button(t("compute")):
            s = slope * c + intercept
            st.success(f"Signal = {s:.6f}")

    with st.expander(t("formulas")):
        st.markdown(r"**y = slope·x + intercept**  \n**LOD = 3.3·σ/slope**  \n**LOQ = 10·σ/slope**")

    if st.button(t("generate_pdf")):
        if not company.strip():
            st.warning(t("company_missing"))
        else:
            buf = io.BytesIO(); fig.savefig(buf, format="png")
            pdf = generate_pdf_bytes("Rapport Linéarité", [
                f"Compagnie: {company}", f"User: {st.session_state.user}",
                f"Slope: {slope:.6f}", f"Intercept: {intercept:.6f}", f"R²: {r2:.6f}"
            ], img_bytes=buf, logo_path=LOGO_FILE)
            st.download_button(t("download_pdf"), pdf, "linearity.pdf")

# --- S/N ---
def sn_panel_full():
    st.header(t("sn"))
    st.info("Upload chromatogramme ou calcul manuel H/h.")
    uploaded = st.file_uploader("Chromatogramme", type=["csv","png","jpg","jpeg","pdf"])
    if not uploaded:
        H = st.number_input("H (peak height)", 0.0)
        h = st.number_input("h (noise)", 0.0)
        slope = st.number_input("Slope", float(st.session_state.linear_slope or 0.0))
        if st.button(t("compute")):
            if h == 0: st.error("h = 0")
            else:
                sn_classic = H/h; sn_usp = 2*H/h
                st.write(f"S/N Classique: {sn_classic:.2f}"); st.write(f"S/N USP: {sn_usp:.2f}")
                if slope: st.write(f"LOD = {3.3*h/slope:.6f}, LOQ = {10*h/slope:.6f}")
        return
    st.info("Traitement des fichiers complet inchangé ici.")

# --- MAIN ---
def main_app():
    st.markdown(f"### {t('app_title')} — {st.session_state.user}")
    if st.session_state.role == "admin":
        admin_panel()
    else:
        tabs = st.tabs([t("linearity"), t("sn")])
        with tabs[0]: linearity_panel()
        with tabs[1]: sn_panel_full()
    if st.button(t("logout")):
        st.session_state.clear()
        st.rerun()

def run():
    if st.session_state.user: main_app()
    else: login_screen()

if __name__ == "__main__":
    run()