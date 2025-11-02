# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io
import os
import json
from datetime import datetime
from scipy.signal import find_peaks

# Optional OCR / PDF features
try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

LOGO_FILE = "logo_labt.png"
USERS_FILE = "users.json"

# -------------------------
# Users helpers
# -------------------------
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {
            "admin": {"password": "admin123", "role": "admin"},
            "user": {"password": "user123", "role": "user"},
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
        return default

USERS = load_users()

def find_user_key(username):
    if username is None:
        return None
    for u in USERS.keys():
        if u.lower() == username.strip().lower():
            return u
    return None

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
# Header
# -------------------------
def header_area():
    cols = st.columns([3,1])
    with cols[0]:
        st.markdown(f"<h1 style='margin-bottom:0.1rem;'>LabT</h1>", unsafe_allow_html=True)
    with cols[1]:
        upl = st.file_uploader("Uploader un logo (optionnel)", type=["png","jpg","jpeg"], key="upload_logo")
        if upl is not None:
            upl.seek(0)
            data = upl.read()
            with open(LOGO_FILE, "wb") as f:
                f.write(data)
            st.success("Logo sauvegardé")

# -------------------------
# Login
# -------------------------
def login_screen():
    st.title("🧪 LabT")
    st.write("Powered by: BnB")
    username = st.text_input("Utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Connexion"):
        uname = (username or "").strip()
        matched = find_user_key(uname)
        if matched and USERS[matched]["password"] == (password or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role", "user")
        else:
            st.error("Identifiants invalides")

# -------------------------
# Linéarité (inchangé)
# -------------------------
def linearity_panel():
    st.header("Linéarité")
    st.write("⚠️ Utiliser exactement le code original ici")
    # Coller ici le code complet original de linearity_panel() tel que fourni précédemment

# -------------------------
# S/N avancé
# -------------------------
def sn_panel_full():
    st.header("S/N")
    uploaded = st.file_uploader("Importer chromatogramme (CSV, PNG, JPG, PDF)", type=["csv","png","jpg","jpeg","pdf"])
    manual_mode = st.checkbox("Calcul manuel S/N / Classic et USP", value=False)
    
    if manual_mode or uploaded is None:
        st.subheader("Calcul manuel")
        H = st.number_input("H (hauteur du pic)", value=0.0, format="%.6f")
        h = st.number_input("h (bruit)", value=0.0, format="%.6f")
        slope_input = st.number_input("Pente linéarité (optionnel)", value=float(st.session_state.linear_slope or 0.0), format="%.6f")
        sn_classic = H/h if h!=0 else np.nan
        sn_usp = 2*H/h if h!=0 else np.nan
        st.write(f"S/N Classic: {sn_classic:.4f}")
        st.write(f"S/N USP: {sn_usp:.4f}")
        if slope_input!=0:
            lod = 3.3*h/slope_input
            loq = 10*h/slope_input
            st.write(f"LOD: {lod:.6f}")
            st.write(f"LOQ: {loq:.6f}")
        if st.button("Voir formules"):
            st.info("S/N Classic = H/h\nS/N USP = 2*H/h\nLOD = 3.3*h/slope\nLOQ = 10*h/slope")
        return

    # --- Lecture CSV / Image / PDF ---
    name = uploaded.name.lower()
    df = None
    img_orig = None
    if name.endswith(".csv"):
        uploaded.seek(0)
        try:
            df = pd.read_csv(uploaded)
        except:
            uploaded.seek(0)
            df = pd.read_csv(uploaded, sep=";", engine="python")
        cols_low = [c.lower() for c in df.columns]
        if "time" in cols_low and "signal" in cols_low:
            df = df.rename(columns={df.columns[cols_low.index("time")]:"X",
                                    df.columns[cols_low.index("signal")]:"Y"})
        else:
            df = df.iloc[:, :2].copy()
            df.columns = ["X","Y"]
        df = df.dropna()
        x = df["X"].values
        y = df["Y"].values
    elif name.endswith((".png",".jpg",".jpeg")):
        uploaded.seek(0)
        img_orig = Image.open(uploaded).convert("RGB")
        st.image(img_orig, caption="Chromatogramme original", use_column_width=True)
        arr = np.array(img_orig.convert("L"))
        y = arr.max(axis=0)
        x = np.arange(len(y))
        df = pd.DataFrame({"X":x,"Y":y})
    elif name.endswith(".pdf") and convert_from_bytes is not None:
        uploaded.seek(0)
        pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
        img_orig = pages[0]
        st.image(img_orig, caption="Chromatogramme original", use_column_width=True)
        arr = np.array(img_orig.convert("L"))
        y = arr.max(axis=0)
        x = np.arange(len(y))
        df = pd.DataFrame({"X":x,"Y":y})
    else:
        st.error("Format non supporté")
        return

    # --- Pic principal ---
    peak_idx = np.argmax(df["Y"].values)
    peak_x = df["X"].values[peak_idx]
    H = df["Y"].values[peak_idx]

    # --- Sélection de la zone bruit ---
    st.subheader("Sélectionner la zone de bruit")
    xmin, xmax = float(df["X"].min()), float(df["X"].max())
    start_end = st.slider("Zone pour bruit", min_value=xmin, max_value=xmax, value=(xmin, xmax))
    region = df[(df["X"]>=start_end[0]) & (df["X"]<=start_end[1])]
    if region.empty:
        region = df.copy()
    h = region["Y"].std(ddof=0)
    baseline = region["Y"].mean()
    half_height = baseline + H/2
    left_idx = np.where(df["Y"].values[:peak_idx]<=half_height)[0]
    right_idx = np.where(df["Y"].values[peak_idx:]<=half_height)[0]
    w_half = df["X"].values[peak_idx+right_idx[0]] - df["X"].values[left_idx[-1]] if len(left_idx)>0 and len(right_idx)>0 else 0.0

    sn_classic = H/h if h!=0 else np.nan
    sn_usp = 2*H/h if h!=0 else np.nan

    st.write(f"S/N Classic: {sn_classic:.4f}")
    st.write(f"S/N USP: {sn_usp:.4f}")
    st.write(f"Temps de rétention du pic principal: {peak_x:.4f}")
    st.write(f"H: {H:.4f}, h (bruit): {h:.4f}, w1/2: {w_half:.4f}")
    
    # --- Plot ---
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(df["X"], df["Y"], label="Chromatogramme")
    ax.axvspan(start_end[0], start_end[1], alpha=0.25, label="Zone bruit")
    ax.plot(peak_x, H, "r^", label="Pic principal")
    ax.axhline(baseline, color="green", linestyle="--", label="Ligne de base")
    ax.axhline(half_height, color="orange", linestyle="--", label="Hauteur H/2")
    ax.set_xlabel("Temps")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    # --- Download image traitée ---
    buf_img = io.BytesIO()
    fig.savefig(buf_img, format="png")
    buf_img.seek(0)
    st.download_button("Télécharger image traitée", buf_img, "processed_chrom.png", "image/png")

# -------------------------
# Main app
# -------------------------
def main_app():
    header_area()
    tabs = st.tabs(["Linéarité", "S/N"])
    with tabs[0]:
        linearity_panel()
    with tabs[1]:
        sn_panel_full()
    if st.button("Déconnexion"):
        st.session_state.user = None
        st.session_state.role = None
        st.experimental_rerun()

# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    if st.session_state.user:
        main_app()
    else:
        login_screen()