# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image, ImageOps
import io
import json
import os
from datetime import datetime

# -------------------------
# Users helpers
# -------------------------
USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

def load_users():
    try:
        with open(USERS_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {"admin":{"password":"admin","role":"admin"},"user":{"password":"user","role":"user"}}
        try:
            with open(USERS_FILE,"w",encoding="utf-8") as f:
                json.dump(default,f,indent=4,ensure_ascii=False)
        except:
            pass
        return default

def save_users(users):
    with open(USERS_FILE,"w",encoding="utf-8") as f:
        json.dump(users,f,indent=4,ensure_ascii=False)

USERS = load_users()

def find_user_key(username):
    if username is None:
        return None
    for u in USERS.keys():
        if u.lower() == username.strip().lower():
            return u
    return None

# -------------------------
# Translations
# -------------------------
TEXTS = {
    "FR":{
        "app_title":"LabT",
        "powered":"Propulsé par BnB",
        "username":"Utilisateur",
        "password":"Mot de passe",
        "login":"Connexion",
        "logout":"Déconnexion",
        "invalid":"Identifiants invalides",
        "linearity":"Linéarité",
        "sn":"S/N",
        "admin":"Admin",
        "company":"Nom de la compagnie",
        "input_csv":"CSV",
        "input_manual":"Saisie manuelle",
        "concentration":"Concentration",
        "signal":"Signal",
        "unit":"Unité",
        "generate_pdf":"Générer PDF",
        "download_pdf":"Télécharger PDF",
        "download_csv":"Télécharger CSV",
        "sn_classic":"S/N Classique",
        "sn_usp":"S/N USP",
        "lod":"LOD (conc.)",
        "loq":"LOQ (conc.)",
        "formulas":"Formules",
        "select_region":"Sélectionner la zone",
        "add_user":"Ajouter utilisateur",
        "delete_user":"Supprimer utilisateur",
        "modify_user":"Modifier mot de passe",
        "enter_username":"Nom d'utilisateur",
        "enter_password":"Mot de passe (simple)",
        "upload_chrom":"Importer chromatogramme (CSV, PNG, JPG, PDF)",
        "digitize_info":"Digitizing : OCR tenté si pytesseract installé (best-effort)",
        "export_sn_pdf":"Exporter S/N PDF",
        "download_original_pdf":"Télécharger PDF original",
        "change_pwd":"Changer mot de passe (hors session)",
        "compute":"Compute",
        "company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport.",
        "select_section":"Section",
        "upload_logo":"Uploader un logo (optionnel)"
    },
    "EN":{
        "app_title":"LabT",
        "powered":"Powered by BnB",
        "username":"Username",
        "password":"Password",
        "login":"Login",
        "logout":"Logout",
        "invalid":"Invalid credentials",
        "linearity":"Linearity",
        "sn":"S/N",
        "admin":"Admin",
        "company":"Company name",
        "input_csv":"CSV",
        "input_manual":"Manual input",
        "concentration":"Concentration",
        "signal":"Signal",
        "unit":"Unit",
        "generate_pdf":"Generate PDF",
        "download_pdf":"Download PDF",
        "download_csv":"Download CSV",
        "sn_classic":"S/N Classic",
        "sn_usp":"S/N USP",
        "lod":"LOD (conc.)",
        "loq":"LOQ (conc.)",
        "formulas":"Formulas",
        "select_region":"Select region",
        "add_user":"Add user",
        "delete_user":"Delete user",
        "modify_user":"Modify password",
        "enter_username":"Username",
        "enter_password":"Password (simple)",
        "upload_chrom":"Upload chromatogram (CSV, PNG, JPG, PDF)",
        "digitize_info":"Digitizing: OCR attempted if pytesseract available (best-effort)",
        "export_sn_pdf":"Export S/N PDF",
        "download_original_pdf":"Download original PDF",
        "change_pwd":"Change password (outside session)",
        "compute":"Compute",
        "company_missing":"Please enter company name before generating the report.",
        "select_section":"Section",
        "upload_logo":"Upload logo (optional)"
    }
}

def t(key):
    lang = st.session_state.get("lang","FR")
    return TEXTS.get(lang,TEXTS["FR"]).get(key,key)

# -------------------------
# Session defaults
# -------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "FR"
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

# -------------------------
# Login page
# -------------------------
def login_page():
    st.title("🧪 LabT")
    st.subheader(t("login"))
    st.text(t("powered"))

    username = st.text_input(t("username"))
    password = st.text_input(t("password"), type="password")
    if st.button(t("login")):
        uname = (username or "").strip()
        matched = find_user_key(uname)
        if matched and USERS[matched]["password"] == (password or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            st.experimental_rerun()
        else:
            st.error(t("invalid"))

# -------------------------
# Linearity panel
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"),key="company_name")

    mode = st.radio("Input mode",[t("input_csv"),t("input_manual")],key="lin_input_mode")
    df = None
    if mode == t("input_csv"):
        uploaded = st.file_uploader(t("input_csv"),type=["csv"],key="lin_csv")
        if uploaded:
            try:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded)
                cols_low = [c.lower() for c in df0.columns]
                if "concentration" in cols_low and "signal" in cols_low:
                    df = df0.rename(columns={df0.columns[cols_low.index("concentration")]:"Concentration",
                                             df0.columns[cols_low.index("signal")]:"Signal"})
                elif len(df0.columns)>=2:
                    df = df0.iloc[:,:2].copy()
                    df.columns=["Concentration","Signal"]
                else:
                    st.error("CSV must contain at least two columns (concentration, signal).")
            except Exception as e:
                st.error(f"CSV error: {e}")
    else:
        st.caption("Enter concentrations and signals (comma separated)")
        cols = st.columns(2)
        conc_input = cols[0].text_area("Concentrations",height=120,key="lin_manual_conc")
        sig_input = cols[1].text_area("Signals",height=120,key="lin_manual_sig")
        try:
            concs = [float(c.replace(",",".").strip()) for c in conc_input.split(",") if c.strip()]
            sigs = [float(s.replace(",",".").strip()) for s in sig_input.split(",") if s.strip()]
            if len(concs)!=len(sigs):
                st.error("Number of concentrations and signals must match")
            elif len(concs)<2:
                st.warning("At least two pairs are required")
            else:
                df = pd.DataFrame({"Concentration":concs,"Signal":sigs})
        except Exception as e:
            if conc_input.strip() or sig_input.strip():
                st.error(f"Manual parse error: {e}")

    if df is None:
        st.info("Provide data")
        return

    df["Concentration"] = pd.to_numeric(df["Concentration"])
    df["Signal"] = pd.to_numeric(df["Signal"])
    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values,1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    st.session_state.linear_slope = slope
    st.write(f"Slope = {slope:.6f}, Intercept = {intercept:.6f}")

    fig, ax = plt.subplots()
    ax.scatter(df["Concentration"],df["Signal"],label="Data")
    ax.plot(df["Concentration"],slope*df["Concentration"]+intercept,"r--",label="Fit")
    ax.set_xlabel("Concentration")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

# -------------------------
# S/N panel
# -------------------------
def sn_panel():
    st.header(t("sn"))
    uploaded = st.file_uploader(t("upload_chrom"),type=["csv","png","jpg","jpeg","pdf"],key="sn_file")

    slope_choice = st.radio("Slope source",["Use linearity slope","Enter manually"],key="sn_slope_choice")
    if slope_choice=="Use linearity slope":
        slope_input = st.session_state.linear_slope or 0.0
    else:
        slope_input = st.number_input("Slope manual",value=0.0,format="%.6f",key="sn_slope_manual")

    # Manual calculation
    if uploaded is None:
        st.info("Manual S/N calculation")
        H = st.number_input("H (peak height)",value=0.0,format="%.6f",key="manual_H")
        h = st.number_input("h (noise)",value=0.0,format="%.6f",key="manual_h")
        sn_classic = H/h if h!=0 else float("nan")
        sn_usp = 2*H/h if h!=0 else float("nan")
        lod = 3.3*h/slope_input if slope_input!=0 else float("nan")
        loq = 10*h/slope_input if slope_input!=0 else float("nan")
        st.write(f"S/N Classic: {sn_classic:.4f}")
        st.write(f"S/N USP: {sn_usp:.4f}")
        st.write(f"LOD: {lod:.6f}, LOQ: {loq:.6f}")
        return

    try:
        # Convert to image and invert
        img = Image.open(uploaded).convert("L")
        img_inv = ImageOps.invert(img)
        arr = np.array(img_inv)
        signal = arr.max(axis=0).astype(float)
        x = np.arange(len(signal))
    except Exception as e:
        st.error(f"Image processing failed: {e}")
        return

    min_idx = int(x[0])
    max_idx = int(x[-1])
    sel_idx = st.slider(t("select_region"), min_value=min_idx,max_value=max_idx,value=(min_idx,max_idx),key="sn_slider")
    noise_region = signal[sel_idx[0]:sel_idx[1]] if sel_idx[1]>sel_idx[0] else signal
    h = noise_region.std() if len(noise_region)>0 else 1.0
    H = signal.max()
    sn_classic = H/h if h!=0 else float("nan")
    sn_usp = 2*H/h if h!=0 else float("nan")
    lod = 3.3*h/slope_input if slope_input!=0 else float("nan")
    loq = 10*h/slope_input if slope_input!=0 else float("nan")
    peak_idx = np.argmax(signal)
    tR = x[peak_idx]

    st.write(f"H = {H:.4f}, h = {h:.4f}, tR = {tR}")
    st.write(f"S/N Classic = {sn_classic:.4f}, S/N USP = {sn_usp:.4f}")
    st.write(f"LOD = {lod:.6f}, LOQ = {loq:.6f}")

    # Plot
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(x,signal,label="Chromatogram")
    ax.axhline(H/2,color="r",linestyle="--",label="H/2")
    ax.axvline(peak_idx,color="g",linestyle="--",label=f"tR = {tR}")
    ax.set_xlabel("Pixel / Time")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    if st.checkbox(t("formulas"),key="show_formulas"):
        st.markdown("""
        - S/N Classic = H / h  
        - S/N USP = 2 * H / h  
        - LOD = 3.3 * h / slope  
        - LOQ = 10 * h / slope  
        - tR = retention time of main peak
        """)

# -------------------------
# Feedback page
# -------------------------
def feedback_panel():
    st.header("Feedback / Suggestions")
    name = st.text_input("Name / Nom")
    message = st.text_area("Message / Message")
    if st.button("Send / Envoyer"):
        if name.strip() and message.strip():
            if not os.path.exists("feedback.csv"):
                df_fb = pd.DataFrame(columns=["Name","Message","Date"])
            else:
                df_fb = pd.read_csv("feedback.csv")
            df_fb = pd.concat([df_fb,pd.DataFrame({"Name":[name],"Message":[message],"Date":[datetime.now()]})],ignore_index=True)
            df_fb.to_csv("feedback.csv",index=False)
            st.success("Message sent / Envoyé")
        else:
            st.warning("Please enter name and message / Veuillez remplir nom et message")

# -------------------------
# Main
# -------------------------
def main_app():
    if st.session_state.user is None:
        login_page()
        return
    st.sidebar.title("LabT")
    if st.sidebar.button(t("logout")):
        st.session_state.user = None
        st.session_state.role = None
        st.experimental_rerun()
    page = st.sidebar.radio(t("select_section"),[t("linearity"),t("sn"),"Feedback"])
    if page==t("linearity"):
        linearity_panel()
    elif page==t("sn"):
        sn_panel()
    else:
        feedback_panel()

def run():
    main_app()

if __name__=="__main__":
    run()