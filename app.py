# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
import os

# -------------------------------
# Constants and Config
# -------------------------------
USER_FILE = "users.json"
PDF_LOGO = "logo.png"

# -------------------------------
# Helper Functions
# -------------------------------

def load_users():
    if not os.path.exists(USER_FILE):
        # Default admin user
        users = {"admin": {"password": "admin", "role": "admin"}}
        with open(USER_FILE, "w") as f:
            json.dump(users, f)
    else:
        with open(USER_FILE, "r") as f:
            users = json.load(f)
    return users

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def check_login(username, password):
    users = load_users()
    username_lower = username.lower()
    for user, info in users.items():
        if user.lower() == username_lower and info["password"] == password:
            return info["role"]
    return None

def create_pdf_report(title, user, company, date, fig=None, filename="report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(PDF_LOGO):
        pdf.image(PDF_LOGO, x=10, y=8, w=30)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"User: {user}", ln=True)
    pdf.cell(0, 10, f"Company: {company}", ln=True)
    pdf.cell(0, 10, f"Date: {date}", ln=True)
    if fig is not None:
        fig_file = "temp_plot.png"
        fig.savefig(fig_file)
        pdf.image(fig_file, x=10, y=70, w=190)
        os.remove(fig_file)
    pdf.output(filename)
    st.success(f"Report saved as {filename}")

# -------------------------------
# User Management
# -------------------------------

def admin_screen(current_user):
    st.title("Admin Panel / Panneau Admin")
    users = load_users()
    st.subheader("Manage Users / Gérer les utilisateurs")
    for user, info in users.items():
        st.write(f"{user} ({info['role']})")
    new_user = st.text_input("New username / Nouvel utilisateur")
    new_pass = st.text_input("Password / Mot de passe", type="password")
    new_role = st.selectbox("Role / Rôle", ["user", "admin"])
    if st.button("Add User / Ajouter"):
        if new_user and new_pass:
            users[new_user] = {"password": new_pass, "role": new_role}
            save_users(users)
            st.success(f"User {new_user} added!")
            st.experimental_rerun()

def change_password(username):
    users = load_users()
    st.subheader("Change Password / Changer mot de passe")
    old_pass = st.text_input("Current password / Mot de passe actuel", type="password")
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
    if st.button("Change / Changer"):
        if old_pass == users[username]["password"]:
            users[username]["password"] = new_pass
            save_users(users)
            st.success("Password changed!")
        else:
            st.error("Wrong current password / Mot de passe actuel incorrect")

# -------------------------------
# Linéarité
# -------------------------------

def linearity_screen():
    st.subheader("Linearity / Linéarité")
    choice = st.radio("Choose input / Choisir saisie", ["CSV", "Manual / Manuel"])
    if choice == "CSV":
        uploaded_file = st.file_uploader("Upload CSV / Importer CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
    else:
        n = st.number_input("Number of points / Nombre de points", min_value=2, step=1)
        data = {}
        concentrations = []
        signals = []
        for i in range(int(n)):
            c = st.number_input(f"Concentration {i+1}", key=f"c{i}")
            s = st.number_input(f"Signal {i+1}", key=f"s{i}")
            concentrations.append(c)
            signals.append(s)
        if concentrations and signals:
            df = pd.DataFrame({"Concentration": concentrations, "Signal": signals})
    
    if 'df' in locals():
        x = df["Concentration"].values
        y = df["Signal"].values
        # Linear fit
        slope, intercept = np.polyfit(x, y, 1)
        r2 = np.corrcoef(x, y)[0,1]**2
        st.write(f"Slope / Pente: {slope}, Intercept / Ordonnée à l'origine: {intercept}, R²: {r2}")
        fig, ax = plt.subplots()
        ax.scatter(x, y)
        ax.plot(x, slope*x + intercept, color="red")
        ax.set_xlabel("Concentration")
        ax.set_ylabel("Signal")
        st.pyplot(fig)
        return slope, intercept

# -------------------------------
# S/N
# -------------------------------

def sn_screen():
    st.subheader("Signal / Noise Calculation")
    uploaded_file = st.file_uploader("Upload chromatogram CSV / Importer CSV", type=["csv", "png", "pdf"])
    if uploaded_file:
        st.success("File uploaded!")
        # Logic to parse CSV or display PNG/PDF would go here
        # For simplicity, we show CSV example
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            st.line_chart(df)
        st.info("S/N calculation can now be done on selected region")

# -------------------------------
# Main Screens
# -------------------------------

def user_screen(username):
    st.title(f"User Panel / Panneau Utilisateur ({username})")
    if st.button("Change Password / Changer mot de passe"):
        change_password(username)
    menu = st.radio("Menu", ["Linearity / Linéarité", "S/N Calculation / S/N", "Logout / Déconnexion"])
    if menu.startswith("Linearity"):
        linearity_screen()
    elif menu.startswith("S/N"):
        sn_screen()
    elif menu.startswith("Logout"):
        logout()

def login_screen():
    st.title("Login / Connexion")
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        role = check_login(username, password)
        if role:
            st.session_state['username'] = username
            st.session_state['role'] = role
            st.experimental_rerun()
        else:
            st.error("Wrong username or password / Nom d'utilisateur ou mot de passe incorrect")

def logout():
    st.session_state.clear()
    st.experimental_rerun()

def main():
    if "username" not in st.session_state:
        login_screen()
    else:
        if st.session_state["role"] == "admin":
            admin_screen(st.session_state["username"])
            if st.button("Logout / Déconnexion"):
                logout()
        else:
            user_screen(st.session_state["username"])

if __name__ == "__main__":
    main()