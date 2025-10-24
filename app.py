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
# 🈹 BILINGUE
# ========================
def set_language():
    if "lang" not in st.session_state:
        st.session_state.lang = "EN"
    st.session_state.lang = st.selectbox(
        "🌐 Language / Langue", ["EN", "FR"], index=0 if st.session_state.lang=="EN" else 1, key="lang_select"
    )

def T(en, fr):
    return fr if st.session_state.lang=="FR" else en

# ========================
# 🔐 USERS
# ========================
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"admin":"admin123", "user1":"test"}, f)
    with open(USERS_FILE,"r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE,"w") as f:
        json.dump(users,f,indent=4)

def login():
    users = load_users()
    username = st.text_input(T("Username","Nom d’utilisateur"), key="login_user").strip().lower()
    password = st.text_input(T("Password","Mot de passe"), type="password", key="login_pass")
    if st.button(T("Login","Connexion"), key="login_btn"):
        if username in users and users[username]==password:
            st.session_state.user = username
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error(T("Invalid username or password","Nom d’utilisateur ou mot de passe invalide"))

# ========================
# ⚙️ CHANGE PASSWORD (Discret)
# ========================
def change_password():
    users = load_users()
    st.subheader(T("Change Password","Changer le mot de passe"))
    username = st.session_state.user
    old = st.text_input(T("Old Password","Ancien mot de passe"), type="password", key="old_pw")
    new = st.text_input(T("New Password","Nouveau mot de passe"), type="password", key="new_pw")
    confirm = st.text_input(T("Confirm Password","Confirmer le mot de passe"), type="password", key="confirm_pw")
    if st.button(T("Update Password","Mettre à jour"), key="update_pw"):
        if users[username]!=old:
            st.error(T("Incorrect old password","Ancien mot de passe incorrect"))
        elif new!=confirm:
            st.error(T("Passwords do not match","Les mots de passe ne correspondent pas"))
        else:
            users[username]=new
            save_users(users)
            st.success(T("Password updated!","Mot de passe mis à jour !"))

# ========================
# 🧮 LINÉARITÉ
# ========================
def linearity_tab():
    st.header(T("Linearity","Linéarité"))
    method = st.radio(T("Input method","Méthode d'entrée"), [T("CSV","CSV"), T("Manual","Manuel")], key="lin_method")

    if method==T("CSV","CSV"):
        file = st.file_uploader(T("Upload CSV file","Importer un fichier CSV"), type="csv", key="csv_lin")
        if not file:
            return
        try:
            df = pd.read_csv(file)
            if df.shape[1]<2:
                st.error(T("CSV must have at least two columns","Le CSV doit contenir au moins deux colonnes"))
                return
        except Exception as e:
            st.error(f"{T('Error reading CSV','Erreur lecture CSV')}: {e}")
            return
    else:
        conc_str = st.text_input(T("Enter concentrations separated by commas","Entrer les concentrations séparées par des virgules"), key="manual_conc")
        sig_str = st.text_input(T("Enter signals separated by commas","Entrer les signaux séparés par des virgules"), key="manual_sig")
        if not conc_str or not sig_str:
            return
        try:
            conc_list = [float(x.strip()) for x in conc_str.split(",")]
            sig_list = [float(x.strip()) for x in sig_str.split(",")]
            df = pd.DataFrame({"Concentration":conc_list,"Signal":sig_list})
        except:
            st.error(T("Invalid manual input","Entrée manuelle invalide"))
            return

    st.dataframe(df)
    x, y = df["Concentration"], df["Signal"]
    slope, intercept, r, _, _ = stats.linregress(x,y)
    st.write(T("Slope","Pente"), ":", slope)
    st.write(T("Intercept","Ordonnée à l’origine"), ":", intercept)
    st.write("R²:", round(r**2,4))

    fig, ax = plt.subplots()
    ax.scatter(x,y,label="Data")
    ax.plot(x, slope*x+intercept, color="red", label=f"y={round(slope,3)}x+{round(intercept,3)}")
    ax.legend()
    st.pyplot(fig)
    st.session_state.slope = slope

    # Calcul inconnu
    calc_type = st.selectbox(T("Calculate","Calculer"), [T("Unknown concentration","Concentration inconnue"), T("Unknown signal","Signal inconnu")], key="calc_type")
    if calc_type==T("Unknown concentration","Concentration inconnue"):
        signal_value = st.number_input(T("Enter signal","Entrer le signal"), key="input_signal")
        if signal_value:
            conc_calc = (signal_value - intercept)/slope
            st.success(f"{T('Calculated concentration','Concentration calculée')}: {conc_calc:.3f}")
    else:
        conc_value = st.number_input(T("Enter concentration","Entrer la concentration"), key="input_conc")
        if conc_value:
            signal_calc = slope*conc_value+intercept
            st.success(f"{T('Calculated signal','Signal calculé')}: {signal_calc:.3f}")

    # Export PDF
    if st.button(T("Export PDF Report","Exporter le rapport PDF"), key="export_pdf"):
        company = st.text_input(T("Company name for PDF","Nom de la compagnie pour le PDF"), key="company_name")
        if not company:
            st.warning(T("Please enter company name","Veuillez entrer le nom de la compagnie"))
        else:
            export_pdf(company, slope, intercept, r, df, st.session_state.user)

# ========================
# 📈 S/N, LOD, LOQ
# ========================
def sn_tab():
    st.header("S/N, LOD, LOQ")
    file = st.file_uploader(T("Upload chromatogram (CSV, PNG, PDF)","Importer chromatogramme (CSV, PNG, PDF)"), type=["csv","png","pdf"], key="sn_file")
    if not file:
        return

    # Slider pour sélectionner zone
    zone_start = st.number_input(T("Zone start","Début de la zone"), value=0.0, key="zone_start")
    zone_end = st.number_input(T("Zone end","Fin de la zone"), value=1.0, key="zone_end")

    if file.type=="text/csv":
        try:
            df = pd.read_csv(file)
            if df.shape[1]<2:
                st.error(T("CSV must have at least two columns","Le CSV doit contenir au moins deux colonnes"))
                return
            df.columns = ["Time","Signal"]
            df_zone = df[(df["Time"]>=zone_start) & (df["Time"]<=zone_end)]
            st.line_chart(df_zone.set_index("Time"))
            baseline = np.std(df_zone["Signal"])
            signal_max = df_zone["Signal"].max()
            sn = signal_max/baseline
            st.write(f"S/N = {sn:.2f}")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
    else:
        try:
            if file.type=="image/png":
                img = Image.open(file)
                st.image(img)
                st.info(T("Manual S/N calculation for image not implemented","Calcul S/N manuel pour image non implémenté"))
            elif file.type=="application/pdf":
                st.info(T("PDF preview not implemented","Aperçu PDF non implémenté"))
        except Exception as e:
            st.error(f"File preview error: {e}")

# ========================
# 📑 PDF EXPORT
# ========================
def export_pdf(company,slope,intercept,r,df,user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",14)
    pdf.cell(200,10,f"{company}",ln=True,align="C")
    pdf.set_font("Arial","",12)
    pdf.cell(200,10,f"{T('Generated by','Généré par')} {user}",ln=True)
    pdf.cell(200,10,f"{T('Date','Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}",ln=True)
    pdf.cell(200,10,f"Slope/Pente: {round(slope,4)}",ln=True)
    pdf.cell(200,10,f"Intercept/Ordonnée: {round(intercept,4)}",ln=True)
    pdf.cell(200,10,f"R²: {round(r**2,4)}",ln=True)
    plt.figure()
    plt.scatter(df["Concentration"], df["Signal"])
    plt.plot(df["Concentration"], slope*df["Concentration"]+intercept, color="red")
    plt.xlabel("Concentration")
    plt.ylabel("Signal")
    buf = io.BytesIO()
    plt.savefig(buf,format="png")
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
        st.session_state.logged_in=False

    if not st.session_state.logged_in:
        login()
        return

    user = st.session_state.user

    if user=="admin":
        st.subheader(T("User Management","Gestion des utilisateurs"))
        if st.button(T("Add User","Ajouter un utilisateur")):
            st.info("Add user functionality")
        if st.button(T("Delete User","Supprimer un utilisateur")):
            st.info("Delete user functionality")
        if st.button(T("Modify User","Modifier un utilisateur")):
            st.info("Modify user functionality")
    else:
        tab = st.radio("", [T("Linearity","Linéarité"),"S/N"], horizontal=True)
        if tab==T("Linearity","Linéarité"):
            linearity_tab()
        else:
            sn_tab()

        if st.button(T("Change Password","Changer le mot de passe"), key="discrete_pw_btn"):
            change_password()

    if st.button(T("Logout","Déconnexion"), key="logout_btn"):
        st.session_state.logged_in=False
        st.session_state.user=None
        st.experimental_rerun()

if __name__=="__main__":
    main()