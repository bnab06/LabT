# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import json
from PIL import Image
from io import BytesIO
from scipy import stats

# ---------- Constantes ----------
USERS_FILE = "users.json"

# ---------- Utils ----------
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(pwd):
    # Simple hash pour l'exemple
    import hashlib
    return hashlib.sha256(pwd.encode()).hexdigest()

def T(fr, en):
    """Traduction selon la langue sélectionnée"""
    lang = st.session_state.get("lang", "en")
    return fr if lang == "fr" else en

# ---------- Login ----------
def login_form():
    st.title("LabT")
    st.session_state.lang = st.selectbox("Language / Langue", ["English", "Français"], index=0)
    users = load_users()
    username = st.text_input(T("Utilisateur", "Username"))
    password = st.text_input(T("Mot de passe", "Password"), type="password")
    if st.button(T("Connexion", "Login")):
        user = users.get(username.lower())
        if user and user["password"] == hash_password(password):
            st.session_state.logged_in = True
            st.session_state.user = username.lower()
            st.session_state.is_admin = user.get("admin", False)
        else:
            st.error(T("Utilisateur ou mot de passe invalide", "Invalid username or password"))

# ---------- Logout ----------
def logout():
    for key in ["logged_in", "user", "is_admin"]:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()

# ---------- Change Password ----------
def change_password():
    st.subheader(T("Changer mot de passe", "Change password"))
    old = st.text_input(T("Ancien mot de passe", "Old password"), type="password")
    new = st.text_input(T("Nouveau mot de passe", "New password"), type="password")
    if st.button(T("Valider", "Confirm")):
        users = load_users()
        user = st.session_state.user
        if users[user]["password"] == hash_password(old):
            users[user]["password"] = hash_password(new)
            save_users(users)
            st.success(T("Mot de passe changé", "Password changed"))
        else:
            st.error(T("Ancien mot de passe incorrect", "Old password incorrect"))

# ---------- Linéarité ----------
def linearity_tab():
    st.header(T("Linéarité", "Linearity"))
    input_type = st.radio(T("Mode de saisie", "Input mode"), [T("CSV", "CSV"), T("Saisie manuelle", "Manual")])
    df = None
    if input_type == T("CSV", "CSV"):
        file = st.file_uploader(T("Importer un fichier CSV", "Upload CSV"), type="csv")
        if file:
            try:
                df = pd.read_csv(file)
                if df.shape[1] < 2:
                    st.error(T("CSV doit contenir au moins deux colonnes", "CSV must have at least two columns"))
                    return
            except:
                st.error(T("Erreur lecture CSV", "Error reading CSV"))
    else:
        x_str = st.text_input(T("Valeurs concentration séparées par virgules", "Concentration values separated by commas"))
        y_str = st.text_input(T("Valeurs signal séparées par virgules", "Signal values separated by commas"))
        if x_str and y_str:
            try:
                x = np.array([float(i) for i in x_str.split(",")])
                y = np.array([float(i) for i in y_str.split(",")])
                df = pd.DataFrame({"x": x, "y": y})
            except:
                st.error(T("Erreur de saisie", "Input error"))

    if df is not None:
        x = df.iloc[:,0].values
        y = df.iloc[:,1].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        st.write(T(f"R²: {r_value**2:.4f}", f"R²: {r_value**2:.4f}"))
        fig, ax = plt.subplots()
        ax.scatter(x, y, label="Data")
        ax.plot(x, intercept + slope*x, 'r', label="Fit")
        ax.set_xlabel(T("Concentration", "Concentration"))
        ax.set_ylabel(T("Signal", "Signal"))
        ax.legend()
        st.pyplot(fig)
        st.session_state.slope = slope
        st.session_state.intercept = intercept

        unknown_choice = st.selectbox(T("Calculer", "Calculate"), [T("Concentration inconnue", "Unknown concentration"), T("Signal inconnu", "Unknown signal")])
        if unknown_choice == T("Concentration inconnue", "Unknown concentration"):
            sig = st.number_input(T("Entrer le signal", "Enter signal"))
            conc = (sig - intercept)/slope
            st.write(T(f"Concentration inconnue: {conc:.4f}", f"Unknown concentration: {conc:.4f}"))
        else:
            conc = st.number_input(T("Entrer la concentration", "Enter concentration"))
            sig = slope*conc + intercept
            st.write(T(f"Signal inconnu: {sig:.4f}", f"Unknown signal: {sig:.4f}"))

        # Export PDF
        if st.button(T("Exporter PDF", "Export PDF")):
            company = st.text_input(T("Nom de la compagnie", "Company name"))
            if not company:
                st.warning(T("Veuillez entrer le nom de la compagnie", "Please enter company name"))
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0,10,f"{company}",ln=1)
                pdf.set_font("Arial","",12)
                pdf.cell(0,10,f"Utilisateur: {st.session_state.user}",ln=1)
                pdf.cell(0,10,f"Date: {datetime.now().strftime('%Y-%m-%d')}",ln=1)
                pdf.cell(0,10,f"Slope: {slope:.4f}",ln=1)
                pdf.cell(0,10,f"Intercept: {intercept:.4f}",ln=1)
                pdf.cell(0,10,f"R²: {r_value**2:.4f}",ln=1)
                # ajouter figure
                img_path = "temp_plot.png"
                fig.savefig(img_path)
                pdf.image(img_path,x=10,y=80,w=180)
                pdf.output("linearity_report.pdf")
                st.success(T("PDF généré", "PDF generated"))

# ---------- S/N ----------
def sn_tab():
    st.header(T("Signal / Noise", "Signal / Noise"))
    uploaded_file = st.file_uploader(T("Importer CSV, PNG ou PDF", "Upload CSV, PNG, PDF"), type=["csv","png","pdf"])
    if uploaded_file:
        if uploaded_file.type == "text/csv":
            try:
                df = pd.read_csv(uploaded_file)
                if df.shape[1] < 2:
                    st.error(T("CSV doit contenir au moins deux colonnes", "CSV must have at least two columns"))
                    return
                st.line_chart(df)
            except:
                st.error(T("Erreur lecture CSV", "Error reading CSV"))
        else:
            try:
                img = Image.open(uploaded_file)
                st.image(img)
            except:
                st.error(T("Fichier image non reconnu", "Unidentified image file"))

# ---------- Main ----------
def main():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_form()
        return

    if st.session_state.is_admin:
        st.header(T("Admin - Gestion utilisateurs", "Admin - User Management"))
        # ajouter boutons add, delete, modify users
        change_password()
    else:
        tab = st.radio(T("Sélectionner un onglet", "Select tab"), [T("Linéarité", "Linearity"), T("S/N", "Signal/Noise")])
        if tab == T("Linéarité", "Linearity"):
            linearity_tab()
        else:
            sn_tab()
        st.button(T("Changer mot de passe", "Change password"), on_click=change_password)
        st.button(T("Déconnexion", "Logout"), on_click=logout)

if __name__ == "__main__":
    main()