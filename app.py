# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import io
import json
import tempfile
from datetime import datetime

# Optional features
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {"admin": {"password": "admin123", "role": "admin"},
                   "user": {"password": "user123", "role": "user"}}
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        return default

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

USERS = load_users()
# -------------------------
# S/N panel (amélioré, mais 100% compatible avec le reste)
# -------------------------
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))
    uploaded = st.file_uploader(
        t("upload_chrom"),
        type=["csv", "png", "jpg", "jpeg", "pdf"],
        key="sn_uploader"
    )

    if uploaded is None:
        st.info("Upload a file or use manual S/N input.")
        sn_manual_mode = True
    else:
        sn_manual_mode = False

    # Mode manuel (inchangé)
    if sn_manual_mode:
        st.subheader("Manual S/N calculation")
        H = st.number_input("H (peak height)", value=0.0)
        h = st.number_input("h (noise)", value=0.0)
        slope_input = st.number_input("Slope (optional for conc. calculation)", value=float(st.session_state.linear_slope or 0.0))
        unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0, key="sn_unit_manual")
        if st.button("Compute S/N"):
            sn_classic = H / h if h != 0 else float("nan")
            sn_usp = 2 * H / h if h != 0 else float("nan")
            st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
            st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
            if slope_input != 0:
                lod = 3.3 * h / slope_input
                loq = 10 * h / slope_input
                st.write(f"{t('lod')} ({unit}): {lod:.4f}")
                st.write(f"{t('loq')} ({unit}): {loq:.4f}")
        return

    # Lecture du fichier uploadé
    ext = uploaded.name.split(".")[-1].lower()
    signal = None
    time_index = None

    # CSV
    if ext == "csv":
        try:
            uploaded.seek(0)
            df = pd.read_csv(uploaded)
            cols_low = [c.lower() for c in df.columns]
            if "time" in cols_low and "signal" in cols_low:
                time_index = df.iloc[:, cols_low.index("time")].values
                signal = pd.to_numeric(df.iloc[:, cols_low.index("signal")], errors="coerce").fillna(0).values
            elif len(df.columns) >= 2:
                time_index = df.iloc[:, 0].values
                signal = pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0).values
            else:
                st.error("CSV must have at least two columns (time, signal).")
                return
            st.subheader("Raw data preview")
            st.dataframe(df.head(50))
        except Exception as e:
            st.error(f"CSV error: {e}")
            return

    # Images / PDF → OCR
    elif ext in ["png", "jpg", "jpeg", "pdf"]:
        try:
            if ext == "pdf" and convert_from_bytes is not None:
                images = convert_from_bytes(uploaded.read())
                img = images[0]
            else:
                img = Image.open(uploaded).convert("RGB")

            df = extract_xy_from_image_pytesseract(img)
            if df.empty:
                st.error("Unable to extract numeric data from image.")
                return

            df = df.sort_values("X")
            time_index = df["X"].values
            signal = df["Y"].values

            st.subheader("Extracted chromatogram (digitized)")
            fig_preview, axp = plt.subplots(figsize=(8, 3))
            axp.plot(time_index, signal, color="blue")
            axp.set_xlabel("Time / Points")
            axp.set_ylabel("Signal")
            st.pyplot(fig_preview)

        except Exception as e:
            st.error(f"Image/PDF error: {e}")
            return

    # Si pas de signal → stop
    if signal is None:
        st.warning("No valid signal detected.")
        return

    # Sélection directe sur chromatogramme original
    n = len(signal)
    st.subheader(t("select_region"))

    default_start = int(n * 0.25)
    default_end = int(n * 0.75)
    start, end = st.slider("Select analysis region", 0, n - 1, (default_start, default_end), key="sn_region_slider")

    try:
        x_axis = np.array(time_index)
        if not np.issubdtype(x_axis.dtype, np.number):
            x_axis = np.arange(n)
    except Exception:
        x_axis = np.arange(n)

    # Affichage fidèle du chromatogramme
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x_axis, signal, label="Chromatogram", color="black")
    ax.axvspan(x_axis[start], x_axis[end], color="orange", alpha=0.3, label="Selected region")
    ax.set_xlabel("Time / Points")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    # Extraction et calcul
    region = signal[start:end+1]
    if len(region) < 2:
        st.warning("Select a larger region.")
        return

    peak = float(np.max(region))
    baseline = float(np.mean(region))
    height = peak - baseline
    noise_std = float(np.std(region, ddof=0))
    unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0, key="sn_unit_region")

    sn_classic = peak / noise_std if noise_std != 0 else float("nan")
    sn_usp = height / noise_std if noise_std != 0 else float("nan")

    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")

    if st.session_state.linear_slope is not None:
        slope = st.session_state.linear_slope
        if slope != 0:
            lod = 3.3 * noise_std / slope
            loq = 10 * noise_std / slope
            st.write(f"{t('lod')} ({unit}): {lod:.4f}")
            st.write(f"{t('loq')} ({unit}): {loq:.4f}")
# -------------------------
# Main app navigation
# -------------------------
def main_app():
    st.sidebar.title("LabT")
    section = st.sidebar.radio(
        t("select_section"),
        [t("linearity"), t("sn"), t("admin")],
        key="main_section",
    )

    if section == t("linearity"):
        linearity_panel()
    elif section == t("sn"):
        sn_panel_full()
    elif section == t("admin"):
        admin_panel()
    else:
        st.error("Unknown section selected.")


# -------------------------
# Login screen (avec signature)
# -------------------------
def login_screen():
    st.title("LabT - Login")

    if "login_error" not in st.session_state:
        st.session_state.login_error = ""

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        with open("users.json", "r") as f:
            users = json.load(f)
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.session_state.login_error = "Invalid username or password."

    if st.session_state.login_error:
        st.error(st.session_state.login_error)

    # ✅ Signature ajoutée en bas
    st.markdown(
        "<div style='position: fixed; bottom: 10px; width: 100%; text-align: center; color: gray;'>"
        "Powered by: <b>BnB</b>"
        "</div>",
        unsafe_allow_html=True,
    )


# -------------------------
# Main controller
# -------------------------
def run():
    st.set_page_config(page_title="LabT", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_screen()
    else:
        main_app()


# -------------------------
# App entry point
# -------------------------
if __name__ == "__main__":
    run()
