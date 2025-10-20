# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import json
import os

# ---------------------------
# Utils : Gestion utilisateurs
# ---------------------------
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        # Création fichier par défaut avec un admin et 2 users
        default_users = {
            "admin": {"password": "admin123", "role": "admin"},
            "user1": {"password": "user123", "role": "user"},
            "user2": {"password": "user123", "role": "user"}
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f)
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    return users

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def check_login(username, password):
    users = load_users()
    username = username.lower()
    if username in users and users[username]["password"] == password:
        return users[username]["role"]
    return None

def change_password(username, new_password):
    users = load_users()
    username = username.lower()
    users[username]["password"] = new_password
    save_users(users)

# ---------------------------
# Utils : Linéarité
# ---------------------------
def linearity_calc(df):
    # df must have 'Concentration' and 'Signal'
    x = df['Concentration'].values
    y = df['Signal'].values
    slope, intercept = np.polyfit(x, y, 1)
    return slope, intercept, x, y

def calc_unknown_conc(signal, slope, intercept):
    return (signal - intercept)/slope

def calc_unknown_signal(conc, slope, intercept):
    return slope*conc + intercept

# ---------------------------
# Utils : S/N
# ---------------------------
def sn_classic(yvals, noise_region=None):
    s = np.array(yvals)
    peak = np.max(s)
    if noise_region is not None:
        noise = s[noise_region[0]:noise_region[1]]
        noise_std = np.std(noise)
    else:
        noise_std = np.std(s[:int(len(s)*0.1)])  # 10% début
    sn_ratio = peak / noise_std if noise_std !=0 else np.nan
    return sn_ratio, peak, noise_std

def sn_usp(yvals, baseline_region=None):
    s = np.array(yvals)
    peak = np.max(s)
    if baseline_region is not None:
        baseline = s[baseline_region[0]:baseline_region[1]]
        noise_std = np.std(baseline)
    else:
        noise_std = np.std(s[:int(len(s)*0.1)])
    sn_ratio = peak / (2*noise_std) if noise_std !=0 else np.nan
    return sn_ratio, peak, noise_std

# ---------------------------
# Utils : PDF export
# ---------------------------
def export_pdf(results, plots, user, company):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Lab Report - {company}", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"User: {user} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1)
    pdf.ln(10)
    for key, val in results.items():
        pdf.cell(0, 10, f"{key}: {val}", ln=1)
    for i, plot in enumerate(plots):
        plot.savefig(f"temp_plot_{i}.png")
        pdf.image(f"temp_plot_{i}.png", w=180)
    pdf_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(pdf_file)
    return pdf_file

# ---------------------------
# Interface principale
# ---------------------------
def login_screen():
    st.title("LabT - Login / Connexion")
    lang = st.radio("Language / Langue", ["English", "Français"])
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        role = check_login(username, password)
        if role:
            st.session_state['username'] = username.lower()
            st.session_state['role'] = role
            st.session_state['logged_in'] = True
        else:
            st.error("Invalid credentials / Identifiants incorrects")

def admin_screen():
    st.header("Admin Panel / Panneau Admin")
    users = load_users()
    st.subheader("Current users / Utilisateurs actuels")
    st.write(users)
    st.subheader("Add / Delete user / Ajouter / Supprimer utilisateur")
    new_user = st.text_input("New username / Nouveau nom")
    new_pass = st.text_input("Password / Mot de passe")
    if st.button("Add user / Ajouter"):
        users[new_user.lower()] = {"password": new_pass, "role": "user"}
        save_users(users)
        st.success("User added / Utilisateur ajouté")
    del_user = st.text_input("Username to delete / Supprimer")
    if st.button("Delete user / Supprimer"):
        if del_user.lower() in users:
            del users[del_user.lower()]
            save_users(users)
            st.success("User deleted / Utilisateur supprimé")
        else:
            st.error("User not found / Utilisateur non trouvé")

def user_screen():
    st.header("LabT Application")
    tab = st.radio("Select mode / Choisir le mode", ["Linearity / Linéarité", "Signal-to-Noise S/N"])
    
    if tab == "Linearity / Linéarité":
        st.subheader("Upload CSV or enter manually / Importer CSV")
        file = st.file_uploader("Upload CSV / Importer CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            slope, intercept, x, y = linearity_calc(df)
            st.write(f"Slope / Pente: {slope:.4f}, Intercept: {intercept:.4f}")
            fig, ax = plt.subplots()
            ax.scatter(x, y, label="Data")
            ax.plot(x, slope*x+intercept, 'r', label="Fit")
            ax.set_xlabel("Concentration")
            ax.set_ylabel("Signal")
            ax.legend()
            st.pyplot(fig)
            st.subheader("Calculate unknown / Calcul inconnu")
            unknown_type = st.radio("Type / Type", ["Signal -> Conc", "Conc -> Signal"])
            if unknown_type == "Signal -> Conc":
                sig = st.number_input("Signal")
                if st.button("Calculate"):
                    conc = calc_unknown_conc(sig, slope, intercept)
                    st.success(f"Concentration = {conc:.4f}")
            else:
                conc = st.number_input("Concentration")
                if st.button("Calculate"):
                    sig = calc_unknown_signal(conc, slope, intercept)
                    st.success(f"Signal = {sig:.4f}")

    elif tab == "Signal-to-Noise S/N":
        st.subheader("Upload CSV / Importer CSV")
        file = st.file_uploader("Upload CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            yvals = df['Signal'].values
            st.subheader("Select region for noise / Choisir la zone de bruit")
            noise_start = st.number_input("Start index", min_value=0, max_value=len(yvals)-1, value=0)
            noise_end = st.number_input("End index", min_value=0, max_value=len(yvals)-1, value=len(yvals)//10)
            sn, peak, noise_std = sn_classic(yvals, noise_region=(noise_start, noise_end))
            st.success(f"S/N classic: {sn:.2f}, Peak: {peak:.2f}, Noise std: {noise_std:.2f}")
            fig, ax = plt.subplots()
            ax.plot(yvals, label="Signal")
            ax.axvspan(noise_start, noise_end, color='red', alpha=0.2, label="Noise region")
            ax.legend()
            st.pyplot(fig)

def change_password_screen():
    st.header("Change Password / Changer mot de passe")
    old_pass = st.text_input("Old password / Ancien mot de passe", type="password")
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
    if st.button("Change / Changer"):
        username = st.session_state['username']
        users = load_users()
        if users[username]["password"] == old_pass:
            change_password(username, new_pass)
            st.success("Password changed / Mot de passe changé")
        else:
            st.error("Old password incorrect / Ancien mot de passe incorrect")

def app():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if not st.session_state['logged_in']:
        login_screen()
    else:
        role = st.session_state['role']
        if role == "admin":
            admin_screen()
        else:
            user_screen()
            change_password_screen()

if __name__ == "__main__":
    app()