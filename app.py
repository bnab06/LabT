import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import os
from fpdf import FPDF
from datetime import datetime
import base64

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

def login_action(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"Login successful ✅ / Vous êtes connecté en tant que {selected_user}")
    else:
        st.error("Incorrect username or password ❌ / Nom d’utilisateur ou mot de passe incorrect")

def login():
    st.title("🔬 LabT - Login / Connexion")
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", list(load_users().keys()), key="login_user")
    password = st.text_input("Password / Mot de passe:", type="password", key="login_password")
    if st.button("Login / Se connecter"):
        login_action(selected_user, password)
# -------------------------------
# Page admin : gestion des utilisateurs
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer / Delete" and not password):
        st.warning("All fields must be filled / Tous les champs doivent être remplis !")
        return
    users = load_users()
    if action in ["Ajouter / Add"]:
        if username in users:
            st.warning("User already exists / Utilisateur déjà existant.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("User added ✅ / Utilisateur ajouté")
    elif action in ["Modifier / Edit"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("User modified ✅ / Utilisateur modifié")
    elif action in ["Supprimer / Delete"]:
        if username not in users:
            st.warning("User not found / Utilisateur introuvable.")
        else:
            del users[username]
            save_users(users)
            st.success("User deleted ✅ / Utilisateur supprimé")

def manage_users():
    st.header("👥 User Management / Gestion des utilisateurs")
    st.write(f"Logged in as / Connecté en tant que **{st.session_state.username}**")

    action = st.selectbox("Action / Choisir une action:", ["Ajouter / Add", "Modifier / Edit", "Supprimer / Delete"], key="action_admin")
    username = st.text_input("Username / Nom d’utilisateur:", key="username_admin")
    password = st.text_input("Password / Mot de passe:", key="password_admin")
    role = st.selectbox("Role / Rôle:", ["user", "admin"], key="role_admin")
    st.button("Submit / Valider", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Logout / Déconnexion", on_click=logout)

# -------------------------------
# PDF texte uniquement
# -------------------------------
def generate_pdf(title, content_text, company=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report / Rapport LabT", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Company / Compagnie: {company}", ln=True)
    pdf.cell(0, 10, f"User / Utilisateur: {st.session_state.username}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"App: LabT", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 8, content_text)

    pdf_file = f"{title}_{st.session_state.username}.pdf"
    pdf.output(pdf_file)
    return pdf_file

def offer_pdf_actions(pdf_file):
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download / Télécharger PDF</a>', unsafe_allow_html=True)
# -------------------------------
# Linéarité et S/N
# -------------------------------
def linearity_page():
    st.header("📈 Linearity / Linéarité")
    st.write(f"Logged in as / Connecté en tant que **{st.session_state.username}**")

    uploaded_file = st.file_uploader("Upload CSV / Importer CSV:", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.df_linearity = df
            st.dataframe(df.head())

            st.session_state.unit = st.text_input("Unit of unknown / Unité de l’inconnu:", value="mg/L")

            if st.button("Calculate / Calculer"):
                x = df['Concentration'].values
                y = df['Signal'].values

                # Droite de régression
                coeffs = np.polyfit(x, y, 1)
                slope, intercept = coeffs
                st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée à l'origine: {intercept:.4f}")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=x, y=y, mode='markers', name='Data'))
                fig.add_trace(go.Scatter(x=x, y=slope*x + intercept, mode='lines', name='Fit'))
                st.plotly_chart(fig)

                st.session_state.slope = slope
                st.session_state.intercept = intercept

        except Exception as e:
            st.error(f"Error reading CSV / Erreur dans le CSV: {e}")

# -------------------------------
# Signal-to-Noise page
# -------------------------------
def sn_page():
    st.header("🔊 Signal-to-Noise / Rapport S/N")
    df = st.session_state.get('df_linearity', None)
    if df is None:
        st.warning("Please upload a linearity CSV first / Importez d'abord un CSV pour la linéarité")
        return

    use_linear_fit = st.checkbox("Use linear fit for LOQ/LOD / Utiliser la droite de linéarité pour LOQ/LOD", value=True)

    if st.button("Calculate S/N / Calculer S/N"):
        try:
            y = df['Signal'].values
            x = df['Concentration'].values

            noise = np.std(y[:5])  # exemple simplifié: bruit sur les 5 premiers points
            sn_values = y / noise

            sn_max = np.max(sn_values)
            st.write(f"Max S/N: {sn_max:.4f}")

            if use_linear_fit:
                slope = st.session_state.get('slope', None)
                if slope is not None:
                    lod = 3.3 * noise / slope
                    loq = 10 * noise / slope
                    st.write(f"LOD: {lod:.4f} {st.session_state.unit}")
                    st.write(f"LOQ: {loq:.4f} {st.session_state.unit}")

        except Exception as e:
            st.error(f"Error in calculation / Erreur dans les calculs: {e}")

# -------------------------------
# Export PDF S/N
# -------------------------------
def export_sn_pdf():
    if 'df_linearity' not in st.session_state or st.session_state.df_linearity is None:
        st.warning("Upload CSV first / Importez d'abord un CSV")
        return

    company = st.text_input("Company / Compagnie:", value="", key="company_pdf")
    if st.button("Prepare PDF / Préparer PDF"):
        if not company.strip():
            st.error("Please enter company name / Veuillez saisir le nom de la compagnie")
            return

        df = st.session_state.df_linearity
        slope = st.session_state.get('slope', None)
        intercept = st.session_state.get('intercept', None)
        unit = st.session_state.get('unit', "")

        content = "S/N Report / Rapport S/N\n\n"
        content += f"Unit of unknown / Unité de l’inconnu: {unit}\n\n"
        content += f"Slope / Pente: {slope if slope is not None else 'N/A'}\n"
        content += f"Intercept / Ordonnée: {intercept if intercept is not None else 'N/A'}\n\n"

        # Calcul S/N exemple
        y = df['Signal'].values
        noise = np.std(y[:5])
        sn_max = np.max(y / noise)
        content += f"Max S/N: {sn_max:.4f} {unit}\n"

        if slope is not None:
            lod = 3.3 * noise / slope
            loq = 10 * noise / slope
            content += f"LOD: {lod:.4f} {unit}\n"
            content += f"LOQ: {loq:.4f} {unit}\n"

        pdf_file = generate_pdf("S_N_Report", content, company=company)
        offer_pdf_actions(pdf_file)