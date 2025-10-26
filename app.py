import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# ----------------- Config -----------------
st.set_page_config(page_title="LabT", layout="wide")

# ----------------- Users JSON (temp hardcoded) -----------------
users = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"}
}

# ----------------- Translations -----------------
LANG = {
    "en": {
        "login":"Login","password":"Password","submit":"Submit","sn":"S/N",
        "linearity":"Linearity","invalid":"Invalid credentials","powered":"Powered by BnB",
        "admin_panel":"Admin Panel","manage_users":"Manage Users","modify":"Modify",
        "delete":"Delete","input_type":"Input type","csv":"CSV","manual":"Manual","unit":"Unit",
        "formulas":"Formulas","select_region":"Select region for S/N",
        "upload_file":"Upload image/pdf/csv","logout":"Logout",
        "export_pdf":"Export PDF","download_pdf":"Download PDF","download_csv":"Download CSV",
        "concentration":"Concentration","signal":"Signal",
        "formula_text":"y = slope * X + intercept\nLOD = 3.3 * SD / slope\nLOQ = 10 * SD / slope",
        "slope":"Slope","intercept":"Intercept","r2":"R²","sn_classic":"S/N Classic",
        "sn_usp":"S/N USP","lod":"LOD","loq":"LOQ"
    },
    "fr": {
        "login":"Utilisateur","password":"Mot de passe","submit":"Valider","sn":"S/N",
        "linearity":"Linéarité","invalid":"Identifiants invalides","powered":"Powered by BnB",
        "admin_panel":"Panneau Admin","manage_users":"Gestion des utilisateurs","modify":"Modifier",
        "delete":"Supprimer","input_type":"Type d'entrée","csv":"CSV","manual":"Manuel","unit":"Unité",
        "formulas":"Formules","select_region":"Sélectionner la zone pour S/N",
        "upload_file":"Importer image/pdf/csv","logout":"Déconnexion",
        "export_pdf":"Exporter en PDF","download_pdf":"Télécharger PDF","download_csv":"Télécharger CSV",
        "concentration":"Concentration","signal":"Signal",
        "formula_text":"y = pente * X + intercept\nLOD = 3.3 * SD / pente\nLOQ = 10 * SD / pente",
        "slope":"Pente","intercept":"Ordonnée à l’origine","r2":"R²","sn_classic":"S/N Classique",
        "sn_usp":"S/N USP","lod":"LOD","loq":"LOQ"
    }
}

def t(key):
    return LANG[st.session_state.lang][key]

# ----------------- Session -----------------
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_role" not in st.session_state: st.session_state.user_role = None
if "lang" not in st.session_state: st.session_state.lang = "fr"

# ----------------- Login -----------------
def login_panel():
    st.title("LabT")
    st.selectbox("Language / Langue", ["fr","en"], key="lang", on_change=lambda: st.experimental_rerun())
    user = st.text_input(t("login"))
    pwd = st.text_input(t("password"), type="password")
    if st.button(t("submit"), key="login_btn"):
        user_lower = user.lower()
        for u in users:
            if u.lower() == user_lower and users[u]["password"] == pwd:
                st.session_state.logged_in = True
                st.session_state.user_role = users[u]["role"]
                st.experimental_rerun()
        else:
            st.error(t("invalid"))
    st.markdown("<p style='text-align:center;font-size:12px;color:gray;margin-top:50px;'>"+t("powered")+"</p>", unsafe_allow_html=True)

# ----------------- Logout -----------------
def logout():
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.experimental_rerun()

# ----------------- Main App -----------------
def main_app():
    st.sidebar.title("Menu")
    if st.session_state.user_role == "admin":
        menu = st.sidebar.radio("Menu", [t("admin_panel")])
    else:
        menu = st.sidebar.radio("Menu", [t("linearity"), t("sn")])
    st.sidebar.button(t("logout"), on_click=logout, key="logout_btn")

    if menu == t("linearity"): linear_panel()
    elif menu == t("sn"): sn_panel()
    elif menu == t("admin_panel"): admin_panel()

# ----------------- Admin -----------------
def admin_panel():
    st.title(t("admin_panel"))
    st.write(t("manage_users"))
    for u in list(users.keys()):
        cols = st.columns([2,1,1])
        cols[0].write(f"{u} - role: {users[u]['role']}")
        if cols[1].button(t("modify"), key=f"mod_{u}"):
            new_pwd = st.text_input(f"Nouveau mot de passe pour {u}", type="password", key=f"pwd_{u}")
            if new_pwd:
                users[u]["password"] = new_pwd
                st.success(f"Mot de passe pour {u} mis à jour")
        if cols[2].button(t("delete"), key=f"del_{u}"):
            if u != "admin":
                users.pop(u)
                st.success(f"{u} supprimé")
                st.experimental_rerun()

# ----------------- Linearity -----------------
def linear_panel():
    st.title(t("linearity"))
    if st.button(t("formulas")):
        st.info(t("formula_text"))
    input_type = st.radio(t("input_type"), [t("csv"), t("manual")])
    df = None
    if input_type == t("csv"):
        file = st.file_uploader("CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        conc = st.text_area(t("concentration") + " (comma-separated)")
        signal = st.text_area(t("signal") + " (comma-separated)")
        if conc and signal:
            try:
                df = pd.DataFrame({
                    "Concentration":[round(float(x),4) for x in conc.split(",")],
                    "Signal":[round(float(x),4) for x in signal.split(",")]
                })
            except:
                st.warning("Invalid manual input")

    unit = st.selectbox(t("unit"), ["µg/mL","mg/mL"])
    if df is not None:
        X = df["Concentration"].values.reshape(-1,1)
        y = df["Signal"].values
        reg = LinearRegression().fit(X,y)
        slope = round(reg.coef_[0],4)
        intercept = round(reg.intercept_,4)
        r2 = round(r2_score(y, reg.predict(X)),4)
        st.write(f"{t('slope')}: {slope}, {t('r2')}: {r2}")

        plt.figure()
        plt.scatter(df["Concentration"], df["Signal"])
        plt.plot(df["Concentration"], reg.predict(X), 'r')
        plt.xlabel(f"{t('concentration')} ({unit})")
        plt.ylabel(t("signal"))
        st.pyplot(plt)

        # Export PDF (safe in memory)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 12)
        pdf.cell(0,10,f"{t('slope')}: {slope}", ln=1)
        pdf.cell(0,10,f"{t('intercept')}: {intercept}", ln=1)
        pdf.cell(0,10,f"{t('r2')}: {r2}", ln=1)
        pdf_io = io.BytesIO()
        pdf.output(pdf_io)
        st.download_button(t("download_pdf"), pdf_io.getvalue(), file_name="linearity.pdf")
        st.session_state.linear_slope = slope

# ----------------- Signal / Noise -----------------
def sn_panel():
    st.title(t("sn"))
    file = st.file_uploader(t("upload_file"), type=["png","jpg","pdf","csv"])
    signal = None

    if file:
        ext = file.name.split(".")[-1].lower()
        if ext == "csv":
            df = pd.read_csv(file)
            st.dataframe(df)
            if "Signal" in df.columns: signal = df["Signal"].values
        elif ext in ["png","jpg","jpeg"]:
            img = Image.open(file)
            st.image(img, caption=file.name)
            arr = np.array(img.convert("L"))
            signal = arr.max(axis=0)
        elif ext == "pdf":
            st.write("📄 " + file.name)
            file_bytes = file.read()
            st.download_button("📥 Télécharger le PDF original", data=file_bytes, file_name=file.name)
            st.info("Affichage natif PDF impossible sur Streamlit Cloud, mais le fichier est prêt à télécharger.")

    if signal is not None:
        start, end = st.slider(t("select_region"), 0, len(signal)-1, (0,len(signal)//2))
        region_signal = signal[start:end+1]
        sn_classic = np.max(region_signal)/np.std(region_signal)
        sn_usp = np.mean(region_signal)/np.std(region_signal)
        st.write(f"{t('sn_classic')}: {round(sn_classic,4)}, {t('sn_usp')}: {round(sn_usp,4)}")

        if "linear_slope" in st.session_state:
            slope = st.session_state.linear_slope
            sd = np.std(region_signal)
            lod = round(3.3*sd/slope,4)
            loq = round(10*sd/slope,4)
            st.write(f"{t('lod')}: {lod}, {t('loq')}: {loq}")

        csv_io = io.StringIO()
        pd.DataFrame({"Signal":region_signal}).to_csv(csv_io, index=False)
        st.download_button(t("download_csv"), csv_io.getvalue(), file_name="sn_data.csv")

# ----------------- Run -----------------
if st.session_state.logged_in:
    main_app()
else:
    login_panel()