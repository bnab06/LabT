import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import io, json, os
from datetime import datetime
from scipy import stats
from PIL import Image

# ========================
# 🈹 BILINGUE - Français / English
# ========================
def get_lang():
    return st.session_state.get("lang", "EN")

def T(en, fr):
    LANG = get_lang()
    return fr if LANG == "FR" else en

def set_language():
    lang = st.selectbox("🌐 Language / Langue", ["EN", "FR"], index=0, key="lang_select")
    st.session_state.lang = lang

# ========================
# 🔐 USERS
# ========================
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"admin": "admin123", "user1": "test"}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ------------------------
# LOGIN
# ------------------------
def login():
    users = load_users()
    username = st.text_input(T("Username", "Nom d’utilisateur"), key="login_user").strip().lower()
    password = st.text_input(T("Password", "Mot de passe"), type="password", key="login_pass")

    if st.button(T("Login", "Connexion"), use_container_width=True):
        if username in users and users[username] == password:
            st.session_state.user = username
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error(T("Invalid username or password", "Nom d’utilisateur ou mot de passe invalide"))

# ------------------------
# CHANGE PASSWORD (discret)
# ------------------------
def change_password():
    users = load_users()
    st.subheader(T("Change Password", "Changer le mot de passe"))
    username = st.session_state.user
    old = st.text_input(T("Old Password", "Ancien mot de passe"), type="password", key="old_pw")
    new = st.text_input(T("New Password", "Nouveau mot de passe"), type="password", key="new_pw")
    confirm = st.text_input(T("Confirm Password", "Confirmer le mot de passe"), type="password", key="confirm_pw")
    if st.button(T("Update Password", "Mettre à jour"), use_container_width=True):
        if users[username] != old:
            st.error(T("Incorrect old password", "Ancien mot de passe incorrect"))
        elif new != confirm:
            st.error(T("Passwords do not match", "Les mots de passe ne correspondent pas"))
        else:
            users[username] = new
            save_users(users)
            st.success(T("Password updated!", "Mot de passe mis à jour !"))

# ------------------------
# LINÉARITÉ
# ------------------------
def linearity_tab():
    st.header(T("Linearity", "Linéarité"))

    file = st.file_uploader(T("Upload CSV file", "Importer un fichier CSV"), type="csv", key="csv_lin")
    if not file:
        return

    try:
        df = pd.read_csv(file)
        if df.shape[1] < 2:
            st.error(T("CSV must have at least two columns.", "Le CSV doit contenir au moins deux colonnes."))
            return
    except Exception as e:
        st.error(f"Error reading CSV / Erreur lecture CSV: {e}")
        return

    df.columns = ["Concentration", "Signal"]
    st.dataframe(df)

    x, y = df["Concentration"], df["Signal"]
    slope, intercept, r, _, _ = stats.linregress(x, y)

    st.write(T("Slope", "Pente"), ":", slope)
    st.write(T("Intercept", "Ordonnée à l’origine"), ":", intercept)
    st.write("R²:", round(r ** 2, 4))

    # Courbe
    fig, ax = plt.subplots()
    ax.scatter(x, y, label="Data")
    ax.plot(x, slope * x + intercept, color="red", label=f"y={round(slope,3)}x+{round(intercept,3)}")
    ax.legend()
    st.pyplot(fig)

    st.session_state.slope = slope

    # Choix du type de calcul inconnu
    calc_type = st.selectbox(T("Calculate:", "Calculer :"),
                             [T("Unknown concentration", "Concentration inconnue"),
                              T("Unknown signal", "Signal inconnu")],
                             key="calc_type")

    if calc_type == T("Unknown concentration", "Concentration inconnue"):
        signal_value = st.number_input(T("Enter signal", "Entrer le signal"))
        if signal_value:
            concentration = (signal_value - intercept) / slope
            st.success(f"{T('Calculated concentration','Concentration calculée')}: {concentration:.3f}")
    else:
        conc_value = st.number_input(T("Enter concentration", "Entrer la concentration"))
        if conc_value:
            signal = slope * conc_value + intercept
            st.success(f"{T('Calculated signal','Signal calculé')}: {signal:.3f}")

    # Export PDF
    company = st.text_input(T("Company name for PDF", "Nom de la compagnie pour le PDF"))
    if st.button(T("Export PDF Report", "Exporter le rapport PDF"), use_container_width=True):
        if not company:
            st.warning(T("Please enter company name.", "Veuillez entrer le nom de la compagnie."))
            return
        export_pdf(company, slope, intercept, r, df, st.session_state.user)

# ------------------------
# S/N, LOD, LOQ
# ------------------------
def sn_tab():
    st.header("S/N, LOD, LOQ")

    file = st.file_uploader(T("Upload chromatogram (CSV, PNG, or PDF)", 
                              "Importer un chromatogramme (CSV, PNG ou PDF)"), 
                              type=["csv", "png", "pdf"], key="sn_file")

    if not file:
        return

    if file.type == "text/csv":
        try:
            df = pd.read_csv(file)
            if df.shape[1] < 2:
                st.error(T("CSV must have at least two columns.", "Le CSV doit contenir au moins deux colonnes."))
                return
            df.columns = ["Time", "Signal"]
            st.line_chart(df.set_index("Time"))
            baseline = np.std(df["Signal"])
            signal_max = df["Signal"].max()
            sn = signal_max / baseline
            st.write(f"S/N = {sn:.2f}")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
    else:
        try:
            if file.type == "application/pdf":
                st.info(T("PDF preview not implemented", "Aperçu PDF non implémenté"))
            elif file.type == "image/png":
                st.image(file)
        except Exception as e:
            st.error(f"File preview error: {e}")

# ------------------------
# EXPORT PDF
# ------------------------
def export_pdf(company, slope, intercept, r, df, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, f"{company}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"{T('Generated by','Généré par')} {user}", ln=True)
    pdf.cell(200, 10, f"{T('Date','Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(200, 10, f"Slope/Pente: {round(slope,4)}", ln=True)
    pdf.cell(200, 10, f"Intercept/Ordonnée: {round(intercept,4)}", ln=True)
    pdf.cell(200, 10, f"R²: {round(r**2,4)}", ln=True)

    # Courbe
    plt.figure()
    plt.scatter(df["Concentration"], df["Signal"])
    plt.plot(df["Concentration"], slope*df["Concentration"] + intercept, color="red")
    plt.xlabel("Concentration")
    plt.ylabel("Signal")
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    image = Image.open(buf)
    image.save("temp_plot.png")
    pdf.image("temp_plot.png", x=30, w=150)
    pdf.output("report.pdf")

    with open("report.pdf", "rb") as f:
        st.download_button(T("📄 Download Report", "📄 Télécharger le rapport"), f, file_name="report.pdf")

# ------------------------
# LOGOUT
# ------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.experimental_rerun()

# ------------------------
# MAIN
# ------------------------
def main():
    set_language()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
        return

    user = st.session_state.user

    if user == "admin":
        st.subheader(T("User Management", "Gestion des utilisateurs"))
        users = load_users()
        st.write(list(users.keys()))
        st.button(T("Logout", "Déconnexion"), on_click=lambda: logout())
    else:
        tab = st.radio("", [T("Linearity", "Linéarité"), "S/N"], horizontal=True)
        if tab == T("Linearity", "Linéarité"):
            linearity_tab()
        else:
            sn_tab()

        # Changement mot de passe discret
        with st.expander(T("Change password", "Changer le mot de passe")):
            change_password()

        st.button(T("Logout", "Déconnexion"), on_click=lambda: logout())

if __name__ == "__main__":
    main()