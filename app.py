# ------------------- PARTIE 1 -------------------
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from fpdf import FPDF
import json

# ------------------- SESSION -------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "unit" not in st.session_state:
    st.session_state.unit = ""
if "users" not in st.session_state:
    st.session_state.users = {}
if "slope" not in st.session_state:
    st.session_state.slope = None

# ------------------- USERS -------------------
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {"admin": {"password": "admin", "role": "admin"}}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)
# ------------------- PARTIE 2 -------------------

def login_action(username, password):
    users = st.session_state.users
    user = users.get(username.lower())
    if user and user["password"] == password:
        st.session_state.logged_in = True
        st.session_state.user_role = user["role"]
        st.session_state.current_user = username.lower()
        st.experimental_rerun()
    else:
        st.error("Login failed / Échec de connexion")

def login_page():
    st.title("App: LabT / LabT")
    st.session_state.users = load_users()
    
    username = st.text_input("Username / Nom d'utilisateur:")
    password = st.text_input("Password / Mot de passe:", type="password")
    
    if st.button("Login / Connexion"):
        login_action(username, password)

def main_menu():
    if st.session_state.user_role == "admin":
        option = st.selectbox("Admin Menu:", ["Add / Ajouter user", "Modify / Modifier user", "Delete / Supprimer user"])
        st.button("Go / Valider", on_click=admin_action, args=(option,))
    else:
        option = st.selectbox("User Menu:", ["Modify password / Modifier mot de passe"])
        st.button("Go / Valider", on_click=user_action, args=(option,))

def admin_action(option):
    if option.startswith("Add"):
        add_user()
    elif option.startswith("Modify"):
        modify_user()
    elif option.startswith("Delete"):
        delete_user()

def user_action(option):
    if option.startswith("Modify"):
        modify_password()
# ------------------- PARTIE 3 -------------------

import pandas as pd
import numpy as np
import plotly.graph_objects as go

def load_csv(file):
    try:
        df = pd.read_csv(file)
        st.session_state.df = df
        st.success("CSV loaded / CSV chargé")
        return df
    except Exception as e:
        st.error(f"Error reading CSV / Erreur de lecture CSV: {e}")
        return None

def calculate_unknown(df, factor=1):
    # Exemple : calcul concentration inconnue
    try:
        y = df["Signal"].values
        x = df["Concentration"].values
        slope = np.polyfit(x, y, 1)[0]
        st.session_state.slope = slope
        unknown_signal = df["Unknown"].iloc[-1]
        unknown_conc = unknown_signal / slope
        st.session_state.unknown_conc = unknown_conc
        return unknown_conc
    except Exception as e:
        st.error(f"Error in calculation / Erreur dans les calculs: {e}")
        return None

def sn_classic(df, height_factor=1):
    # Calcul S/N classique
    noise = df["Signal"].iloc[0:5].std()
    peak = df["Signal"].max()
    sn = peak / (height_factor * noise)
    st.session_state.sn_classic = sn
    return sn

def sn_usp(df):
    # Calcul S/N USP basé sur la pente de la courbe de linéarité
    x = df["Concentration"].values
    y = df["Signal"].values
    slope = np.polyfit(x, y, 1)[0]
    noise = df["Signal"].iloc[0:5].std()
    lod = 3.3 * noise / slope
    loq = 10 * noise / slope
    st.session_state.lod = lod
    st.session_state.loq = loq
    return slope, lod, loq

def plot_chromatogram(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Signal"], mode='lines', name="Chromatogram"))
    st.plotly_chart(fig)

def export_pdf(df, filename="report.pdf"):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(0, 10, "App: LabT", ln=True)
    
    # Ajouter unités et valeurs inconnues
    conc_unit = st.session_state.unit if "unit" in st.session_state else ""
    unknown = st.session_state.unknown_conc if "unknown_conc" in st.session_state else "N/A"
    
    pdf.cell(0, 10, f"Unknown concentration: {unknown} {conc_unit}", ln=True)
    
    # Ajouter S/N et LOD/LOQ
    sn_val = st.session_state.sn_classic if "sn_classic" in st.session_state else "N/A"
    lod_val = st.session_state.lod if "lod" in st.session_state else "N/A"
    loq_val = st.session_state.loq if "loq" in st.session_state else "N/A"
    
    pdf.cell(0, 10, f"S/N: {sn_val}", ln=True)
    pdf.cell(0, 10, f"LOD: {lod_val} {conc_unit}, LOQ: {loq_val} {conc_unit}", ln=True)
    
    pdf.output(filename)
    st.success(f"PDF exported: {filename}")
# ------------------- PARTIE 4 -------------------

import json
import streamlit as st
from getpass import getpass

USERS_FILE = "users.json"

# ----------------- Gestion utilisateurs -----------------
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        return users
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def add_user(username, password, role="user"):
    users = load_users()
    users[username.lower()] = {"password": password, "role": role}
    save_users(users)
    st.success(f"User '{username}' added successfully / ajouté avec succès")

def delete_user(username):
    users = load_users()
    key = username.lower()
    if key in users:
        del users[key]
        save_users(users)
        st.success(f"User '{username}' deleted successfully / supprimé avec succès")
    else:
        st.error(f"User '{username}' not found / non trouvé")

def change_password(username, new_password):
    users = load_users()
    key = username.lower()
    if key in users:
        users[key]["password"] = new_password
        save_users(users)
        st.success(f"Password changed successfully / mot de passe modifié")
    else:
        st.error(f"User '{username}' not found / non trouvé")

# ----------------- Login -----------------
def login_page():
    st.title("App: LabT - Login")
    users = load_users()
    
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    
    if st.button("Login / Connexion"):
        key = username.lower()
        if key in users and users[key]["password"] == password:
            st.session_state.user = key
            st.session_state.role = users[key]["role"]
            st.success(f"Login successful ✅ / Vous êtes connecté en tant que {st.session_state.role}")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password / Nom d'utilisateur ou mot de passe incorrect")

# ----------------- Admin menu -----------------
def admin_menu():
    st.subheader("Admin: User Management / Gestion des utilisateurs")
    
    menu = st.selectbox("Choose action / Choisir une action:", 
                        ["Add / Ajouter", "Delete / Supprimer", "Modify password / Modifier mot de passe"])
    
    if menu.startswith("Add"):
        new_user = st.text_input("New username / Nouveau nom d'utilisateur")
        new_pass = st.text_input("Password / Mot de passe", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        if st.button("Add User / Ajouter"):
            if new_user and new_pass:
                add_user(new_user, new_pass, role)
            else:
                st.warning("Please enter username and password / veuillez saisir le nom et mot de passe")
    
    elif menu.startswith("Delete"):
        del_user = st.text_input("Username to delete / Nom d'utilisateur à supprimer")
        if st.button("Delete User / Supprimer"):
            if del_user:
                delete_user(del_user)
            else:
                st.warning("Please enter username / veuillez saisir le nom d'utilisateur")
    
    elif menu.startswith("Modify"):
        mod_user = st.text_input("Username / Nom d'utilisateur")
        new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
        if st.button("Change Password / Modifier"):
            if mod_user and new_pass:
                change_password(mod_user, new_pass)
            else:
                st.warning("Please enter username and new password / veuillez saisir nom et mot de passe")

# ----------------- User menu -----------------
def user_menu():
    st.subheader("User: Change your password / Modifier votre mot de passe")
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
    if st.button("Change / Modifier"):
        change_password(st.session_state.user, new_pass)

# ----------------- Main app -----------------
def main():
    if "user" not in st.session_state:
        login_page()
    else:
        role = st.session_state.role
        if role == "admin":
            admin_menu()
        else:
            user_menu()

if __name__ == "__main__":
    main()