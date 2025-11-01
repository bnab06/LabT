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
import os
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

# Page config (no sidebar)
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"  # optional saved logo path

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

# make login case-insensitive: create a helper to find user key by case-insensitive match
def find_user_key(username):
    if username is None:
        return None
    for u in USERS.keys():
        if u.lower() == username.strip().lower():
            return u
    return None

# -------------------------
# Translations
# -------------------------
TEXTS = {
    "FR": {
        "app_title":"LabT",
        "powered":"Powered by BnB",
        "username":"Utilisateur",
        "password":"Mot de passe",
        "login":"Connexion",
        "logout":"Déconnexion",
        "invalid":"Identifiants invalides",
        "linearity":"Linéarité",
        "sn":"S/N",
        "admin":"Admin",
        "company":"Nom de la compagnie",
        "input_csv":"CSV",
        "input_manual":"Saisie manuelle",
        "concentration":"Concentration",
        "signal":"Signal",
        "unit":"Unité",
        "generate_pdf":"Générer PDF",
        "download_pdf":"Télécharger PDF",
        "download_csv":"Télécharger CSV",
        "sn_classic":"S/N Classique",
        "sn_usp":"S/N USP",
        "lod":"LOD (conc.)",
        "loq":"LOQ (conc.)",
        "formulas":"Formules",
        "select_region":"Sélectionner la zone",
        "add_user":"Ajouter utilisateur",
        "delete_user":"Supprimer utilisateur",
        "modify_user":"Modifier mot de passe",
        "enter_username":"Nom d'utilisateur",
        "enter_password":"Mot de passe (simple)",
        "upload_chrom":"Importer chromatogramme (CSV, PNG, JPG, PDF)",
        "digitize_info":"Digitizing : OCR tenté si pytesseract installé (best-effort)",
        "export_sn_pdf":"Exporter S/N PDF",
        "download_original_pdf":"Télécharger PDF original",
        "change_pwd":"Changer mot de passe (hors session)",
        "compute":"Compute",
        "company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport.",
        "select_section":"Section",
        "upload_logo":"Uploader un logo (optionnel)"
    },
    "EN": {
        "app_title":"LabT",
        "powered":"Powered by BnB",
        "username":"Username",
        "password":"Password",
        "login":"Login",
        "logout":"Logout",
        "invalid":"Invalid credentials",
        "linearity":"Linearity",
        "sn":"S/N",
        "admin":"Admin",
        "company":"Company name",
        "input_csv":"CSV",
        "input_manual":"Manual input",
        "concentration":"Concentration",
        "signal":"Signal",
        "unit":"Unit",
        "generate_pdf":"Generate PDF",
        "download_pdf":"Download PDF",
        "download_csv":"Download CSV",
        "sn_classic":"S/N Classic",
        "sn_usp":"S/N USP",
        "lod":"LOD (conc.)",
        "loq":"LOQ (conc.)",
        "formulas":"Formulas",
        "select_region":"Select region",
        "add_user":"Add user",
        "delete_user":"Delete user",
        "modify_user":"Modify password",
        "enter_username":"Username",
        "enter_password":"Password (simple)",
        "upload_chrom":"Upload chromatogram (CSV, PNG, JPG, PDF)",
        "digitize_info":"Digitizing: OCR attempted if pytesseract available (best-effort)",
        "export_sn_pdf":"Export S/N PDF",
        "download_original_pdf":"Download original PDF",
        "change_pwd":"Change password (outside session)",
        "compute":"Compute",
        "company_missing":"Please enter company name before generating the report.",
        "select_section":"Section",
        "upload_logo":"Upload logo (optional)"
    }
}

def t(key):
    lang = st.session_state.get("lang", "FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(key, key)

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
# PDF generator
# -------------------------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=8, w=25)
            pdf.set_xy(40, 10)
        except Exception:
            pdf.set_xy(10, 10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=1, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 11)
    for line in lines:
        pdf.multi_cell(0, 7, line)
    if img_bytes is not None:
        try:
            if isinstance(img_bytes, io.BytesIO):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes.getvalue())
                    tmpname = tmpf.name
                pdf.ln(4)
                pdf.image(tmpname, x=20, w=170)
            elif isinstance(img_bytes, bytes):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes)
                    tmpname = tmpf.name
                pdf.ln(4)
                pdf.image(tmpname, x=20, w=170)
            else:
                # If a path was passed
                if isinstance(img_bytes, str) and os.path.exists(img_bytes):
                    pdf.ln(4)
                    pdf.image(img_bytes, x=20, w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# -------------------------
# OCR helper (best-effort)
# -------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
    """
    Try to extract numeric X,Y pairs from image text via pytesseract.
    Returns DataFrame with columns X,Y or empty DF if not possible.
    """
    if pytesseract is None:
        return pd.DataFrame(columns=["X","Y"])
    try:
        text = pytesseract.image_to_string(img)
    except Exception:
        return pd.DataFrame(columns=["X","Y"])
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        # try separators
        for sep in [",", ";", "\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip() != ""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",","."))
                        y = float(parts[1].replace(",","."))
                        rows.append([x,y])
                        break
                    except Exception:
                        pass
        else:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",","."))
                    y = float(parts[1].replace(",","."))
                    rows.append([x,y])
                except Exception:
                    pass
    return pd.DataFrame(rows, columns=["X","Y"])

# -------------------------
# Header (title + logo upload)
# -------------------------
def header_area():
    cols = st.columns([3,1])
    with cols[0]:
        st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    with cols[1]:
        # upload logo (optional) and save to LOGO_FILE
        upl = st.file_uploader(t("upload_logo"), type=["png","jpg","jpeg"], key="upload_logo")
        if upl is not None:
            try:
                upl.seek(0)
                data = upl.read()
                with open(LOGO_FILE, "wb") as f:
                    f.write(data)
                st.success("Logo saved")
            except Exception as e:
                st.warning(f"Logo save error: {e}")

# -------------------------
# Login screen
# -------------------------
def login_screen():
    header_area()
    st.write("")
    lang = st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="login_lang")
    st.session_state.lang = lang

    with st.form("login_form", clear_on_submit=False):
        cols = st.columns([2,1])
        with cols[0]:
            username = st.text_input(t("username"), key="username_login")
        with cols[1]:
            password = st.text_input(t("password"), type="password", key="password_login")
        submitted = st.form_submit_button(t("login"))

    if submitted:
        uname = (username or "").strip()
        if not uname:
            st.error(t("invalid"))
            return
        matched = find_user_key(uname)
        if matched and USERS[matched]["password"] == (password or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            return
        else:
            st.error(t("invalid"))

    st.markdown(
        "<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>"
        f"{t('powered')}"
        "</div>",
        unsafe_allow_html=True,
    )

    # password change outside session
    with st.expander(t("change_pwd"), expanded=False):
        st.write("Change a user's password (works even if not logged in).")
        u_name = st.text_input("Username to change", key="chg_user")
        u_pwd = st.text_input("New password", type="password", key="chg_pwd")
        if st.button("Change password", key="chg_btn"):
            if not u_name.strip() or not u_pwd:
                st.warning("Enter username and new password")
            else:
                found = find_user_key(u_name)
                if not found:
                    st.warning("User not found")
                else:
                    USERS[found]["password"] = u_pwd.strip()
                    save_users(USERS)
                    st.success(f"Password updated for {found}")

# -------------------------
# Admin panel (users dropdown)
# -------------------------
def admin_panel():
    st.header(t("admin"))
    col_left, col_right = st.columns([2,1])
    with col_left:
        st.subheader("Existing users")
        users_list = list(USERS.keys())
        sel = st.selectbox("Select user", users_list, key="admin_sel_user")
        if sel:
            info = USERS.get(sel, {})
            st.write(f"Username: **{sel}**")
            st.write(f"Role: **{info.get('role','user')}**")
            if st.button("Modify selected user"):
                with st.expander(f"Modify {sel}", expanded=True):
                    new_pwd = st.text_input(f"New password for {sel}", type="password", key=f"newpwd_{sel}")
                    new_role = st.selectbox("Role", ["user","admin"], index=0 if info.get("role","user")=="user" else 1, key=f"newrole_{sel}")
                    if st.button("Save changes", key=f"save_{sel}"):
                        if new_pwd:
                            USERS[sel]["password"] = new_pwd
                        USERS[sel]["role"] = new_role
                        save_users(USERS)
                        st.success(f"Updated {sel}")
                        st.experimental_rerun()
            if st.button("Delete selected user"):
                if sel.lower() == "admin":
                    st.warning("Cannot delete admin")
                else:
                    USERS.pop(sel)
                    save_users(USERS)
                    st.success(f"{sel} deleted")
                    st.experimental_rerun()

    with col_right:
        st.subheader(t("add_user"))
        with st.form("form_add_user"):
            new_user = st.text_input(t("enter_username"), key="add_username")
            new_pass = st.text_input(t("enter_password"), type="password", key="add_password")
            role = st.selectbox("Role", ["user","admin"], key="add_role")
            add_sub = st.form_submit_button("Add")
        if add_sub:
            if not new_user.strip() or not new_pass.strip():
                st.warning("Enter username and password")
            else:
                # case-insensitive check
                if find_user_key(new_user) is not None:
                    st.warning("User exists")
                else:
                    USERS[new_user.strip()] = {"password": new_pass.strip(), "role": role}
                    save_users(USERS)
                    st.success(f"User {new_user.strip()} added")
                    st.experimental_rerun()

# -------------------------
# Linearity panel (automatic compute, single unknown field)
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name")

    mode = st.radio("Input mode", [t("input_csv"), t("input_manual")], key="lin_input_mode")
    df = None

    if mode == t("input_csv"):
        uploaded = st.file_uploader(t("input_csv"), type=["csv"], key="lin_csv")
        if uploaded:
            try:
                uploaded.seek(0)
                # try common separators ; or ,
                try:
                    df0 = pd.read_csv(uploaded)
                except Exception:
                    uploaded.seek(0)
                    df0 = pd.read_csv(uploaded, sep=';', engine='python')
                cols_low = [c.lower() for c in df0.columns]
                if "concentration" in cols_low and "signal" in cols_low:
                    df = df0.rename(columns={df0.columns[cols_low.index("concentration")]: "Concentration",
                                             df0.columns[cols_low.index("signal")]: "Signal"})
                elif len(df0.columns) >= 2:
                    df = df0.iloc[:, :2].copy()
                    df.columns = ["Concentration","Signal"]
                else:
                    st.error("CSV must contain at least two columns (concentration, signal).")
                    df = None
            except Exception as e:
                st.error(f"CSV error: {e}")
                df = None
    else:
        st.caption("Enter concentrations (comma-separated) and signals (comma-separated).")
        cols = st.columns(2)
        conc_input = cols[0].text_area("Concentrations (comma separated)", height=120, key="lin_manual_conc")
        sig_input = cols[1].text_area("Signals (comma separated)", height=120, key="lin_manual_sig")
        # Automatic parsing without button
        try:
            concs = [float(c.replace(",",".").strip()) for c in conc_input.split(",") if c.strip()!=""]
            sigs = [float(s.replace(",",".").strip()) for s in sig_input.split(",") if s.strip()!=""]
            if len(concs) != len(sigs):
                st.error("Number of concentrations and signals must match.")
            elif len(concs) < 2:
                st.warning("At least two pairs are required.")
            else:
                df = pd.DataFrame({"Concentration":concs, "Signal":sigs})
        except Exception as e:
            if conc_input.strip() or sig_input.strip():
                st.error(f"Manual parse error: {e}")

    unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="lin_unit")

    if df is None:
        st.info("Please provide data (CSV or manual).")
        return

    # ensure numeric and sorted
    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"])
        df["Signal"] = pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Concentration and Signal must be numeric.")
        return

    if len(df) < 2:
        st.warning("At least 2 points are required.")
        return

    # Fit linear regression
    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred)**2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values))**2)
    r2 = float(1 - ss_res/ss_tot) if ss_tot != 0 else 0.0

    # store slope for S/N conversions
    st.session_state.linear_slope = slope

    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.4f}")

    fig, ax = plt.subplots(figsize=(7,3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope*xs + intercept, color="red", label="Fit")
    ax.set_xlabel(f"{t('concentration')} ({unit})")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # Single automatic unknown field (interchangeable)
    calc_choice = st.radio("Calculate", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_calc_choice")
    unknown_label = "Enter value"
    val = st.number_input(unknown_label, format="%.6f", key="lin_unknown", value=0.0)

    # automatically compute and show result
    try:
        if calc_choice.startswith(t("signal")):
            # signal -> conc
            if slope == 0:
                st.error("Slope is zero, cannot compute concentration.")
            else:
                conc = (float(val) - intercept) / slope
                st.success(f"Concentration = {conc:.6f} {unit}")
        else:
            # conc -> signal
            sigp = slope * float(val) + intercept
            st.success(f"Signal = {sigp:.6f}")
    except Exception as e:
        st.error(f"Compute error: {e}")

    # formulas
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Linearity:** \( y = slope \cdot X + intercept \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

    # Export CSV & PDF (require company)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")

    if st.button(t("generate_pdf"), key="lin_pdf"):
        if not company or company.strip()=="":
            st.warning(t("company_missing"))
        else:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            lines = [
                f"Company: {company or 'N/A'}",
                f"User: {st.session_state.user or 'Unknown'}",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Slope: {slope:.6f}",
                f"Intercept: {intercept:.6f}",
                f"R²: {r2:.6f}"
            ]
            logo_path = LOGO_FILE if os.path.exists(LOGO_FILE) else None
            pdf_bytes = generate_pdf_bytes("Linearity report", lines, img_bytes=buf, logo_path=logo_path)
            st.download_button(t("download_pdf"), pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")

# -------------------------
# S/N
# -------------------------

# app_sn_ace.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import tempfile
from datetime import datetime
from PIL import Image
import matplotlib.pyplot as plt

# signal processing
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_widths

# plotting interactive
import plotly.graph_objects as go

# PDF export (fpdf is lightweight)
try:
    from fpdf import FPDF
    FPDP_AVAILABLE = True
except Exception:
    FPDP_AVAILABLE = False

# Optional OCR and PDF conversion
try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    PDF2IMG_AVAILABLE = True
except Exception:
    PDF2IMG_AVAILABLE = False

# Optional streamlit helper to get plotly click events
try:
    from streamlit_plotly_events import plotly_events
    PLOTLY_EVENTS_AVAILABLE = True
except Exception:
    PLOTLY_EVENTS_AVAILABLE = False

# ---------------------------
# i18n minimal
# ---------------------------
TEXT = {
    "fr": {
        "title": "S/N — Panel ACE",
        "upload": "Télécharger chromatogramme (CSV / PNG / JPG / PDF)",
        "lang": "Langue",
        "smoothing": "Lissage (sigma gaussien)",
        "noise_region": "Zone bruit (sélection X)",
        "detecting": "Détection des pics…",
        "no_signal": "Aucun signal valide détecté.",
        "peaks_found": "Pics détectés",
        "download_csv": "Télécharger résultats CSV",
        "download_pdf": "Télécharger rapport PDF",
        "sn_classic": "S/N Classique",
        "sn_usp": "S/N USP",
        "export_error": "Export PDF non disponible (fpdf manquant).",
        "instructions_click": "Clique sur un pic dans le graphique pour le sélectionner (ou choisis dans la table).",
        "image_original": "Image originale",
        "table_peaks": "Table des pics détectés",
        "select_peak_table": "Sélectionner un pic (table) pour recalculer",
    },
    "en": {
        "title": "S/N — ACE Panel",
        "upload": "Upload chromatogram (CSV / PNG / JPG / PDF)",
        "lang": "Language",
        "smoothing": "Smoothing (Gaussian sigma)",
        "noise_region": "Noise region (select X range)",
        "detecting": "Detecting peaks…",
        "no_signal": "No valid signal detected.",
        "peaks_found": "Peaks found",
        "download_csv": "Download results CSV",
        "download_pdf": "Download PDF report",
        "sn_classic": "Classic S/N",
        "sn_usp": "USP S/N",
        "export_error": "PDF export not available (fpdf missing).",
        "instructions_click": "Click a peak on the chart to select it (or pick from the table).",
        "image_original": "Original image",
        "table_peaks": "Detected peaks table",
        "select_peak_table": "Select a peak (table) to re-evaluate",
    }
}

def tr(k):
    lang = st.session_state.get("lang", "fr")
    return TEXT.get(lang, TEXT["fr"]).get(k, k)

# ---------------------------
# Helpers
# ---------------------------
def dataframe_from_csv_or_two_cols(file_obj):
    # try common csv read strategies
    file_obj.seek(0)
    try:
        df0 = pd.read_csv(file_obj)
    except Exception:
        file_obj.seek(0)
        df0 = pd.read_csv(file_obj, sep=";", engine="python")
    if df0.shape[1] < 2:
        return None
    cols = [c.lower() for c in df0.columns]
    if "time" in cols and "signal" in cols:
        tcol = df0.columns[cols.index("time")]
        ycol = df0.columns[cols.index("signal")]
        df = df0.rename(columns={tcol: "X", ycol: "Y"})[["X","Y"]].copy()
    else:
        df = df0.iloc[:, :2].copy()
        df.columns = ["X","Y"]
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    return df.dropna().sort_values("X").reset_index(drop=True)

def extract_xy_from_image(img_pil):
    """Attempt OCR; fallback to vertical projection (max) with smoothing."""
    # Try OCR if available
    if OCR_AVAILABLE:
        try:
            txt = pytesseract.image_to_string(img_pil)
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            data = []
            for ln in lines:
                # find floats in line
                parts = []
                for token in ln.replace(",", ".").split():
                    try:
                        parts.append(float(token))
                    except:
                        pass
                if len(parts) >= 2:
                    data.append((parts[0], parts[1]))
            if len(data) >= 2:
                df_ocr = pd.DataFrame(data, columns=["X","Y"]).sort_values("X").reset_index(drop=True)
                return df_ocr
        except Exception:
            pass
    # Fallback: vertical max projection
    arr = np.array(img_pil.convert("L"))
    signal = arr.max(axis=0).astype(float)
    # invert so peaks go up (if image has inverted axes this still often works)
    # We do not blindly invert; user can visually confirm.
    signal = signal.max() - signal
    signal = gaussian_filter1d(signal, sigma=1)
    df_proj = pd.DataFrame({"X": np.arange(len(signal)), "Y": signal})
    return df_proj

def detect_peaks_and_metrics(df, noise_start, noise_end,
                             smoothing_sigma=1.0,
                             min_prominence=None, min_distance=None):
    """
    Returns:
      df (with Y_smooth),
      peaks_idx (np array of indices into df),
      metrics list of dicts for each peak (X,H,h,W,SN_classic,SN_USP,retention_idx)
    """
    df = df.copy()
    # smoothing
    df["Y_smooth"] = gaussian_filter1d(df["Y"].values, sigma=float(smoothing_sigma))
    # noise region
    noise_region = df[(df["X"] >= noise_start) & (df["X"] <= noise_end)]
    if noise_region.shape[0] < 2:
        # fallback to whole signal for noise
        noise_region = df
    h = float(noise_region["Y_smooth"].std(ddof=0) or 1e-12)
    baseline = float(noise_region["Y_smooth"].mean())
    # adaptive defaults
    if min_prominence is None:
        min_prominence = max(0.5*h, (df["Y_smooth"].max() - df["Y_smooth"].min())*0.01)
    if min_distance is None:
        min_distance = max(1, int(len(df)//50))
    # find peaks
    peaks, props = find_peaks(df["Y_smooth"].values, prominence=min_prominence, distance=min_distance)
    metrics = []
    for p in peaks:
        peak_y = float(df["Y_smooth"].iloc[p])
        H = peak_y - baseline
        # width at half height using peak_widths (returns widths in samples)
        widths_res = peak_widths(df["Y_smooth"].values, [p], rel_height=0.5)
        width_samples = float(widths_res[0][0]) if len(widths_res[0])>0 else np.nan
        # convert samples to X units (if X is uniformly spaced; otherwise approximate using neighbor delta)
        if len(df) >= 2:
            dx = float(np.median(np.diff(df["X"].values)))
            W = width_samples * dx
        else:
            W = float(np.nan)
        SN_classic = H / h if h != 0 else float("nan")
        SN_USP = 2*H / h if h != 0 else float("nan")
        metrics.append({
            "peak_index": int(p),
            "retention_time": float(df["X"].iloc[p]),
            "peak_value": peak_y,
            "H": H,
            "h": h,
            "W": W,
            "S/N_classic": SN_classic,
            "S/N_USP": SN_USP
        })
    # Sort metrics by H desc
    metrics = sorted(metrics, key=lambda x: -x["H"])
    return df, peaks, metrics, baseline, h

def generate_csv_bytes(metrics):
    dfm = pd.DataFrame(metrics)
    buf = io.StringIO()
    dfm.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def generate_pdf_bytes(df, metrics, peak_idx_selected, baseline, half_height, noise_start, noise_end, img_pil=None):
    if not FPDP_AVAILABLE:
        raise RuntimeError("fpdf not available")
    # create annotated matplotlib figure and embed in PDF
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(df["X"], df["Y_smooth"], label="Chromatogram (smoothed)")
    # mark all detected peaks
    for m in metrics:
        ax.plot(m["retention_time"], m["peak_value"], marker="v", color="red", markersize=6)
    # highlight selected peak
    if peak_idx_selected is not None:
        sel = df.index.get_loc(peak_idx_selected) if peak_idx_selected in df.index else None
    # noise region
    ax.axvspan(noise_start, noise_end, alpha=0.2, color="grey", label="Noise region")
    # half height
    ax.hlines(half_height, xmin=df["X"].min(), xmax=df["X"].max(), linestyles="--", colors="orange", label="Half height")
    ax.hlines(baseline, xmin=df["X"].min(), xmax=df["X"].max(), linestyles="--", colors="green", label="Baseline")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    tmp_png = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(tmp_png.name, bbox_inches="tight")
    plt.close(fig)

    # Build PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "S/N Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)
    # metrics table: include a few top peaks then full list
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Peaks summary:", ln=True)
    pdf.set_font("Arial", "", 11)
    for i, m in enumerate(metrics):
        pdf.cell(0, 6, f"{i+1}. t={m['retention_time']:.4f}, H={m['H']:.4f}, h={m['h']:.4f}, W={m['W']:.4f}, S/N={m['S/N_classic']:.2f}", ln=True)
        if i>=19:  # prevent too long PDF header
            break
    pdf.ln(4)
    # insert image
    pdf.image(tmp_png.name, x=10, w=pdf.w - 20)
    # return bytes
    out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(out_tmp.name)
    with open(out_tmp.name, "rb") as f:
        data = f.read()
    # cleanup temp files
    try:
        os.unlink(tmp_png.name)
        os.unlink(out_tmp.name)
    except:
        pass
    return data

# ---------------------------
# Streamlit UI
# ---------------------------
def run_app():
    st.set_page_config(page_title="S/N ACE", layout="wide")
    if "lang" not in st.session_state:
        st.session_state["lang"] = "fr"

    # header / language
    cols = st.columns([1, 4, 1])
    with cols[0]:
        st.selectbox(TR := tr("lang") if False else "Language", options=["fr","en"], index=0, key="lang", on_change=lambda: None)
    with cols[1]:
        st.title(tr("title"))
    # upload + options area (left)
    left, right = st.columns([1, 2])
    with left:
        uploaded = st.file_uploader(tr("upload"), type=["csv","png","jpg","jpeg","pdf"])
        st.markdown("---")
        smoothing_sigma = st.slider(tr("smoothing"), 0.0, 5.0, 1.0, step=0.1)
        st.markdown("**Noise region (X)**")
        # placeholders for noise slider min/max until we have df
        noise_min_in = st.empty()
        noise_max_in = st.empty()
        st.markdown("---")
        st.write("Exports")
        csv_btn = st.empty()
        pdf_btn = st.empty()
        st.markdown("---")
        st.write("Notes:")
        st.write("- If OCR/PDF modules are missing, the app uses image projection (fallback).")
        st.write("- Click peaks on the chart when Plotly events are available.")
    with right:
        # main area for image and chart and table
        if uploaded is None:
            st.info("Upload a chromatogram (CSV or image) to start.")
            return

        name = uploaded.name.lower()
        df = None
        orig_image = None
        # load content
        try:
            if name.endswith(".csv"):
                df = dataframe_from_csv_or_two_cols(uploaded)
                if df is None:
                    st.error(tr("no_signal"))
                    return
            elif name.endswith((".png","jpg","jpeg")):
                uploaded.seek(0)
                orig_image = Image.open(uploaded).convert("RGB")
                st.subheader(tr("image_original"))
                st.image(orig_image, use_column_width=True)
                df = extract_xy_from_image(orig_image)
            elif name.endswith(".pdf"):
                uploaded.seek(0)
                if PDF2IMG_AVAILABLE:
                    try:
                        pages = convert_from_bytes(uploaded.read(), dpi=200, first_page=1, last_page=1)
                        orig_image = pages[0]
                    except Exception:
                        # fallback
                        uploaded.seek(0)
                        orig_image = Image.open(io.BytesIO(uploaded.read())).convert("RGB")
                else:
                    # try reading bytes into pillow (first page) as fallback
                    try:
                        uploaded.seek(0)
                        orig_image = Image.open(io.BytesIO(uploaded.read())).convert("RGB")
                    except Exception:
                        st.warning("PDF conversion failed and pdf2image not available; try installing poppler/pdf2image.")
                        st.stop()
                st.subheader(tr("image_original"))
                st.image(orig_image, use_column_width=True)
                df = extract_xy_from_image(orig_image)
            else:
                st.error("Unsupported file type.")
                return
        except Exception as e:
            st.error(f"File read error: {e}")
            return

        if df is None or df.empty:
            st.warning(tr("no_signal"))
            return

        # ensure numeric and sorted
        df = df.dropna().sort_values("X").reset_index(drop=True)

        # set noise slider now with real min/max
        x_min, x_max = float(df["X"].min()), float(df["X"].max())
        # override placeholders
        noise_start, noise_end = st.slider(tr("noise_region"),
                                           min_value=float(x_min),
                                           max_value=float(x_max),
                                           value=(x_min + 0.25*(x_max-x_min), x_min + 0.75*(x_max-x_min)),
                                           step=float(max((x_max-x_min)/1000, 1e-12)))
        # detect peaks and compute metrics
        df_proc, peaks_idx, metrics, baseline, h = detect_peaks_and_metrics(
            df, noise_start, noise_end, smoothing_sigma, min_prominence=None, min_distance=None
        )

        # DataFrame for table
        if metrics:
            df_metrics = pd.DataFrame(metrics)
            # round values for nicer display
            df_metrics_display = df_metrics.copy()
            for col in ["retention_time","peak_value","H","h","W","S/N_classic","S/N_USP"]:
                if col in df_metrics_display:
                    df_metrics_display[col] = df_metrics_display[col].apply(lambda v: (round(float(v),6) if pd.notna(v) else v))
        else:
            df_metrics_display = pd.DataFrame(columns=["retention_time","H","h","W","S/N_classic","S/N_USP"])

        # Plotly interactive chart
        st.subheader("Chromatogram")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_proc["X"], y=df_proc["Y_smooth"], mode="lines", name="Smoothed"))
        # mark peaks
        if len(peaks_idx) > 0:
            peaks_x = df_proc["X"].values[peaks_idx]
            peaks_y = df_proc["Y_smooth"].values[peaks_idx]
            fig.add_trace(go.Scatter(x=peaks_x, y=peaks_y, mode="markers", marker=dict(color="red", size=8), name="Detected peaks"))
        # noise region
        fig.add_vrect(x0=noise_start, x1=noise_end, fillcolor="grey", opacity=0.25, line_width=0)
        # invert y-axis to look like classic chromatogram (peaks up)
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=380, margin=dict(l=20,r=20,t=30,b=20), clickmode="event+select")
        chart = st.plotly_chart(fig, use_container_width=True)

        st.info(tr("instructions_click"))

        # interactive selection: try to use streamlit_plotly_events if available
        peak_selected_idx = None
        if PLOTLY_EVENTS_AVAILABLE:
            try:
                clicked = plotly_events(fig, click_event=True, select_event=False, override_height=380)
                if clicked:
                    clicked_x = clicked[0].get("x")
                    # find nearest X index
                    peak_selected_idx = int(np.argmin(np.abs(df_proc["X"].values - clicked_x)))
            except Exception:
                peak_selected_idx = None

        # fallback to table selection or default highest peak
        st.subheader(tr("table_peaks"))
        if not df_metrics_display.empty:
            # show table and let user choose by retention time
            selected_row = st.selectbox(tr("select_peak_table"), options=df_metrics_display.index.tolist(),
                                        format_func=lambda i: f"#{i+1}  t={df_metrics_display.loc[i,'retention_time']}  H={df_metrics_display.loc[i,'H']}")
            # map to the peak index in df (peak_index stored in metrics)
            peak_selected_idx = metrics[selected_row]["peak_index"]
            st.dataframe(df_metrics_display, height=200)
        else:
            st.write("No peaks detected.")

        # If no selection from events or table, default to highest peak
        if peak_selected_idx is None:
            peak_selected_idx = int(df_proc["Y_smooth"].values.argmax())

        # compute detailed numbers for selected peak
        sel_idx = int(peak_selected_idx)
        sel_retention = float(df_proc["X"].iloc[sel_idx])
        sel_peak_value = float(df_proc["Y_smooth"].iloc[sel_idx])
        sel_H = float(sel_peak_value - baseline)
        # half height
        widths_res = peak_widths(df_proc["Y_smooth"].values, [sel_idx], rel_height=0.5)
        width_samples = float(widths_res[0][0]) if len(widths_res[0])>0 else np.nan
        dx = float(np.median(np.diff(df_proc["X"].values))) if len(df_proc)>1 else 1.0
        sel_W = width_samples * dx
        sel_h = h
        sel_SN_classic = sel_H / sel_h if sel_h != 0 else float("nan")
        sel_SN_USP = 2*sel_H / sel_h if sel_h != 0 else float("nan")

        # show summary numbers
        st.subheader("Selected peak metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Retention", f"{sel_retention:.6g}")
        col2.metric("H", f"{sel_H:.6g}")
        col3.metric("h (noise σ)", f"{sel_h:.6g}")
        col4.metric("W (half height)", f"{sel_W:.6g}")
        st.write(f"{tr('sn_classic')}: {sel_SN_classic:.6g}    |    {tr('sn_usp')}: {sel_SN_USP:.6g}")

        # Export buttons
        # CSV of metrics
        if metrics:
            csv_bytes = generate_csv_bytes(metrics)
            csv_btn.download_button(label=tr("download_csv"), data=csv_bytes, file_name="sn_peaks.csv", mime="text/csv")
        else:
            csv_btn.write("No peaks to export")

        # PDF export
        if FPDP_AVAILABLE:
            try:
                half_height = baseline + sel_H/2
                pdf_bytes = generate_pdf_bytes(df_proc, metrics, sel_idx, baseline, half_height, noise_start, noise_end, img_pil=orig_image)
                pdf_btn.download_button(label=tr("download_pdf"), data=pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")
            except Exception as e:
                pdf_btn.write(f"PDF export error: {e}")
        else:
            pdf_btn.write(tr("export_error"))

# ---------------------------
if __name__ == "__main__":
    run_app()

# -------------------------
# Main app (tabs at top, modern)
# -------------------------
def main_app():
    header_area()
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang")
        st.session_state.lang = lang

    # tabs: admin only visible to admin users; admin does NOT have calculations access
    if st.session_state.role == "admin":
        tabs = st.tabs([t("admin")])
        with tabs[0]:
            admin_panel()
    else:
        tabs = st.tabs([t("linearity"), t("sn")])
        with tabs[0]:
            linearity_panel()
        with tabs[1]:
            sn_panel_full()

    if st.button(t("logout")):
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.linear_slope = None
        st.experimental_rerun()

# -------------------------
# Entry point
# -------------------------
def run():
    if st.session_state.user:
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run()