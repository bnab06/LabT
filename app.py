import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import json
from io import BytesIO

# --------- Utils ---------
def load_users():
    with open("users.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

def export_linearity_pdf(name, x, y, slope, intercept, r2, unit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Rapport de linéarité - {name}", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Unité concentration : {unit}", ln=True)
    pdf.cell(0, 10, f"Pente : {slope:.4f}", ln=True)
    pdf.cell(0, 10, f"Intercept : {intercept:.4f}", ln=True)
    pdf.cell(0, 10, f"R² : {r2:.4f}", ln=True)
    # Graphique
    fig, ax = plt.subplots()
    ax.scatter(x, y)
    ax.plot(x, slope*np.array(x)+intercept, color="red")
    ax.set_xlabel(f"Concentration ({unit})")
    ax.set_ylabel("Signal")
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    pdf.image(buf, x=10, y=80, w=180)
    buf.close()
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

def export_sn_csv(name, sn_value):
    df = pd.DataFrame({"Rapport": [name], "S/N": [sn_value]})
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf

# --------- Login ---------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

def login():
    st.title("Connexion")
    username = st.text_input("Utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        users = load_users()
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = users[username]["role"]
            st.success(f"Connecté en tant que {username} ({st.session_state.role})")
        else:
            st.error("Utilisateur ou mot de passe invalide")

def logout():
    if st.button("Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

# --------- Admin Menu ---------
def admin_menu():
    st.header("Gestion des utilisateurs")
    users = load_users()
    st.subheader("Ajouter un utilisateur")
    new_user = st.text_input("Nom d'utilisateur")
    new_pass = st.text_input("Mot de passe", type="password")
    role = st.selectbox("Rôle", ["user", "admin"])
    if st.button("Ajouter"):
        if new_user and new_pass:
            users[new_user] = {"password": new_pass, "role": role}
            save_users(users)
            st.success(f"Utilisateur {new_user} ajouté.")
    st.subheader("Liste des utilisateurs")
    for u, info in users.items():
        st.write(f"{u} - {info['role']}")
        if st.button(f"Supprimer {u}"):
            if u != st.session_state.username:
                users.pop(u)
                save_users(users)
                st.success(f"{u} supprimé.")
            else:
                st.error("Impossible de se supprimer soi-même.")

# --------- Linéarité ---------
def linearity_tab():
    st.header("Linéarité")
    company_name = st.text_input("Nom de la compagnie", "Ma compagnie")
    unit = st.text_input("Unité de concentration", "µg/mL")
    input_type = st.radio("Mode d'entrée", ["CSV", "Saisie manuelle"])
    if input_type == "CSV":
        file = st.file_uploader("Importer CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            st.dataframe(df)
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
    else:
        conc = st.text_input("Concentrations (séparées par des virgules)")
        signal = st.text_input("Signaux (séparés par des virgules)")
        if conc and signal:
            try:
                x = np.array([float(i) for i in conc.split(",")])
                y = np.array([float(i) for i in signal.split(",")])
            except:
                st.error("Valeurs invalides")
                return
    if 'x' in locals() and 'y' in locals():
        A = np.vstack([x, np.ones(len(x))]).T
        try:
            m, c = np.linalg.lstsq(A, y, rcond=None)[0]
            y_fit = m*x + c
            r2 = 1 - np.sum((y - y_fit)**2)/np.sum((y - np.mean(y))**2)
            st.write(f"Pente : {m:.4f}")
            st.write(f"Intercept : {c:.4f}")
            st.write(f"R² : {r2:.4f}")
            fig, ax = plt.subplots()
            ax.scatter(x, y)
            ax.plot(x, y_fit, color="red")
            ax.set_xlabel(f"Concentration ({unit})")
            ax.set_ylabel("Signal")
            st.pyplot(fig)
            st.session_state.linear_slope = m

            # Calcul concentration inconnue
            unknown_signal = st.number_input("Signal inconnu")
            if st.button("Calculer concentration inconnue"):
                conc_unknown = (unknown_signal - c)/m
                st.write(f"Concentration estimée : {conc_unknown:.4f} {unit}")

            # Export PDF
            if st.button("Exporter rapport PDF"):
                pdf_file = export_linearity_pdf(company_name, x, y, m, c, r2, unit)
                st.download_button("Télécharger PDF", pdf_file, file_name="linearity_report.pdf")
        except np.linalg.LinAlgError:
            st.error("Erreur calcul linéarité : SVD did not converge")

# --------- S/N ---------
def sn_tab():
    st.header("Signal / Bruit")
    company_name = st.text_input("Nom de la compagnie S/N", "Ma compagnie S/N")
    input_type = st.radio("Source", ["CSV", "Image PDF/PNG"])
    if input_type == "CSV":
        file = st.file_uploader("Importer CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
            st.dataframe(df)
            start = st.number_input("Début zone")
            end = st.number_input("Fin zone")
            if st.button("Calculer S/N"):
                subset = df[(df.iloc[:,0]>=start)&(df.iloc[:,0]<=end)]
                signal = subset.iloc[:,1].max()
                noise = subset.iloc[:,1].std()
                sn = signal/noise
                st.write(f"S/N : {sn:.4f}")
                # Export CSV
                csv_file = export_sn_csv(company_name, sn)
                st.download_button("Télécharger CSV S/N", csv_file, file_name="sn_report.csv")
    else:
        file = st.file_uploader("Importer image", type=["png","pdf"])
        if file:
            st.info("Calcul S/N depuis image non encore implémenté")

# --------- Main ---------
if not st.session_state.logged_in:
    login()
else:
    st.write(f"Bienvenue {st.session_state.username} ({st.session_state.role})")
    logout()
    tabs = st.tabs(["Linéarité", "S/N"] + (["Admin"] if st.session_state.role=="admin" else []))
    linearity_tab() if tabs[0] else None
    sn_tab() if tabs[1] else None
    if st.session_state.role=="admin" and len(tabs)>2:
        admin_menu() if tabs[2] else None