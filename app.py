# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
from pdf2image import convert_from_bytes

# =========================
# 🔹 CONFIGURATION GÉNÉRALE
# =========================
st.set_page_config(page_title="LabT", layout="wide")

# -------------------------
# 📋 UTILISATEURS (liste déroulante)
# -------------------------
users = {
    "admin": {"password": "admin", "role": "admin", "access": ["Linéarité", "S/N"]},
    "user": {"password": "user", "role": "user", "access": ["Linéarité", "S/N"]}
}

# -------------------------
# 📦 CONVERTIR PDF → IMAGE
# -------------------------
def pdf_to_png(file):
    images = convert_from_bytes(file.read())
    img_byte_arr = BytesIO()
    images[0].save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return Image.open(img_byte_arr)

# -------------------------
# 🔹 PAGE DE CONNEXION
# -------------------------
def login_page():
    st.title("🔐 Connexion / Login")

    username = st.selectbox("Utilisateur / User :", list(users.keys()))
    password = st.text_input("Mot de passe / Password :", type="password")

    if st.button("Connexion / Login"):
        if username in users and password == users[username]["password"]:
            st.session_state["logged_in"] = True
            st.session_state["user"] = username
            st.session_state["role"] = users[username]["role"]
            st.success("✅ Connexion réussie !")
            st.experimental_rerun()
        else:
            st.error("❌ Authentification échouée.")

# -------------------------
# 🔹 MODULE LINÉARITÉ
# -------------------------
def linearity_panel():
    st.subheader("📈 Linéarité / Linearity")

    uploaded_file = st.file_uploader("Importer un fichier CSV contenant les données de calibration :", type=["csv"])
    unit = st.selectbox("Unité de concentration :", ["µg/mL", "mg/mL", "ng/mL", "ppm"], index=0)

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Aperçu des données :", df.head())

            if "Concentration" in df.columns and "Signal" in df.columns:
                x = df["Concentration"]
                y = df["Signal"]

                slope, intercept = np.polyfit(x, y, 1)
                y_pred = slope * x + intercept

                fig, ax = plt.subplots()
                ax.scatter(x, y, label="Données expérimentales", alpha=0.7)
                ax.plot(x, y_pred, color="red", label=f"y = {slope:.4f}x + {intercept:.4f}")
                ax.set_xlabel(f"Concentration ({unit})")
                ax.set_ylabel("Signal (mV ou a.u.)")
                ax.legend()
                st.pyplot(fig)

                r = np.corrcoef(x, y)[0, 1]
                st.markdown(f"**Pente :** {slope:.4f}")
                st.markdown(f"**Ordonnée à l’origine :** {intercept:.4f}")
                st.markdown(f"**Coefficient de corrélation (r) :** {r:.4f}")

                mode = st.radio("Choisir le calcul :", ["Concentration inconnue à partir du signal", "Signal à partir de la concentration"])

                if mode == "Concentration inconnue à partir du signal":
                    signal_input = st.number_input("Entrer le signal mesuré :", min_value=0.0, step=0.001)
                    if signal_input > 0:
                        concentration_calc = (signal_input - intercept) / slope
                        st.success(f"Concentration estimée : {concentration_calc:.4f} {unit}")
                else:
                    conc_input = st.number_input(f"Entrer la concentration ({unit}) :", min_value=0.0, step=0.001)
                    if conc_input > 0:
                        signal_calc = slope * conc_input + intercept
                        st.success(f"Signal estimé : {signal_calc:.4f}")

                st.session_state["slope"] = slope
                st.session_state["unit"] = unit

            else:
                st.error("Le fichier doit contenir les colonnes 'Concentration' et 'Signal'.")
        except Exception as e:
            st.error(f"Erreur : {e}")

# -------------------------
# 🔹 MODULE S/N
# -------------------------
def sn_panel():
    st.subheader("📊 Rapport Signal / Bruit (S/N)")

    file = st.file_uploader("Importer une image chromatogramme (png, jpg, jpeg, pdf)", type=["png", "jpg", "jpeg", "pdf"])

    if file:
        if file.name.lower().endswith(".pdf"):
            st.info("Conversion du PDF en image PNG...")
            image = pdf_to_png(file)
        else:
            image = Image.open(file)

        st.image(image, caption="Chromatogramme original", use_container_width=True)

        threshold = st.slider("Sensibilité (Threshold)", 0, 255, 50)

        # Calculs manuels S/N
        st.markdown("### 🔢 Calcul manuel")
        h = st.number_input("Hauteur du pic (h)", min_value=0.0, step=0.01)
        H = st.number_input("Hauteur du bruit (H)", min_value=0.0, step=0.01)

        slope = st.session_state.get("slope", None)
        unit = st.session_state.get("unit", "µg/mL")

        if slope is None:
            st.info("⚠️ Aucune pente trouvée. Saisir manuellement :")
            slope = st.number_input("Pente (slope)", min_value=0.0, step=0.0001)

        if h > 0 and H > 0:
            sn_classic = h / H
            sn_usp = (2 * h) / H
            st.success(f"S/N (Classique) = {sn_classic:.2f}")
            st.success(f"S/N (USP) = {sn_usp:.2f}")

            lod = (3 * H / slope) if slope else None
            loq = (10 * H / slope) if slope else None

            if lod and loq:
                st.markdown(f"**LOD :** {lod:.4f} {unit}")
                st.markdown(f"**LOQ :** {loq:.4f} {unit}")

        with st.expander("📘 Formules de calcul"):
            st.markdown("""
            **Formules :**
            - S/N (Classique) = h / H  
            - S/N (USP) = 2h / H  
            - LOD = 3 × (H / pente)  
            - LOQ = 10 × (H / pente)
            """)

# -------------------------
# 🔹 MODULE ADMIN
# -------------------------
def admin_panel():
    st.subheader("⚙️ Gestion des utilisateurs")

    action = st.selectbox("Action :", ["Ajouter un utilisateur", "Supprimer un utilisateur", "Modifier privilèges"])

    if action == "Ajouter un utilisateur":
        name = st.text_input("Nom d'utilisateur")
        pwd = st.text_input("Mot de passe", type="password")
        privileges = st.multiselect("Modules autorisés", ["Linéarité", "S/N"])
        if st.button("Créer"):
            users[name] = {"password": pwd, "role": "user", "access": privileges}
            st.success(f"Utilisateur '{name}' ajouté avec succès ✅")

    elif action == "Supprimer un utilisateur":
        to_delete = st.selectbox("Choisir un utilisateur :", list(users.keys()))
        if st.button("Supprimer"):
            if to_delete != "admin":
                del users[to_delete]
                st.success("Utilisateur supprimé.")
            else:
                st.warning("Impossible de supprimer l’administrateur.")

    elif action == "Modifier privilèges":
        user = st.selectbox("Choisir un utilisateur :", list(users.keys()))
        if user in users:
            privileges = st.multiselect("Modules autorisés :", ["Linéarité", "S/N"], default=users[user]["access"])
            if st.button("Mettre à jour"):
                users[user]["access"] = privileges
                st.success("Privilèges mis à jour ✅")

# -------------------------
# 🔹 PAGE PRINCIPALE
# -------------------------
def main_app():
    st.sidebar.title("🔍 Menu principal")

    choice = st.sidebar.radio("Navigation :", ["Linéarité", "S/N", "Changer mot de passe", "Feedback", "Déconnexion"])

    if choice == "Linéarité":
        linearity_panel()
    elif choice == "S/N":
        sn_panel()
    elif choice == "Changer mot de passe":
        st.info("🔐 Fonction à venir.")
    elif choice == "Feedback":
        st.text_area("Vos retours :", placeholder="Saisissez ici votre commentaire...")
        st.button("Envoyer")
    elif choice == "Déconnexion":
        st.session_state.clear()
        st.experimental_rerun()

# -------------------------
# 🚀 LANCEMENT DE L'APPLICATION
# -------------------------
def run():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_page()
    else:
        if st.session_state["role"] == "admin":
            tabs = st.tabs(["Application", "Admin"])
            with tabs[0]:
                main_app()
            with tabs[1]:
                admin_panel()
        else:
            main_app()

if __name__ == "__main__":
    run()