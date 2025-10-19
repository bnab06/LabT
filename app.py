import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import base64
import os

USERS_FILE = "users.json"

# -------------------------------
# Initialisation session_state
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = None
if "current_page" not in st.session_state:
    st.session_state.current_page = None
if "unit" not in st.session_state:
    st.session_state.unit = "µg/mL"  # valeur par défaut
if "slope" not in st.session_state:
    st.session_state.slope = None

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
    st.session_state.username = ""
    st.session_state.role = None

def login_action(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"Login successful ✅ / Vous êtes connecté en tant que {selected_user}")
        st.experimental_rerun()
    else:
        st.error("Incorrect username or password ❌ / Nom d’utilisateur ou mot de passe incorrect")

def login():
    st.title("🔬 LabT - Login / Connexion")
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", list(load_users().keys()), key="login_user")
    password = st.text_input("Password / Mot de passe:", type="password", key="login_pass")
    st.button("Log in / Se connecter", on_click=login_action, args=(selected_user, password))
# -------------------------------
# Admin : Gestion des utilisateurs (bilingue)
# -------------------------------
def validate_user_action(action, username, password, role, lang="en"):
    if not username or (action != ("Supprimer" if lang=="fr" else "Delete") and not password):
        st.warning("All fields must be filled! / Tous les champs doivent être remplis !")
        return
    users = load_users()
    if action in ["Ajouter", "Add"]:
        if username in users:
            st.warning("User already exists / Utilisateur déjà existant.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("User added ✅ / Utilisateur ajouté ✅")
    elif action in ["Modifier", "Modify"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("User modified ✅ / Utilisateur modifié ✅")
    elif action in ["Supprimer", "Delete"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            del users[username]
            save_users(users)
            st.success("User deleted ✅ / Utilisateur supprimé ✅")

def manage_users():
    st.header("👥 User Management / Gestion des utilisateurs")
    st.write(f"You are logged in as **{st.session_state.username}** / Vous êtes connecté en tant que **{st.session_state.username}**")
    
    lang = st.selectbox("Language / Langue:", ["English", "Français"], key="admin_lang")
    
    actions = ["Add", "Modify", "Delete"] if lang=="English" else ["Ajouter", "Modifier", "Supprimer"]
    action = st.selectbox("Action:", actions, key="action_admin")
    username = st.text_input("Username / Nom d’utilisateur:", key="username_admin")
    password = st.text_input("Password / Mot de passe:", key="password_admin")
    role = st.selectbox("Role / Rôle:", ["user", "admin"], key="role_admin")
    
    st.button("Validate / Valider", on_click=validate_user_action, args=(action, username, password, role, "en" if lang=="English" else "fr"))
    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Linearity Curve / Courbe de linéarité")
    st.write(f"You are logged in as **{st.session_state.username}** / Vous êtes connecté en tant que **{st.session_state.username}**")
    
    conc_input = st.text_input("Known concentrations (comma separated) / Concentrations connues (séparées par des virgules)", key="conc_input")
    resp_input = st.text_input("Responses (comma separated) / Réponses (séparées par des virgules)", key="resp_input")
    unknown_type = st.selectbox("Unknown type / Type d'inconnu:", ["Unknown concentration / Concentration inconnue", "Unknown signal / Signal inconnu"], key="unknown_type")
    unknown_value = st.number_input("Unknown value / Valeur inconnue:", value=0.0, step=0.1, key="unknown_value")
    unit = st.selectbox("Unit / Unité:", ["µg/mL", "mg/L", "g/L"], index=0, key="unit_lin")
    company_name = st.text_input("Company name for PDF / Nom de la compagnie pour le PDF:", value="", key="company_name_lin")
    
    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("Lists must have same length and cannot be empty / Les listes doivent avoir la même taille et ne pas être vides.")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"
            st.session_state.slope = slope
            st.session_state.unit = unit

            # Graph
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope*conc + intercept, mode="lines", name=f"Line ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Linearity Curve / Courbe de linéarité")
            st.plotly_chart(fig)
            st.success(f"Equation / Équation : {eq}")

            if slope != 0:
                if "Concentration inconnue" in unknown_type:
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 Unknown concentration = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 Unknown signal = {result:.4f}")

            def export_pdf_linearity():
                if company_name.strip() == "":
                    st.warning("Please enter company name before exporting PDF / Veuillez saisir le nom de la compagnie avant d'exporter le PDF.")
                    return
                content_text = f"""Linearity Curve / Courbe de linéarité:
Equation / Équation: {eq}
Unknown type / Type inconnu: {unknown_type}
Unknown value / Valeur inconnue: {unknown_value}
Result / Résultat: {result:.4f} {unit if 'Concentration' in unknown_type else ''}
"""
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter le PDF", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs : {e}")
    
    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# S/N
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()

    # USP baseline: first 10% of points
    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_ratio = signal_peak / noise
    sn_usp = signal_peak / noise_usp

    lod = 3 * noise
    loq = 10 * noise

    return sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp

def sn_page():
    st.header("📊 Signal-to-Noise / Rapport signal/bruit (S/N)")
    st.write(f"You are logged in as **{st.session_state.username}** / Vous êtes connecté en tant que **{st.session_state.username}**")
    
    company_name = st.text_input("Company name for PDF / Nom de la compagnie pour le PDF:", value="", key="company_name_sn")
    
    uploaded_file = st.file_uploader("Upload chromatogram CSV / Téléverser un CSV de chromatogramme", type=["csv"], key="sn_upload")
    
    use_linearity = st.checkbox("Use linearity curve for LOD/LOQ / Utiliser la courbe de linéarité pour LOD/LOQ", value=False, key="sn_use_lin")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]
            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV must contain columns 'Time' and 'Signal' / CSV doit contenir les colonnes : Time et Signal")
                return

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Time / Temps", yaxis_title="Signal", title="Chromatogram / Chromatogramme")
            st.plotly_chart(fig)

            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)
            st.success(f"S/N ratio = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (baseline noise / bruit baseline = {noise_usp:.4f})")

            sn_conc = sn_usp_conc = "N/A"
            if st.session_state.slope and st.session_state.slope != 0 and use_linearity:
                sn_conc = sn_ratio / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope
                st.info(f"S/N in concentration: {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N in concentration: {sn_usp_conc:.4f} {st.session_state.unit}")
``            def export_pdf_sn():
                if company_name.strip() == "":
                    st.warning("Please enter company name before exporting PDF / Veuillez saisir le nom de la compagnie avant d'exporter le PDF.")
                    return

                content_text = f"""Signal-to-Noise Report / Rapport Signal/Bruit:
Peak signal / Signal maximum: {signal_peak:.4f}
Noise / Bruit: {noise:.4f}
USP baseline noise / Bruit baseline USP: {noise_usp:.4f}
S/N ratio: {sn_ratio:.4f}
USP S/N: {sn_usp:.4f}
LOD (3*noise): {lod:.4f}
LOQ (10*noise): {loq:.4f}
"""
                if use_linearity and 'sn_conc' in locals():
                    content_text += f"S/N in concentration: {sn_conc:.4f} {st.session_state.unit}\n"
                    content_text += f"USP S/N in concentration: {sn_usp_conc:.4f} {st.session_state.unit}\n"

                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF / Exporter le PDF", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"Error reading CSV / Erreur lors de la lecture du CSV : {e}")

    st.button("⬅️ Logout / Déconnexion", on_click=logout)
# -------------------------------
# Main menu / Menu principal
# -------------------------------
def main_menu():
    # Language selection (English by default)
    if "language" not in st.session_state:
        st.session_state.language = "EN"

    lang = st.selectbox("Language / Langue", ["EN", "FR"], key="lang_select")
    st.session_state.language = lang

    role = st.session_state.role
    if role == "admin":
        st.header("Admin Panel / Panneau Admin")
        manage_users()
    elif role == "user":
        st.header("User Panel / Panneau Utilisateur")
        choice_dict = {
            "EN": ["Linearity Curve", "Signal-to-Noise (S/N)"],
            "FR": ["Courbe de linéarité", "Rapport Signal/Bruit (S/N)"]
        }
        choice = st.selectbox("Choose an option / Choisir une option:", choice_dict[lang], key="user_menu")
        if choice in ["Linearity Curve", "Courbe de linéarité"]:
            linearity_page()
        elif choice in ["Signal-to-Noise (S/N)", "Rapport Signal/Bruit (S/N)"]:
            sn_page()
    else:
        st.error("Unknown role / Rôle inconnu.")

# -------------------------------
# App launcher / Lancement de l'app
# -------------------------------
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "unit" not in st.session_state:
        st.session_state.unit = ""
    if not st.session_state.logged_in:
        login()
    else:
        main_menu()