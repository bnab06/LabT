---

### 4️⃣ app.py (structure complète moderne, intégrant tout)

```python
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import json
from datetime import datetime
from fpdf import FPDF
import easyocr
import fitz
from PIL import Image

st.set_page_config(page_title="LabT", layout="wide")

USERS_FILE = "users.json"

# --- Gestion utilisateurs ---
def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def login_page():
    st.title("LabT - Connexion")
    users = load_users()
    user_selected = st.selectbox("Choisir l'utilisateur", list(users.keys()))
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if password == users[user_selected]["password"]:
            st.session_state.user = user_selected
            st.session_state.page = "menu"
        else:
            st.error("Mot de passe incorrect")

def admin_page():
    st.header("Gestion utilisateurs (Admin)")
    users = load_users()
    st.subheader("Ajouter un utilisateur")
    new_user = st.text_input("Nom utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    if st.button("Ajouter"):
        if new_user and new_pass:
            users[new_user] = {"password": new_pass}
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté.")
    st.subheader("Supprimer un utilisateur")
    del_user = st.selectbox("Choisir utilisateur à supprimer", list(users.keys()))
    if st.button("Supprimer"):
        if del_user != "admin":
            users.pop(del_user, None)
            save_users(users)
            st.success(f"Utilisateur {del_user} supprimé.")
    if st.button("Retour menu"):
        st.session_state.page = "menu"

def menu_page():
    st.header(f"Connecté en tant que {st.session_state.user}")
    if st.session_state.user == "admin":
        if st.button("Gérer utilisateurs"):
            st.session_state.page = "admin"
    else:
        choice = st.selectbox("Choisir fonctionnalité", ["S/N USP", "Linéarité"])
        if choice == "S/N USP":
            st.session_state.page = "sn"
        elif choice == "Linéarité":
            st.session_state.page = "linearite"
    if st.button("Déconnexion"):
        st.session_state.page = "login"

# --- Fonction S/N USP ---
def sn_page():
    st.header("S/N USP")
    uploaded_file = st.file_uploader("Charger PDF ou PNG", type=["pdf","png"])
    if uploaded_file:
        st.success(f"Fichier chargé: {uploaded_file.name}")
        reader = easyocr.Reader(["en"])
        if uploaded_file.name.endswith(".png"):
            result = reader.readtext(uploaded_file.read())
            st.write(result)
        else:
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            all_results = []
            for page_number in range(len(doc)):
                page = doc.load_page(page_number)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                result = reader.readtext(img)
                all_results.append({"page": page_number+1, "text": result})
            st.write(all_results)
    if st.button("Retour menu principal"):
        st.session_state.page = "menu"

# --- Fonction linéarité ---
def linearite_page():
    st.header("Linéarité")
    method = st.radio("Méthode d'entrée", ["Manuelle", "CSV"])
    conc_unit = st.selectbox("Unité concentration", ["µg/ml", "mg/ml"])
    response_unit = st.selectbox("Réponse", ["Aire", "Absorbance"])
    if method == "Manuelle":
        conc_str = st.text_input("Concentrations séparées par virgule")
        resp_str = st.text_input("Réponses séparées par virgule")
        if st.button("Tracer"):
            try:
                c = [float(x.strip()) for x in conc_str.split(",")]
                r = [float(x.strip()) for x in resp_str.split(",")]
                df = pd.DataFrame({"Concentration": c, "Réponse": r})
                fig = go.Figure(data=go.Scatter(x=df["Concentration"], y=df["Réponse"], mode="markers+lines"))
                fig.update_layout(xaxis_title=f"Concentration ({conc_unit})", yaxis_title=f"Réponse ({response_unit})")
                st.plotly_chart(fig)
                r2 = np.corrcoef(c, r)[0,1]**2
                st.info(f"R² = {r2:.4f}")
            except:
                st.error("Erreur dans la conversion des valeurs")
    elif method == "CSV":
        file_csv = st.file_uploader("Charger CSV", type=["csv"])
        if file_csv:
            df = pd.read_csv(file_csv)
            fig = go.Figure(data=go.Scatter(x=df.iloc[:,0], y=df.iloc[:,1], mode="markers+lines"))
            fig.update_layout(xaxis_title=f"Concentration ({conc_unit})", yaxis_title=f"Réponse ({response_unit})")
            st.plotly_chart(fig)
    if st.button("Retour menu principal"):
        st.session_state.page = "menu"

# --- Session state ---
if "page" not in st.session_state:
    st.session_state.page = "login"
if "user" not in st.session_state:
    st.session_state.user = None

# --- Routing ---
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "menu":
    menu_page()
elif st.session_state.page == "admin":
    admin_page()
elif st.session_state.page == "sn":
    sn_page()
elif st.session_state.page == "linearite":
    linearite_page()