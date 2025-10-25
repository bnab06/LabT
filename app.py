# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io
from pdf2image import convert_from_path
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# ----------------- Config -----------------
st.set_page_config(page_title="LabT", layout="wide")

# ----------------- Users JSON -----------------
users = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"}
}

# ----------------- Translations -----------------
LANG = {
    "en": {
        "login":"Login","password":"Password","submit":"Submit","sn":"S/N","linearity":"Linearity",
        "invalid":"Invalid credentials","powered":"Powered by BnB","admin_panel":"Admin Panel",
        "manage_users":"Manage Users","modify":"Modify","delete":"Delete",
        "input_type":"Input type","csv":"CSV","manual":"Manual","unit":"Unit",
        "formulas":"Formulas"
    },
    "fr": {
        "login":"Utilisateur","password":"Mot de passe","submit":"Valider","sn":"S/N","linearity":"Linéarité",
        "invalid":"Identifiants invalides","powered":"Powered by BnB","admin_panel":"Panneau Admin",
        "manage_users":"Gestion des utilisateurs","modify":"Modifier","delete":"Supprimer",
        "input_type":"Type d'entrée","csv":"CSV","manual":"Manuel","unit":"Unité",
        "formulas":"Formules"
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
        if user in users and users[user]["password"] == pwd:
            st.session_state.logged_in = True
            st.session_state.user_role = users[user]["role"]
            st.experimental_rerun()
        else:
            st.error(t("invalid"))
    st.markdown("<p style='text-align:center;font-size:12px;color:gray;'>"+t("powered")+"</p>", unsafe_allow_html=True)

# ----------------- Logout -----------------
def logout():
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.experimental_rerun()

# ----------------- Main App -----------------
def main_app():
    st.sidebar.title("Menu")
    menu_options = [t("sn"), t("linearity")]
    if st.session_state.user_role == "admin":
        menu_options = [t("admin_panel")]
    menu = st.sidebar.radio("Go to", menu_options)
    st.sidebar.button("Logout / Déconnexion", on_click=logout, key="logout_btn")

    if menu==t("linearity"): linear_panel()
    elif menu==t("sn"): sn_panel()
    elif menu==t("admin_panel"): admin_panel()

# ----------------- Admin -----------------
def admin_panel():
    st.title(t("admin_panel"))
    st.write(t("manage_users"))
    for u in users:
        cols = st.columns([2,1,1])
        cols[0].write(f"{u} - role: {users[u]['role']}")
        if cols[1].button(t("modify"), key=f"mod_{u}"):
            new_pwd = st.text_input(f"New password for {u}", type="password")
            if new_pwd:
                users[u]["password"] = new_pwd
                st.success(f"Password for {u} updated")
        if cols[2].button(t("delete"), key=f"del_{u}"):
            if u != "admin":
                users.pop(u)
                st.success(f"{u} deleted")
                st.experimental_rerun()

# ----------------- Linearity -----------------
def linear_panel():
    st.title(t("linearity"))
    st.button(t("formulas"), help="y = slope*X + intercept\nLOD = 3.3*SD/slope\nLOQ = 10*SD/slope")
    input_type = st.radio(t("input_type"), [t("csv"), t("manual")])
    df = None
    if input_type==t("csv"):
        file = st.file_uploader("Upload CSV", type=["csv"])
        if file: df = pd.read_csv(file)
    else:
        conc = st.text_area("Concentration (comma-separated)")
        signal = st.text_area("Signal (comma-separated)")
        if conc and signal:
            try:
                df = pd.DataFrame({
                    "Concentration":[round(float(x),4) for x in conc.split(",")],
                    "Signal":[round(float(x),4) for x in signal.split(",")]
                })
            except: st.warning("Invalid manual input")
    unit = st.selectbox(t("unit"), ["ug/mL","mg/mL"])
    if df is not None:
        X = df["Concentration"].values.reshape(-1,1)
        y = df["Signal"].values
        reg = LinearRegression().fit(X,y)
        slope = round(reg.coef_[0],4)
        intercept = round(reg.intercept_,4)
        r2 = round(r2_score(y, reg.predict(X)),4)
        st.write(f"Slope: {slope}, R²: {r2}")
        plt.figure()
        plt.scatter(df["Concentration"], df["Signal"])
        plt.plot(df["Concentration"], reg.predict(X), 'r')
        plt.xlabel(f"Concentration ({unit})")
        plt.ylabel("Signal")
        st.pyplot(plt)
        if st.button("Export PDF", key="linear_pdf"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial","",12)
            pdf.cell(0,10,f"Slope: {slope}", ln=1)
            pdf.cell(0,10,f"R²: {r2}", ln=1)
            pdf_file="linearity.pdf"
            pdf.output(pdf_file)
            st.download_button("Download PDF", pdf_file, file_name="linearity.pdf")
        # Store slope for S/N calculation
        st.session_state.linear_slope = slope

# ----------------- Signal/Noise -----------------
def sn_panel():
    st.title(t("sn"))
    file = st.file_uploader("Upload image/pdf/csv", type=["png","jpg","pdf","csv"])
    signal = None
    if file:
        # CSV
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            st.dataframe(df)
            if "Signal" in df.columns: signal = df["Signal"].values
        # PDF
        elif file.name.endswith(".pdf"):
            try:
                images = convert_from_path(file)
                for i,img in enumerate(images):
                    st.image(img, caption=f"Page {i+1}")
                    arr = np.array(img.convert("L"))
                    sig = arr.max(axis=0)
                    if signal is None: signal = sig
                    st.line_chart(sig)
            except: st.warning("Cannot process PDF")
        # Image
        else:
            try:
                img = Image.open(file).convert("L")
                arr = np.array(img)
                signal = arr.max(axis=0)
                st.line_chart(signal)
            except: st.warning("Cannot process image")

    # Slider for region selection
    if signal is not None:
        start, end = st.slider("Select region for S/N", 0, len(signal)-1, (0,len(signal)-1))
        region_signal = signal[start:end+1]
        sn_classic = region_signal.max()/region_signal.std() if region_signal.std()!=0 else np.nan
        sn_usp = np.mean(region_signal)/np.std(region_signal) if np.std(region_signal)!=0 else np.nan
        st.write(f"S/N Classic: {round(sn_classic,4)}, S/N USP: {round(sn_usp,4)}")
        if "linear_slope" in st.session_state:
            st.write(f"Slope from linearity (exportable): {st.session_state.linear_slope}")
        # Export CSV
        csv_io = io.StringIO()
        pd.DataFrame({"Signal":region_signal}).to_csv(csv_io,index=False)
        st.download_button("Download CSV", csv_io.getvalue(), file_name="sn_data.csv")
        # Export PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial","",12)
        pdf.cell(0,10,"S/N Report",ln=1)
        pdf.cell(0,10,f"S/N Classic: {round(sn_classic,4)}", ln=1)
        pdf.cell(0,10,f"S/N USP: {round(sn_usp,4)}", ln=1)
        pdf_file="sn_report.pdf"
        pdf.output(pdf_file)
        st.download_button("Download PDF", pdf_file, file_name="sn_report.pdf")

# ----------------- Run -----------------
if st.session_state.logged_in:
    main_app()
else:
    login_panel()