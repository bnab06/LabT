import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import easyocr
import io
from PIL import Image

# -------------------- Utilisateurs --------------------
USERS_FILE = "users.json"
import json
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        users = {"admin": "admin123", "bb": "bb123", "user": "user123"}
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        return users
users = load_users()

# -------------------- Connexion --------------------
def login_page():
    st.title("LabT")
    st.subheader("Connexion")
    selected_user = st.selectbox("Choisir utilisateur", list(users.keys()))
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if users.get(selected_user)==password:
            st.session_state["user"] = selected_user
            st.success(f"Connecté en tant que {selected_user}")
            main_menu()
        else:
            st.error("Mot de passe incorrect")

# -------------------- Menu --------------------
def main_menu():
    st.title("LabT - Menu")
    st.write(f"Utilisateur connecté : {st.session_state.get('user','')}")
    choice = st.selectbox("Choisir fonctionnalité", ["Linéarité", "S/N", "Gérer utilisateurs", "Se déconnecter"])
    
    if choice=="Linéarité":
        linearity_page()
    elif choice=="S/N":
        sn_page()
    elif choice=="Gérer utilisateurs":
        if st.session_state.get("user")=="admin":
            manage_users()
        else:
            st.warning("Accès réservé à l'admin")
    elif choice=="Se déconnecter":
        st.session_state.clear()
        st.success("Déconnecté")
        login_page()

# -------------------- Linéarité --------------------
def linearity_page():
    st.header("Linéarité")
    unit_conc = st.selectbox("Unité concentration", ["µg/mL","mg/mL"])
    unit_signal = st.selectbox("Unité signal", ["Aire","Absorbance"])
    conc_input = st.text_input("Concentrations (virgule séparées)","1,2,3")
    resp_input = st.text_input("Réponses (virgule séparées)","100,200,300")
    
    if st.button("Tracer"):
        try:
            c = np.array([float(x.strip()) for x in conc_input.split(",")])
            r = np.array([float(x.strip()) for x in resp_input.split(",")])
            coeff = np.polyfit(c,r,1)
            y_fit = np.polyval(coeff,c)
            r2 = np.corrcoef(c,r)[0,1]**2
            st.write(f"R² = {r2:.4f}")
            fig,ax = plt.subplots()
            ax.scatter(c,r)
            ax.plot(c,y_fit,color='red')
            ax.set_xlabel(f"Concentration ({unit_conc})")
            ax.set_ylabel(f"Réponse ({unit_signal})")
            st.pyplot(fig)
            # concentration inconnue
            unknown_signal = st.number_input("Signal inconnu")
            if unknown_signal:
                conc_unknown = (unknown_signal - coeff[1])/coeff[0]
                st.info(f"Concentration inconnue = {conc_unknown:.4f} {unit_conc}")
            # Export PDF
            if st.button("Télécharger rapport PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial","B",16)
                pdf.cell(0,10,"Rapport Linéarité",ln=True)
                pdf.set_font("Arial","",12)
                pdf.cell(0,10,f"Utilisateur: {st.session_state.get('user')}",ln=True)
                pdf.cell(0,10,f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
                pdf.cell(0,10,f"R² = {r2:.4f}",ln=True)
                pdf.output("linearite.pdf")
                with open("linearite.pdf","rb") as f:
                    st.download_button("Télécharger PDF",f,"linearite.pdf")
        except Exception as e:
            st.error(f"Erreur: {e}")
    if st.button("Retour menu"):
        main_menu()

# -------------------- Signal / Bruit --------------------
def sn_page():
    st.header("S/N")
    uploaded_file = st.file_uploader("Uploader CSV, PNG ou PDF", type=["csv","png","pdf"])
    start = st.number_input("Début",value=0.0)
    end = st.number_input("Fin",value=1.0)
    
    if st.button("Calculer S/N"):
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                    y = df.iloc[:,1].values if df.shape[1]>1 else df.iloc[:,0].values
                else:
                    # OCR rapide
                    reader = easyocr.Reader(['en'])
                    img = Image.open(io.BytesIO(uploaded_file.read()))
                    result = reader.readtext(np.array(img))
                    y = [float(r[1]) for r in result if r[1].replace(".","",1).isdigit()]
                peak_height = np.max(y[int(start):int(end)])
                noise = np.std(y[int(start):int(end)])
                sn = peak_height/noise if noise!=0 else 0
                lod = 3*noise
                loq = 10*noise
                st.write(f"S/N = {sn:.2f}, LOD = {lod:.2f}, LOQ = {loq:.2f}")
                st.line_chart(y)
            except Exception as e:
                st.error(f"Erreur: {e}")
    if st.button("Retour menu"):
        main_menu()

# -------------------- Admin --------------------
def manage_users():
    st.header("Gestion utilisateurs")
    new_user = st.text_input("Nom utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    if st.button("Ajouter"):
        if new_user and new_pass:
            users[new_user]=new_pass
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté")
    if st.button("Retour menu"):
        main_menu()

# -------------------- Main --------------------
if "user" not in st.session_state:
    login_page()
else:
    main_menu()