import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import json
from io import BytesIO

# -------------------
# Gestion des utilisateurs
# -------------------
USER_FILE = "users.json"

def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except:
        return {"admin": {"password": "admin123", "role": "admin"}}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

users = load_users()

# -------------------
# Login
# -------------------
def login_area():
    st.title("LabT - Login / Connexion")
    username = st.text_input("Utilisateur / Username")
    password = st.text_input("Mot de passe / Password", type="password")
    login = st.button("Se connecter / Login")
    if login:
        if username in users and users[username]["password"] == password:
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]
        else:
            st.error("Utilisateur ou mot de passe invalide / Invalid username or password")

def logout():
    st.session_state.pop("username", None)
    st.session_state.pop("role", None)
    st.experimental_rerun()

# -------------------
# PDF
# -------------------
def create_pdf(title, data, company_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"{title} - {company_name}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    for line in data:
        pdf.cell(0, 8, line, ln=True)
    return pdf

# -------------------
# Calcul linéarité
# -------------------
def linearity_tab():
    st.header("Linéarité / Linearity")
    input_type = st.radio("Choisir méthode / Choose method", ["CSV", "Saisie manuelle / Manual entry"])
    
    if input_type.startswith("CSV"):
        file = st.file_uploader("Importer CSV / Upload CSV", type="csv")
        if file:
            df = pd.read_csv(file)
            if df.shape[1] < 2:
                st.error("Le CSV doit contenir au moins deux colonnes / CSV must have at least two columns")
                return
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
    else:
        x_text = st.text_input("Concentrations séparées par ',' / Concentrations separated by ','")
        y_text = st.text_input("Signaux séparés par ',' / Signals separated by ','")
        if x_text and y_text:
            x = np.array([float(v.strip()) for v in x_text.split(",")])
            y = np.array([float(v.strip()) for v in y_text.split(",")])
    
    if 'x' in locals() and 'y' in locals():
        # Ajustement linéaire
        try:
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs
            y_fit = slope * x + intercept
            r2 = np.corrcoef(y, y_fit)[0,1]**2
            st.line_chart(pd.DataFrame({"x":x, "y":y, "fit":y_fit}).set_index("x"))
            st.write(f"Slope / Pente: {slope:.4f}, R²: {r2:.4f}")
            
            # Calcul concentration inconnue automatiquement
            y_unknown = st.number_input("Signal inconnu / Unknown signal")
            if y_unknown != 0:
                c_unknown = (y_unknown - intercept)/slope
                st.write(f"Concentration inconnue / Unknown concentration: {c_unknown:.4f}")
            
            # Export PDF
            company_name = st.text_input("Nom compagnie / Company name")
            export_pdf = st.button("Exporter PDF / Export PDF")
            if export_pdf:
                if not company_name:
                    st.warning("Veuillez entrer le nom de la compagnie / Enter company name")
                else:
                    data = [f"Slope / Pente: {slope:.4f}", f"R²: {r2:.4f}"]
                    pdf = create_pdf("Rapport Linéarité / Linearity Report", data, company_name)
                    pdf.output("linearity_report.pdf")
                    st.success("PDF exporté / PDF exported")
        except Exception as e:
            st.error(f"Erreur calcul linéarité / Linearity calculation error: {e}")

# -------------------
# Calcul S/N
# -------------------
def calculate_sn(signal, baseline=None):
    if baseline is None:
        baseline = np.min(signal)
    noise = np.std(signal - baseline)
    sn_classic = (np.max(signal) - baseline) / noise if noise != 0 else np.nan
    sn_usp = np.max(signal) / noise if noise != 0 else np.nan
    return sn_classic, sn_usp

def sn_tab():
    st.header("S/N")
    file = st.file_uploader("Importer CSV, PNG ou PDF / Upload CSV, PNG or PDF", type=["csv","png","pdf"])
    if file:
        df_sn = None
        if file.name.endswith(".csv"):
            df_sn = pd.read_csv(file)
            st.line_chart(df_sn)
        else:
            st.write("Aperçu PNG/PDF non implémenté / Preview not implemented")
        
        if df_sn is not None:
            signal_col = st.selectbox("Colonne signal / Signal column", df_sn.columns)
            signal = df_sn[signal_col].values
            start_idx = st.number_input("Début zone / Start index", min_value=0, max_value=len(signal)-1, value=0)
            end_idx = st.number_input("Fin zone / End index", min_value=1, max_value=len(signal), value=len(signal))
            
            if end_idx > start_idx:
                selected_signal = signal[start_idx:end_idx]
                sn_classic, sn_usp = calculate_sn(selected_signal)
                st.write(f"S/N Classique / Classic: {sn_classic:.2f}")
                st.write(f"S/N USP: {sn_usp:.2f}")
                
                company_name = st.text_input("Nom compagnie / Company name")
                export_pdf = st.button("Exporter PDF / Export PDF")
                if export_pdf:
                    if not company_name:
                        st.warning("Veuillez entrer le nom de la compagnie / Enter company name")
                    else:
                        data = [f"S/N Classique / Classic: {sn_classic:.2f}", f"S/N USP: {sn_usp:.2f}"]
                        pdf = create_pdf("S/N Report", data, company_name)
                        pdf.output("sn_report.pdf")
                        st.success("PDF exporté / PDF exported")
    st.button("Retour au menu / Back to menu")

# -------------------
# Changement mot de passe user
# -------------------
def change_password_tab():
    st.header("Changer mot de passe / Change password")
    old_pw = st.text_input("Ancien mot de passe / Old password", type="password")
    new_pw = st.text_input("Nouveau mot de passe / New password", type="password")
    confirm_pw = st.text_input("Confirmer / Confirm", type="password")
    if st.button("Changer / Change"):
        username = st.session_state.get("username")
        if username and users[username]["password"] == old_pw:
            if new_pw == confirm_pw:
                users[username]["password"] = new_pw
                save_users(users)
                st.success("Mot de passe changé / Password changed")
            else:
                st.error("Les mots de passe ne correspondent pas / Passwords do not match")
        else:
            st.error("Ancien mot de passe incorrect / Old password incorrect")
    st.button("Retour au menu / Back to menu")

# -------------------
# Menu principal
# -------------------
def main_app():
    st.title("LabT")
    if st.session_state.get("role") == "admin":
        menu = ["Admin"]
    else:
        menu = ["Linéarité / Linearity", "S/N", "Changer mot de passe / Change password"]
    
    choice = st.selectbox("Menu", menu)
    
    if choice == "Admin":
        st.subheader("Gestion utilisateurs / User management")
        st.write(users)
    elif choice.startswith("Linéarité"):
        linearity_tab()
    elif choice.startswith("S/N"):
        sn_tab()
    elif choice.startswith("Changer"):
        change_password_tab()

# -------------------
# Exécution
# -------------------
if "username" not in st.session_state:
    login_area()
else:
    st.write(f"Connecté en tant que / Logged in as: {st.session_state['username']}")
    if st.button("Se déconnecter / Logout"):
        logout()
    else:
        main_app()