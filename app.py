# -----------------------------
# LABT — PART 1 (core + login/admin/navigation + utils)
# -----------------------------
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io, os, tempfile, json, smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from scipy.signal import find_peaks
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

# --- Vérification poppler (pour PDF) ---
POPPLER_PATH = "/usr/bin/poppler"
if not os.path.exists("/usr/bin/pdftoppm"):
    st.warning("⚠️ Poppler introuvable : l’OCR sur PDF peut ne pas fonctionner correctement.")

# -----------------------------
# Configuration de l’application
# -----------------------------
st.set_page_config(page_title="LabT", layout="wide")

# --- Style CSS léger ---
st.markdown("""
<style>
body {font-family: "Segoe UI", sans-serif;}
div.stButton > button {width: 100%; border-radius: 8px; background-color: #0366d6; color: white;}
div.stSelectbox > div[data-baseweb="select"] {border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Base utilisateurs
# -----------------------------
users = {
    "admin": {"password": "admin", "role": "admin", "access": ["linearity", "sn"]},
    "user1": {"password": "1234", "role": "user", "access": ["sn"]},
    "user2": {"password": "abcd", "role": "user", "access": ["linearity"]},
}

# -----------------------------
# Gestion de session
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "access" not in st.session_state:
    st.session_state["access"] = []

# -----------------------------
# Page de connexion
# -----------------------------
def login_page():
    st.title("🔬 Connexion à LabT")

    username = st.selectbox("👤 Utilisateur", list(users.keys()))
    password = st.text_input("🔑 Mot de passe", type="password")

    if st.button("Se connecter"):
        if username in users and password == users[username]["password"]:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]
            st.session_state["access"] = users[username].get("access", [])
            st.success(f"Bienvenue, {username} !")
            st.rerun()
        else:
            st.error("❌ Identifiants invalides.")

# -----------------------------
# Déconnexion
# -----------------------------
def logout():
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["access"] = []
    st.success("Déconnecté ✅")
    st.rerun()

# -----------------------------
# Lecture OCR (image/pdf)
# -----------------------------
def extract_xy_from_image_or_pdf(file_bytes, filename):
    try:
        ext = filename.split(".")[-1].lower()
        if ext == "pdf":
            images = convert_from_bytes(file_bytes)
            text = ""
            for img in images:
                text += pytesseract.image_to_string(img)
        else:
            img = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(img)

        data = []
        for line in text.splitlines():
            parts = line.strip().replace(",", ".").split()
            if len(parts) == 2:
                try:
                    x, y = map(float, parts)
                    data.append((x, y))
                except:
                    continue
        if not data:
            raise ValueError("Aucune donnée XY trouvée.")
        df = pd.DataFrame(data, columns=["X", "Y"])
        return df
    except Exception as e:
        st.warning(f"OCR invalide : {e}")
        return None

# -----------------------------
# Barre de navigation principale
# -----------------------------
def navigation_menu():
    st.sidebar.title(f"👋 Bonjour, {st.session_state['username']} !")

    module = st.sidebar.selectbox(
        "📘 Modules disponibles",
        ["Accueil", "Linéarité", "S/N", "Feedback", "Admin", "Déconnexion"],
    )
    return module

# -----------------------------
# Accueil
# -----------------------------
def accueil():
    st.title("Bienvenue dans LabT 🧪")
    st.markdown("Sélectionnez un module dans le menu de gauche pour commencer.")
# -----------------------------
# PART 2 — linearity_panel, sn_panel_full, feedback_panel, main_app routing
# (COLLER APRES PARTIE 1)
# -----------------------------
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

# -------------------------
# Linearity panel
# - Kept behavior: CSV or manual input, fit linear regression, compute signal<->concentration
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name_linearity")

    mode = st.radio(t("input_csv"), [t("input_csv"), t("input_manual")], key="lin_input_mode")
    df = None

    # CSV input
    if mode == t("input_csv"):
        uploaded = st.file_uploader(t("input_csv"), type=["csv"], key="lin_csv")
        if uploaded:
            try:
                uploaded.seek(0)
                try:
                    df0 = pd.read_csv(uploaded)
                except Exception:
                    uploaded.seek(0)
                    df0 = pd.read_csv(uploaded, sep=";", engine="python")
                cols_low = [c.lower() for c in df0.columns]
                if "concentration" in cols_low and "signal" in cols_low:
                    df = df0.rename(columns={df0.columns[cols_low.index("concentration")]: "Concentration",
                                             df0.columns[cols_low.index("signal")]: "Signal"})
                elif len(df0.columns) >= 2:
                    df = df0.iloc[:, :2].copy()
                    df.columns = ["Concentration", "Signal"]
                else:
                    st.error("CSV must contain at least two columns (concentration, signal).")
                    return
            except Exception as e:
                st.error(f"CSV error: {e}")
                return

    # Manual input
    else:
        st.caption("Enter concentrations (comma-separated) and signals (comma-separated).")
        cols = st.columns(2)
        conc_input = cols[0].text_area("Concentrations (comma separated)", height=120, key="lin_manual_conc")
        sig_input = cols[1].text_area("Signals (comma separated)", height=120, key="lin_manual_sig")
        # Try parse
        try:
            concs = [float(s.replace(",",".").strip()) for s in conc_input.split(",") if s.strip()!=""]
            sigs = [float(s.replace(",",".").strip()) for s in sig_input.split(",") if s.strip()!=""]
            if concs and sigs:
                if len(concs) != len(sigs):
                    st.error("Number of concentrations and signals must match.")
                    return
                if len(concs) < 2:
                    st.warning("At least two pairs are required.")
                    return
                df = pd.DataFrame({"Concentration": concs, "Signal": sigs})
            else:
                st.info("Enter data or upload a CSV.")
                return
        except Exception as e:
            st.error(f"Manual parse error: {e}")
            return

    # unit selector
    unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0, key="lin_unit_select")

    # ensure numeric
    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"], errors="coerce")
        df["Signal"] = pd.to_numeric(df["Signal"], errors="coerce")
    except Exception:
        st.error("Concentration and Signal must be numeric.")
        return

    df = df.dropna().sort_values("Concentration").reset_index(drop=True)
    if len(df) < 2:
        st.warning("At least 2 valid points required.")
        return

    # Fit linear regression (least squares)
    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred)**2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values))**2)
    r2 = float(1 - ss_res/ss_tot) if ss_tot != 0 else 0.0

    # store slope to session for S/N
    st.session_state["linear_slope"] = slope

    # show metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Slope", f"{slope:.6f}")
    c2.metric("Intercept", f"{intercept:.6f}")
    c3.metric("R²", f"{r2:.4f}")

    # Plot (solid line)
    fig, ax = plt.subplots(figsize=(8,4))
    ax.scatter(df["Concentration"], df["Signal"], label="Data", zorder=3)
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 200)
    ax.plot(xs, slope*xs + intercept, color="black", linestyle="-", linewidth=2, label="Fit")
    ax.set_xlabel(f"{t('concentration')} ({unit})")
    ax.set_ylabel(t("signal"))
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend()
    st.pyplot(fig)

    # Unknown conversions (automatic)
    st.markdown("### Convertisseur (Signal ↔ Concentration)")
    conv_choice = st.radio("Convert", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_conv_choice")
    val = st.number_input("Enter value", format="%.6f", key="lin_conv_val")
    try:
        if conv_choice.startswith(t("signal")):
            if slope == 0:
                st.error("Slope is zero; cannot compute concentration.")
            else:
                conc = (float(val) - intercept) / slope
                st.success(f"Concentration = {conc:.6f} {unit}")
        else:
            sig = slope * float(val) + intercept
            st.success(f"Signal = {sig:.6f}")
    except Exception as e:
        st.error(f"Conversion error: {e}")

    # formulas expander
    with st.expander(t("formulas")):
        st.markdown(r"""
        **Linearity:** \( y = slope \cdot X + intercept \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

    # Export CSV & PDF
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")
    if st.button(t("generate_pdf"), key="lin_pdf_btn"):
        if not company or company.strip()=="":
            st.warning(t("company_missing"))
        else:
            imgbuf = io.BytesIO()
            fig.savefig(imgbuf, format="png", bbox_inches="tight")
            imgbuf.seek(0)
            lines = [
                f"Company: {company}",
                f"User: {st.session_state.get('username','Unknown')}",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Slope: {slope:.6f}",
                f"Intercept: {intercept:.6f}",
                f"R²: {r2:.6f}"
            ]
            pdfb = generate_pdf_bytes("Linearity report", lines, img_bytes=imgbuf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
            st.download_button(t("download_pdf"), pdfb, file_name="linearity_report.pdf", mime="application/pdf")


# -------------------------
# S/N panel (improved) — works on original image (no redraw), uses real pixel X axis or CSV Time
# - For images: vertical projection of image intensity -> signal (preserves original axes as pixel indices)
# - Displays annotated image and lets user select noise region using two-handle slider (on X axis units used)
# -------------------------
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))

    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_input")
    # manual fallback
    manual_mode = st.checkbox(t("manual_sn"), key="sn_manual_mode", value=False)

    # Manual mode: allow H,h and slope selection
    if manual_mode:
        st.subheader(t("manual_sn"))
        H = st.number_input("H (peak signal)", value=0.0, format="%.6f", key="manual_H")
        h = st.number_input("h (noise)", value=0.0, format="%.6f", key="manual_h")
        slope_src = st.radio("Slope source", ("From linearity", "Manual"), key="manual_slope_src")
        slope_val = None
        if slope_src == "From linearity":
            slope_val = st.session_state.get("linear_slope", None)
            if slope_val is None:
                st.warning("No slope available from linearity. Please enter manually.")
                slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="manual_slope_missing")
        else:
            slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="manual_slope_val")

        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = (2 * H / h) if h != 0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        if slope_val and slope_val != 0:
            unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"], key="manual_unit_choice")
            lod = 3.3 * h / slope_val
            loq = 10 * h / slope_val
            st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
            st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
        return

    if uploaded is None:
        st.info("Upload chromatogram (CSV or image) or enable manual mode.")
        return

    name = uploaded.name.lower()
    df = None
    orig_img = None
    using_image = False
    using_csv = False

    # CSV path: use numeric X (time) and Y (signal)
    if name.endswith(".csv"):
        using_csv = True
        try:
            uploaded.seek(0)
            try:
                df0 = pd.read_csv(uploaded)
            except Exception:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded, sep=";", engine="python")
            if df0.shape[1] < 2:
                st.error("CSV must contain at least two columns (time, signal).")
                return
            cols_low = [c.lower() for c in df0.columns]
            if "time" in cols_low and "signal" in cols_low:
                df = df0.rename(columns={df0.columns[cols_low.index("time")]: "X",
                                         df0.columns[cols_low.index("signal")]: "Y"})
            else:
                df = df0.iloc[:, :2].copy()
                df.columns = ["X", "Y"]
            df["X"] = pd.to_numeric(df["X"], errors="coerce")
            df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
            df = df.dropna().sort_values("X").reset_index(drop=True)
        except Exception as e:
            st.error(f"CSV read error: {e}")
            return

    # Image path: compute vertical projection on grayscale intensities
    elif name.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
        using_image = True
        try:
            uploaded.seek(0)
            orig_img = Image.open(uploaded).convert("RGB")
            st.subheader("Original image")
            st.image(orig_img, use_column_width=True)
            # Convert to grayscale and compute vertical projection (we invert intensity so peaks upward)
            gray = np.array(orig_img.convert("L")).astype(float)
            # Normalize: darker pixels -> lower values; we want peaks positive: take inverted intensity
            inv = 255.0 - gray
            # Sum (or max) along rows to get a chromatogram-like profile; max better for sharp peaks
            signal = inv.max(axis=0).astype(float)
            # Smooth a bit for stability
            signal_smooth = gaussian_filter1d(signal, sigma=1)
            x_axis = np.arange(len(signal_smooth))  # pixel indices -> used as X (retention units = pixels)
            df = pd.DataFrame({"X": x_axis, "Y": signal_smooth})
        except Exception as e:
            st.error(f"Image processing error: {e}")
            return

    # PDF path: convert first page to image (best-effort)
    elif name.endswith(".pdf"):
        uploaded.seek(0)
        pil_img, err = pdf_to_png_bytes(uploaded)
        if pil_img is None:
            st.error(err)
            return
        try:
            orig_img = pil_img.convert("RGB")
            st.subheader("Original image (from PDF)")
            st.image(orig_img, use_column_width=True)
            gray = np.array(orig_img.convert("L")).astype(float)
            inv = 255.0 - gray
            signal = inv.max(axis=0).astype(float)
            signal_smooth = gaussian_filter1d(signal, sigma=1)
            x_axis = np.arange(len(signal_smooth))
            df = pd.DataFrame({"X": x_axis, "Y": signal_smooth})
            using_image = True
        except Exception as e:
            st.error(f"PDF->image processing error: {e}")
            return
    else:
        st.error("Unsupported file type.")
        return

    if df is None or df.empty:
        st.error("No signal could be extracted.")
        return

    # Ensure sorted numeric
    df = df.dropna().sort_values("X").reset_index(drop=True)

    # If X is constant -> create artificial X
    if df["X"].nunique() == 1:
        st.warning("Signal plat ou OCR invalide : création d'un axe X artificiel.")
        df["X"] = np.arange(len(df))

    # X axis min/max for slider
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    # default region: central 25%-75%
    default_start = x_min + 0.25*(x_max - x_min)
    default_end = x_min + 0.75*(x_max - x_min)

    # Single 2-handle slider to pick noise region
    st.subheader(t("noise_region"))
    try:
        start, end = st.slider(t("select_region"),
                               min_value=float(x_min),
                               max_value=float(x_max),
                               value=(float(default_start), float(default_end)),
                               key="sn_select_range")
    except Exception as e:
        st.warning(f"Slider init error: {e}")
        start, end = float(x_min), float(x_max)

    region = df[(df["X"] >= start) & (df["X"] <= end)]
    if region.shape[0] < 2:
        st.warning("Région trop petite pour estimer le bruit — utilisation du signal complet.")
        region = df

    # Main peak: choose global max on Y (as requested)
    y_arr = df["Y"].values
    x_arr = df["X"].values
    peak_idx = int(np.argmax(y_arr))
    peak_x = float(x_arr[peak_idx])
    peak_y = float(y_arr[peak_idx])

    # Baseline and noise: computed from selected region
    noise_std = float(region["Y"].std(ddof=0)) if not region.empty else float(np.std(y_arr))
    baseline = float(region["Y"].mean()) if not region.empty else float(np.mean(y_arr))
    height = peak_y - baseline

    # FWHM: approximate half height crossings on the original X axis
    half_height = baseline + height / 2.0
    left_idxs = np.where(y_arr[:peak_idx] <= half_height)[0]
    right_idxs = np.where(y_arr[peak_idx:] <= half_height)[0]
    W = np.nan
    try:
        if len(left_idxs) > 0:
            left_x = x_arr[left_idxs[-1]]
            W = peak_x - left_x
        if len(right_idxs) > 0:
            right_x = x_arr[peak_idx + right_idxs[0]]
            W = (W if not np.isnan(W) else 0.0) + (right_x - peak_x)
    except Exception:
        W = np.nan

    # S/N calculations
    noise_val = noise_std if noise_std != 0 else 1e-12
    sn_classic = peak_y / noise_val
    sn_usp = height / noise_val

    # Display numbers
    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
    # retention: if using CSV with time units we show them; if image, X is pixels
    unit_label = "pixels" if using_image and not using_csv else "time"
    st.write(f"Peak retention (X) [{unit_label}]: {peak_x:.4f}")
    st.write(f"H: {height:.4f}, noise σ: {noise_std:.4f}, W (approx FWHM): {W if not np.isnan(W) else 0.0:.4f}")

    # LOD/LOQ using slope from linearity or manual
    slope_from_lin = st.session_state.get("linear_slope", None)
    st.write("Slope for LOD/LOQ:")
    slope_choice = st.radio("Slope source", ("From linearity", "Manual input"), key="sn_slope_choice")
    slope_val = None
    if slope_choice == "From linearity":
        slope_val = slope_from_lin
        if slope_val is None:
            st.warning("No slope from linearity available. Please enter manual slope.")
            slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="sn_slope_manual_missing")
    else:
        slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="sn_slope_manual")

    if slope_val and slope_val != 0:
        unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"], key="sn_unit_select")
        lod = 3.3 * noise_std / slope_val
        loq = 10 * noise_std / slope_val
        st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
        st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
    else:
        st.info("Slope not provided -> LOD/LOQ in concentration cannot be computed.")

    # Plot: annotate on top of original data. Note: if original is image we still plot the extracted profile,
    # but we will also produce an annotated image for download (preserving original colors).
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(df["X"], df["Y"], color="black", label="Signal (extracted)")
    ax.axvspan(start, end, alpha=0.2, color="gray", label=t("noise_region"))
    ax.axhline(baseline, color="green", linestyle="--", label="Baseline")
    ax.axhline(half_height, color="orange", linestyle="--", label="Half height")
    ax.plot([peak_x], [peak_y], marker="o", markersize=8, color="red", label="Main peak")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend(loc="upper right")
    st.pyplot(fig)

    # Annotated image creation (original image + mark retention pixel)
    if using_image and orig_img is not None:
        try:
            annot = orig_img.copy()
            draw = ImageDraw.Draw(annot)
            W_img, H_img = annot.size
            # Map peak_x (pixel index) to image x coordinate (if df X is pixel index it's direct)
            # If df X range differs (rare), do linear mapping
            x_df_min, x_df_max = df["X"].min(), df["X"].max()
            if x_df_max - x_df_min == 0:
                x_px = int(W_img/2)
            else:
                x_px = int((peak_x - x_df_min) / (x_df_max - x_df_min) * (W_img - 1))
            # draw vertical line and red dot at top for the peak x
            draw.line([(x_px, 0), (x_px, H_img)], fill="red", width=2)
            # mark small circle at top area where peak is visible (y location approximate)
            # try to find the y pixel corresponding to peak_y relative to the inverted grayscale profile
            gray = np.array(orig_img.convert("L")).astype(float)
            inv = 255.0 - gray
            col_vals = inv[:, min(max(0, x_px), inv.shape[1]-1)]
            # approximate y position where inv is maximal in that column
            y_px = int(np.argmax(col_vals))
            r = 6
            draw.ellipse((x_px-r, y_px-r, x_px+r, y_px+r), outline="red", width=3)
            # add text
            txt = f"Peak X={peak_x:.2f}"
            try:
                font = ImageFont.load_default()
                draw.text((10, 10), txt, fill="black", font=font)
            except Exception:
                draw.text((10,10), txt, fill="black")
            # display annotated image
            st.subheader("Annotated image (for download)")
            st.image(annot, use_column_width=True)
            # download annotated image
            buf_img = io.BytesIO()
            annot.save(buf_img, format="PNG")
            buf_img.seek(0)
            st.download_button(t("download_image"), data=buf_img.getvalue(), file_name="sn_annotated.png", mime="image/png")
        except Exception as e:
            st.warning(f"Could not create annotated image: {e}")

    # Peaks detection in selected region (based on absolute threshold)
    try:
        threshold_factor = st.slider(t("threshold"), 0.0, 10.0, 3.0, step=0.1, key="sn_threshold")
        min_dist = st.number_input(t("min_distance"), value=5, min_value=1, step=1, key="sn_min_dist")
        threshold_abs = baseline + threshold_factor * noise_std
        region_vals = region["Y"].values
        peaks_idx, props = find_peaks(region_vals, height=threshold_abs, distance=int(min_dist))
        peaks_x = region["X"].values[peaks_idx] if len(peaks_idx) else np.array([])
        peaks_y = region_vals[peaks_idx] if len(peaks_idx) else np.array([])
    except Exception:
        peaks_x = np.array([])
        peaks_y = np.array([])

    st.write(f"Peaks detected in region: {len(peaks_x)}")
    if len(peaks_x):
        st.dataframe(pd.DataFrame({"X": peaks_x, "Y": peaks_y}))

    # Export CSV of extracted profile
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_profile.csv", mime="text/csv")

    # Export PDF report with the matplotlib figure embedded
    if st.button(t("export_sn_pdf")):
        try:
            imgbuf = io.BytesIO()
            fig.savefig(imgbuf, format="png", bbox_inches="tight")
            imgbuf.seek(0)
            lines = [
                f"File: {uploaded.name}",
                f"User: {st.session_state.get('username','Unknown')}",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"{t('sn_classic')}: {sn_classic:.4f}",
                f"{t('sn_usp')}: {sn_usp:.4f}",
                f"Peak X: {peak_x:.4f}",
                f"H: {height:.4f}, noise σ: {noise_std:.4f}, W: {W if not np.isnan(W) else 0.0:.4f}"
            ]
            pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=imgbuf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
            st.download_button(t("download_pdf"), pdfb, file_name="sn_report.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF export failed: {e}")

    # formulas
    with st.expander(t("formulas")):
        st.markdown(r"""
        **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
        **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)


# -------------------------
# Feedback panel (simple + admin replies)
# -------------------------
FEEDBACK_PATH = FEEDBACK_FILE if 'FEEDBACK_FILE' in globals() else "feedback.json"

def load_feedback_local():
    if not os.path.exists(FEEDBACK_PATH):
        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
    with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_feedback_local(feeds):
    with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
        json.dump(feeds, f, indent=2, ensure_ascii=False)

def feedback_panel():
    st.header("Feedback & Support")
    st.write("Envoyez vos commentaires. L'admin peut lire et répondre.")

    with st.form("feedback_form", clear_on_submit=True):
        sender = st.text_input("Nom (optionnel)", value=st.session_state.get("username",""))
        message = st.text_area("Message", height=140)
        sent = st.form_submit_button(t("upload_feedback"))
        if sent:
            if not message.strip():
                st.warning("Message vide.")
            else:
                feeds = load_feedback_local()
                feeds.append({
                    "sender": sender or st.session_state.get("username","anonymous"),
                    "message": message,
                    "time": datetime.now().isoformat(),
                    "reply": ""
                })
                save_feedback_local(feeds)
                st.success("Feedback envoyé — merci !")

    # Admin view: list feedback and reply
    if st.session_state.get("role") == "admin":
        st.markdown("---")
        st.subheader(t("view_feedback"))
        feeds = load_feedback_local()
        if not feeds:
            st.info("No feedback yet.")
        else:
            for i, fb in enumerate(feeds):
                st.write(f"**{fb['sender']}** — {fb['time']}")
                st.write(fb["message"])
                if fb.get("reply"):
                    st.info(f"Reply: {fb['reply']}")
                with st.form(f"reply_form_{i}", clear_on_submit=False):
                    r = st.text_input("Votre réponse", key=f"reply_input_{i}")
                    if st.form_submit_button("Envoyer réponse", key=f"reply_btn_{i}"):
                        feeds[i]["reply"] = r
                        save_feedback_local(feeds)
                        st.success("Réponse enregistrée.")


# -------------------------
# main_app routing (uses dropdown or top buttons depending on Part1)
# -------------------------
def main_app():
    # Reuse header_area from PART1 if present; otherwise simple header
    try:
        header_area()
    except Exception:
        st.title("LabT")

    # language selector top-right if available in PART1
    try:
        cols = st.columns([1,3,1])
        with cols[2]:
            lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.get("lang","FR")=="FR" else 1, key="top_lang")
            st.session_state["lang"] = lang
    except Exception:
        pass

    st.markdown(f"### 👋 {'Bonjour' if st.session_state.get('lang','FR')=='FR' else 'Hello'}, **{st.session_state.get('username','')}**")

    # Navigation: use a dropdown to avoid duplicate widget issues
    module = st.selectbox("Module", ["Linéarité", "S/N", "Feedback", "Admin", "Déconnexion"], index=0, key="main_module_select")

    if module in ("Linéarité", "Linearity"):
        if has_access("linearity"):
            linearity_panel()
        else:
            st.warning("Access denied to Linearity.")
    elif module in ("S/N", "S/N"):
        if has_access("sn"):
            sn_panel_full()
        else:
            st.warning("Access denied to S/N.")
    elif module in ("Feedback",):
        feedback_panel()
    elif module in ("Admin",):
        if st.session_state.get("role") == "admin":
            admin_panel()
        else:
            st.warning("Admin only.")
    elif module in ("Déconnexion", "Logout", "Déconnexion"):
        logout()
    else:
        st.info("Select a module.")

# Entrypoint for PART2 (call from bottom of file)
def run_app():
    if st.session_state.get("logged_in"):
        main_app()
    else:
        login_page()

# If script is run directly, call run_app()
if __name__ == "__main__":
    run_app()
# -------------------------
# End PART 2
# -------------------------
# -----------------------------
# PART 3 — utils, files bootstrap & requirements
# -----------------------------
import base64

# --- Access management (simplified)
def has_access(module_name: str) -> bool:
    """Check if current user has access to given module."""
    role = st.session_state.get("role", "")
    access = st.session_state.get("access", [])
    # Admins always have access to Admin panel
    if role == "admin" and module_name.lower() == "admin":
        return True
    if role == "admin":
        return True
    if isinstance(access, list) and module_name.lower() in [a.lower() for a in access]:
        return True
    return False


# --- PDF generator utility
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    for line in lines:
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 6))
    if img_bytes:
        try:
            img_buf = io.BytesIO(img_bytes.read() if hasattr(img_bytes, "read") else img_bytes)
            story.append(Spacer(1, 12))
            story.append(RLImage(img_buf, width=400, height=200))
        except Exception:
            pass
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


# --- PDF to PNG converter (best-effort, optional poppler)
def pdf_to_png_bytes(uploaded_file):
    try:
        from pdf2image import convert_from_bytes
        pdf_bytes = uploaded_file.read()
        pages = convert_from_bytes(pdf_bytes, dpi=200)
        if not pages:
            return None, "No pages in PDF."
        first_page = pages[0]
        return first_page, None
    except Exception as e:
        return None, f"PDF conversion failed: {e}. Please install poppler or use an image instead."


# --- Bootstrap local files if missing ---
def ensure_files():
    # users.json
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {"password": "admin", "role": "admin", "access": ["linearity","sn","feedback","admin"]},
            "analyst": {"password": "1234", "role": "user", "access": ["linearity","sn","feedback"]}
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=2, ensure_ascii=False)

    # feedback.json
    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)

    # default logo if none provided
    if not os.path.exists(LOGO_FILE):
        img = Image.new("RGB", (300, 80), color=(230, 230, 240))
        draw = ImageDraw.Draw(img)
        draw.text((20, 25), "LabT", fill="black")
        img.save(LOGO_FILE)

ensure_files()


# --- Streamlit run entrypoint ---
def run():
    if st.session_state.get("logged_in"):
        main_app()
    else:
        login_page()


# If launched directly
if __name__ == "__main__":
    run()