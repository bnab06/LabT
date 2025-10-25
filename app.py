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
LANG = {"en": {"login":"Login","password":"Password","submit":"Submit","sn":"S/N","linearity":"Linearity",
               "invalid":"Invalid credentials","powered":"Powered by BnB"},
        "fr": {"login":"Utilisateur","password":"Mot de passe","submit":"Valider","sn":"S/N",
               "linearity":"Linéarité","invalid":"Identifiants invalides","powered":"Powered by BnB"}}

def t(key):
    return LANG[st.session_state.lang][key]

# ----------------- Session -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "lang" not in st.session_state:
    st.session_state.lang = "fr"  # default FR

# ----------------- Login -----------------
def login_panel():
    st.title("LabT")
    st.selectbox("Language / Langue", ["fr","en"], key="lang", on_change=lambda: st.experimental_rerun())
    user = st.text_input(t("login"))
    pwd = st.text_input(t("password"), type="password")
    if st.button(t("submit")):
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
        menu_options = ["Admin"]
    menu = st.sidebar.radio("Go to", menu_options)
    st.sidebar.button("Logout / Déconnexion", on_click=logout)

    if menu==t("linearity"): linear_panel()
    elif menu==t("sn"): sn_panel()
    elif menu=="Admin": admin_panel()

# ----------------- Admin -----------------
def admin_panel():
    st.title("Admin Panel")
    st.write("Gestion des utilisateurs")
    for u in users:
        st.write(f"{u} - role: {users[u]['role']}")

# ----------------- Linearity -----------------
def linear_panel():
    st.title(t("linearity"))

    input_type = st.radio("Input type", ["CSV","Manual"])
    if input_type=="CSV":
        file = st.file_uploader("Upload CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        conc = st.text_area("Concentration (comma-separated)")
        signal = st.text_area("Signal (comma-separated)")
        if conc and signal:
            try:
                df = pd.DataFrame({
                    "Concentration":[float(x) for x in conc.split(",")],
                    "Signal":[float(x) for x in signal.split(",")]
                })
            except:
                st.warning("Invalid manual input")
                return

    # Dropdown unité
    unit = st.selectbox("Unit", ["ug/mL","mg/mL"])
    if 'df' in locals():
        X = df["Concentration"].values.reshape(-1,1)
        y = df["Signal"].values
        reg = LinearRegression().fit(X, y)
        slope = reg.coef_[0]
        intercept = reg.intercept_
        r2 = r2_score(y, reg.predict(X))
        st.write(f"Slope: {round(slope,4)}, R2: {round(r2,4)}")
        plt.figure()
        plt.scatter(df["Concentration"], df["Signal"])
        plt.plot(df["Concentration"], reg.predict(X), 'r')
        plt.xlabel(f"Concentration ({unit})")
        plt.ylabel("Signal")
        st.pyplot(plt)
        if st.button("Export PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "", 12)
            pdf.cell(0,10,f"Slope: {slope}",ln=1)
            pdf.cell(0,10,f"R2: {r2}",ln=1)
            pdf_file = "linearity.pdf"
            pdf.output(pdf_file)
            st.download_button("Download PDF", pdf_file, file_name="linearity.pdf")

# ----------------- Signal/Noise -----------------
def sn_panel():
    st.title(t("sn"))
    file = st.file_uploader("Upload image/pdf/csv", type=["png","jpg","pdf","csv"])
    if file:
        # CSV
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            st.dataframe(df)
        # PDF
        elif file.name.endswith(".pdf"):
            try:
                images = convert_from_path(file)
                for i,img in enumerate(images):
                    st.image(img, caption=f"Page {i+1}")
                    arr = np.array(img.convert("L"))
                    signal = arr.max(axis=0)
                    st.line_chart(signal)
            except:
                st.warning("Cannot process PDF")
        # Image
        else:
            try:
                img = Image.open(file).convert("L")
                arr = np.array(img)
                signal = arr.max(axis=0)
                st.line_chart(signal)
            except:
                st.warning("Cannot process image")

        # Export CSV
        if 'signal' in locals():
            csv_io = io.StringIO()
            pd.DataFrame({"Signal":signal}).to_csv(csv_io,index=False)
            st.download_button("Download CSV", csv_io.getvalue(), file_name="sn_data.csv")
            # Export PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial","",12)
            pdf.cell(0,10,"S/N Report",ln=1)
            pdf.cell(0,10,f"Max Signal: {signal.max()}",ln=1)
            pdf_file="sn_report.pdf"
            pdf.output(pdf_file)
            st.download_button("Download PDF", pdf_file, file_name="sn_report.pdf")

# ----------------- Run -----------------
if st.session_state.logged_in:
    main_app()
else:
    login_panel()