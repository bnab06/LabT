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
    st.session_state.current_page = None

def login():
    users = load_users()
    st.title("🔬 LabT - Connexion")

    selected_user = st.selectbox("Choisir un utilisateur :", list(users.keys()))
    password = st.text_input("Mot de passe :", type="password")

    if st.button("Se connecter", key="login_btn"):
        if selected_user in users and users[selected_user]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = selected_user
            st.session_state.role = users[selected_user]["role"]
            # Page par défaut après connexion
            st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
            st.success("Connexion réussie ✅")
        else:
            st.error("Nom d’utilisateur ou mot de passe incorrect ❌")

# -------------------------------
# Page admin : gestion des utilisateurs
# -------------------------------
def manage_users():
    st.header("👥 Gestion des utilisateurs")
    users = load_users()

    action = st.selectbox("Action :", ["Ajouter", "Modifier", "Supprimer"], key="action_admin")
    username = st.text_input("Nom d’utilisateur :", key="username_admin")
    password = st.text_input("Mot de passe :", key="password_admin")
    role = st.selectbox("Rôle :", ["user", "admin"], key="role_admin")

    if st.button("Valider", key="validate_admin"):
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

    if st.button("⬅️ Déconnexion", key="logout_admin"):
        logout()

# -------------------------------
# Page Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Courbe de linéarité")

    conc_input = st.text_input("Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Réponses (absorbance ou aire, séparées par des virgules)", key="resp_input")

    unknown_type = st.selectbox("Type d'inconnu :", ["Concentration inconnue", "Signal inconnu"], key="unknown_type")
    unknown_value = st.number_input("Valeur inconnue :", value=0.0, step=0.1, key="unknown_value")
    
    # ⚡ Unités uniquement pour concentration
    unit = st.selectbox("Unité :", ["mg/L", "µg/mL", "g/L"], key="unit")

    try:
        conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
        resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
        if len(conc) != len(resp) or len(conc) == 0:
            st.warning("Les listes doivent avoir la même taille et ne pas être vides.")
            return

        slope, intercept = np.polyfit(conc, resp, 1)
        eq = f"y = {slope:.4f}x + {intercept:.4f}"

        # Graphique
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
        fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept, mode="lines", name=f"Droite ({eq})"))
        fig.update_layout(xaxis_title=f"Concentration ({unit})",
                          yaxis_title="Signal",
                          title="Courbe de linéarité")
        st.plotly_chart(fig)

        st.success(f"Équation : {eq}")

        # Calcul inconnu instantané
        if slope == 0:
            st.error("La pente est nulle, impossible de calculer l’inconnu.")
        else:
            if unknown_type == "Concentration inconnue":
                result = (unknown_value - intercept) / slope
                st.info(f"🔹 Concentration inconnue = {result:.4f} {unit}")
            else:  # signal inconnu
                result = slope * unknown_value + intercept
                st.info(f"🔹 Signal inconnu = {result:.4f}")  # pas d'unité

    except Exception as e:
        st.error(f"Erreur dans les calculs : {e}")

    if st.button("⬅️ Déconnexion", key="logout_linearity"):
        logout()

# -------------------------------
# Page S/N
# -------------------------------
def sn_page():
    st.header("📊 Calcul du rapport signal/bruit (S/N)")

    uploaded_file = st.file_uploader("Téléverser un chromatogramme (CSV)", type=["csv"], key="sn_upload")

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [c.strip().lower() for c in df.columns]

            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV doit contenir les colonnes : Time et Signal")
                return

            # Graphique
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Temps",
                              yaxis_title="Signal",
                              title="Chromatogramme")
            st.plotly_chart(fig)

            # Calcul S/N
            noise = df["signal"].std()
            signal_peak = df["signal"].max()
            sn_ratio = signal_peak / noise
            st.success(f"Rapport S/N = {sn_ratio:.2f}")

        except Exception as e:
            st.error(f"Erreur de lecture CSV : {e}")
    else:
        st.info("Veuillez téléverser un fichier CSV contenant les colonnes Time et Signal.")

    if st.button("⬅️ Déconnexion", key="logout_sn"):
        logout()

# -------------------------------
# Menu principal avec navigation immédiate
# -------------------------------
def main_menu():
    role = st.session_state.role

    if role == "admin":
        st.session_state.current_page = "manage_users"
    elif role == "user":
        # Menu utilisateur : la page change immédiatement selon la sélection
        choice = st.selectbox(
            "Choisir une option :", 
            ["Courbe de linéarité", "Calcul S/N"], 
            key="main_choice"
        )
        if choice == "Courbe de linéarité":
            st.session_state.current_page = "linearity"
        else:
            st.session_state.current_page = "sn"
    else:
        st.error("Rôle inconnu.")

    # Affichage selon la page active
    page = st.session_state.current_page
    if page == "manage_users":
        manage_users()
    elif page == "linearity":
        linearity_page()
    elif page == "sn":
        sn_page()

# -------------------------------
# Lancement
# -------------------------------
if __name__ == "__main__":
    # Initialisation sécurisée
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "role" not in st.session_state:
        st.session_state.role = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = None

    # Affichage selon session
    if not st.session_state.logged_in:
        login()
    else:
        main_menu()