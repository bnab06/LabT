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
import os

# Optional features
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# Page config
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

# -------------------------
# Users helpers
# -------------------------
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # ensure keys exist
            return data
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

# Normalize users keys to keep original casing but allow case-insensitive lookup:
def find_user_case_insensitive(uname):
    if not uname:
        return None
    for u in USERS:
        if u.lower() == uname.lower():
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
        "select_section":"Section"
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
        "select_section":"Section"
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
            pdf.image(logo_path, x=10, y=8, w=20)
            pdf.set_xy(35, 10)
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
                pdf.ln(4)
                pdf.image(img_bytes, x=20, w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# -------------------------
# OCR helper (best-effort)
# -------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
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
                    except:
                        pass
        else:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",","."))
                    y = float(parts[1].replace(",","."))
                    rows.append([x,y])
                except:
                    pass
    return pd.DataFrame(rows, columns=["X","Y"])

# -------------------------
# Login screen
# -------------------------
def login_screen():
    st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
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
        matched = find_user_case_insensitive(uname)
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
                found = find_user_case_insensitive(u_name.strip())
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
    st.write(t("add_user"))
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
                if any(u.lower() == new_user.strip().lower() for u in USERS):
                    st.warning("User exists")
                else:
                    USERS[new_user.strip()] = {"password": new_pass.strip(), "role": role}
                    save_users(USERS)
                    st.success(f"User {new_user.strip()} added")
                    st.experimental_rerun()

# -------------------------
# Helper fig->bytes
# -------------------------
def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

# -------------------------
# Linearity panel
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name")

    mode = st.radio("Input mode", [t("input_csv"), t("input_manual")], key="lin_input_mode")
    df = None

    if mode == t("input_csv"):
        uploaded = st.file_uploader("Upload CSV with two columns (concentration, signal)", type=["csv"], key="lin_csv")
        if uploaded:
            try:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded)
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
        if st.button("Load manual pairs"):
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
                st.error(f"Manual parse error: {e}")

    unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="lin_unit")

    if df is None:
        st.info("Please provide data (CSV or manual).")
        return

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

    # Single field for unknown (signal or concentration) — compute automatically
    st.markdown("**Unknown value** — choisissez le type et entrez la valeur connue :")
    unknown_type = st.selectbox("Type (known)", [t("signal"), t("concentration")], key="lin_known_type")
    if unknown_type == t("signal"):
        known_val = st.number_input(f"Known {t('signal')}", value=0.0, format="%.6f", key="lin_known_signal")
        # compute concentration from signal automatically
        conc = None
        if slope != 0:
            conc = (known_val - intercept) / slope
        if conc is not None:
            st.success(f"{t('concentration')} = {conc:.6f} {unit}")
    else:
        known_val = st.number_input(f"Known {t('concentration')}", value=0.0, format="%.6f", key="lin_known_conc")
        sigp = slope * known_val + intercept
        st.success(f"{t('signal')} = {sigp:.6f}")

    # formulas
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Linearity:** \( y = slope \cdot X + intercept \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

    # Export CSV
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")

    # Export PDF — only allow generation if company provided; show warning if clicked with empty company
    if st.button(t("generate_pdf"), key="lin_pdf"):
        if not company or company.strip() == "":
            st.warning(t("company_missing"))
        else:
            buf = fig_to_bytes(fig)
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
# S/N panel (full) with sliders on x-axis
# -------------------------
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))

    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_uploader")
    if uploaded is None:
        st.info("Upload a file or use manual S/N input.")
        sn_manual_mode = True
    else:
        sn_manual_mode = False

    # Manual input mode (H/h)
    if sn_manual_mode:
        st.subheader("Manual S/N calculation")
        H = st.number_input("H (peak height)", value=0.0, format="%.6f")
        h = st.number_input("h (noise)", value=0.0, format="%.6f")
        # allow user to input slope if they want concentration conversion
        slope_input = st.number_input("Slope (optional, for conc. conversion)", value=float(st.session_state.linear_slope or 0.0), format="%.6f")
        unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="sn_unit_manual")
        # compute automatically and show
        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2 * H / h if h != 0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        if slope_input != 0:
            lod = 3.3 * h / slope_input
            loq = 10 * h / slope_input
            st.write(f"{t('lod')} ({unit}): {lod:.6f}")
            st.write(f"{t('loq')} ({unit}): {loq:.6f}")
        return

    # If file uploaded, try to parse
    ext = uploaded.name.split(".")[-1].lower()
    signal = None
    x_axis = None
    orig_image = None
    df = None

    # CSV case
    if ext == "csv":
        try:
            uploaded.seek(0)
            df0 = pd.read_csv(uploaded)
            cols_low = [c.lower() for c in df0.columns]
            if "time" in cols_low and "signal" in cols_low:
                idx_t = cols_low.index("time")
                idx_s = cols_low.index("signal")
                x_axis = pd.to_numeric(df0.iloc[:, idx_t], errors="coerce").fillna(method='ffill').values
                signal = pd.to_numeric(df0.iloc[:, idx_s], errors="coerce").fillna(0).values
                df = pd.DataFrame({"X":x_axis, "Y":signal})
            elif len(df0.columns) >= 2:
                x_axis = pd.to_numeric(df0.iloc[:,0], errors="coerce").fillna(np.arange(len(df0))).values
                signal = pd.to_numeric(df0.iloc[:,1], errors="coerce").fillna(0).values
                df = pd.DataFrame({"X":x_axis, "Y":signal})
            else:
                st.error("CSV must have at least two columns (time, signal).")
                return
            st.subheader("Raw data preview")
            st.dataframe(df.head(50))
        except Exception as e:
            st.error(f"CSV error: {e}")
            return

    # Image
    elif ext in ("png","jpg","jpeg"):
        try:
            uploaded.seek(0)
            orig_image = Image.open(uploaded).convert("RGB")
            st.subheader("Original image (as uploaded)")
            st.image(orig_image, use_column_width=True)
            # try to digitize numeric pairs via OCR first
            df_digit = extract_xy_from_image_pytesseract(orig_image)
            if not df_digit.empty:
                df_digit = df_digit.sort_values("X")
                df = df_digit.rename(columns={"X":"X","Y":"Y"})
                x_axis = pd.to_numeric(df["X"], errors="coerce").values
                signal = pd.to_numeric(df["Y"], errors="coerce").values
                st.success("Digitized numeric data from image (OCR).")
            else:
                # fallback: vertical max projection
                arr = np.array(orig_image.convert("L"))
                signal = arr.max(axis=0).astype(float)   # chromatogram-like
                x_axis = np.arange(len(signal))
                df = pd.DataFrame({"X":x_axis, "Y":signal})
                st.info("No numeric table found in image. Using vertical max-projection as chromatogram.")
        except Exception as e:
            st.error(f"Image error: {e}")
            return

    # PDF
    elif ext == "pdf":
        if convert_from_bytes is None:
            st.warning("PDF digitizing requires pdf2image + poppler. Cannot process PDF here.")
            uploaded.seek(0)
            st.download_button(t("download_original_pdf"), uploaded.read(), file_name=uploaded.name)
            return
        try:
            uploaded.seek(0)
            pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
            if not pages:
                st.error("No pages extracted from PDF")
                return
            orig_image = pages[0]
            st.subheader("Original PDF page (as image)")
            st.image(orig_image, use_column_width=True)
            df_digit = extract_xy_from_image_pytesseract(orig_image)
            if not df_digit.empty:
                df_digit = df_digit.sort_values("X")
                df = df_digit.rename(columns={"X":"X","Y":"Y"})
                x_axis = pd.to_numeric(df["X"], errors="coerce").values
                signal = pd.to_numeric(df["Y"], errors="coerce").values
                st.success("Digitized numeric data from PDF (OCR).")
            else:
                arr = np.array(orig_image.convert("L"))
                signal = arr.max(axis=0).astype(float)
                x_axis = np.arange(len(signal))
                df = pd.DataFrame({"X":x_axis, "Y":signal})
                st.info("No numeric table found in PDF page. Using vertical max-projection.")
        except Exception as e:
            st.error(f"PDF error: {e}")
            return
    else:
        st.error("Unsupported file type")
        return

    # Ensure we have df, x_axis, signal
    if df is None or signal is None:
        st.warning("No valid signal detected.")
        return

    # convert to numeric and sort
    try:
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
        df = df.dropna().sort_values("X").reset_index(drop=True)
        x_axis = df["X"].values
        signal = df["Y"].values
    except Exception as e:
        st.error(f"Data processing error: {e}")
        return

    # Region selection: use actual X axis values for sliders
    st.subheader(t("select_region"))
    x_min = float(np.min(x_axis))
    x_max = float(np.max(x_axis))
    # default region centered
    default_start = x_min + 0.25*(x_max-x_min)
    default_end = x_min + 0.75*(x_max-x_min)
    start, end = st.slider("", min_value=x_min, max_value=x_max, value=(default_start, default_end), step=(x_max-x_min)/100.0, key="sn_region_slider")

    # Select region rows
    region = df[(df["X"] >= start) & (df["X"] <= end)]
    if region.shape[0] < 2:
        st.warning("Select a larger region (or slide the handles).")
    # Plot chromatogram with highlighted region (preserve scale)
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(df["X"], df["Y"], label="Chromatogram")
    ax.axvspan(start, end, color="orange", alpha=0.3, label="Selected region")
    ax.set_xlabel("X (original scale)")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    # compute stats on selected region if possible
    if region.shape[0] >= 2:
        peak = float(np.max(region["Y"].values))
        baseline = float(np.mean(region["Y"].values))
        height = peak - baseline
        noise_std = float(np.std(region["Y"].values, ddof=0))
        unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="sn_unit_region")

        sn_classic = peak / noise_std if noise_std != 0 else float("nan")
        sn_usp = height / noise_std if noise_std != 0 else float("nan")

        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")

        # If slope known (from linearity) or user provides it, convert noise -> conc LOD/LOQ
        slope_for_conversion = st.session_state.linear_slope if (st.session_state.linear_slope is not None and st.session_state.linear_slope!=0) else None
        user_slope = st.number_input("If slope not set, enter slope for conc. conversion (optional)", value=0.0, format="%.6f", key="sn_user_slope")
        slope_to_use = slope_for_conversion if slope_for_conversion else (user_slope if user_slope!=0 else None)
        if slope_to_use:
            lod = 3.3 * noise_std / slope_to_use
            loq = 10 * noise_std / slope_to_use
            st.write(f"{t('lod')} ({unit}): {lod:.6f}")
            st.write(f"{t('loq')} ({unit}): {loq:.6f}")

        # Export CSV of region
        csv_buf = io.StringIO()
        pd.DataFrame({"X":region["X"].values, "Signal":region["Y"].values}).to_csv(csv_buf, index=False)
        st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv")

        # Export PDF: snapshot of region plot + metrics
        buf = fig_to_bytes(fig)
        lines = [
            f"File: {uploaded.name}",
            f"User: {st.session_state.user or 'Unknown'}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{t('sn_classic')}: {sn_classic:.4f}",
            f"{t('sn_usp')}: {sn_usp:.4f}"
        ]
        if slope_to_use:
            lines.append(f"Slope used: {slope_to_use:.6f}")
            lines.append(f"{t('lod')}: {lod:.6f}")
            lines.append(f"{t('loq')}: {loq:.6f}")
        logo_path = LOGO_FILE if os.path.exists(LOGO_FILE) else None
        pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=buf, logo_path=logo_path)
        st.download_button("Download S/N PDF", pdfb, file_name="sn_report.pdf", mime="application/pdf")
    else:
        st.info("Selected region contains less than 2 points; cannot compute S/N metrics.")

    # formulas expander
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
        **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \) where Height ≈ (peak - baseline)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

# -------------------------
# Main app (tabs at top, modern)
# -------------------------
def main_app():
    st.markdown(f"### {t('app_title')} — {st.session_state.user or ''}")
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang")
        st.session_state.lang = lang

    # tabs: admin only visible to admin users
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