import streamlit as st
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from PIL import Image
import io

# --------- CONFIG LANGUE / LOGIN ---------
LANGS = {"FR": "Français", "EN": "English"}
if "lang" not in st.session_state:
    st.session_state.lang = "FR"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("Login / Connexion")
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    if st.button("Login / Connexion"):
        if username == "admin" and password == "admin":
            st.session_state.logged_in = True
            st.success("Login successful / Connexion réussie")
        else:
            st.error("Invalid credentials / Identifiants incorrects")

def logout():
    st.session_state.logged_in = False
    st.experimental_rerun()

# --------- PAGE LINÉARITÉ ---------
def page_linearity():
    st.header("Linéarité / Linearity")
    df = None  # <- initialisation

    method = st.radio(
        "Méthode / Method",
        ["Importer CSV", "Saisie manuelle", "Saisie manuelle (en construction)"]
    )

    if method == "Importer CSV":
        uploaded_file = st.file_uploader("Choisir un fichier CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Erreur lecture CSV : {e}")
    elif method.startswith("Saisie manuelle"):
        n = st.number_input("Nombre de points / Number of points", min_value=1, step=1)
        data = []
        for i in range(n):
            x = st.number_input(f"Concentration {i+1}", key=f"x{i}")
            y = st.number_input(f"Signal {i+1}", key=f"y{i}")
            data.append([x, y])
        if data:
            df = pd.DataFrame(data, columns=["Concentration", "Signal"])

    if df is not None and len(df) > 0:
        st.write(df)
        # Calcul pente/intercept
        try:
            slope, intercept = np.polyfit(df["Concentration"], df["Signal"], 1)
            st.write(f"Pente / Slope : {slope:.4f}")
            st.write(f"Intercept : {intercept:.4f}")

            signal_inconnu = st.number_input("Signal inconnu / Unknown signal")
            if signal_inconnu:
                conc_inconnu = (signal_inconnu - intercept) / slope
                st.write(f"Concentration inconnue / Unknown conc : {conc_inconnu:.4f}")

            # LOD / LOQ en concentration (simplifié)
            st.subheader("LOD / LOQ en concentration")
            sigma = st.number_input("Sigma / écart-type du bruit", min_value=0.0, step=0.001)
            if sigma > 0:
                lod = 3.3 * sigma / slope
                loq = 10 * sigma / slope
                st.write(f"LOD : {lod:.4f}")
                st.write(f"LOQ : {loq:.4f}")
        except Exception as e:
            st.error(f"Erreur calcul linéarité : {e}")

# --------- PAGE SIGNAL/BRUIT ---------
def page_sn():
    st.header("Signal / Bruit / Signal to Noise (S/N)")
    uploaded_file = st.file_uploader("Charger chromatogramme CSV ou image", type=["csv", "png", "jpg", "jpeg"])
    df = None
    signal_column = "Signal"

    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Erreur lecture CSV : {e}")
        else:
            try:
                image = Image.open(uploaded_file)
                st.image(image, use_column_width=True)
            except Exception as e:
                st.error(f"Erreur lecture image : {e}")

    if df is not None and signal_column in df.columns:
        signal = df[signal_column].values
        peaks, _ = find_peaks(signal)
        if len(peaks) > 0:
            peak_heights = signal[peaks]
            noise = np.std(signal[:10])  # bruit estimé sur premiers points
            sn_values = peak_heights / noise
            st.write("S/N classique :")
            st.write(sn_values)

            # S/N USP simplifié
            sn_usp = (max(peak_heights) - min(signal)) / (2*noise)
            st.write(f"S/N USP : {sn_usp:.4f}")
        else:
            st.warning("Aucun pic détecté / No peaks detected")

# --------- PAGE PRINCIPALE ---------
def main():
    st.sidebar.title("Menu")
    lang_choice = st.sidebar.selectbox("Langue / Language", list(LANGS.values()))
    st.session_state.lang = "FR" if lang_choice == "Français" else "EN"

    if not st.session_state.logged_in:
        login()
        return
    else:
        if st.sidebar.button("Logout / Déconnexion"):
            logout()

    page = st.sidebar.selectbox("Page", ["Linéarité / Linearity", "S/N / Signal to Noise"])
    if page.startswith("Linéarité"):
        page_linearity()
    elif page.startswith("S/N"):
        page_sn()

if __name__ == "__main__":
    main()