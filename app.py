
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from fpdf import FPDF
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io
import plotly.graph_objects as go

# ---------- Session ----------
if "lang" not in st.session_state:
    st.session_state.lang = "FR"
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

# ---------- Traduction ----------
texts = {"FR":{"login":"Connexion","user":"Utilisateur","password":"Mot de passe","logout":"Se déconnecter","linear":"Linéarité","sn":"S/N","choose_file":"Charger fichier","file_type":"Type de fichier","upload":"Importer","classic":"Classique","usp":"USP","show_formulas":"Afficher formules","export_pdf":"Exporter PDF","powered":"Powered by BnB"},"EN":{"login":"Login","user":"User","password":"Password","logout":"Logout","linear":"Linearity","sn":"S/N","choose_file":"Upload file","file_type":"File type","upload":"Upload","classic":"Classic","usp":"USP","show_formulas":"Show formulas","export_pdf":"Export PDF","powered":"Powered by BnB"}}
def t(key): return texts[st.session_state.lang].get(key,key)

# ---------- Auth ----------
USERS = {"admin":"admin123","user":"user123"}
def login_panel():
    st.title("LabT")
    st.selectbox("Langue / Language", ["FR","EN"], key="lang")
    if st.session_state.user is None:
        username = st.text_input(t("user"))
        password = st.text_input(t("password"), type="password")
        if st.button(t("login")):
            if username in USERS and USERS[username]==password:
                st.session_state.user = username
                st.session_state.role = "admin" if username=="admin" else "user"
                st.experimental_rerun()
            else:
                st.error("Invalid login / Identifiants invalides")
        st.markdown("<div style='text-align:center; margin-top:20px; font-style:italic;'>Powered by BnB</div>", unsafe_allow_html=True)
    else:
        main_app()

# ---------- Main App ----------
def main_app():
    st.sidebar.title(f"{t('user')}: {st.session_state.user}")
    if st.session_state.role=="admin":
        admin_panel()
    else:
        user_panel()

# ---------- Admin ----------
def admin_panel():
    st.header("Admin Panel")
    st.write("Gestion des utilisateurs")
    if st.sidebar.button(t("logout")):
        st.session_state.user=None
        st.session_state.role=None
        st.experimental_rerun()
    # Simple gestion user
    st.write("- Ajouter ou supprimer des utilisateurs")

# ---------- User ----------
def user_panel():
    choice = st.sidebar.radio("Menu",[t("linear"),t("sn")])
    if st.sidebar.button(t("logout")):
        st.session_state.user=None
        st.session_state.role=None
        st.experimental_rerun()
    if choice==t("linear"):
        linear_panel()
    else:
        sn_panel()

# ---------- Linear ----------
def linear_panel():
    st.header(t("linear"))
    input_type = st.radio("Input type / Type de saisie", ["CSV","Manual"])
    df = None
    if input_type=="CSV":
        file = st.file_uploader(t("choose_file"), type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        x_values = st.text_area("Concentration (X), comma separated")
        y_values = st.text_area("Signal (Y), comma separated")
        try:
            x=[float(i) for i in x_values.split(",")]
            y=[float(i) for i in y_values.split(",")]
            df=pd.DataFrame({"Concentration":x,"Signal":y})
        except:
            st.error("Invalid input")
    if df is not None and len(df)>1:
        slope, intercept = np.polyfit(df.iloc[:,0], df.iloc[:,1],1)
        r2 = np.corrcoef(df.iloc[:,0], df.iloc[:,1])[0,1]**2
        st.session_state.linear_slope=slope
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=df.iloc[:,0],y=df.iloc[:,1],mode="markers",name="Data"))
        fig.add_trace(go.Scatter(x=df.iloc[:,0],y=slope*df.iloc[:,0]+intercept,mode="lines",name="Fit"))
        fig.update_layout(xaxis_title="Concentration",yaxis_title="Signal")
        st.plotly_chart(fig,use_container_width=True)
        st.write(f"Slope / Pente: {slope:.4f}  Intercept / Ordonnée: {intercept:.4f}  R²: {r2:.4f}")
        # Calcul automatique
        st.subheader("Calcul automatique")
        val_x = st.number_input("X value (concentration)")
        st.write("Signal Y:", slope*val_x+intercept)
        val_y = st.number_input("Y value (signal)")
        st.write("Concentration X:", (val_y-intercept)/slope)
        # Export PDF
        if st.button(t("export_pdf")):
            pdf=FPDF()
            pdf.add_page()
            pdf.set_font("Arial",size=12)
            pdf.cell(200,10,txt="LabT - Linearity Report",ln=True,align="C")
            pdf.cell(200,10,txt=f"User: {st.session_state.user}",ln=True)
            pdf.cell(200,10,txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
            pdf.cell(200,10,txt=f"Slope: {slope:.4f}",ln=True)
            pdf.cell(200,10,txt=f"Intercept: {intercept:.4f}",ln=True)
            pdf.cell(200,10,txt=f"R²: {r2:.4f}",ln=True)
            pdf_output=io.BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)
            st.download_button("Download PDF",pdf_output,file_name="linearity_report.pdf",mime="application/pdf")

# ---------- S/N ----------
def read_csv(file):
    try:
        return pd.read_csv(file)
    except:
        return None
def extract_from_image(image):
    text=pytesseract.image_to_string(image)
    data=[]
    for line in text.splitlines():
        if "," in line or "	" in line:
            parts=line.replace("	",",").split(",")
            try:
                x,y=float(parts[0]),float(parts[1])
                data.append([x,y])
            except:
                pass
    return pd.DataFrame(data,columns=["X","Y"])
def extract_from_pdf(file):
    images=convert_from_path(file)
    all_data=pd.DataFrame(columns=["X","Y"])
    for img in images:
        df=extract_from_image(img)
        all_data=pd.concat([all_data,df])
    return all_data.reset_index(drop=True)
def sn_classic(peak,noise): return peak/noise
def sn_usp(peak,std): return peak/std
def sn_panel():
    st.header(t("sn"))
    file_type=st.selectbox(t("file_type"),["CSV","PDF","PNG"])
    file=st.file_uploader(t("choose_file"), type=["csv","pdf","png"])
    df=None
    if file:
        if file_type=="CSV": df=read_csv(file)
        elif file_type=="PDF": df=extract_from_pdf(file)
        elif file_type=="PNG": img=Image.open(file); df=extract_from_image(img)
    if df is not None and not df.empty:
        st.line_chart(df.set_index("X")["Y"])
        x_min,x_max=st.slider("Select zone",float(df["X"].min()),float(df["X"].max()),(float(df["X"].min()),float(df["X"].max())))
        selected=df[(df["X"]>=x_min)&(df["X"]<=x_max)]
        signal_peak=selected["Y"].max()
        std_noise=selected["Y"].std()
        classic=sn_classic(signal_peak,std_noise)
        usp=sn_usp(signal_peak,std_noise)
        st.subheader("S/N Values")
        st.write(f"Classical / Classique: {classic:.2f}")
        st.write(f"USP: {usp:.2f}")
        if st.checkbox(t("show_formulas")):
            st.info("S/N Classic = Signal Peak / Noise\nS/N USP = Signal Peak / Std(Noise)")
        if st.button(t("export_pdf")):
            pdf=FPDF()
            pdf.add_page()
            pdf.set_font("Arial",size=12)
            pdf.cell(200,10,txt="LabT - S/N Report",ln=True,align="C")
            pdf.cell(200,10,txt=f"User: {st.session_state.user}",ln=True)
            pdf.cell(200,10,txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
            pdf.cell(200,10,txt=f"S/N Classic: {classic:.2f}",ln=True)
            pdf.cell(200,10,txt=f"S/N USP: {usp:.2f}",ln=True)
            pdf_output=io.BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)
            st.download_button("Download PDF",pdf_output,file_name="sn_report.pdf",mime="application/pdf")

# ---------- Main ----------
def main():
    st.set_page_config(page_title="LabT", layout="wide")
    login_panel()
if __name__=="__main__": main()
