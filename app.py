# app.py — full
# LabT application (single-file)
# - bilingual (FR/EN)
# - no sidebar (layout wide)
# - Linearity module: kept behavior and UI as requested
# - S/N module: operates on original image (no redrawn artificial chromatogram),
#   uses OCR as fallback, automatic detection of the highest peak (global max Y),
#   allows manual S/N & LOD/LOQ using slope from linearity or manual input,
#   converts PDF->PNG using PyMuPDF (fitz) if available (fallback to pdf2image),
#   exports processed PNG, provides formulas expander.

import streamlit as st
import json, os, io, tempfile
from datetime import datetime
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Optional libs (best-effort)
try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except Exception:
    _HAS_FITZ = False

try:
    from pdf2image import convert_from_bytes
    _HAS_PDF2IMG = True
except Exception:
    _HAS_PDF2IMG = False

try:
    import pytesseract
    _HAS_TESS = True
except Exception:
    _HAS_TESS = False

# signal processing
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

# PDF report; if fpdf fails in some envs you may need to adjust
try:
    from fpdf import FPDF
    _HAS_FPDF = True
except Exception:
    _HAS_FPDF = False

# Page config
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

# Files
USERS_FILE = "users.json"
FEEDBACK_FILE = "feedback.json"
LOGO_FILE = "logo_labt.png"

# -------------------------
# Translations
# -------------------------
TEXTS = {
    "FR": { ... },  # keep same mapping as in your previous code
    "EN": { ... }
}
# We keep the large TEXTS mapping but to keep message short here,
# in your file copy the same TEXTS dict from your previous version (the one you provided).
# For brevity in this message I assume TEXTS is the same as in the code you gave.
# (When pasting into your environment, make sure TEXTS contains the full FR and EN dicts.)

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
if "page" not in st.session_state:
    st.session_state.page = "login"
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

# -------------------------
# Users helpers
# -------------------------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        default = {
            "admin": {"password": "admin", "role": "admin", "access": []},  # admin: only admin panel
            "user": {"password": "user", "role": "user", "access": ["linearity","sn"]},
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)

def load_users():
    ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

USERS = load_users()

def user_list():
    return list(USERS.keys()) if USERS else []

def find_user_key_case_insensitive(name):
    if name is None: return None
    for u in USERS.keys():
        if u.lower() == name.strip().lower():
            return u
    return None

# -------------------------
# Feedback helpers
# -------------------------
def load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_feedback(list_feedback):
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(list_feedback, f, indent=2, ensure_ascii=False)

# -------------------------
# PDF -> PIL helper (prefer fitz)
# -------------------------
def pdf_to_pil_firstpage(uploaded_file):
    """
    Return (PIL.Image, None) on success, or (None, error_message) on failure.
    Uses PyMuPDF (fitz) if available, else pdf2image if available.
    """
    uploaded_file.seek(0)
    data = uploaded_file.read()
    if _HAS_FITZ:
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return img, None
        except Exception as e:
            return None, f"PDF->PNG (fitz) error: {e}"
    elif _HAS_PDF2IMG:
        try:
            pages = convert_from_bytes(data, first_page=1, last_page=1, dpi=200)
            return pages[0], None
        except Exception as e:
            return None, f"PDF->PNG error (pdf2image/poppler): {e}"
    else:
        return None, t("could_not_convert_pdf")

# -------------------------
# PDF report builder (simple)
# -------------------------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    if not _HAS_FPDF:
        raise RuntimeError("fpdf not available")
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=8, w=25)
            pdf.set_xy(40, 10)
        except Exception:
            pdf.set_xy(10,10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=1, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 11)
    for line in lines:
        pdf.multi_cell(0, 7, line)
    if img_bytes is not None:
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                tmpf.write(img_bytes.getvalue() if isinstance(img_bytes, io.BytesIO) else img_bytes)
                tmpname = tmpf.name
            pdf.ln(4)
            pdf.image(tmpname, x=20, w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# -------------------------
# OCR XY extraction (best-effort)
# -------------------------
def extract_xy_from_image_pytesseract(pil_img: Image.Image):
    """
    Try extracting numeric X,Y pairs from an image using pytesseract.
    Returns a DataFrame with columns X,Y if successful, otherwise empty DF.
    This is 'best-effort' and may fail on many instrument images.
    """
    if not _HAS_TESS:
        return pd.DataFrame(columns=["X","Y"])
    try:
        txt = pytesseract.image_to_string(pil_img)
    except Exception:
        return pd.DataFrame(columns=["X","Y"])
    rows = []
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        # remove non-number except separators
        cleaned = "".join(ch if (ch.isdigit() or ch in ".,;- −- ") else " " for ch in line)
        # try common separators
        for sep in [",", ";", "\t", " - ", "-", " "]:
            if sep in cleaned:
                parts = [p.strip() for p in cleaned.split(sep) if p.strip()!=""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",","."))
                        y = float(parts[1].replace(",","."))
                        rows.append((x,y))
                        break
                    except Exception:
                        continue
        else:
            # fallback: whitespace splitted
            parts = cleaned.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",","."))
                    y = float(parts[1].replace(",","."))
                    rows.append((x,y))
                except Exception:
                    pass
    if rows:
        df = pd.DataFrame(rows, columns=["X","Y"]).sort_values("X").reset_index(drop=True)
        return df
    return pd.DataFrame(columns=["X","Y"])

# -------------------------
# Header area
# -------------------------
def header_area():
    cols = st.columns([3,1])
    with cols[0]:
        st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    with cols[1]:
        upl = st.file_uploader(t("upload_logo"), type=["png","jpg","jpeg"], key="upload_logo_box")
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
    cols = st.columns([2,1])
    with cols[1]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="login_lang")
        st.session_state.lang = lang

    st.markdown("### 🔐 " + t("login"))
    users = user_list()
    if not users:
        st.error(t("no_users"))
        return

    uname = st.selectbox(t("username"), users, key="login_user_select")
    pwd = st.text_input(t("password"), type="password", key="login_password")
    if st.button(t("login"), key="login_btn"):
        matched = find_user_key_case_insensitive(uname)
        if matched and USERS.get(matched, {}).get("password") == (pwd or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role", "user")
            st.session_state.page = "linearity"  # land on linearity by default
            st.success(f"{t('login')} OK")
            return
        else:
            st.error(t("invalid"))

    st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

# -------------------------
# Logout
# -------------------------
def logout():
    for k in ["user","role","page","linear_slope"]:
        if k in st.session_state:
            del st.session_state[k]
    st.session_state.page = "login"

# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header(t("admin"))
    st.write("Gérer les utilisateurs et leurs droits (linéarité / S/N).")
    users = user_list()
    if not users:
        st.info(t("no_users"))
        return

    action = st.selectbox("Action", ["Afficher utilisateur","Modifier utilisateur","Ajouter utilisateur","Supprimer utilisateur"], key="admin_action")
    if action == "Afficher utilisateur":
        sel = st.selectbox("Sélectionner utilisateur", users, key="admin_show_sel")
        if sel:
            info = USERS.get(sel, {})
            st.write(f"Username: **{sel}**")
            st.write(f"Role: **{info.get('role','user')}**")
            st.write(f"Rights: **{', '.join(info.get('access', []))}**")
    elif action == "Modifier utilisateur":
        sel = st.selectbox("Sélectionner utilisateur", users, key="admin_mod_sel")
        if sel:
            info = USERS.get(sel, {})
            with st.form(f"modify_form_{sel}", clear_on_submit=False):
                new_pwd = st.text_input("Nouveau mot de passe (laisser vide pour conserver)", type="password", key=f"pwd_{sel}")
                new_role = st.selectbox("Role", ["user","admin"], index=0 if info.get("role","user")=="user" else 1, key=f"rolesel_{sel}")
                acc_line = st.checkbox("Accès linéarité", value=("linearity" in info.get("access", [])), key=f"acc_lin_{sel}")
                acc_sn = st.checkbox("Accès S/N", value=("sn" in info.get("access", [])), key=f"acc_sn_{sel}")
                submitted = st.form_submit_button("Enregistrer")
                if submitted:
                    if new_pwd:
                        USERS[sel]["password"] = new_pwd
                    USERS[sel]["role"] = new_role
                    new_access = []
                    if acc_line: new_access.append("linearity")
                    if acc_sn: new_access.append("sn")
                    USERS[sel]["access"] = new_access
                    save_users(USERS)
                    st.success(f"{sel} mis à jour.")
    elif action == "Ajouter utilisateur":
        with st.form("add_user_form", clear_on_submit=True):
            new_user = st.text_input("Nom utilisateur", key="add_username")
            new_pass = st.text_input("Mot de passe", type="password", key="add_password")
            role = st.selectbox("Role", ["user","admin"], key="add_role")
            acc_lin = st.checkbox("Accès linéarité", value=True, key="add_acc_lin")
            acc_sn = st.checkbox("Accès S/N", value=True, key="add_acc_sn")
            sub = st.form_submit_button("Ajouter")
            if sub:
                if not new_user.strip() or not new_pass.strip():
                    st.warning("Enter username and password")
                else:
                    if find_user_key_case_insensitive(new_user) is not None:
                        st.warning("User exists")
                    else:
                        access = []
                        if acc_lin: access.append("linearity")
                        if acc_sn: access.append("sn")
                        USERS[new_user.strip()] = {"password": new_pass.strip(), "role": role, "access": access}
                        save_users(USERS)
                        st.success(f"User {new_user.strip()} added")
    elif action == "Supprimer utilisateur":
        sel = st.selectbox("Sélectionner", users, key="admin_del_sel")
        if sel:
            if st.button("Supprimer", key="admin_del_btn"):
                if sel.lower() == "admin":
                    st.warning("Cannot delete admin")
                else:
                    USERS.pop(sel, None)
                    save_users(USERS)
                    st.success(f"{sel} deleted")

# -------------------------
# Access check: admin must NOT see linearity/sn modules by default.
# Only users with access lists can open them. Admin sees only admin panel.
# -------------------------
def has_access(module_name):
    user = st.session_state.get("user")
    if not user:
        return False
    access = USERS.get(user, {}).get("access", [])
    return module_name in access

# -------------------------
# Linearity panel
# (kept behaviour: CSV or manual input; automatic compute; slope exported to session)
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name_lin")
    mode = st.radio("Input mode", [t("input_csv"), t("input_manual")], key="lin_input_mode_v2")
    df = None
    if mode == t("input_csv"):
        uploaded = st.file_uploader(t("input_csv"), type=["csv"], key="lin_csv_v2")
        if uploaded:
            try:
                uploaded.seek(0)
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
        conc_input = cols[0].text_area("Concentrations (comma separated)", height=120, key="lin_manual_conc_v2")
        sig_input = cols[1].text_area("Signals (comma separated)", height=120, key="lin_manual_sig_v2")
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

    unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="lin_unit_v2")

    if df is None:
        st.info("Please provide data (CSV or manual).")
        return

    # numeric check
    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"])
        df["Signal"] = pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Concentration and Signal must be numeric.")
        return
    if len(df) < 2:
        st.warning("At least 2 points are required.")
        return

    # Fit line
    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0]); intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred)**2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values))**2)
    r2 = float(1 - ss_res/ss_tot) if ss_tot != 0 else 0.0

    # store slope
    st.session_state.linear_slope = slope

    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.4f}")

    fig, ax = plt.subplots(figsize=(7,3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope*xs + intercept, color="black", label="Fit")  # solid
    ax.set_xlabel(f"{t('concentration')} ({unit})")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # compute unknown automatically (no button)
    calc_choice = st.radio("Calculate", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_calc_choice_v2")
    val = st.number_input("Enter value", format="%.6f", key="lin_unknown_v2", value=0.0)
    try:
        if calc_choice.startswith(t("signal")):
            if slope == 0:
                st.error("Slope is zero.")
            else:
                conc = (float(val) - intercept) / slope
                st.success(f"Concentration = {conc:.6f} {unit}")
        else:
            sigp = slope * float(val) + intercept
            st.success(f"Signal = {sigp:.6f}")
    except Exception as e:
        st.error(f"Compute error: {e}")

    # formulas expander
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Linearity:** \( y = slope \cdot X + intercept \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

    # Export CSV & PDF
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv", key="lin_dl_csv_v2")

    if st.button(t("generate_pdf"), key="lin_pdf_v2"):
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
            pdf_bytes = generate_pdf_bytes("Linearity report", lines, img_bytes=buf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
            st.download_button(t("download_pdf"), pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf", key="lin_pdf_dl_v2")

# -------------------------
# S/N panel (operate on original image)
# -------------------------
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))

    manual_mode = st.checkbox(t("manual_sn"), value=False, key="sn_manual_toggle_v2")
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_uploader_v2")

    if manual_mode:
        st.subheader(t("manual_sn"))
        H = st.number_input("H (peak height)", value=0.0, format="%.6f", key="manual_H_sn_v2")
        h = st.number_input("h (noise)", value=0.0, format="%.6f", key="manual_h_sn_v2")
        slope_choice = st.radio("Slope source", ("From linearity", "Manual input"), key="manual_slope_choice_v2")
        slope_val = None
        if slope_choice == "From linearity":
            slope_val = st.session_state.get("linear_slope", None)
            if slope_val is None:
                st.warning("No slope available from linearity.")
                slope_val = st.number_input("Enter slope manually", value=0.0, format="%.6f", key="manual_slope_missing_v2")
        else:
            slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="manual_slope_sn_v2")

        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2 * H / h if h != 0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        if slope_val and slope_val != 0:
            unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"], index=0, key="manual_unit_choice_v2")
            lod = 3.3 * h / slope_val
            loq = 10 * h / slope_val
            st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
            st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
        return

    if uploaded is None:
        st.info("Upload a chromatogram (CSV/image/pdf) or switch to manual mode.")
        return

    name = uploaded.name.lower()
    df = None
    orig_image = None

    # CSV handling
    if name.endswith(".csv"):
        try:
            uploaded.seek(0)
            try:
                df0 = pd.read_csv(uploaded)
            except Exception:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded, sep=";", engine="python")
            if df0.shape[1] < 2:
                st.error("CSV must contain at least two columns.")
                return
            cols_low = [c.lower() for c in df0.columns]
            if "time" in cols_low and "signal" in cols_low:
                df = df0.rename(columns={df0.columns[cols_low.index("time")]: "X",
                                         df0.columns[cols_low.index("signal")]: "Y"})
            else:
                df = df0.iloc[:, :2].copy()
                df.columns = ["X","Y"]
            df["X"] = pd.to_numeric(df["X"], errors="coerce")
            df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            return

    # Image handling
    elif name.endswith((".png",".jpg",".jpeg")):
        try:
            uploaded.seek(0)
            pil_img = Image.open(uploaded).convert("RGB")
            orig_image = pil_img.copy()
            st.subheader("Original image")
            st.image(orig_image, use_column_width=True)
            # try to get numeric XY from OCR
            df = extract_xy_from_image_pytesseract(orig_image)
            if df.empty:
                # fallback: vertical projection (take columnwise max)
                arr = np.array(orig_image.convert("L"))
                signal = arr.max(axis=0).astype(float)
                df = pd.DataFrame({"X": np.arange(len(signal)), "Y": signal})
        except Exception as e:
            st.error(f"Image error: {e}")
            return

    # PDF handling
    elif name.endswith(".pdf"):
        pil_img, err = pdf_to_pil_firstpage(uploaded)
        if pil_img is None:
            st.error(err)
            return
        orig_image = pil_img.convert("RGB")
        st.subheader("Original image (from PDF)")
        st.image(orig_image, use_column_width=True)
        df = extract_xy_from_image_pytesseract(orig_image)
        if df.empty:
            arr = np.array(orig_image.convert("L"))
            signal = arr.max(axis=0).astype(float)
            df = pd.DataFrame({"X": np.arange(len(signal)), "Y": signal})

    else:
        st.error("Unsupported file type.")
        return

    if df is None or df.empty:
        st.error("No valid signal detected.")
        return

    # Ensure numeric & sorted
    df = df.dropna().sort_values("X").reset_index(drop=True)
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    if x_min == x_max:
        # flat X -> create artificial axis (but we still compute peak on Y)
        st.warning("Signal plat ou OCR invalide : les valeurs X sont identiques. Utilisation d'un axe X artificiel.")
        df["X"] = np.arange(len(df))
        x_min, x_max = 0.0, float(len(df)-1)

    # user selects noise region using two-handle slider
    st.subheader(t("noise_region"))
    default_start = x_min + 0.25*(x_max-x_min)
    default_end = x_min + 0.75*(x_max-x_min)
    try:
        start, end = st.slider(t("select_region"),
                               min_value=float(x_min),
                               max_value=float(x_max),
                               value=(float(default_start), float(default_end)),
                               key="sn_range_slider_v2")
    except Exception as e:
        st.warning(f"Slider initialization issue: {e}")
        start, end = float(x_min), float(x_max)

    region = df[(df["X"] >= start) & (df["X"] <= end)].copy()
    if region.shape[0] < 2:
        st.warning("Région trop petite pour estimer le bruit — calcul automatique utilisé.")
        region = df

    # peak detection controls
    st.subheader("Peak detection settings")
    threshold_factor = st.slider(t("threshold"), 0.0, 10.0, 3.0, step=0.1, key="sn_threshold_v2")
    min_distance = st.number_input(t("min_distance"), value=5, min_value=1, step=1, key="sn_min_dist_v2")

    # compute main peak = global max on Y (explicit)
    x_arr = df["X"].values
    y_arr = df["Y"].values
    # if y range is extremely large due to scale, still use argmax
    peak_idx = int(np.argmax(y_arr))
    peak_x = float(x_arr[peak_idx])
    peak_y = float(y_arr[peak_idx])

    # noise / baseline from region (std and mean)
    noise_std = float(region["Y"].std(ddof=0)) if not region.empty else float(np.std(y_arr))
    baseline = float(region["Y"].mean()) if not region.empty else float(np.mean(y_arr))
    height = peak_y - baseline

    # FWHM approx using half-height points (try to compute on original X scale)
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

    noise_val = noise_std if noise_std != 0 else 1e-12
    sn_classic = peak_y / noise_val
    sn_usp = height / noise_val

    # Display numeric results (including retention time)
    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
    st.write(f"Peak retention (X): {peak_x:.4f}")
    st.write(f"H (height): {height:.4f}, noise h (std): {noise_std:.4f}, W (approx): {W:.4f}")

    # slope selection for LOD/LOQ
    slope_auto = st.session_state.get("linear_slope", None)
    slope_choice = st.radio("Slope source", ("From linearity", "Manual input"), key="sn_slope_choice_v2")
    slope_val = None
    if slope_choice == "From linearity":
        slope_val = slope_auto
        if slope_val is None:
            st.warning("No slope from linearity available.")
            slope_val = st.number_input("Enter slope manually", value=0.0, format="%.6f", key="sn_slope_missing_v2")
    else:
        slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="sn_slope_manual_v2")

    if slope_val and slope_val != 0:
        unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"], index=0, key="sn_unit_choice_v2")
        lod = 3.3 * noise_std / slope_val
        loq = 10 * noise_std / slope_val
        st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
        st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
    else:
        st.info("Slope not provided -> LOD/LOQ in concentration cannot be computed.")

    # Generate plot overlayed on original axes scale
    # IMPORTANT: we are NOT redrawing a fake chromatogram; we plot the measured Y vs extracted X.
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(df["X"], df["Y"], color="black", label="Chromatogram")
    ax.axvspan(start, end, alpha=0.25, color="gray", label=t("noise_region"))
    ax.axhline(baseline, color="green", linestyle="--", label="Baseline")
    ax.axhline(half_height, color="orange", linestyle="--", label="Half height")
    ax.plot([peak_x], [peak_y], marker="o", markersize=8, color="red", label="Main peak")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend(loc="upper right")
    st.pyplot(fig)

    # Peak finding within region using find_peaks based on threshold and distance
    threshold_abs = baseline + threshold_factor * noise_std
    peaks_x = np.array([]); peaks_y = np.array([])
    try:
        y_region = region["Y"].values
        peaks_idx, props = find_peaks(y_region, height=threshold_abs, distance=int(min_distance))
        if len(peaks_idx):
            peaks_x = region["X"].values[peaks_idx]
            peaks_y = y_region[peaks_idx]
    except Exception:
        peaks_x = np.array([]); peaks_y = np.array([])

    st.write(f"Peaks detected in region: {len(peaks_x)}")
    if len(peaks_x):
        st.dataframe(pd.DataFrame({"X": peaks_x, "Y": peaks_y}))

    # Export original-derived CSV
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv", key="sn_csv_dl_v2")

    # Export processed image (figure) PNG
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    st.download_button(t("download_image"), img_buf.getvalue(), file_name="sn_processed.png", mime="image/png", key="sn_img_dl_v2")

    # PDF report
    if st.button(t("export_sn_pdf"), key="sn_export_pdf_btn_v2"):
        lines = [
            f"File: {uploaded.name}",
            f"User: {st.session_state.get('user','Unknown')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{t('sn_classic')}: {sn_classic:.4f}",
            f"{t('sn_usp')}: {sn_usp:.4f}",
            f"Peak X (Retention time): {peak_x:.4f}",
            f"H: {height:.4f}, Noise: {noise_std:.4f}, W: {W:.4f}"
        ]
        pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=img_buf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
        st.download_button(t("download_pdf"), pdfb, file_name="sn_report.pdf", mime="application/pdf", key="sn_pdf_dl_v2")

    # formulas
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
        **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

# -------------------------
# Feedback panel
# -------------------------
def feedback_panel():
    st.header("Feedback & support")
    st.write("Envoyez vos commentaires / suggestions. L'admin peut lire et répondre.")
    with st.form("feedback_form_v2", clear_on_submit=True):
        name = st.text_input("Votre nom (optionnel)", value=st.session_state.get("user",""))
        fb = st.text_area("Message", height=120)
        submitted = st.form_submit_button(t("upload_feedback"))
        if submitted:
            if not fb.strip():
                st.warning("Message vide.")
            else:
                feeds = load_feedback()
                feeds.append({
                    "sender": name or st.session_state.get("user","anonymous"),
                    "message": fb,
                    "time": datetime.now().isoformat(),
                    "reply": ""
                })
                save_feedback(feeds)
                st.success("Feedback envoyé. Merci!")

    # admin reads & replies
    if st.session_state.get("role") == "admin":
        st.markdown("---")
        st.subheader(t("view_feedback"))
        feeds = load_feedback()
        if not feeds:
            st.info("No feedback yet.")
        else:
            for i, f in enumerate(feeds):
                st.write(f"**{f['sender']}** ({f['time']})")
                st.write(f"{f['message']}")
                if f.get("reply"):
                    st.info(f"Reply: {f['reply']}")
                with st.form(f"reply_form_v2_{i}", clear_on_submit=False):
                    r = st.text_input(t("reply"), key=f"reply_input_v2_{i}")
                    if st.form_submit_button("Send reply", key=f"reply_btn_v2_{i}"):
                        feeds[i]["reply"] = r
                        save_feedback(feeds)
                        st.success("Reply saved.")

# -------------------------
# Main app (menu dropdown)
# -------------------------
def main_app():
    header_area()
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang_main_v2")
        st.session_state.lang = lang

    user = st.session_state.get("user")
    role = st.session_state.get("role","user")
    st.markdown(f"### 👋 {'Bonjour' if st.session_state.lang=='FR' else 'Hello'}, **{user}** !")

    # Menu: dropdown (not mixing admin & modules)
    menu = ["Linearity","S/N","Feedback","Admin","Logout"]
    choice = st.selectbox("Module", menu, index=0, key="top_menu_v2")

    if choice == "Logout":
        logout()
        st.success("Logged out")
        return

    if choice == "Admin":
        if role == "admin":
            admin_panel()
        else:
            st.warning("Admin only.")
        return

    if choice == "Linearity":
        if has_access("linearity"):
            linearity_panel()
        else:
            st.warning("Access denied to linearity.")
        return

    if choice == "S/N":
        if has_access("sn"):
            sn_panel_full()
        else:
            st.warning("Access denied to S/N.")
        return

    if choice == "Feedback":
        feedback_panel()
        return

# -------------------------
# Entrypoint
# -------------------------
def run_app():
    if st.session_state.get("user"):
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run_app()