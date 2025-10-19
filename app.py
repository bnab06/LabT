import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import json

# --- Chargement utilisateurs ---
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Crée un utilisateur admin par défaut si le fichier n'existe pas
        default_users = {"admin": {"password": "admin", "role": "admin"}}
        save_users(default_users)
        return default_users

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# --- Login ---
def login():
    st.title("LabT")
    users = load_users()
    usernames = list(users.keys())
    username = st.selectbox("Choisissez un utilisateur", usernames)
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if password == users[username]["password"]:
            st.session_state["user"] = username
            st.session_state["role"] = users[username]["role"]
            st.success(f"Connecté en tant que {username}")
            st.experimental_rerun()
        else:
            st.error("Mot de passe incorrect")

# --- Déconnexion ---
def logout():
    if st.button("Déconnexion"):
        st.session_state.clear()
        st.success("Déconnecté ! Rafraîchissez la page pour revenir au login.")

# --- Gestion des utilisateurs (Admin) ---
def manage_users():
    users = load_users()
    st.subheader("Gestion des utilisateurs")
    
    # Ajouter utilisateur
    st.write("Ajouter un nouvel utilisateur")
    new_user = st.text_input("Nom utilisateur", key="new_user")
    new_pass = st.text_input("Mot de passe", type="password", key="new_pass")
    role = st.selectbox("Rôle", ["admin", "user"], key="role_select")
    if st.button("Ajouter utilisateur"):
        if new_user and new_pass:
            if new_user in users:
                st.warning("Utilisateur déjà existant")
            else:
                users[new_user] = {"password": new_pass, "role": role}
                save_users(users)
                st.success("Utilisateur ajouté")
        else:
            st.warning("Nom et mot de passe requis")
    
    # Supprimer utilisateur
    st.write("Supprimer un utilisateur")
    del_user = st.selectbox("Sélectionnez un utilisateur", list(users.keys()), key="del_user")
    if st.button("Supprimer utilisateur"):
        if del_user in users:
            del users[del_user]
            save_users(users)
            st.success("Utilisateur supprimé")

# --- Linéarité ---
def linearity_page():
    st.header("Linéarité")
    conc = st.text_input("Concentrations (séparées par virgules)", key="conc")
    resp = st.text_input("Réponses (aires ou absorbances, séparées par virgules)", key="resp")
    unit = st.selectbox("Unité de concentration", ["µg/mL", "mg/mL"], key="unit")
    unknown_type = st.selectbox("Calculer", ["Concentration inconnue", "Signal inconnu"], key="unknown_type")
    unknown_val = st.text_input(f"Valeur inconnue ({unknown_type})", key="unknown_val")
    
    if st.button("Calculer linéarité"):
        try:
            c = np.array([float(x.strip()) for x in conc.split(",")])
            r = np.array([float(x.strip()) for x in resp.split(",")])
            coef = np.polyfit(c, r, 1)
            slope, intercept = coef
            r2 = np.corrcoef(c, r)[0,1]**2
            st.write(f"Équation: y = {slope:.4f}x + {intercept:.4f}, R² = {r2:.4f}")
            
            fig, ax = plt.subplots()
            ax.scatter(c, r, color="blue")
            ax.plot(c, slope*c + intercept, color="red")
            ax.set_xlabel(f"Concentration ({unit})")
            ax.set_ylabel("Réponse")
            st.pyplot(fig)
            
            if unknown_val:
                unknown_val = float(unknown_val)
                if unknown_type == "Concentration inconnue":
                    result = (unknown_val - intercept)/slope
                    st.success(f"{unknown_type}: {result:.4f} {unit}")
                else:
                    result = slope*unknown_val + intercept
                    st.success(f"{unknown_type}: {result:.4f} aire/absorbance")
        except Exception as e:
            st.error(f"Erreur: {e}")

# --- S/N USP ---
def sn_page():
    st.header("Calcul Signal/Bruit (S/N)")
    uploaded_file = st.file_uploader("Charger CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.write(df.head())
            start = st.number_input("Début de la zone", value=0, min_value=0, max_value=len(df)-1)
            end = st.number_input("Fin de la zone", value=len(df)-1, min_value=0, max_value=len(df)-1)
            signal = df.iloc[start:end, 1].values
            noise = np.std(signal)
            sn = np.max(signal)/noise
            st.success(f"S/N: {sn:.4f}")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=signal, mode='lines', name='Signal'))
            st.plotly_chart(fig)
        except Exception as e:
            st.error(f"Erreur: {e}")

# --- Menu principal ---
def main_menu():
    if "user" not in st.session_state:
        login()
    else:
        st.write(f"Connecté en tant que {st.session_state['user']}")
        logout()
        role = st.session_state["role"]
        if role == "admin":
            manage_users()
        else:
            menu = st.selectbox("Choisissez une fonction", ["Linéarité", "S/N USP"])
            if menu == "Linéarité":
                linearity_page()
            else:
                sn_page()

# --- Exécution ---
if __name__ == "__main__":
    main_menu()