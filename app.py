# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import io

# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

# ----------------------------
# TRANSLATIONS
# ----------------------------
def t(text):
    # Simplified: return text as-is
    return text

# ----------------------------
# PAGE LOGIN
# ----------------------------
def login_page():
    st.title(t("Login / Connexion"))
    username = st.text_input(t("Username / Nom d'utilisateur"))
    password = st.text_input(t("Password / Mot de passe"), type="password")
    login_btn = st.button(t("Login / Se connecter"))
    st.markdown("<p style='font-size:0.7em;text-align:center;'>Powered by BnB</p>", unsafe_allow_html=True)
    if login_btn:
        # Here, dummy auth
        if username == "admin" and password == "admin":
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error(t("Invalid credentials / Identifiants invalides"))

# ----------------------------
# LINEARITY PANEL (unchanged)
# ----------------------------
def linearity_panel():
    st.header(t("Linearity"))
    uploaded = st.file_uploader(t("Upload CSV (Time,Signal,Conc)"), type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.write(df.head())
            # simple linear regression
            if "Signal" in df.columns and "Conc" in df.columns:
                slope = np.polyfit(df["Conc"], df["Signal"], 1)[0]
                st.session_state.linear_slope = slope
                st.write(f"Slope / Pente: {slope:.6f}")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

# ----------------------------
# S/N PANEL ENHANCED
# ----------------------------
def sn_panel():
    st.header(t("Signal to Noise / Rapport Signal/Bruit"))
    uploaded = st.file_uploader(t("Upload chromatogram (CSV, PNG, JPG, JPEG, PDF)"), type=["csv","png","jpg","jpeg","pdf"])
    mode_manual = st.checkbox("Manual S/N calculation (H,h,slope)", value=False)
    
    # --- Variables ---
    H = h = slope = 0.0
    sn_classic = sn_usp = lod = loq = np.nan
    peak_x = 0.0

    # --- Formulas explainer ---
    with st.expander("Formulas / Formules"):
        st.markdown("""
        **S/N Classic** = Peak height / Noise std deviation  
        **S/N USP** = 2 × Peak height / Noise std deviation  
        **LOD** = 3.3 × Noise / Slope  
        **LOQ** = 10 × Noise / Slope  
        **Width @ Half height** = distance between left and right X where Y = H/2
        """)

    # --- Manual calculation ---
    if mode_manual:
        H = st.number_input("H (peak height)", value=0.0, format="%.6f")
        h = st.number_input("h (noise)", value=0.0, format="%.6f")
        use_linear_slope = st.checkbox("Use slope from linearity panel", value=True)
        if use_linear_slope and st.session_state.linear_slope:
            slope = st.session_state.linear_slope
        else:
            slope = st.number_input("Slope (m)", value=0.0, format="%.6f")
        if h != 0:
            sn_classic = H/h
            sn_usp = 2*H/h
            if slope != 0:
                lod = 3.3*h/slope
                loq = 10*h/slope
        st.write(f"S/N Classic: {sn_classic:.4f}")
        st.write(f"S/N USP: {sn_usp:.4f}")
        st.write(f"LOD: {lod:.6f}, LOQ: {loq:.6f}")

    # --- Image/CSV upload ---
    if uploaded and not mode_manual:
        name = uploaded.name.lower()
        df = None
        # CSV
        if name.endswith(".csv"):
            uploaded.seek(0)
            try: df = pd.read_csv(uploaded)
            except: uploaded.seek(0); df = pd.read_csv(uploaded, sep=";", engine="python")
            df.columns = ["X","Y"] if len(df.columns)>=2 else df.columns
            df["X"] = pd.to_numeric(df["X"], errors="coerce")
            df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
        # Image
        elif name.endswith((".png",".jpg",".jpeg")):
            uploaded.seek(0)
            img = Image.open(uploaded).convert("L")
            arr = np.array(img)
            arr = arr.max() - arr
            df = pd.DataFrame({"X": np.arange(arr.shape[1]), "Y": arr.max(axis=0)})
        if df is not None:
            df = df.dropna().sort_values("X").reset_index(drop=True)
            # Slider unique
            x_min, x_max = float(df["X"].min()), float(df["X"].max())
            slider_range = st.slider("Select noise region", min_value=x_min, max_value=x_max, value=(x_min+0.25*(x_max-x_min), x_min+0.75*(x_max-x_min)))
            region = df[(df["X"]>=slider_range[0]) & (df["X"]<=slider_range[1])]
            if len(region)==0: region = df
            peak_idx = df["Y"].idxmax()
            peak_x = df.loc[peak_idx,"X"]
            peak_y = df.loc[peak_idx,"Y"]
            baseline = region["Y"].mean()
            height = peak_y - baseline
            half_height = baseline + height/2
            left_idx = df[df["X"]<=peak_x][df["Y"]<=half_height]["X"]
            right_idx = df[df["X"]>=peak_x][df["Y"]<=half_height]["X"]
            W = (right_idx.iloc[0]-left_idx.iloc[-1]) if len(left_idx)>0 and len(right_idx)>0 else np.nan
            noise_std = region["Y"].std(ddof=0)
            sn_classic = peak_y/noise_std
            sn_usp = height/noise_std
            if st.session_state.linear_slope:
                slope = st.session_state.linear_slope
                lod = 3.3*noise_std/slope
                loq = 10*noise_std/slope
            st.write(f"S/N Classic: {sn_classic:.4f}, S/N USP: {sn_usp:.4f}")
            st.write(f"Peak X (retention time): {peak_x:.4f}, H: {height:.4f}, Noise h: {noise_std:.4f}, Width W: {W:.4f}")
            if slope != 0: st.write(f"LOD: {lod:.6f}, LOQ: {loq:.6f}")
            # Plot
            fig, ax = plt.subplots(figsize=(10,3))
            ax.plot(df["X"], df["Y"], label="Chromatogram")
            ax.axvspan(slider_range[0], slider_range[1], alpha=0.25, color="yellow", label="Noise region")
            ax.plot(peak_x, peak_y,"r^", label="Main peak")
            ax.axhline(baseline,color="green",linestyle="--",label="Baseline")
            ax.axhline(half_height,color="orange",linestyle="--",label="Half height")
            ax.set_xlabel("Time / Temps")
            ax.set_ylabel("Signal")
            ax.legend()
            st.pyplot(fig)
            # Export image
            buf_img = io.BytesIO()
            fig.savefig(buf_img, format="png", bbox_inches="tight")
            buf_img.seek(0)
            st.download_button("Download processed image","image/png", buf_img.getvalue())

# ----------------------------
# MAIN APP
# ----------------------------
def main_app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_page()
        return
    st.sidebar.title("LabT Panels")
    choice = st.sidebar.radio("Select panel / Sélectionnez le panel", ["Linearity", "S/N"])
    if choice=="Linearity":
        linearity_panel()
    elif choice=="S/N":
        sn_panel()

# ----------------------------
# RUN
# ----------------------------
def run():
    main_app()

if __name__=="__main__":
    run()