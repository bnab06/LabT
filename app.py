import streamlit as st
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from datetime import datetime
import plotly.graph_objects as go
import os

# ===============================
# CONFIGURATION DE L'APPLICATION
# ===============================
st.set_page_config(page_title="LabT - Analyse S/N", layout="wide")

USERS_FILE = "users.json"

# ===============================
# FONCTIONS D’UTILISATION
# ===============================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    else:
        return {"admin": {"password": "admin123", "role": "admin"}}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def login():
    st.title("🔐 Connexion à LabT")
    users = load_users()

    username = st.text_input("Nom d’utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = users[username]["role"]
            st.experimental_rerun()
        else:
            st.error("Nom d’utilisateur ou mot de passe incorrect.")

def logout():
    if st.button("🔓 Déconnexion"):
        for key in ["user", "role"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()  # ✅ correction ici

# ===============================
# INTERFACE ADMIN
# ===============================
def admin_page():
    st.header("👑 Panneau Administrateur")
    users = load_users()

    st.subheader("Utilisateurs existants")
    for username, data in users.items():
        st.write(f"- {username} ({data['role']})")

    st.subheader("➕ Ajouter un nouvel utilisateur")
    new_user = st.text_input("Nom d’utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["user", "admin"])

    if st.button("Créer l’utilisateur"):
        if new_user in users:
            st.warning("Cet utilisateur existe déjà.")
        else:
            users[new_user] = {"password": new_pass, "role": role}
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté ✅")
            st.experimental_rerun()

    st.subheader("🗑 Supprimer un utilisateur")
    user_to_delete = st.selectbox("Choisir un utilisateur", list(users.keys()))
    if st.button("Supprimer"):
        if user_to_delete == "admin":
            st.warning("Impossible de supprimer l’administrateur principal.")
        else:
            del users[user_to_delete]
            save_users(users)
            st.success(f"Utilisateur {user_to_delete} supprimé ✅")
            st.experimental_rerun()

# ===============================
# PAGE D’ANALYSE
# ===============================
def analyse_page():
    st.header("📈 Analyse S/N à partir d’un fichier CSV")

    uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine="python")
        except Exception:
            st.error("Erreur de lecture du CSV. Vérifie le séparateur (; ou ,).")
            return

        st.dataframe(df.head())

        time_col = st.selectbox("Colonne Temps", df.columns)
        signal_col = st.selectbox("Colonne Signal", df.columns)

        # Conversion
        df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
        df[signal_col] = pd.to_numeric(df[signal_col], errors="coerce")
        df = df.dropna()

        height_factor = st.slider("Facteur de hauteur pour détection", 0.1, 1.0, 0.3)
        distance = st.slider("Distance minimale entre pics", 1, 100, 20)

        peaks, _ = find_peaks(df[signal_col], height=np.max(df[signal_col]) * height_factor, distance=distance)

        if len(peaks) == 0:
            st.warning("⚠️ Aucun pic détecté. Essaie d’ajuster les paramètres.")
            return

        st.success(f"{len(peaks)} pics détectés ✅")

        # Graphique
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[time_col], y=df[signal_col], mode="lines", name="Signal"))
        fig.add_trace(go.Scatter(
            x=df[time_col].iloc[peaks],
            y=df[signal_col].iloc[peaks],
            mode="markers",
            name="Pics détectés",
            marker=dict(color="red", size=8)
        ))
        st.plotly_chart(fig, use_container_width=True)

        # Calcul S/N
        st.subheader("📊 Calcul du Signal / Bruit")
        peak_index = st.selectbox("Choisir un pic pour calcul", list(range(len(peaks))))
        peak_pos = peaks[peak_index]

        signal = df[signal_col].iloc[peak_pos]
        noise_region = df[signal_col].iloc[max(0, peak_pos - 50):peak_pos]
        noise = np.std(noise_region)

        sn_ratio = signal / noise if noise != 0 else np.nan
        st.metric("Rapport Signal / Bruit (S/N)", f"{sn_ratio:.2f}")

# ===============================
# APPLICATION PRINCIPALE
# ===============================
def main():
    if "user" not in st.session_state:
        login()
        return

    st.sidebar.write(f"👋 Connecté en tant que **{st.session_state['user']}** ({st.session_state['role']})")
    logout()

    if st.session_state["role"] == "admin":
        page = st.sidebar.selectbox("Navigation", ["Analyse", "Admin"])
        if page == "Analyse":
            analyse_page()
        else:
            admin_page()
    else:
        analyse_page()

# ===============================
# LANCEMENT
# ===============================
if __name__ == "__main__":
    main()