import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
import io
import fitz  # PyMuPDF pour PDF
from pathlib import Path

# ---------- CONFIGURATION ----------
USERS_FILE = "users.json"
DEFAULT_UNIT = "µg/mL"
LANGUAGES = {"FR": "Français", "EN": "English"}

# ---------- UTILITAIRES ----------
def load_users():
    if Path(USERS_FILE).exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def check_login(username, password):
    users = load_users()
    return username in users and users[username]["password"] == password

def is_admin(username):
    users = load_users()
    return users.get(username, {}).get("role") == "admin"

def plot_linearity(x, y, unit):
    slope, intercept = np.polyfit(x, y, 1)
    r2 = np.corrcoef(x, y)[0,1]**2
    fig, ax = plt.subplots()
    ax.scatter(x, y)
    ax.plot(x, slope*x + intercept, color="red")
    ax.set_xlabel(f"Concentration ({unit})")
    ax.set_ylabel("Signal")
    ax.set_title(f"Linéarité (R² = {r2:.4f})")
    return fig, slope, intercept, r2

def generate_pdf(title, text, filename="report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, text)
    pdf.output(filename)
    return filename

# ---------- AUTHENTIFICATION ----------
def login_page():
    st.title("LabT – Login")
    username = st.text_input("Utilisateur / Username")
    password = st.text_input("Mot de passe / Password", type="password")
    language = st.selectbox("Langue / Language", list(LANGUAGES.keys()))
    if st.button("Se connecter / Login"):
        if check_login(username, password):
            st.session_state["username"] = username
            st.session_state["language"] = language
            st.session_state["logged_in"] = True
        else:
            st.error("Utilisateur ou mot de passe invalide / Invalid username or password")

def logout():
    st.session_state.clear()
    st.experimental_rerun()

# ---------- LINÉARITÉ ----------
def linearity_tab():
    st.header("Linéarité / Linearity")
    method = st.radio("Choix / Method", ["CSV", "Saisie manuelle / Manual input"])
    
    if method == "CSV":
        file = st.file_uploader("Importer CSV", type="csv")
        if file:
            df = pd.read_csv(file)
            if df.shape[1] < 2:
                st.warning("CSV must have at least two columns")
                return
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
    else:
        x_str = st.text_input("Concentrations séparées par des virgules / Concentrations separated by commas")
        y_str = st.text_input("Signaux séparés par des virgules / Signals separated by commas")
        if x_str and y_str:
            x = np.array([float(i.strip()) for i in x_str.split(",")])
            y = np.array([float(i.strip()) for i in y_str.split(",")])
    
    unit = st.text_input("Unité / Unit", value=DEFAULT_UNIT)
    if 'x' in locals() and 'y' in locals():
        fig, slope, intercept, r2 = plot_linearity(x, y, unit)
        st.pyplot(fig)
        st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée à l'origine: {intercept:.4f}, R²: {r2:.4f}")
        
        # Concentration inconnue
        signal_unknown = st.number_input("Signal inconnu / Unknown signal")
        if signal_unknown:
            conc = (signal_unknown - intercept)/slope
            st.write(f"Concentration inconnue: {conc:.4f} {unit}")
        
        # Export PDF
        company = st.text_input("Nom de la compagnie / Company name")
        if st.button("Exporter rapport / Export report"):
            if not company:
                st.warning("Veuillez entrer le nom de la compagnie / Enter company name")
            else:
                text = f"Company: {company}\nSlope: {slope}\nIntercept: {intercept}\nR²: {r2}"
                filename = generate_pdf("Rapport Linéarité / Linearity Report", text)
                st.success("PDF généré")
                st.download_button("Télécharger PDF / Download PDF", filename)

# ---------- S/N ----------
def sn_tab():
    st.header("S/N Calculation / Calcul S/N")
    file = st.file_uploader("Importer CSV, PNG ou PDF / Upload CSV, PNG or PDF", type=["csv","png","pdf"])
    if file:
        st.write("Aperçu du fichier / Preview")
        if file.type=="application/pdf":
            doc = fitz.open(stream=file.read(), filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap()
            img = pix.tobytes("png")
            st.image(img)
        elif file.type.startswith("image/"):
            st.image(file)
        else:
            df = pd.read_csv(file)
            st.dataframe(df.head())
        
        # Zone pour S/N
        st.write("Sélectionner la zone / Select range")
        start = st.number_input("Début / Start", value=0)
        end = st.number_input("Fin / End", value=10)
        if 'df' in locals():
            sn_signal = df.iloc[start:end,1].values
            sn = np.mean(sn_signal)/np.std(sn_signal)
            st.write(f"S/N: {sn:.4f}")

# ---------- ADMIN ----------
def admin_tab():
    st.header("Admin – Gestion des utilisateurs")
    users = load_users()
    st.write(users)
    
    new_user = st.text_input("Nouvel utilisateur / New user")
    new_pass = st.text_input("Mot de passe / Password", type="password")
    if st.button("Ajouter / Add user"):
        if new_user and new_pass:
            users[new_user] = {"password": new_pass, "role": "user"}
            save_users(users)
            st.success("Utilisateur ajouté / User added")
    
    del_user = st.text_input("Supprimer utilisateur / Delete user")
    if st.button("Supprimer / Delete"):
        if del_user in users:
            users.pop(del_user)
            save_users(users)
            st.success("Utilisateur supprimé / User deleted")

# ---------- CHANGER MOT DE PASSE ----------
def change_password():
    st.header("Changer mot de passe / Change password")
    old = st.text_input("Ancien mot de passe / Old password", type="password")
    new = st.text_input("Nouveau mot de passe / New password", type="password")
    if st.button("Valider / Submit"):
        username = st.session_state["username"]
        users = load_users()
        if users[username]["password"]==old:
            users[username]["password"]=new
            save_users(users)
            st.success("Mot de passe changé / Password updated")
        else:
            st.error("Ancien mot de passe incorrect / Old password incorrect")

# ---------- APPLICATION ----------
def main():
    if "logged_in" not in st.session_state:
        login_page()
    else:
        st.sidebar.button("Déconnexion / Logout", on_click=logout)
        username = st.session_state["username"]
        if is_admin(username):
            admin_tab()
        else:
            tabs = st.tabs(["Linéarité / Linearity","S/N / S/N"])
            with tabs[0]:
                linearity_tab()
            with tabs[1]:
                sn_tab()
            st.button("Changer mot de passe / Change password", on_click=change_password)

if __name__ == "__main__":
    main()