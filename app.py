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
from scipy.signal import find_peaks

# -----------------------
# Utils / Auth
# -----------------------
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    else:
        # Admin par défaut
        users = {"admin": {"password": "admin123", "role": "admin"}}
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        return users

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def check_login(username, password):
    users = load_users()
    username_lower = username.lower()
    if username_lower in users and users[username_lower]["password"] == password:
        return users[username_lower]["role"]
    return None

# -----------------------
# Main screens
# -----------------------
def login_screen():
    st.title("LabT - Login / Connexion")
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        role = check_login(username, password)
        if role:
            st.session_state["username"] = username.lower()
            st.session_state["role"] = role
            st.experimental_rerun()
        else:
            st.warning("Invalid credentials / Identifiants incorrects")

def admin_screen():
    st.title("Admin - Gestion des utilisateurs")
    users = load_users()
    st.subheader("Current users / Utilisateurs actuels")
    for u, info in users.items():
        st.write(f"{u} ({info['role']})")
    st.subheader("Add / Supprimer user")
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    new_role = st.selectbox("Role", ["user", "admin"])
    if st.button("Add user / Ajouter"):
        users[new_user.lower()] = {"password": new_pass, "role": new_role}
        save_users(users)
        st.success("User added")
    del_user = st.text_input("Username to delete")
    if st.button("Delete user / Supprimer"):
        if del_user.lower() in users:
            users.pop(del_user.lower())
            save_users(users)
            st.success("User deleted")
        else:
            st.warning("User not found / Utilisateur introuvable")

def user_screen():
    st.title("User / Utilisateur")
    st.write(f"Welcome / Bienvenue : {st.session_state['username']}")

    # --- Change password ---
    st.subheader("Change password / Modifier mot de passe")
    old_pass = st.text_input("Current password / Mot de passe actuel", type="password")
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
    if st.button("Change / Modifier"):
        users = load_users()
        username = st.session_state["username"]
        if users[username]["password"] == old_pass:
            users[username]["password"] = new_pass
            save_users(users)
            st.success("Password changed / Mot de passe modifié")
        else:
            st.warning("Incorrect current password / Mot de passe actuel incorrect")

    st.subheader("Linearity / Linéarité")
    method = st.radio("Input method / Méthode", ["CSV upload", "Manual / Saisie"])
    if method == "CSV upload":
        file = st.file_uploader("Upload CSV (Concentration, Signal)", type="csv")
        if file:
            df = pd.read_csv(file)
    else:
        n = st.number_input("Number of points", 2, 20, 2)
        concs = []
        signals = []
        for i in range(n):
            c = st.number_input(f"Concentration {i+1}", 0.0)
            s = st.number_input(f"Signal {i+1}", 0.0)
            concs.append(c)
            signals.append(s)
        df = pd.DataFrame({"Concentration": concs, "Signal": signals})

    if 'df' in locals() and not df.empty:
        x = df['Concentration'].values
        y = df['Signal'].values
        slope, intercept = np.polyfit(x, y, 1)
        y_fit = slope * x + intercept
        r2 = np.corrcoef(y, y_fit)[0,1]**2
        st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée à l'origine: {intercept:.4f}, R2: {r2:.4f}")
        fig, ax = plt.subplots()
        ax.scatter(x, y, label="Data")
        ax.plot(x, y_fit, color="red", label="Fit")
        ax.set_xlabel("Concentration")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)

    st.subheader("Signal / Noise")
    sn_file = st.file_uploader("Upload chromatogram CSV (Time, Signal)", type="csv")
    if sn_file:
        sn_df = pd.read_csv(sn_file)
        st.line_chart(sn_df.set_index(sn_df.columns[0]))
        noise_start, noise_end = st.slider("Select noise region", 0, int(sn_df.shape[0])-1, (0, 10))
        noise = sn_df.iloc[noise_start:noise_end,1]
        peak = sn_df.iloc[:,1].max()
        sn_val = peak / noise.std()
        st.write(f"S/N: {sn_val:.2f}")

# -----------------------
# Main app
# -----------------------
def main():
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "role" not in st.session_state:
        st.session_state["role"] = ""

    if st.session_state["username"] == "":
        login_screen()
    else:
        if st.session_state["role"] == "admin":
            admin_screen()
        else:
            user_screen()

if __name__ == "__main__":
    main()