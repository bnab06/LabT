# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import json
import os

# -------- CONFIG --------
st.set_page_config(page_title="LabT App", layout="wide")
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LOGO_PATH = os.path.join(DATA_DIR, "LabT_logo.png")

# -------- UTILS --------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def authenticate(username, password):
    users = load_users()
    username = username.lower()
    if username in users and users[username]["password"] == password:
        return True, users[username]["role"]
    return False, None

def logout():
    for key in st.session_state.keys():
        st.session_state[key] = None
    st.experimental_rerun()

def change_password(username):
    st.subheader("Change password / Changer mot de passe")
    old_pw = st.text_input("Current password / Mot de passe actuel", type="password")
    new_pw = st.text_input("New password / Nouveau mot de passe", type="password")
    confirm_pw = st.text_input("Confirm / Confirmer", type="password")
    if st.button("Change / Changer"):
        users = load_users()
        uname = username.lower()
        if users[uname]["password"] == old_pw:
            if new_pw == confirm_pw:
                users[uname]["password"] = new_pw
                save_users(users)
                st.success("Password changed / Mot de passe changé")
            else:
                st.error("Passwords do not match / Les mots de passe ne correspondent pas")
        else:
            st.error("Incorrect current password / Mot de passe actuel incorrect")

# -------- LINÉARITÉ --------
def linearity_page():
    st.subheader("Linearity / Linéarité")
    option = st.radio("Input method / Méthode de saisie", ["CSV", "Manual / Manuel"])
    if option == "CSV":
        uploaded_file = st.file_uploader("Upload CSV / Importer CSV", type=["csv"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine="python")
                if "Concentration" in df.columns and "Signal" in df.columns:
                    x = df["Concentration"].values
                    y = df["Signal"].values
                else:
                    st.error("CSV must contain 'Concentration' and 'Signal' / CSV doit contenir 'Concentration' et 'Signal'")
                    return
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
                return
    else:
        n = st.number_input("Number of points / Nombre de points", min_value=2, step=1)
        conc_list = []
        signal_list = []
        for i in range(int(n)):
            conc = st.number_input(f"Concentration {i+1}", key=f"conc{i}")
            sig = st.number_input(f"Signal {i+1}", key=f"sig{i}")
            conc_list.append(conc)
            signal_list.append(sig)
        x = np.array(conc_list)
        y = np.array(signal_list)
    
    if st.button("Calculate / Calculer"):
        slope, intercept = np.polyfit(x, y, 1)
        y_fit = slope * x + intercept
        r2 = np.corrcoef(y, y_fit)[0,1]**2
        st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée à l'origine: {intercept:.4f}, R²: {r2:.4f}")
        fig, ax = plt.subplots()
        ax.scatter(x, y, label="Data / Données")
        ax.plot(x, y_fit, color="red", label="Fit / Ajustement")
        ax.set_xlabel("Concentration")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)
        st.session_state["linearity_slope"] = slope
        st.session_state["linearity_intercept"] = intercept

# -------- SIGNAL / BRUIT --------
def sn_page():
    st.subheader("Signal / Noise / S/N")
    uploaded_file = st.file_uploader("Upload chromatogram (CSV, PDF, PNG) / Importer chromatogramme", type=["csv","pdf","png"])
    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")
        # Note: PDF/PNG parsing requires external tools (e.g., PyPDF2 or OpenCV). CSV used here.
        if uploaded_file.name.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine="python")
                if "Time" not in df.columns or "Signal" not in df.columns:
                    st.error("CSV must contain 'Time' and 'Signal'")
                    return
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
                return
        st.write("Select range for S/N calculation / Sélectionner la plage pour calcul S/N")
        time_min, time_max = st.slider("Time range / Plage de temps", float(df["Time"].min()), float(df["Time"].max()), (float(df["Time"].min()), float(df["Time"].max())))
        mask = (df["Time"] >= time_min) & (df["Time"] <= time_max)
        peak = df["Signal"][mask].max()
        noise_std = df["Signal"][mask].std()
        sn_classic = peak / noise_std if noise_std > 0 else np.nan
        st.write(f"S/N Classic: {sn_classic:.4f}")
        if "linearity_slope" in st.session_state:
            slope = st.session_state["linearity_slope"]
            lod = 3 * noise_std / slope
            loq = 10 * noise_std / slope
            st.write(f"LOD: {lod:.4f}, LOQ: {loq:.4f} (Concentration)")

# -------- PDF RAPPORT --------
def generate_pdf(company, username):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=10, y=8, w=33)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{company}", ln=True, align="C")
    pdf.cell(0, 10, f"User: {username}  Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.output(os.path.join(DATA_DIR, "report.pdf"))

# -------- USER MENU --------
def user_menu(username):
    st.sidebar.button("Logout / Déconnexion", on_click=logout)
    change_pw = st.sidebar.checkbox("Change password / Changer mot de passe")
    if change_pw:
        change_password(username)
    tab = st.radio("Menu", ["Linearity / Linéarité", "S/N", "Generate PDF / Rapport PDF"])
    if tab.startswith("Linearity"):
        linearity_page()
    elif tab.startswith("S/N"):
        sn_page()
    else:
        company = st.text_input("Company / Société")
        if not company:
            st.warning("Enter company name / Entrer le nom de la société")
        else:
            generate_pdf(company, username)
            st.success("PDF generated / PDF généré")

# -------- ADMIN MENU --------
def admin_menu(username):
    st.sidebar.button("Logout / Déconnexion", on_click=logout)
    st.subheader("Manage Users / Gérer les utilisateurs")
    users = load_users()
    st.write("Existing users:")
    for u, info in users.items():
        st.write(f"{u} - {info['role']}")

# -------- LOGIN PAGE --------
def login_page():
    st.title("LabT App")
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        auth, role = authenticate(username, password)
        if auth:
            st.session_state["username"] = username.lower()
            st.session_state["role"] = role
            st.experimental_rerun()
        else:
            st.error("Wrong username or password ❌ / Nom d'utilisateur ou mot de passe incorrect")

# -------- MAIN --------
def main():
    if "username" not in st.session_state:
        login_page()
    else:
        username = st.session_state["username"]
        role = st.session_state.get("role","user")
        if role == "admin":
            admin_menu(username)
        else:
            user_menu(username)

if __name__ == "__main__":
    main()