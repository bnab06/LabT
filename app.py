import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import json
from scipy import stats
from PIL import Image
import io

# -------------------- UTILITIES --------------------
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def authenticate(username, password):
    users = load_users()
    for u in users:
        if u["username"].lower() == username.lower() and u["password"] == password:
            return u
    return None

def generate_pdf(title, company, user, x, y, slope, intercept, R2, conc_unknown=None, signal_unknown=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, company, ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"User: {user} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.cell(0, 10, title, ln=True)
    # plot
    fig, ax = plt.subplots()
    ax.scatter(x, y, label="Data")
    ax.plot(x, slope*np.array(x)+intercept, 'r', label="Fit")
    ax.set_xlabel("Concentration")
    ax.set_ylabel("Signal")
    ax.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format="PNG")
    buf.seek(0)
    pdf.image(buf, x=10, y=50, w=pdf.w - 20)
    pdf.ln(120)
    pdf.cell(0, 10, f"Slope: {slope:.4f}", ln=True)
    pdf.cell(0, 10, f"Intercept: {intercept:.4f}", ln=True)
    pdf.cell(0, 10, f"R²: {R2:.4f}", ln=True)
    if conc_unknown is not None:
        pdf.cell(0, 10, f"Calculated Concentration: {conc_unknown:.4f}", ln=True)
    if signal_unknown is not None:
        pdf.cell(0, 10, f"Calculated Signal: {signal_unknown:.4f}", ln=True)
    filename = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# -------------------- SESSION STATE --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if "password_change" not in st.session_state:
    st.session_state.password_change = False

# -------------------- LANGUAGE --------------------
language = st.selectbox("Language / Langue", ["English", "Français"])
T = lambda fr, en: en if language=="English" else fr

# -------------------- LOGIN --------------------
if not st.session_state.logged_in:
    st.title(T("Login", "Connexion"))
    username = st.text_input(T("Username", "Utilisateur"))
    password = st.text_input(T("Password", "Mot de passe"), type="password")
    if st.button(T("Login", "Connexion")):
        user = authenticate(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
        else:
            st.error(T("Invalid username or password", "Utilisateur ou mot de passe invalide"))

# -------------------- MAIN APP --------------------
if st.session_state.logged_in:
    user = st.session_state.user
    role = user["role"]

    # -------------------- ADMIN --------------------
    if role == "admin":
        st.title(T("Admin Panel", "Gestion des utilisateurs"))
        st.subheader(T("Users List", "Liste des utilisateurs"))
        users = load_users()
        for u in users:
            st.write(f"{u['username']} ({u['role']})")
        # Add user
        new_user = st.text_input(T("New username", "Nouvel utilisateur"))
        new_pass = st.text_input(T("Password", "Mot de passe"), type="password")
        new_role = st.selectbox(T("Role", "Rôle"), ["user", "admin"])
        if st.button(T("Add User", "Ajouter utilisateur")) and new_user and new_pass:
            users.append({"username": new_user, "password": new_pass, "role": new_role})
            save_users(users)
            st.success(T("User added", "Utilisateur ajouté"))
    
    # -------------------- USER --------------------
    else:
        st.title(T("Application", "Application"))
        # Password change (discret)
        if st.button(T("Change Password", "Changer mot de passe")):
            st.session_state.password_change = True
        if st.session_state.password_change:
            old_pass = st.text_input(T("Old password", "Ancien mot de passe"), type="password")
            new_pass1 = st.text_input(T("New password", "Nouveau mot de passe"), type="password")
            new_pass2 = st.text_input(T("Confirm password", "Confirmer mot de passe"), type="password")
            if st.button(T("Submit", "Valider")):
                if old_pass==user["password"] and new_pass1==new_pass2:
                    users = load_users()
                    for u in users:
                        if u["username"] == user["username"]:
                            u["password"] = new_pass1
                    save_users(users)
                    st.success(T("Password changed", "Mot de passe modifié"))
                    st.session_state.password_change = False
                else:
                    st.error(T("Error", "Erreur"))

        tab = st.radio(T("Choose Section", "Choisir le volet"), [T("Linearity", "Linéarité"), T("S/N")])
        
        # -------------------- LINEARITY --------------------
        if tab == T("Linearity", "Linéarité"):
            st.subheader(T("Linearity Calculation", "Calcul de linéarité"))
            input_type = st.radio(T("Input Type", "Type de saisie"), [T("CSV", "CSV"), T("Manual", "Manuelle")])
            if input_type == T("CSV", "CSV"):
                file = st.file_uploader("Upload CSV", type=["csv"])
                if file:
                    df = pd.read_csv(file)
                    if df.shape[1]<2:
                        st.error(T("CSV must have at least two columns", "Le CSV doit contenir au moins deux colonnes"))
                    else:
                        x = df.iloc[:,0].values
                        y = df.iloc[:,1].values
            else:
                conc = st.text_input(T("Concentrations (comma)", "Concentrations (séparées par des virgules)"))
                signal = st.text_input(T("Signals (comma)", "Signaux (séparés par des virgules)"))
                if conc and signal:
                    try:
                        x = np.array([float(c.strip()) for c in conc.split(",")])
                        y = np.array([float(s.strip()) for s in signal.split(",")])
                    except:
                        st.error(T("Invalid input", "Erreur de saisie"))

            unknown_choice = st.selectbox(T("Unknown to calculate", "Inconnu à calculer"), [T("Concentration", "Concentration"), T("Signal", "Signal")])
            unknown_value = st.number_input(T("Enter known value", "Entrez la valeur connue"), value=0.0)

            if 'x' in locals() and 'y' in locals():
                slope, intercept, r_value, _, _ = stats.linregress(x, y)
                fig, ax = plt.subplots()
                ax.scatter(x, y, label="Data")
                ax.plot(x, slope*x + intercept, 'r', label="Fit")
                ax.set_xlabel("Concentration")
                ax.set_ylabel("Signal")
                ax.legend()
                st.pyplot(fig)

                conc_unknown = signal_unknown = None
                if unknown_choice == T("Concentration", "Concentration"):
                    conc_unknown = (unknown_value - intercept)/slope
                    st.write(T("Calculated Concentration", "Concentration calculée"), conc_unknown)
                else:
                    signal_unknown = slope*unknown_value + intercept
                    st.write(T("Calculated Signal", "Signal calculé"), signal_unknown)

                st.write(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}, R²: {r_value**2:.4f}")

                if st.button(T("Export PDF", "Exporter PDF")):
                    company = st.text_input(T("Company Name for PDF", "Nom de l'entreprise pour le PDF"))
                    if company:
                        pdf_file = generate_pdf("Linearity", company, user["username"], x, y, slope, intercept, r_value**2, conc_unknown, signal_unknown)
                        st.success(T("PDF generated", f"PDF généré: {pdf_file}"))
                    else:
                        st.warning(T("Please enter company name", "Veuillez entrer le nom de l'entreprise"))


        # -------------------- S/N --------------------
        else:
            st.subheader(T("Signal to Noise", "Calcul S/N"))
            uploaded_file = st.file_uploader(T("Upload CSV / PNG / PDF", "Importer CSV / PNG / PDF"), type=["csv","png","pdf"])
            if uploaded_file:
                if uploaded_file.name.endswith("csv"):
                    df_sn = pd.read_csv(uploaded_file)
                    if df_sn.shape[1]<2:
                        st.error(T("CSV must have at least two columns", "Le CSV doit contenir au moins deux colonnes"))
                    else:
                        st.line_chart(df_sn)
                elif uploaded_file.name.endswith(("png","jpg","jpeg")):
                    try:
                        img = Image.open(uploaded_file)
                        st.image(img)
                    except:
                        st.error(T("Cannot read image", "Impossible de lire l'image"))
                else:
                    st.info(T("PDF preview not implemented", "Aperçu PDF non implémenté"))

        if st.button(T("Logout", "Déconnexion")):
            st.session_state.update({"logged_in":False,"user":None})