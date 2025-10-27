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

def t(key):
    translations = {
        "sn": "Signal / Noise",
        "sn_classic": "S/N (classic)",
        "sn_usp": "S/N (USP)",
        "lod": "LOD",
        "loq": "LOQ",
        "unit": "Unit",
        "upload_chrom": "Upload chromatogram (CSV, image, or PDF)",
        "digitize_info": "You can upload chromatograms or enter data manually.",
        "select_region": "Select analysis region",
        "linearity": "Linearity",
        "admin": "Admin Panel",
        "select_section": "Select a section"
    }
    return translations.get(key, key)

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {"admin": {"password": "admin123", "role": "admin"},
                   "user": {"password": "user123", "role": "user"}}
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default

def extract_xy_from_image_pytesseract(img):
    if pytesseract is None:
        st.error("pytesseract not installed.")
        return pd.DataFrame(columns=["X", "Y"])

    text = pytesseract.image_to_string(img)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    data = []
    for line in lines:
        parts = line.replace(",", ".").split()
        nums = [p for p in parts if p.replace(".", "", 1).isdigit()]
        if len(nums) >= 2:
            data.append((float(nums[0]), float(nums[1])))
    if not data:
        return pd.DataFrame(columns=["X", "Y"])
    return pd.DataFrame(data, columns=["X", "Y"])

def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv", "png", "jpg", "jpeg", "pdf"], key="sn_uploader")

    if uploaded is None:
        st.info("Upload a file or use manual S/N input.")
        sn_manual_mode = True
    else:
        sn_manual_mode = False

    if sn_manual_mode:
        st.subheader("Manual S/N calculation")
        H = st.number_input("H (peak height)", value=0.0)
        h = st.number_input("h (noise)", value=0.0)
        slope_input = st.number_input("Slope (optional for conc. calculation)", value=0.0)
        unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0)
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

    ext = uploaded.name.split(".")[-1].lower()
    signal = None
    time_index = None

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

    if signal is None:
        st.warning("No valid signal detected.")
        return

    n = len(signal)
    st.subheader(t("select_region"))
    default_start = int(n * 0.25)
    default_end = int(n * 0.75)
    start, end = st.slider("Select analysis region", 0, n - 1, (default_start, default_end))

    x_axis = np.array(time_index) if time_index is not None else np.arange(n)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x_axis, signal, label="Chromatogram", color="black")
    ax.axvspan(x_axis[start], x_axis[end], color="orange", alpha=0.3, label="Selected region")
    ax.legend()
    st.pyplot(fig)

    region = signal[start:end+1]
    if len(region) < 2:
        st.warning("Select a larger region.")
        return

    peak = float(np.max(region))
    baseline = float(np.mean(region))
    height = peak - baseline
    noise_std = float(np.std(region, ddof=0))
    unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0)

    sn_classic = peak / noise_std if noise_std != 0 else float("nan")
    sn_usp = height / noise_std if noise_std != 0 else float("nan")

    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")

    slope = st.number_input("Slope (optional for LOD/LOQ)", value=0.0)
    if slope != 0:
        lod = 3.3 * noise_std / slope
        loq = 10 * noise_std / slope
        st.write(f"{t('lod')} ({unit}): {lod:.4f}")
        st.write(f"{t('loq')} ({unit}): {loq:.4f}")

def linearity_panel():
    st.header("Linearity Panel")
    st.info("This section will handle linearity calculations.")

def admin_panel():
    st.header("Admin Panel")
    st.info("Manage users or app settings here.")

def main_app():
    st.sidebar.title("LabT")
    section = st.sidebar.radio(t("select_section"), [t("linearity"), t("sn"), t("admin")])
    if section == t("linearity"):
        linearity_panel()
    elif section == t("sn"):
        sn_panel_full()
    elif section == t("admin"):
        admin_panel()
    else:
        st.error("Unknown section selected.")

def login_screen():
    st.title("LabT - Login")
    if "login_error" not in st.session_state:
        st.session_state.login_error = ""

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

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

    st.markdown("<div style='position: fixed; bottom: 10px; width: 100%; text-align: center; color: gray;'>Powered by: <b>BnB</b></div>", unsafe_allow_html=True)

def run():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login_screen()
    else:
        main_app()

if __name__ == "__main__":
    run()
