import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import json, os, base64
from datetime import datetime

# ==============================
# CONFIGURATION INITIALE
# ==============================
st.set_page_config(page_title="LabT", layout="wide")

USERS_FILE = "users.json"
LOGO_FILE = "labt_logo.png"

def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "user1": {"password": "user1", "role": "user"},
            "user2": {"password": "user2", "role": "user"},
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)

def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r") as f:
        data = json.load(f)
    normalized = {}
    for k, v in data.items():
        normalized[k.lower()] = v
    return normalized

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def normalize_username(u):
    return u.strip().lower()

# ==============================
# LOGIN / LOGOUT
# ==============================
def login(username, password):
    users = load_users()
    uname = normalize_username(username)
    if uname in users and users[uname]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = uname
        st.session_state.role = users[uname]["role"]
        st.success("✅ Connexion réussie")
    else:
        st.error("❌ Nom d’utilisateur ou mot de passe incorrect")

def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.experimental_rerun()

# ==============================
# LINEARITÉ
# ==============================
def compute_linearity(conc, resp):
    conc = np.array(conc, dtype=float)
    resp = np.array(resp, dtype=float)
    slope, intercept = np.polyfit(conc, resp, 1)
    r2 = np.corrcoef(conc, resp)[0,1]**2
    return slope, intercept, r2

def plot_linearity(conc, resp, slope, intercept, r2, unit):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Données"))
    xline = np.linspace(min(conc), max(conc), 100)
    fig.add_trace(go.Scatter(x=xline, y=slope*xline+intercept, mode="lines", name=f"Fit R²={r2:.4f}"))
    fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Linéarité")
    return fig

# ==============================
# SIGNAL / BRUIT
# ==============================
def compute_sn(signal, noise_zone=None):
    peak = np.max(signal)
    noise_std = np.std(signal if noise_zone is None else signal[noise_zone[0]:noise_zone[1]])
    return peak / noise_std if noise_std != 0 else np.nan, peak, noise_std

def plot_chrom(time, signal):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time, y=signal, mode="lines", name="Signal"))
    fig.update_layout(xaxis_title="Temps", yaxis_title="Signal", title="Chromatogramme")
    return fig

# ==============================
# PDF
# ==============================
def generate_pdf(title, content, company, user):
    if not company.strip():
        st.warning("⚠️ Entrez le nom de l’entreprise avant de générer le rapport.")
        return
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Rapport LabT", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Entreprise : {company}", ln=True)
    pdf.cell(0, 8, f"Utilisateur : {user}", ln=True)
    pdf.cell(0, 8, f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 8, content)
    file_path = "rapport_LabT.pdf"
    pdf.output(file_path)
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.download_button("⬇️ Télécharger le PDF", f, file_name="rapport_LabT.pdf")

# ==============================
# ADMIN
# ==============================
def admin_page():
    st.header("👥 Gestion des utilisateurs")
    action = st.selectbox("Action", ["Ajouter", "Modifier", "Supprimer"])
    uname = st.text_input("Nom d’utilisateur")
    pwd = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["user", "admin"])
    users = load_users()

    def act():
        un = normalize_username(uname)
        if action == "Ajouter":
            users[un] = {"password": pwd, "role": role}
            save_users(users)
            st.success("Utilisateur ajouté ✅")
        elif action == "Modifier":
            if un in users:
                if pwd: users[un]["password"] = pwd
                users[un]["role"] = role
                save_users(users)
                st.success("Utilisateur modifié ✅")
            else:
                st.error("Utilisateur introuvable ❌")
        elif action == "Supprimer":
            if un in users:
                del users[un]; save_users(users)
                st.success("Utilisateur supprimé ✅")
            else:
                st.error("Utilisateur introuvable ❌")

    st.button("Valider", on_click=act)
    st.button("Se déconnecter", on_click=logout)

# ==============================
# UTILISATEUR
# ==============================
def linearity_page():
    st.subheader("📈 Linéarité")
    mode = st.radio("Mode :", ["Téléverser CSV", "Saisie manuelle"])
    unit = st.text_input("Unité de concentration", "µg/mL")

    if mode == "Téléverser CSV":
        file = st.file_uploader("Charger le fichier CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            conc = df.iloc[:,0].values
            resp = df.iloc[:,1].values
            slope, intercept, r2 = compute_linearity(conc, resp)
            fig = plot_linearity(conc, resp, slope, intercept, r2, unit)
            st.plotly_chart(fig)
            st.session_state.slope, st.session_state.intercept = slope, intercept
            st.success(f"Slope={slope:.4f}, Intercept={intercept:.4f}, R²={r2:.4f}")
    else:
        n = st.number_input("Nombre de points", 2, 10, 3)
        conc, resp = [], []
        for i in range(int(n)):
            c = st.number_input(f"Concentration {i+1}", key=f"c{i}")
            r = st.number_input(f"Signal {i+1}", key=f"r{i}")
            conc.append(c); resp.append(r)
        if st.button("Calculer"):
            slope, intercept, r2 = compute_linearity(conc, resp)
            fig = plot_linearity(conc, resp, slope, intercept, r2, unit)
            st.plotly_chart(fig)
            st.session_state.slope, st.session_state.intercept = slope, intercept
            st.success(f"Slope={slope:.4f}, Intercept={intercept:.4f}, R²={r2:.4f}")

    st.divider()
    st.subheader("Calcul inconnu")
    choice = st.radio("Choix :", ["Connaissant signal → concentration", "Connaissant concentration → signal"])
    slope = st.session_state.get("slope")
    intercept = st.session_state.get("intercept")
    if slope is not None:
        if choice.startswith("Connaissant signal"):
            s = st.number_input("Signal mesuré")
            st.info(f"Concentration estimée = {(s - intercept) / slope:.4f} {unit}")
        else:
            c = st.number_input("Concentration")
            st.info(f"Signal estimé = {slope * c + intercept:.4f}")

def sn_page():
    st.subheader("📊 Rapport Signal / Bruit")
    file = st.file_uploader("Charger fichier (CSV, PNG, PDF)", type=["csv", "png", "pdf"])
    if file and file.name.endswith(".csv"):
        df = pd.read_csv(file)
        df.columns = [c.lower() for c in df.columns]
        if "time" in df.columns and "signal" in df.columns:
            st.plotly_chart(plot_chrom(df["time"], df["signal"]))
            s_n, peak, noise = compute_sn(df["signal"])
            st.success(f"S/N={s_n:.2f}, Pic={peak:.2f}, Bruit={noise:.2f}")
            slope = st.session_state.get("slope")
            if slope:
                lod = 3*noise/slope; loq = 10*noise/slope
                st.info(f"LOD={lod:.4f}, LOQ={loq:.4f}")
        else:
            st.error("Le CSV doit contenir 'Time' et 'Signal'.")
    elif file:
        st.warning("Extraction automatique à partir d'image/PDF non encore supportée.")

def change_password():
    users = load_users()
    uname = st.session_state.username
    curr = st.text_input("Mot de passe actuel", type="password")
    newp = st.text_input("Nouveau mot de passe", type="password")
    def apply():
        if users[uname]["password"] != curr:
            st.error("Mot de passe actuel incorrect ❌")
            return
        users[uname]["password"] = newp
        save_users(users)
        st.success("Mot de passe modifié ✅")
    st.button("Appliquer", on_click=apply)

def user_menu():
    st.header(f"Bienvenue {st.session_state.username}")
    choice = st.selectbox("Menu :", ["Linéarité", "Signal/Bruit", "Changer mot de passe", "Déconnexion"])
    if choice == "Linéarité": linearity_page()
    elif choice == "Signal/Bruit": sn_page()
    elif choice == "Changer mot de passe": change_password()
    else: logout()

# ==============================
# MAIN
# ==============================
def main():
    ensure_users_file()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🔬 LabT - Connexion")
        u = st.text_input("Nom d’utilisateur")
        p = st.text_input("Mot de passe", type="password")
        st.button("Se connecter", on_click=login, args=(u, p))
    else:
        if st.session_state.role == "admin":
            admin_page()
        else:
            user_menu()

if __name__ == "__main__":
    main()