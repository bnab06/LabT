import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import os

USERS_FILE = "users.json"

# -------------------------------
# Gestion des utilisateurs
# -------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "bb": {"password": "bb", "role": "user"},
            "user": {"password": "user", "role": "user"},
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------------
# Connexion et session
# -------------------------------
def logout():
    st.session_state.logged_in = False
    st.rerun()  # ✅ corrigé

def login():
    users = load_users()
    st.title("🔬 LabT - Connexion")
    selected_user = st.selectbox("Choisir un utilisateur :", list(users.keys()))
    password = st.text_input("Mot de passe :", type="password")

    if st.button("Se connecter"):
        if selected_user in users and users[selected_user]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = selected_user
            st.session_state.role = users[selected_user]["role"]
            st.success("Connexion réussie ✅")
            st.rerun()
        else:
            st.error("Nom d’utilisateur ou mot de passe incorrect ❌")

# -------------------------------
# Page admin : gestion des utilisateurs
# -------------------------------
def manage_users():
    st.header("👥 Gestion des utilisateurs")
    users = load_users()

    action = st.selectbox("Action :", ["Ajouter", "Modifier", "Supprimer"])
    username = st.text_input("Nom d’utilisateur :")
    password = st.text_input("Mot de passe :")
    role = st.selectbox("Rôle :", ["user", "admin"])

    if st.button("Valider"):
        if action == "Ajouter":
            if username in users:
                st.warning("Utilisateur déjà existant.")
            else:
                users[username] = {"password": password, "role": role}
                save_users(users)
                st.success("Utilisateur ajouté ✅")

        elif action == "Modifier":
            if username not in users:
                st.warning("Utilisateur introuvable.")
            else:
                if password:
                    users[username]["password"] = password
                users[username]["role"] = role
                save_users(users)
                st.success("Utilisateur modifié ✅")

        elif action == "Supprimer":
            if username not in users:
                st.warning("Utilisateur introuvable.")
            else:
                del users[username]
                save_users(users)
                st.success("Utilisateur supprimé ✅")

    if st.button("⬅️ Déconnexion"):
        logout()

# -------------------------------
# Page Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Courbe de linéarité")

    conc_input = st.text_input("Concentrations connues (séparées par des virgules)")
    resp_input = st.text_input("Réponses (absorbance ou aire, séparées par des virgules)")

    unknown_type = st.selectbox("Type d'inconnu :", ["Concentration inconnue", "Signal inconnu"])
    unknown_value = st.number_input("Valeur inconnue :", value=0.0, step=0.1)
    unit = st.text_input("Unité :", value="")

    if st.button("Tracer la courbe"):
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.error("Les listes doivent avoir la même taille et ne pas être vides.")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            eq = f"y = {slope:.4f}x + {intercept:.4f}"

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept,
                                     mode="lines", name=f"Droite ({eq})"))
            fig.update_layout(xaxis_title="Concentration", yaxis_title="Signal",
                              title="Courbe de linéarité")
            st.plotly_chart(fig)

            st.success(f"Équation : {eq}")

            if unknown_type == "Concentration inconnue":
                result = (unknown_value - intercept) / slope
                st.info(f"🔹 Concentration inconnue = {result:.4f} {unit}")
            else:
                result = slope * unknown_value + intercept
                st.info(f"🔹 Signal inconnu = {result:.4f} {unit}")

        except Exception as e:
            st.error(f"Erreur dans les calculs : {e}")

    if st.button("⬅️ Déconnexion"):
        logout()

# -------------------------------
# Page S/N
# -------------------------------
def sn_page():
    st.header("📊 Calcul du rapport signal/bruit (S/N)")

    uploaded_file = st.file_uploader("Téléverser un chromatogramme (CSV, PNG ou PDF)")

    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file)
                cols = [c.lower() for c in df.columns]
                if "time" not in cols or "signal" not in cols:
                    st.error("CSV doit contenir les colonnes : Time et Signal")
                    return

                df.columns = [c.lower() for c in df.columns]
                st.line_chart(df, x="time", y="signal")

                noise = df["signal"].std()
                signal = df["signal"].max()
                sn_ratio = signal / noise
                st.success(f"Rapport S/N = {sn_ratio:.2f}")

            except Exception as e:
                st.error(f"Erreur de lecture CSV : {e}")

        else:
            st.warning("Formats PDF et PNG non encore pris en charge.")

    if st.button("⬅️ Déconnexion"):
        logout()

# -------------------------------
# Menu principal
# -------------------------------
def main_menu():
    role = st.session_state.role
    st.title("🧪 LabT - Menu principal")

    if role == "admin":
        manage_users()
    elif role == "user":
        choice = st.selectbox("Choisir une option :", ["Courbe de linéarité", "Calcul S/N"])
        if choice == "Courbe de linéarité":
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Rôle inconnu.")

# -------------------------------
# Lancement
# -------------------------------
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
        main_menu()