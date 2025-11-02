# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from PIL import Image, ImageOps
import io
from fpdf import FPDF
import json

# ------------------------------
# Connexion (JSON) avec Powered by BnB
# ------------------------------
def login_page():
    st.title("LabT Login / Connexion")
    st.markdown("**Powered by BnB**")
    
    users_file = "users.json"
    with open(users_file, "r") as f:
        users = json.load(f)
    
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    
    if st.button("Login / Se connecter"):
        if username in users and users[username] == password:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.experimental_rerun()
        else:
            st.error("Invalid credentials / Identifiants invalides")

# ------------------------------
# Linéarité inchangée
# ------------------------------
def linearity_panel():
    st.header("Linearity / Linéarité")
    st.info("Linéarité inchangée. CSV ou saisie manuelle")
    
    csv_file = st.file_uploader("Upload CSV (X=Concentration, Y=Signal)", type=["csv"])
    manual_input = st.checkbox("Manual input / Saisie manuelle")
    
    if csv_file:
        df = pd.read_csv(csv_file)
        st.dataframe(df)
    elif manual_input:
        conc = st.text_input("Enter concentrations (comma separated)", "")
        sig = st.text_input("Enter signals (comma separated)", "")
        if conc and sig:
            conc_list = [float(c.strip()) for c in conc.split(",")]
            sig_list = [float(s.strip()) for s in sig.split(",")]
            df = pd.DataFrame({"Concentration": conc_list, "Signal": sig_list})
            st.dataframe(df)
    
    # Calcul inconnu
    st.subheader("Unknown / Inconnu")
    unknown_signal = st.number_input("Enter unknown signal", value=0.0)
    if 'df' in locals() and not df.empty:
        slope, intercept = np.polyfit(df["Concentration"], df["Signal"], 1)
        unknown_conc = (unknown_signal - intercept)/slope
        st.write(f"Estimated concentration: {unknown_conc:.4f}")

    # Export slope for S/N
    if 'df' in locals() and not df.empty:
        st.session_state['slope_linearity'] = slope

# ------------------------------
# S/N amélioré
# ------------------------------
def sn_panel_enhanced():
    st.header("S/N Analysis / Analyse S/N")
    
    uploaded = st.file_uploader("Upload chromatogram (CSV, PNG, JPG, PDF)", type=["csv","png","jpg","jpeg","pdf"])
    manual = False
    df = None

    # ---------------------
    # CSV
    # ---------------------
    if uploaded and uploaded.name.lower().endswith(".csv"):
        uploaded.seek(0)
        try:
            df0 = pd.read_csv(uploaded)
        except:
            uploaded.seek(0)
            df0 = pd.read_csv(uploaded, sep=";", engine="python")
        cols_low = [c.lower() for c in df0.columns]
        if "time" in cols_low and "signal" in cols_low:
            df = df0.rename(columns={df0.columns[cols_low.index("time")]:"X",
                                     df0.columns[cols_low.index("signal")]:"Y"})
        else:
            df = df0.iloc[:, :2].copy()
            df.columns = ["X","Y"]
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

    # ---------------------
    # Image
    # ---------------------
    elif uploaded and uploaded.name.lower().endswith((".png",".jpg",".jpeg",".pdf")):
        uploaded.seek(0)
        if uploaded.name.lower().endswith(".pdf"):
            try:
                from pdf2image import convert_from_bytes
                pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
                img = pages[0].convert("L")
            except:
                st.error("PDF processing failed. Make sure poppler is installed.")
                return
        else:
            img = Image.open(uploaded).convert("L")
        
        # Convert to B/W for analysis
        img_bw = img.point(lambda x: 0 if x<128 else 255, '1')
        arr = np.array(img_bw).astype(float)
        arr = arr.max(axis=0)  # projection verticale
        df = pd.DataFrame({"X": np.arange(len(arr)), "Y": arr})
        st.subheader("Chromatogram original / Chromatogramme original")
        st.image(img, use_column_width=True)

    # ---------------------
    # Manuel
    # ---------------------
    if df is None:
        manual = True
        st.info("Manual S/N calculation / Calcul manuel")
        H = st.number_input("H (peak height / hauteur du pic)", value=0.0, format="%.6f")
        h = st.number_input("h (noise / bruit)", value=0.0, format="%.6f")
        slope_input = st.number_input("Slope / pente", value=0.0, format="%.6f")
        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2*H/h if h != 0 else float("nan")
        st.write(f"S/N Classic: {sn_classic:.4f}")
        st.write(f"S/N USP: {sn_usp:.4f}")
        if slope_input:
            lod = 3.3*h/slope_input
            loq = 10*h/slope_input
            st.write(f"LOD: {lod:.6f}")
            st.write(f"LOQ: {loq:.6f}")
        return

    # ---------------------
    # Slider unique pour zone de bruit
    # ---------------------
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    default_start = x_min + 0.25*(x_max-x_min)
    default_end = x_min + 0.75*(x_max-x_min)
    start, end = st.slider("Select X range for noise / Sélectionner zone de bruit",
                            min_value=float(x_min),
                            max_value=float(x_max),
                            value=(float(default_start), float(default_end)))
    region = df[(df["X"]>=start)&(df["X"]<=end)]
    noise_std = region["Y"].std(ddof=0) if not region.empty else np.std(df["Y"])
    baseline = region["Y"].mean() if not region.empty else np.mean(df["Y"])

    # ---------------------
    # Pic principal
    # ---------------------
    y = df["Y"].values
    x = df["X"].values
    peak_idx = np.argmax(y)
    peak_x = x[peak_idx]
    peak_y = y[peak_idx]
    height = peak_y - baseline
    half_height = baseline + height/2

    left_idx = np.where(y[:peak_idx]<=half_height)[0]
    right_idx = np.where(y[peak_idx:]<=half_height)[0]
    W = (x[peak_idx] - x[left_idx[-1]] if len(left_idx)>0 else np.nan)
    if len(right_idx)>0:
        W += x[peak_idx+right_idx[0]] - x[peak_idx]

    # ---------------------
    # Calcul S/N
    # ---------------------
    sn_classic = peak_y / noise_std
    sn_usp = height / noise_std
    st.write(f"S/N Classic: {sn_classic:.4f}")
    st.write(f"S/N USP: {sn_usp:.4f}")
    st.write(f"H: {height:.4f}, Noise h: {noise_std:.4f}, W1/2: {W:.4f}, Peak X: {peak_x:.4f}")

    # ---------------------
    # Plot
    # ---------------------
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(x,y, label="Chromatogram")
    ax.axvspan(start,end,alpha=0.25,label="Noise region")
    ax.plot(peak_x, peak_y,"r^", label="Main peak")
    ax.axhline(baseline, color="green", linestyle="--", label="Baseline")
    ax.axhline(half_height,color="orange",linestyle="--", label="Half height")
    ax.set_xlabel("Time")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    # ---------------------
    # Export image et PDF
    # ---------------------
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    st.download_button("Download processed image", buf, "sn_image.png", "image/png")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"S/N Analysis Report",0,1,"C")
    pdf.cell(0,8,f"S/N Classic: {sn_classic:.4f}",0,1)
    pdf.cell(0,8,f"S/N USP: {sn_usp:.4f}",0,1)
    pdf.cell(0,8,f"H: {height:.4f}, Noise h: {noise_std:.4f}, W1/2: {W:.4f}, Peak X: {peak_x:.4f}",0,1)
    pdf.image(buf, x=10, y=50, w=190)
    pdf_buf = io.BytesIO()
    pdf.output(pdf_buf)
    pdf_buf.seek(0)
    st.download_button("Download PDF", pdf_buf, "sn_report.pdf", "application/pdf")

# ------------------------------
# Main
# ------------------------------
def main_app():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        login_page()
        return
    st.sidebar.title(f"Welcome {st.session_state['username']}")
    page = st.sidebar.radio("Select page / Choisir page", ["Linearity / Linéarité", "S/N"])
    if page.startswith("Linearity"):
        linearity_panel()
    elif page.startswith("S/N"):
        sn_panel_enhanced()

def run():
    main_app()

if __name__ == "__main__":
    run()