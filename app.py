import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from PIL import Image
import io

st.set_page_config(page_title="LabT", layout="wide")

# --- Fonctions utilitaires ---

def lin_regression(df):
    x = df['Concentration']
    y = df['Signal']
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return slope, intercept, r_value**2

def calc_signal_from_conc(conc, slope, intercept):
    return slope * conc + intercept

def calc_conc_from_signal(signal, slope, intercept):
    if slope == 0:
        return np.nan
    return (signal - intercept) / slope

def calc_sn(signal_peak, noise_std):
    return signal_peak / noise_std

def calc_lod_loq(slope, sn_factor=3.3):
    # LOD = 3.3 * σ / slope, LOQ = 10 * σ / slope
    # ici σ = bruit estimé, on utilisera sn_factor * σ / slope
    return sn_factor / slope

# --- Page Linéarité ---
def page_linearity():
    st.header("Linéarité")

    method = st.radio("Méthode:", ["Importer CSV", "Saisie manuelle"])
    
    if method == "Importer CSV":
        uploaded_file = st.file_uploader("Choisir un CSV", type=["csv"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                if 'Concentration' not in df.columns or 'Signal' not in df.columns:
                    st.error("Le CSV doit contenir les colonnes: 'Concentration' et 'Signal'")
                    return None
                st.dataframe(df)
            except Exception as e:
                st.error(f"Erreur lecture CSV: {e}")
                return None
    else:
        st.write("Saisie manuelle (en construction)")
        df = pd.DataFrame(columns=["Concentration", "Signal"])
        n = st.number_input("Nombre de points", min_value=1, value=3, step=1)
        for i in range(n):
            conc = st.number_input(f"Concentration {i+1}", value=0.0)
            sig = st.number_input(f"Signal {i+1}", value=0.0)
            df.loc[i] = [conc, sig]
    
    if df is not None and len(df) > 1:
        slope, intercept, r2 = lin_regression(df)
        st.write(f"Pente: {slope:.4f}, Intercept: {intercept:.4f}, R²: {r2:.4f}")
        st.session_state['slope'] = slope
        st.session_state['intercept'] = intercept
        
        st.subheader("Calcul inversé")
        signal_input = st.number_input("Entrer Signal pour obtenir Concentration", value=0.0)
        st.write("Concentration:", calc_conc_from_signal(signal_input, slope, intercept))
        conc_input = st.number_input("Entrer Concentration pour obtenir Signal", value=0.0)
        st.write("Signal:", calc_signal_from_conc(conc_input, slope, intercept))

# --- Page Signal to Noise ---
def page_sn():
    st.header("Signal / Bruit (S/N)")
    uploaded_file = st.file_uploader("Choisir un CSV ou Image chromatogramme", type=["csv","png","jpg","jpeg"])
    
    if uploaded_file:
        if uploaded_file.name.lower().endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file)
                if 'Time' not in df.columns or 'Signal' not in df.columns:
                    st.error("Le CSV doit contenir les colonnes: 'Time' et 'Signal'")
                    return
                st.line_chart(df.set_index('Time')['Signal'])
                
                # Calcul S/N
                noise_std = df['Signal'].iloc[:10].std()  # bruit estimé sur les 10 premiers points
                peak_signal = df['Signal'].max()
                sn_classic = calc_sn(peak_signal, noise_std)
                sn_usp = peak_signal / (2*noise_std)
                
                st.write(f"S/N classique: {sn_classic:.2f}")
                st.write(f"S/N USP: {sn_usp:.2f}")
                
                # LOD / LOQ si linéarité existante
                slope = st.session_state.get('slope', None)
                intercept = st.session_state.get('intercept', None)
                if slope:
                    lod = 3.3 * noise_std / slope
                    loq = 10 * noise_std / slope
                    st.write(f"LOD (concentration): {lod:.4f}")
                    st.write(f"LOQ (concentration): {loq:.4f}")
                
            except Exception as e:
                st.error(f"Erreur lecture CSV: {e}")
        else:
            try:
                image = Image.open(uploaded_file)
                st.image(image, use_column_width=True)
                st.info("Calcul S/N à partir d'image non implémenté")
            except Exception as e:
                st.error(f"Erreur lecture image: {e}")

# --- Page principale ---
def main():
    st.title("LabT")
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Aller à", ["Linéarité", "S/N"])
    
    if page == "Linéarité":
        page_linearity()
    elif page == "S/N":
        page_sn()

if __name__ == "__main__":
    main()