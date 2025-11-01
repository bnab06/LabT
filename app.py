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

def sn_panel_full():
    import re, io, os
    from PIL import Image
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from datetime import datetime
    from scipy.ndimage import gaussian_filter1d
    from scipy.signal import find_peaks
    import streamlit as st

    st.header("Signal-to-Noise Panel")

    uploaded = st.file_uploader("Upload chromatogram (CSV / PNG / JPG / PDF)", 
                                type=["csv","png","jpg","jpeg","pdf"])
    sn_manual_mode = uploaded is None

    # --- MANUAL MODE ---
    if sn_manual_mode:
        st.subheader("Manual S/N calculation")
        H = st.number_input("H (peak height)", value=0.0, format="%.6f")
        h = st.number_input("h (noise)", value=0.0, format="%.6f")
        slope_auto_raw = st.session_state.get("linear_slope", 0.0)
        try:
            slope_auto = float(slope_auto_raw)
        except:
            slope_auto = 0.0
        slope_input = st.number_input("Slope (imported or manual)", value=slope_auto, format="%.6f")
        unit = st.selectbox("Unit", ["µg/mL", "mg/mL", "ng/mL"])
        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2 * H / h if h != 0 else float("nan")
        st.write(f"S/N Classic: {sn_classic:.4f}")
        st.write(f"S/N USP: {sn_usp:.4f}")
        if slope_input:
            try:
                lod = 3.3 * h / slope_input
                loq = 10 * h / slope_input
                st.write(f"LOD ({unit}): {lod:.6f}")
                st.write(f"LOQ ({unit}): {loq:.6f}")
            except:
                pass
        return

    # --- Helper: extract data from image or OCR fallback ---
    def extract_xy_from_image(image):
        try:
            import pytesseract
            text = pytesseract.image_to_string(image)
            lines = text.splitlines()
            data = []
            for line in lines:
                line_clean = re.sub(r"[^\d\.,\- ]", " ", line)
                parts = line_clean.split()
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",", "."))
                        y = float(parts[1].replace(",", "."))
                        data.append((x, y))
                    except:
                        continue
            if data:
                df_ocr = pd.DataFrame(data, columns=["X","Y"]).sort_values("X").reset_index(drop=True)
                return df_ocr
        except Exception:
            pass

        # OCR fail → vertical projection
        arr = np.array(image.convert("L"))
        if arr.mean() > 127:
            arr = 255 - arr
        signal = arr.max(axis=0).astype(float)
        signal_smooth = gaussian_filter1d(signal, sigma=1)
        if len(signal_smooth) < 50:
            x = np.linspace(0, len(signal_smooth)-1, 50)
            signal_smooth = np.interp(x, np.arange(len(signal_smooth)), signal_smooth)
        df = pd.DataFrame({"X": np.arange(len(signal_smooth)), "Y": signal_smooth})
        return df

    # --- Read file ---
    df = None
    fname = uploaded.name.lower()
    if fname.endswith(".csv"):
        uploaded.seek(0)
        try:
            df0 = pd.read_csv(uploaded)
        except:
            uploaded.seek(0)
            df0 = pd.read_csv(uploaded, sep=";", engine="python")
        if df0.shape[1] < 2:
            st.error("CSV must have at least two columns")
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
    elif fname.endswith((".png",".jpg",".jpeg")):
        uploaded.seek(0)
        img = Image.open(uploaded).convert("RGB")
        st.image(img, use_column_width=True)
        df = extract_xy_from_image(img)
    elif fname.endswith(".pdf"):
        try:
            from pdf2image import convert_from_bytes
            uploaded.seek(0)
            pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
            img = pages[0]
            st.image(img, use_column_width=True)
            df = extract_xy_from_image(img)
        except Exception:
            st.warning("PDF conversion failed. Using placeholder image.")
            img = Image.new("RGB", (600,200), "white")
            df = extract_xy_from_image(img)
    else:
        st.error("Unsupported file type")
        return

    if df is None or df.empty:
        st.warning("No valid signal detected.")
        return

    df = df.dropna().sort_values("X").reset_index(drop=True)

    # --- Region selection ---
    x_min, x_max = df["X"].min(), df["X"].max()
    if x_min == x_max:
        st.warning("Signal is flat or OCR invalid. Using artificial X range.")
        x_min, x_max = 0, len(df)-1
    default_start = x_min + 0.25*(x_max-x_min)
    default_end = x_min + 0.75*(x_max-x_min)
    start, end = st.slider("Select X range",
                            min_value=float(x_min),
                            max_value=float(x_max),
                            value=(float(default_start), float(default_end)))
    region = df[(df["X"] >= start) & (df["X"] <= end)].copy()
    if len(region) < 2:
        st.warning("Region too small. Using full signal.")
        region = df.copy()

    # --- Peak detection ---
    st.subheader("Peak detection settings")
    y_region = region["Y"].values
    baseline = float(np.mean(y_region))
    noise_std = float(np.std(y_region)) or 1e-12
    peak_val = float(np.max(y_region))
    height = peak_val - baseline

    height_factor = st.slider("Height factor (baseline + factor*σ)", 0.0, 10.0, 3.0, 0.1)
    threshold = baseline + height_factor * noise_std

    num_points = len(region)
    min_dist_slider = max(1, num_points // 100)
    max_dist_slider = max(min_dist_slider, num_points // 2)
    min_distance = st.slider("Min distance between peaks",
                             min_value=1,
                             max_value=max_dist_slider,
                             value=min_dist_slider)

    peaks_idx, peaks_props = find_peaks(y_region, height=threshold, distance=min_distance)

    if len(peaks_idx) == 0 and height > 0:
        for factor in np.linspace(height_factor*0.5, 0.1, 10):
            threshold = baseline + factor*noise_std
            peaks_idx, peaks_props = find_peaks(y_region, height=threshold, distance=min_distance)
            if len(peaks_idx) > 0:
                st.info(f"Height factor auto-adjusted to {factor:.2f} to detect peaks.")
                break

    peaks_x = region["X"].values[peaks_idx] if len(peaks_idx) else np.array([])
    peaks_y = y_region[peaks_idx] if len(peaks_idx) else np.array([])

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(df["X"], df["Y"], label="Chromatogram")
    ax.axvspan(start, end, alpha=0.25, label="Selected region")
    if len(peaks_x):
        ax.plot(peaks_x, peaks_y, "r^", label="Detected peaks")
    ax.hlines(threshold, xmin=start, xmax=end, linestyles="--", label=f"Threshold")
    ax.legend()
    st.pyplot(fig)

    # --- Compute S/N ---
    sn_classic = peak_val/noise_std
    sn_usp = height/noise_std
    st.write(f"S/N Classic: {sn_classic:.4f}")
    st.write(f"S/N USP: {sn_usp:.4f}")

    slope_auto = st.session_state.get("linear_slope", 1.0)
    try:
        slope_auto = float(slope_auto)
    except:
        slope_auto = 1.0
    slope_input = st.number_input("Slope (for LOD/LOQ)", value=slope_auto, min_value=0.0, step=0.01)
    if slope_input > 0:
        lod = 3.3 * noise_std / slope_input
        loq = 10 * noise_std / slope_input
        st.write(f"LOD: {lod:.6f}")
        st.write(f"LOQ: {loq:.6f}")

    # --- Export CSV ---
    csv_buf = io.StringIO()
    region.to_csv(csv_buf, index=False)
    st.download_button("Download region CSV", csv_buf.getvalue(), "sn_region.csv", "text/csv")

    # --- Export PDF ---
    if st.button("Export S/N PDF"):
        from fpdf import FPDF
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0,10,f"File: {uploaded.name}", ln=True)
        pdf.cell(0,10,f"Date: {datetime.now():%Y-%m-%d %H:%M:%S}", ln=True)
        pdf.cell(0,10,f"S/N Classic: {sn_classic:.4f}", ln=True)
        pdf.cell(0,10,f"S/N USP: {sn_usp:.4f}", ln=True)
        if slope_input > 0:
            pdf.cell(0,10,f"LOD: {lod:.6f}", ln=True)
            pdf.cell(0,10,f"LOQ: {loq:.6f}", ln=True)
        if len(peaks_x):
            pdf.cell(0,10,"Detected Peaks:", ln=True)
            for xi, yi in zip(peaks_x, peaks_y):
                pdf.cell(0,8,f" - {xi:.6g}, {yi:.6g}", ln=True)
        pdf.image(buf, x=10, y=None, w=180)
        pdf_out = io.BytesIO()
        pdf.output(pdf_out)
        pdf_out.seek(0)
        st.download_button("Download S/N PDF", pdf_out, "sn_report.pdf", "application/pdf")

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