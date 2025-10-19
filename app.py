import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime

# ---------- Initialisation session ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "unit" not in st.session_state:
    st.session_state.unit = ""

# ---------- Langue ----------
lang_options = {"English": "en", "Français": "fr"}
st.session_state.lang = st.selectbox("Select language / Sélectionnez la langue", list(lang_options.keys()), index=0)
lang = lang_options[st.session_state.lang]

texts = {
    "en": {"username": "Username", "password": "Password", "login": "Login",
           "error": "Incorrect username or password", "welcome": "Login successful ✅"},
    "fr": {"username": "Nom d'utilisateur", "password": "Mot de passe", "login": "Se connecter",
           "error": "Nom d'utilisateur ou mot de passe incorrect", "welcome": "Connexion réussie ✅"}
}

# ---------- Chargement utilisateurs ----------
def load_users(json_file="users.json"):
    try:
        with open(json_file, "r") as f:
            users = json.load(f)
        users = {k.lower(): v for k, v in users.items()}
        return users
    except:
        return {}

def save_users(users, json_file="users.json"):
    with open(json_file, "w") as f:
        json.dump(users, f, indent=4)

# ---------- Login ----------
if not st.session_state.logged_in:
    with st.form("login_form"):
        username = st.text_input(texts[lang]["username"])
        password = st.text_input(texts[lang]["password"], type="password")
        submit = st.form_submit_button(texts[lang]["login"])
        if submit:
            users = load_users()
            u = username.strip().lower()
            if u in users and users[u]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.session_state.role = users[u]["role"]
                st.success(f"{texts[lang]['welcome']} / You are logged in as {users[u]['role']}")
            else:
                st.error(texts[lang]["error"])

# ---------- Menu ----------
if st.session_state.logged_in:
    st.write(f"👤 {st.session_state.user} ({st.session_state.role})")
    if st.session_state.role.lower() == "admin":
        st.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False, "user": "", "role": ""}))
        st.subheader("Admin Menu / Menu Admin")
        selected_option = st.selectbox("Choose action / Choisir action:",
                                       ["Add User / Ajouter", "Delete User / Supprimer", "Unknown calculation / Calcul inconnu",
                                        "S/N Calculation / Calcul S/N", "Exit / Quitter"])
# ---------- Partie Admin ----------
if st.session_state.role.lower() == "admin":
    users = load_users()
    
    if selected_option.startswith("Add User"):
        st.subheader("Add New User / Ajouter un utilisateur")
        new_user = st.text_input("Username / Nom d'utilisateur")
        new_password = st.text_input("Password / Mot de passe", type="password")
        role_choice = st.selectbox("Role / Rôle", ["Admin", "User"])
        if st.button("Add / Ajouter"):
            key = new_user.strip().lower()
            if key in users:
                st.error("User already exists / L'utilisateur existe déjà")
            elif new_user == "" or new_password == "":
                st.warning("Username and password cannot be empty / Le nom et le mot de passe ne peuvent pas être vides")
            else:
                users[key] = {"password": new_password, "role": role_choice}
                save_users(users)
                st.success(f"User {new_user} added / ajouté avec succès")
    
    elif selected_option.startswith("Delete User"):
        st.subheader("Delete User / Supprimer un utilisateur")
        del_user = st.selectbox("Choose user / Choisir un utilisateur", list(users.keys()))
        if st.button("Delete / Supprimer"):
            if del_user in users:
                del users[del_user]
                save_users(users)
                st.success(f"User {del_user} deleted / supprimé avec succès")
            else:
                st.error("User not found / Utilisateur introuvable")
    
    elif selected_option.startswith("Exit"):
        st.session_state.logged_in = False
        st.session_state.user = ""
        st.session_state.role = ""
        st.experimental_rerun()
# ---------- Partie Calculs ----------
if st.session_state.role.lower() in ["admin", "user"]:
    st.subheader("Calculations / Calculs")
    
    selected_calc = st.selectbox(
        "Choose calculation / Choisir le calcul",
        ["Unknown calculation / Calcul inconnu", "S/N Classical / S/N Classique", "S/N USP"]
    )

    # Unité pour la concentration
    if "unit" not in st.session_state:
        st.session_state.unit = ""

    st.session_state.unit = st.text_input(
        "Unit for unknown / Unité pour l'inconnu",
        value=st.session_state.unit,
        key="unit"
    )

    # --- Calcul inconnu ---
    if selected_calc.startswith("Unknown"):
        st.write("Unknown calculation / Calcul inconnu")
        conc_values = st.text_area("Enter concentration values separated by commas / Entrez les valeurs de concentration séparées par des virgules")
        signal_values = st.text_area("Enter signal values separated by commas / Entrez les valeurs de signal séparées par des virgules")

        if st.button("Compute / Calculer"):
            try:
                conc_list = [float(x.strip()) for x in conc_values.split(",")]
                sig_list = [float(x.strip()) for x in signal_values.split(",")]
                avg_conc = np.mean(conc_list)
                avg_signal = np.mean(sig_list)
                st.success(f"Average concentration / Moyenne concentration: {avg_conc:.4f} {st.session_state.unit}")
                st.success(f"Average signal / Moyenne signal: {avg_signal:.4f}")
            except Exception as e:
                st.error(f"Error in calculation / Erreur dans les calculs: {e}")

    # --- Signal/Noise Classical & USP ---
    if selected_calc.startswith("S/N"):
        st.write("Signal-to-Noise Calculation / Calcul S/N")
        sn_signal = st.text_area("Enter signal values / Entrez les valeurs de signal")
        sn_blank = st.text_area("Enter blank values / Entrez les valeurs du blanc")
        sn_method = "classical" if "Classical" in selected_calc else "usp"

        if st.button("Compute S/N / Calculer S/N"):
            try:
                signal_list = np.array([float(x.strip()) for x in sn_signal.split(",")])
                blank_list = np.array([float(x.strip()) for x in sn_blank.split(",")])
                
                noise = np.std(blank_list)
                sn_ratio = np.mean(signal_list) / noise
                
                st.success(f"S/N ({sn_method}) : {sn_ratio:.4f}")
                
                # LOD & LOQ based on slope if linearity provided
                if "slope" in st.session_state and st.session_state.slope:
                    lod = (3.3 * noise) / st.session_state.slope
                    loq = (10 * noise) / st.session_state.slope
                    st.info(f"LOD: {lod:.4f} {st.session_state.unit}, LOQ: {loq:.4f} {st.session_state.unit}")
            except Exception as e:
                st.error(f"Error in S/N calculation / Erreur S/N: {e}")
# ---------- Partie Export PDF ----------
from fpdf import FPDF

def export_pdf_report():
    # Vérification de l'entreprise
    company = st.text_input("Company name / Nom de l'entreprise")
    if not company:
        st.warning("Please enter the company name before generating the report / Veuillez entrer le nom de l'entreprise avant de générer le rapport")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"App: LabT", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    
    pdf.cell(0, 8, f"Company / Entreprise: {company}", ln=True)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)

    # --- Calcul inconnu ---
    if "avg_conc" in locals():
        pdf.cell(0, 8, f"Unknown calculation / Calcul inconnu:", ln=True)
        pdf.cell(0, 8, f"Average concentration: {avg_conc:.4f} {st.session_state.unit}", ln=True)
        pdf.cell(0, 8, f"Average signal: {avg_signal:.4f}", ln=True)

    # --- S/N ---
    if "sn_ratio" in locals():
        pdf.ln(5)
        pdf.cell(0, 8, f"Signal-to-Noise calculation / Calcul S/N:", ln=True)
        pdf.cell(0, 8, f"S/N: {sn_ratio:.4f}", ln=True)
        if "lod" in locals() and "loq" in locals():
            pdf.cell(0, 8, f"LOD: {lod:.4f} {st.session_state.unit}, LOQ: {loq:.4f} {st.session_state.unit}", ln=True)
    
    # --- Télécharger ---
    pdf_output = "LabT_report.pdf"
    pdf.output(pdf_output)
    st.success(f"PDF report generated / Rapport PDF généré: {pdf_output}")
    st.download_button("Download PDF / Télécharger PDF", pdf_output, file_name=pdf_output)

# Bouton pour générer le rapport
st.button("Generate PDF / Générer PDF", on_click=export_pdf_report)