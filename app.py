import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import io, json, os
from datetime import datetime
from scipy import stats
from PIL import Image
from matplotlib.widgets import RectangleSelector

# ========================
# 🈹 BILINGUE - Français / English
# ========================
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

def T(en, fr):
    return fr if st.session_state.lang == "FR" else en

def set_language():
    st.session_state.lang = st.selectbox("🌐 Language / Langue", ["EN", "FR"], index=0, key="lang_select")

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

# ========================
# ⚙️ CHANGE PASSWORD - Profil
# ========================
def change_password():
    users = load_users()
    st.header(T("Profile", "Profil"))
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

# ========================
# 🧮 LINÉARITÉ
# ========================
def linearity_tab():
    st.header(T("Linearity", "Linéarité"))

    choice = st.radio(T("Input method", "Mode de saisie"), [T("CSV Upload", "Importer CSV"), T("Manual input", "Saisie manuelle")], horizontal=True)

    if choice == T("CSV Upload", "Importer CSV"):
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
    else:
        conc_input = st.text_input(T("Enter concentrations separated by commas", "Entrer concentrations séparées par des virgules"))
        signal_input = st.text_input(T("Enter signals separated by commas", "Entrer signaux séparés par des virgules"))
        if not conc_input or not signal_input:
            return
        try:
            df = pd.DataFrame({
                "Concentration": [float(x) for x in conc_input.split(",")],
                "Signal": [float(x) for x in signal_input.split(",")]
            })
        except:
            st.error(T("Invalid input", "Entrée invalide"))
            return

    df.columns = ["Concentration", "Signal"]
    st.dataframe(df)

    x, y = df["Concentration"], df["Signal"]
    slope, intercept, r_value, _, _ = stats.linregress(x, y)
    st.write(T("Slope", "Pente"), ":", slope)
    st.write(T("Intercept", "Ordonnée à l’origine"), ":", intercept)
    st.write("R²:", round(r_value ** 2, 4))

    # Courbe
    fig, ax = plt.subplots()
    ax.scatter(x, y, label="Data")
    ax.plot(x, slope * x + intercept, color="red", label=f"y={round(slope,3)}x+{round(intercept,3)}")
    ax.legend()
    st.pyplot(fig)

    st.session_state.slope = slope

    calc_type = st.selectbox(T("Calculate:", "Calculer :"),
                             [T("Unknown concentration", "Concentration inconnue"),
                              T("Unknown signal", "Signal inconnu")], key="calc_type")

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

    company = st.text_input(T("Company name for PDF", "Nom de la compagnie pour le PDF"))
    if st.button(T("Export PDF Report", "Exporter le rapport PDF"), use_container_width=True):
        if not company:
            st.warning(T("Please enter company name.", "Veuillez entrer le nom de la compagnie."))
            return
        export_pdf(company, slope, intercept, r_value, df, st.session_state.user)

# ========================
# 📈 S/N, LOD, LOQ
# ========================
def sn_tab():
    st.header(T("S/N, LOD, LOQ", "S/N, LOQ, LOD"))

    uploaded_file = st.file_uploader(T("Upload chromatogram (CSV, PNG, PDF)", 
                                       "Importer chromatogramme (CSV, PNG, PDF)"),
                                     type=["csv","png","pdf"], key="sn_file")
    if not uploaded_file:
        return

    data = None
    if uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
        if df.shape[1] < 2:
            st.error(T("CSV must have at least two columns", "Le CSV doit contenir au moins deux colonnes"))
            return
        df.columns = ["Time", "Signal"]
        data = df
        st.line_chart(df.set_index("Time"))
    else:
        try:
            img = Image.open(uploaded_file)
            st.image(img)
            # TODO: digitize image to extract data
        except Exception as e:
            st.error(f"File preview error: {e}")
            return

    # Slider pour sélectionner portion
    if data is not None:
        start, end = st.slider(T("Select time range for S/N", "Choisir la plage pour S/N"), float(data["Time"].min()), float(data["Time"].max()), (float(data["Time"].min()), float(data["Time"].max())))
        subset = data[(data["Time"] >= start) & (data["Time"] <= end)]
        baseline = np.std(subset["Signal"])
        signal_max = subset["Signal"].max()
        sn_classic = signal_max / baseline
        st.write(f"{T('Classic S/N','S/N classique')} = {sn_classic:.2f}")
        if "slope" in st.session_state:
            loq = 10 * baseline / st.session_state.slope
            lod = 3.3 * baseline / st.session_state.slope
            st.write(f"{T('LOD','LOD')} = {lod:.3f}")
            st.write(f"{T('LOQ','LOQ')} = {loq:.3f}")

# ========================
# 📑 PDF EXPORT
# ========================
def export_pdf(company, slope, intercept, r_value, df, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, f"{company}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"{T('Generated by','Généré par')} {user}", ln=True)
    pdf.cell(200, 10, f"{T('Date','Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(200, 10, f"Slope/Pente: {round(slope,4)}", ln=True)
    pdf.cell(200, 10, f"Intercept/Ordonnée: {round(intercept,4)}", ln=True)
    pdf.cell(200, 10, f"R²: {round(r_value**2,4)}", ln=True)

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

    with open("report.pdf","rb") as f:
        st.download_button(T("📄 Download Report","📄 Télécharger le rapport"), f, file_name="report.pdf")

# ========================
# 🧭 MAIN
# ========================
def main():
    set_language()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
        return

    user = st.session_state.user

    if user == "admin":
        st.header(T("User Management","Gestion des utilisateurs"))
        # Boutons Add, Delete, Modify
        users = load_users()
        if st.button(T("Add User","Ajouter utilisateur")):
            users[f"user{len(users)}"] = "test"
            save_users(users)
            st.success(T("User added","Utilisateur ajouté"))
        if st.button(T("Delete User","Supprimer utilisateur")):
            if "user1" in users:
                del users["user1"]
                save_users(users)
                st.success(T("User deleted","Utilisateur supprimé"))
        if st.button(T("Modify User","Modifier utilisateur")):
            users["user1"] = "newpass"
            save_users(users)
            st.success(T("User modified","Utilisateur modifié"))
    else:
        tab = st.radio("", [T("Linearity", "Linéarité"), "S/N"], horizontal=True)
        if tab == T("Linearity", "Linéarité"):
            linearity_tab()
        else:
            sn_tab()

        # Profil séparé
        change_password()

    if st.button(T("Logout","Déconnexion"), use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.experimental_rerun()

if __name__ == "__main__":
    main()