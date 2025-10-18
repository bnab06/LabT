# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import io
import os

# -------------------- Initialisation --------------------
if 'user' not in st.session_state:
    st.session_state.user = None
if 'users' not in st.session_state:
    # Exemple : admin = motdepasse, bb=user1, user=user2
    st.session_state.users = {"admin":"admin123","bb":"bb123","user":"user123"}

# -------------------- Fonctions --------------------
def login_page():
    st.title("LabT - Connexion")
    user_choice = st.selectbox("Sélectionnez un utilisateur", list(st.session_state.users.keys()))
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if password == st.session_state.users[user_choice]:
            st.session_state.user = user_choice
            st.success(f"Connecté en tant que {user_choice}")
            st.experimental_rerun()
        else:
            st.error("Mot de passe incorrect")

def logout():
    if st.session_state.user:
        st.session_state.user = None
        st.success("Déconnecté")
        st.experimental_rerun()

# -------------------- Gestion Utilisateurs --------------------
def manage_users():
    st.header("Gestion Utilisateurs (Admin)")
    users = st.session_state.users
    st.subheader("Ajouter un utilisateur")
    new_user = st.text_input("Nom utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    if st.button("Ajouter"):
        if new_user and new_pass:
            users[new_user] = new_pass
            st.success(f"Utilisateur {new_user} ajouté")
    st.subheader("Liste des utilisateurs")
    for u in users:
        st.write(u)

# -------------------- Linéarité --------------------
def linearity_page():
    st.header("Linéarité")
    st.write("Saisir les concentrations et réponses séparées par des virgules")
    conc_str = st.text_input("Concentrations (ex: 1,2,3)")
    resp_str = st.text_input("Réponses (aires ou absorbances) (ex: 10,20,30)")
    unit = st.selectbox("Unité concentration", ["µg/ml", "mg/ml"])
    y_unit = st.selectbox("Réponse", ["Aire","Absorbance"])
    unknown_type = st.selectbox("Calculer", ["Concentration inconnue","Signal inconnu"])
    unknown_val = st.text_input("Valeur inconnue (laisser vide si non applicable)")

    if st.button("Calculer linéarité"):
        try:
            c = np.array([float(x.strip()) for x in conc_str.split(",")])
            r = np.array([float(x.strip()) for x in resp_str.split(",")])
            if len(c)!=len(r):
                st.error("Les listes doivent avoir la même longueur")
                return
            # Régression linéaire simple
            slope, intercept = np.polyfit(c, r, 1)
            y_fit = slope * c + intercept
            r2 = np.corrcoef(c, r)[0,1]**2
            st.write(f"Équation : y = {slope:.3f}x + {intercept:.3f}")
            st.write(f"R² = {r2:.4f}")
            plt.figure()
            plt.plot(c, r, "o", label="Data")
            plt.plot(c, y_fit, "-", label="Fit")
            plt.xlabel(f"Concentration ({unit})")
            plt.ylabel(f"{y_unit}")
            plt.legend()
            st.pyplot(plt)
            # Calcul automatique concentration/signal inconnu
            if unknown_val:
                val = float(unknown_val)
                if unknown_type=="Concentration inconnue":
                    conc_unknown = (val - intercept)/slope
                    st.success(f"Concentration inconnue = {conc_unknown:.4f} {unit}")
                else:
                    signal_unknown = slope*val + intercept
                    st.success(f"Signal inconnu = {signal_unknown:.4f} {y_unit}")
        except Exception as e:
            st.error(f"Erreur: {e}")

    # Export PDF
    company_name = st.text_input("Nom de l'entreprise (optionnel)")
    if st.button("Exporter PDF"):
        try:
            pdf = FPDF()
            pdf.add_page()
            if os.path.exists("logo.png"):
                pdf.image("logo.png", x=10, y=8, w=30)
            pdf.set_font("Arial", "B", 16)
            pdf.ln(20)
            pdf.cell(0,10,"Rapport Linéarité LabT",ln=True,align="C")
            pdf.set_font("Arial","",12)
            pdf.ln(5)
            pdf.cell(0,10,f"Utilisateur : {st.session_state.user}",ln=True)
            pdf.cell(0,10,f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
            if company_name:
                pdf.cell(0,10,f"Entreprise : {company_name}",ln=True)
            pdf.ln(5)
            pdf.cell(0,10,f"Équation : y = {slope:.3f}x + {intercept:.3f}",ln=True)
            pdf.cell(0,10,f"R² = {r2:.4f}",ln=True)
            # Courbe
            buf = io.BytesIO()
            plt.figure()
            plt.plot(c, r, "o", label="Data")
            plt.plot(c, y_fit, "-", label="Fit")
            plt.xlabel(f"Concentration ({unit})")
            plt.ylabel(f"{y_unit}")
            plt.legend()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plt.close()
            pdf.image(buf, x=10, w=180)
            buf.close()
            pdf_file="Rapport_Linearite.pdf"
            pdf.output(pdf_file)
            st.success(f"PDF généré : {pdf_file}")
            with open(pdf_file,"rb") as f:
                st.download_button("Télécharger le PDF",f.read(),file_name=pdf_file)
        except Exception as e:
            st.error(f"Erreur lors du PDF: {e}")

# -------------------- S/N USP --------------------
def sn_page():
    st.header("S/N USP")
    uploaded_file = st.file_uploader("Télécharger CSV ou PNG", type=["csv","png"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
                st.write(df.head())
                y = df.iloc[:,1].values
                sn = np.max(y)/np.std(y)
                st.success(f"S/N calculé : {sn:.3f}")
            else:
                st.warning("Extraction des données à partir d'images non implémentée pour PNG")
        except Exception as e:
            st.error(f"Erreur: {e}")

# -------------------- Menu Principal --------------------
def main_menu():
    if st.session_state.user is None:
        login_page()
    else:
        st.title(f"LabT - Connecté en tant que {st.session_state.user}")
        st.button("Déconnexion", on_click=logout)
        choice = st.selectbox("Choisir une fonction", ["Linéarité","S/N USP","Gestion Utilisateurs"] if st.session_state.user=="admin" else ["Linéarité","S/N USP"])
        if choice=="Linéarité":
            linearity_page()
        elif choice=="S/N USP":
            sn_page()
        elif choice=="Gestion Utilisateurs" and st.session_state.user=="admin":
            manage_users()

# -------------------- Lancement --------------------
main_menu()