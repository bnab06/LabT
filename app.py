---

### 4️⃣ `app.py`  

Voici un **exemple complet et moderne** pour LabT, sans sidebar, avec connexion, gestion utilisateurs, linéarité, calcul inconnu et S/N à partir de CSV.  

```python
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime

# --- Chargement utilisateurs ---
USERS_FILE = "users.json"

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

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
        else:
            st.error("Mot de passe incorrect")

# --- Déconnexion ---
def logout():
    if st.button("Déconnexion"):
        st.session_state.clear()
        st.experimental_rerun()

# --- Gestion des utilisateurs (Admin) ---
def manage_users():
    users = load_users()
    st.subheader("Gestion des utilisateurs")
    st.write("Ajouter un nouvel utilisateur")
    new_user = st.text_input("Nom utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["admin", "user"])
    if st.button("Ajouter"):
        if new_user and new_pass:
            users[new_user] = {"password": new_pass, "role": role}
            save_users(users)
            st.success("Utilisateur ajouté")
        else:
            st.warning("Nom et mot de passe requis")
    st.write("Supprimer un utilisateur")
    del_user = st.selectbox("Sélectionnez un utilisateur", list(users.keys()))
    if st.button("Supprimer"):
        if del_user in users:
            del users[del_user]
            save_users(users)
            st.success("Utilisateur supprimé")

# --- Linéarité ---
def linearity_page():
    st.header("Linéarité")
    conc = st.text_input("Concentrations (séparées par virgules)")
    resp = st.text_input("Réponses (aires ou absorbances, séparées par virgules)")
    unit = st.selectbox("Unité de concentration", ["µg/mL", "mg/mL"])
    unknown_type = st.selectbox("Calculer", ["Concentration inconnue", "Signal inconnu"])
    unknown_val = st.text_input(f"Valeur inconnue ({unknown_type})")
    if st.button("Calculer"):
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
                else:
                    result = slope*unknown_val + intercept
                st.success(f"{unknown_type}: {result:.4f} {unit if unknown_type=='Concentration inconnue' else 'aire/absorbance'}")
        except Exception as e:
            st.error(f"Erreur: {e}")

# --- S/N USP ---
def sn_page():
    st.header("Calcul Signal/Bruit (S/N)")
    uploaded_file = st.file_uploader("Charger CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            st.write(df.head())
            start = st.number_input("Début de la zone", value=0)
            end = st.number_input("Fin de la zone", value=len(df)-1)
            signal = df.iloc[start:end,1].values
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
        if role=="admin":
            manage_users()
        else:
            menu = st.selectbox("Choisissez une fonction", ["Linéarité", "S/N USP"])
            if menu=="Linéarité":
                linearity_page()
            else:
                sn_page()

# --- Exécution ---
if __name__ == "__main__":
    main_menu()