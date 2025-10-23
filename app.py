import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import json
from io import BytesIO

# ---------------- USERS ----------------
USERS_FILE = "users.json"

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ---------------- LOGIN ----------------
def login():
    st.title("LabT - Login / Connexion")
    users = load_users()
    
    username = st.text_input("Username / Utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    lang = st.selectbox("Language / Langue", ["Français", "English"])
    
    if st.button("Login / Connexion"):
        if username.lower() in users and password == users[username.lower()]["password"]:
            st.session_state["user"] = username.lower()
            st.session_state["role"] = users[username.lower()]["role"]
            st.session_state["lang"] = lang
        else:
            st.error("Utilisateur ou mot de passe invalide / Invalid username or password")

# ---------------- LOGOUT ----------------
def logout():
    if st.session_state.get("user"):
        if st.button("Logout / Déconnexion"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun()

# ---------------- CHANGE PASSWORD ----------------
def change_password():
    users = load_users()
    st.subheader("Change Password / Changer mot de passe")
    username = st.session_state["user"]
    old_pw = st.text_input("Old Password / Ancien mot de passe", type="password")
    new_pw = st.text_input("New Password / Nouveau mot de passe", type="password")
    
    if st.button("Update / Mettre à jour"):
        if old_pw == users[username]["password"]:
            users[username]["password"] = new_pw
            save_users(users)
            st.success("Password updated / Mot de passe mis à jour")
        else:
            st.error("Old password incorrect / Ancien mot de passe incorrect")

# ---------------- ADMIN MENU ----------------
def admin_menu():
    st.title("Admin - User Management")
    users = load_users()
    st.subheader("Add / Ajouter user")
    new_user = st.text_input("Username")
    new_pw = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    
    if st.button("Add / Ajouter"):
        users[new_user.lower()] = {"password": new_pw, "role": role}
        save_users(users)
        st.success("User added / Utilisateur ajouté")
    
    st.subheader("Existing users / Utilisateurs existants")
    for u in users:
        st.write(f"{u} - {users[u]['role']}")
        col1, col2 = st.columns(2)
        if col1.button(f"Delete {u}"):
            if u != "admin":
                users.pop(u)
                save_users(users)
                st.experimental_rerun()

# ---------------- LINÉARITÉ ----------------
def linearity_tab():
    st.header("Linearity / Linéarité")
    method = st.radio("Input Method / Méthode d'entrée", ["CSV", "Manual / Manuel"])
    
    df = None
    if method == "CSV":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
    else:
        x_input = st.text_input("X values / Valeurs X (comma separated / séparées par des virgules)")
        y_input = st.text_input("Y values / Valeurs Y (comma separated / séparées par des virgules)")
        if x_input and y_input:
            try:
                x = np.array([float(i) for i in x_input.split(",")])
                y = np.array([float(i) for i in y_input.split(",")])
                df = pd.DataFrame({"X": x, "Y": y})
            except:
                st.error("Invalid input / Entrée invalide")
    
    if df is not None:
        try:
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs
            y_pred = slope * x + intercept
            r2 = np.corrcoef(y, y_pred)[0,1]**2
            st.write(f"Slope / Pente: {slope:.4f}")
            st.write(f"R²: {r2:.4f}")
            
            # Plot
            fig, ax = plt.subplots()
            ax.scatter(x, y, label="Data / Données")
            ax.plot(x, y_pred, color="red", label="Fit / Ajustement")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.legend()
            st.pyplot(fig)
            
            # Unknown calculation
            choice = st.selectbox("Calculate / Calculer", ["Unknown concentration / Concentration inconnue",
                                                          "Unknown signal / Signal inconnu"])
            if choice == "Unknown concentration / Concentration inconnue":
                unknown_signal = st.number_input("Signal / Signal")
                if unknown_signal:
                    conc = (unknown_signal - intercept)/slope
                    st.write(f"Concentration: {conc:.4f}")
            else:
                unknown_conc = st.number_input("Concentration / Concentration")
                if unknown_conc:
                    signal = slope*unknown_conc + intercept
                    st.write(f"Signal: {signal:.4f}")
        except Exception as e:
            st.error(f"Linearity calculation error / Erreur calcul linéarité: {str(e)}")

# ---------------- S/N ----------------
def sn_tab():
    st.header("S/N")
    file = st.file_uploader("Upload CSV/PNG/PDF", type=["csv","png","pdf"])
    if file:
        st.success(f"File uploaded / Fichier chargé: {file.name}")
        st.write("Chromatogram preview / Aperçu chromatogramme:")
        if file.name.endswith("csv"):
            df = pd.read_csv(file)
            st.line_chart(df)
        elif file.name.endswith("png"):
            from PIL import Image
            img = Image.open(file)
            st.image(img)
        else:
            st.info("PDF preview not implemented / Aperçu PDF non implémenté")

# ---------------- MAIN ----------------
if "user" not in st.session_state:
    login()
else:
    st.sidebar.title(f"Welcome {st.session_state['user']}")
    logout()
    
    if st.session_state.get("role") == "admin":
        admin_menu()
    else:
        tab = st.radio("Select / Sélectionner", ["Linearity / Linéarité", "S/N"])
        if tab == "Linearity / Linéarité":
            linearity_tab()
        else:
            sn_tab()
        st.markdown("---")
        change_password()