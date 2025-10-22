import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO

# ---------------------------
# Users database (local)
# ---------------------------
users = {
    "admin": {"password": "admin123", "role": "admin"},
    "user1": {"password": "user123", "role": "user"},
}

# ---------------------------
# Session state
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "lang" not in st.session_state:
    st.session_state.lang = "FR"  # default language

# ---------------------------
# Translation dictionary
# ---------------------------
translations = {
    "FR": {
        "login": "Connexion",
        "username": "Utilisateur",
        "password": "Mot de passe",
        "login_button": "Se connecter",
        "invalid": "Utilisateur ou mot de passe invalide",
        "logout": "Déconnexion",
        "linearity": "Linéarité",
        "sn": "S/N",
        "admin_panel": "Admin",
        "manual_input": "Saisie manuelle (valeurs séparées par des virgules)",
        "upload_csv": "Importer CSV",
        "plot_linearity": "Afficher la courbe de linéarité",
        "calculate_unknown": "Calculer concentration inconnue",
        "export_pdf": "Exporter PDF",
        "company_name": "Nom de la compagnie",
        "unit": "Unité (par défaut µg/mL)"
    },
    "EN": {
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "login_button": "Log in",
        "invalid": "Invalid username or password",
        "logout": "Logout",
        "linearity": "Linearity",
        "sn": "S/N",
        "admin_panel": "Admin",
        "manual_input": "Manual input (comma separated values)",
        "upload_csv": "Upload CSV",
        "plot_linearity": "Plot linearity curve",
        "calculate_unknown": "Calculate unknown concentration",
        "export_pdf": "Export PDF",
        "company_name": "Company Name",
        "unit": "Unit (default µg/mL)"
    }
}

# ---------------------------
# Helper for translation
# ---------------------------
def t(key):
    return translations[st.session_state.lang][key]

# ---------------------------
# Login page
# ---------------------------
def login_page():
    st.title("🔬 LabT")
    lang_choice = st.radio("Language / Langue", ["FR", "EN"], index=0 if st.session_state.lang=="FR" else 1, horizontal=True)
    st.session_state.lang = lang_choice

    username = st.text_input(t("username"))
    password = st.text_input(t("password"), type="password")
    if st.button(t("login_button")):
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = users[username]["role"]
        else:
            st.error(t("invalid"))

# ---------------------------
# Admin panel
# ---------------------------
def admin_panel():
    st.header(t("admin_panel"))
    st.write("Ajouter, supprimer ou modifier des utilisateurs ici")
    # Exemple minimal : ajouter un utilisateur
    with st.expander("Ajouter utilisateur"):
        new_user = st.text_input("Nom d'utilisateur")
        new_pass = st.text_input("Mot de passe", type="password")
        role = st.selectbox("Rôle", ["admin","user"])
        if st.button("Ajouter"):
            if new_user not in users:
                users[new_user] = {"password": new_pass, "role": role}
                st.success("Utilisateur ajouté")
            else:
                st.error("Utilisateur existe déjà")

# ---------------------------
# Linearity page
# ---------------------------
def linearity_page():
    st.header(t("linearity"))
    input_method = st.radio("Méthode d'entrée", [t("manual_input"), t("upload_csv")])

    if input_method == t("manual_input"):
        values = st.text_area("Signaux (comma separated)")
        concs = st.text_area("Concentrations (comma separated)")
        if st.button(t("plot_linearity")):
            try:
                y = np.array([float(v.strip()) for v in values.split(",")])
                x = np.array([float(c.strip()) for c in concs.split(",")])
                coef = np.polyfit(x, y, 1)
                y_fit = np.polyval(coef, x)
                r2 = np.corrcoef(y, y_fit)[0,1]**2
                st.write("R²:", r2)
                st.line_chart({"Signal": y, "Fit": y_fit})
                st.session_state.slope = coef[0]  # pour S/N
            except Exception as e:
                st.error(f"Erreur: {e}")

    else:
        csv_file = st.file_uploader(t("upload_csv"), type=["csv"])
        if csv_file is not None:
            df = pd.read_csv(csv_file)
            st.dataframe(df)
            if st.button(t("plot_linearity")):
                try:
                    x = df.iloc[:,0].values
                    y = df.iloc[:,1].values
                    coef = np.polyfit(x, y, 1)
                    y_fit = np.polyval(coef, x)
                    r2 = np.corrcoef(y, y_fit)[0,1]**2
                    st.write("R²:", r2)
                    st.line_chart({"Signal": y, "Fit": y_fit})
                    st.session_state.slope = coef[0]  # pour S/N
                except Exception as e:
                    st.error(f"Erreur: {e}")

# ---------------------------
# S/N page
# ---------------------------
def sn_page():
    st.header(t("sn"))
    file_type = st.radio("Type de fichier", ["CSV","Image PDF/PNG"])
    if file_type=="CSV":
        csv_file = st.file_uploader("CSV", type=["csv"])
        if csv_file:
            df = pd.read_csv(csv_file)
            st.dataframe(df)
            st.write("Sélectionnez la zone pour calculer S/N (ex: index min:max)")
            zone = st.text_input("Ex: 10:50")
            if st.button("Calculer S/N"):
                try:
                    start,end = [int(i) for i in zone.split(":")]
                    signal = df.iloc[start:end,1].values
                    sn = signal.max()/np.std(signal)
                    st.write("S/N =", sn)
                except Exception as e:
                    st.error(f"Erreur: {e}")

    else:
        st.info("Importer un fichier PDF ou PNG et extraire les données (fonction à compléter)")

# ---------------------------
# Main app
# ---------------------------
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        st.write(f"Bonjour {st.session_state.username} ! [{st.session_state.role}]")
        if st.button(t("logout")):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.experimental_rerun()
        
        menu = []
        if st.session_state.role=="admin":
            menu = [t("linearity"), t("sn"), t("admin_panel")]
        else:
            menu = [t("linearity"), t("sn")]

        choice = st.selectbox("Menu", menu)
        if choice==t("linearity"):
            linearity_page()
        elif choice==t("sn"):
            sn_page()
        elif choice==t("admin_panel"):
            admin_panel()

if __name__=="__main__":
    main()