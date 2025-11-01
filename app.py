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

# ============================
# Module S/N — Version MODERNE (coller dans LabT)
# ============================
def sn_panel_full():
    """
    Module S/N moderne — à coller dans LabT.
    - Bilingue (utilise st.session_state.lang ; défaut 'fr')
    - Ne s'affiche que si st.session_state.get('authenticated') is True (sécurité)
    - Support CSV / PNG / JPG / PDF (pdf2image optional)
    - OCR optional (pytesseract) ; fallback projection
    - Détection de tous les pics ; pic principal = max Y
    - Zone X utilisée uniquement pour calcul du bruit
    - Plotly interactif (click selection si streamlit_plotly_events present)
    - Export CSV (toujours) et PDF (si fpdf present)
    """

    # ---- imports locaux (robustness) ----
    import io, os, tempfile
    from datetime import datetime
    import numpy as np
    import pandas as pd

    import matplotlib.pyplot as plt
    from scipy.ndimage import gaussian_filter1d
    from scipy.signal import find_peaks, peak_widths

    # optional libs
    try:
        from PIL import Image
    except Exception:
        Image = None

    try:
        from pdf2image import convert_from_bytes
        PDF2IMG = True
    except Exception:
        convert_from_bytes = None
        PDF2IMG = False

    try:
        import pytesseract
        OCR_AVAILABLE = True
    except Exception:
        pytesseract = None
        OCR_AVAILABLE = False

    try:
        from fpdf import FPDF
        FPDF_AVAILABLE = True
    except Exception:
        FPDF_AVAILABLE = False

    try:
        from streamlit_plotly_events import plotly_events
        PLOTLY_EVENTS = True
    except Exception:
        plotly_events = None
        PLOTLY_EVENTS = False

    try:
        import plotly.graph_objects as go
        PLOTLY_AVAILABLE = True
    except Exception:
        go = None
        PLOTLY_AVAILABLE = False

    # ---- session / auth guards ----
    if "lang" not in st.session_state:
        st.session_state.lang = "fr"
    lang = st.session_state.get("lang", "fr")

    # If your app uses another key for auth change this line accordingly.
    if not st.session_state.get("authenticated", False):
        st.info("🔒 Please log in / Veuillez vous connecter")
        return

    # ---- translations ----
    TRANSL = {
        "fr": {
            "title": "S/N — Module (moderne)",
            "upload": "Télécharger chromatogramme (CSV / PNG / JPG / PDF)",
            "smoothing": "Lissage (sigma)",
            "noise_region": "Zone bruit (X)",
            "instructions": "Cliquez sur un pic dans le graphique pour le sélectionner (optionnel).",
            "no_signal": "Aucun signal valide détecté.",
            "peaks_table": "Table des pics détectés",
            "export_csv": "Télécharger CSV des pics",
            "export_pdf": "Télécharger rapport PDF",
            "sn_classic": "S/N Classique",
            "sn_usp": "S/N USP",
            "baseline": "Ligne de base",
            "half_height": "Demi-hauteur",
            "selected_peak": "Pic sélectionné",
        },
        "en": {
            "title": "S/N — Modern module",
            "upload": "Upload chromatogram (CSV / PNG / JPG / PDF)",
            "smoothing": "Smoothing (sigma)",
            "noise_region": "Noise region (X)",
            "instructions": "Click a peak on the chart to select it (optional).",
            "no_signal": "No valid signal detected.",
            "peaks_table": "Detected peaks table",
            "export_csv": "Download peaks CSV",
            "export_pdf": "Download PDF report",
            "sn_classic": "Classic S/N",
            "sn_usp": "USP S/N",
            "baseline": "Baseline",
            "half_height": "Half height",
            "selected_peak": "Selected peak",
        }
    }
    T = TRANSL.get(lang, TRANSL["fr"])

    # ---- UI header ----
    st.header(T["title"])
    st.caption(T["instructions"])

    # ---- left column: options & upload ----
    col_opts, col_vis = st.columns([1, 2])

    with col_opts:
        uploaded = st.file_uploader(T["upload"], type=["csv", "png", "jpg", "jpeg", "pdf"])
        sigma = st.slider(T["smoothing"], 0.0, 5.0, 1.0, step=0.1)
        st.markdown("---")
        st.write(T["noise_region"])
        # placeholders: real slider created after data load
        placeholder_noise = st.empty()
        st.markdown("---")
        st.write("Exports & tools:")
        col_csv_btn = st.empty()
        col_pdf_btn = st.empty()
        st.write("- OCR optional; PDF conversion optional.")
        st.write(f"- plotly click events available: {PLOTLY_EVENTS}")
        st.write(f"- pdf2image available: {PDF2IMG}")
        st.write(f"- fpdf available: {FPDF_AVAILABLE}")

    # ---- main visualization area ----
    with col_vis:
        if uploaded is None:
            st.info(T["upload"])
            return

        # read file
        df = None
        orig_image = None
        try:
            name = uploaded.name.lower()
            if name.endswith(".csv"):
                uploaded.seek(0)
                df = pd.read_csv(uploaded)
                # allow common two-column formats
                cols_low = [c.lower() for c in df.columns]
                if "time" in cols_low and "signal" in cols_low:
                    df = df.rename(columns={df.columns[cols_low.index("time")]: "X",
                                             df.columns[cols_low.index("signal")]: "Y"})
                else:
                    df = df.iloc[:, :2].copy()
                    df.columns = ["X", "Y"]
                df["X"] = pd.to_numeric(df["X"], errors="coerce")
                df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
                df = df.dropna().sort_values("X").reset_index(drop=True)
            elif name.endswith((".png", ".jpg", ".jpeg")):
                uploaded.seek(0)
                if Image is None:
                    st.error("Pillow missing; cannot read image.")
                    return
                orig_image = Image.open(uploaded).convert("RGB")
                st.subheader(T["title"])
                st.image(orig_image, use_column_width=True)
            elif name.endswith(".pdf"):
                uploaded.seek(0)
                if PDF2IMG:
                    try:
                        pages = convert_from_bytes(uploaded.read(), dpi=200, first_page=1, last_page=1)
                        orig_image = pages[0].convert("RGB")
                    except Exception:
                        uploaded.seek(0)
                        try:
                            orig_image = Image.open(io.BytesIO(uploaded.read())).convert("RGB")
                        except Exception as e:
                            st.error("PDF reading failed.")
                            return
                else:
                    # fallback: try reading via PIL
                    try:
                        uploaded.seek(0)
                        orig_image = Image.open(io.BytesIO(uploaded.read())).convert("RGB")
                    except Exception:
                        st.error("PDF conversion not available; install pdf2image/poppler.")
                        return
                st.image(orig_image, use_column_width=True)
            else:
                st.error("Unsupported file type.")
                return
        except Exception as e:
            st.error(f"File read error: {e}")
            return

        # if image but no dataframe, try OCR or projection
        if (df is None) and (orig_image is not None):
            # try OCR (two-column numbers), else vertical projection
            try:
                if OCR_AVAILABLE:
                    txt = pytesseract.image_to_string(orig_image)
                    # simple parsing: look for two numeric columns per line
                    data = []
                    for ln in txt.splitlines():
                        parts = ln.replace(",", ".").split()
                        nums = []
                        for p in parts:
                            try:
                                v = float(p)
                                nums.append(v)
                            except:
                                pass
                        if len(nums) >= 2:
                            data.append((nums[0], nums[1]))
                    if len(data) >= 2:
                        df = pd.DataFrame(data, columns=["X", "Y"]).sort_values("X").reset_index(drop=True)
                        st.success("OCR: numeric table extracted.")
                # fallback
                if df is None:
                    arr = np.array(orig_image.convert("L"))
                    signal = arr.max(axis=0).astype(float)
                    # invert pixel projection so peaks point up
                    signal = signal.max() - signal
                    signal = gaussian_filter1d(signal, sigma=1.0)
                    df = pd.DataFrame({"X": np.arange(len(signal)), "Y": signal})
                    st.info("OCR failed or incomplete — using vertical projection.")
            except Exception as e:
                st.warning(f"OCR/projection error: {e}")
                arr = np.array(orig_image.convert("L"))
                signal = arr.max(axis=0).astype(float)
                signal = signal.max() - signal
                signal = gaussian_filter1d(signal, sigma=1.0)
                df = pd.DataFrame({"X": np.arange(len(signal)), "Y": signal})

        # final check
        if df is None or df.empty:
            st.warning(T["no_signal"])
            return

        # ensure numeric sorted
        df = df.dropna().sort_values("X").reset_index(drop=True)
        x = df["X"].values
        y = df["Y"].values

        # auto-detect & correct inverted chromatogram (peaks downward)
        # heuristic: if median is higher than mean and peaks are negative relative to baseline
        if np.mean(y) < np.median(y) and np.abs(np.min(y)) > np.abs(np.max(y)):
            y = -y
            df["Y"] = y

        # smoothing
        df["Y_smooth"] = gaussian_filter1d(df["Y"].values, sigma=float(sigma))

        # build noise slider now that we have X range
        x_min, x_max = float(df["X"].min()), float(df["X"].max())
        # replace placeholder with real slider
        noise_start, noise_end = placeholder_noise.slider(
            "", min_value=float(x_min), max_value=float(x_max),
            value=(x_min + 0.25*(x_max - x_min), x_min + 0.75*(x_max - x_min)),
            step=float(max((x_max - x_min)/1000.0, 1e-12))
        )

        # compute noise baseline and std from selected noise region (if region too small fallback to global)
        region_mask = (df["X"] >= noise_start) & (df["X"] <= noise_end)
        if df[region_mask].shape[0] < 3:
            noise_region_df = df.copy()
        else:
            noise_region_df = df[region_mask].copy()
        baseline = float(noise_region_df["Y_smooth"].mean())
        noise_std = float(noise_region_df["Y_smooth"].std(ddof=0) or 1e-12)

        # detect peaks on smoothed Y (use adaptive prominence/distance)
        global_amp = df["Y_smooth"].max() - df["Y_smooth"].min()
        adaptive_prom = max(0.5*noise_std, 0.01*global_amp)
        adaptive_dist = max(1, int(len(df)//50))
        peaks_idx, props = find_peaks(df["Y_smooth"].values, prominence=adaptive_prom, distance=adaptive_dist)

        # metrics per peak
        metrics = []
        for p in peaks_idx:
            peak_y = float(df["Y_smooth"].iloc[p])
            H = peak_y - baseline
            widths_res = peak_widths(df["Y_smooth"].values, [p], rel_height=0.5)
            width_samples = float(widths_res[0][0]) if len(widths_res[0])>0 else np.nan
            dx = float(np.median(np.diff(df["X"].values))) if len(df)>1 else 1.0
            W = width_samples * dx
            SN_classic = H / noise_std if noise_std != 0 else float("nan")
            SN_USP = 2*H / noise_std if noise_std != 0 else float("nan")
            metrics.append({
                "peak_index": int(p),
                "retention_time": float(df["X"].iloc[p]),
                "peak_value": peak_y,
                "H": H,
                "h": noise_std,
                "W": W,
                "S/N_classic": SN_classic,
                "S/N_USP": SN_USP
            })

        # if no peaks detected, use global maximum as single peak
        if len(metrics) == 0:
            p = int(np.argmax(df["Y_smooth"].values))
            peak_y = float(df["Y_smooth"].iloc[p])
            H = peak_y - baseline
            widths_res = peak_widths(df["Y_smooth"].values, [p], rel_height=0.5)
            width_samples = float(widths_res[0][0]) if len(widths_res[0])>0 else np.nan
            dx = float(np.median(np.diff(df["X"].values))) if len(df)>1 else 1.0
            W = width_samples * dx
            SN_classic = H / noise_std if noise_std != 0 else float("nan")
            SN_USP = 2*H / noise_std if noise_std != 0 else float("nan")
            metrics.append({
                "peak_index": int(p),
                "retention_time": float(df["X"].iloc[p]),
                "peak_value": peak_y,
                "H": H,
                "h": noise_std,
                "W": W,
                "S/N_classic": SN_classic,
                "S/N_USP": SN_USP
            })

        # sort metrics by H desc
        metrics = sorted(metrics, key=lambda z: -z["H"])

        # display interactive chart (plotly if available otherwise matplotlib)
        st.subheader("Chromatogram")
        selected_peak_index = None

        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["X"], y=df["Y_smooth"], mode="lines", name="Smoothed"))
            # mark peaks
            if len(metrics) > 0:
                fig.add_trace(go.Scatter(
                    x=[m["retention_time"] for m in metrics],
                    y=[m["peak_value"] for m in metrics],
                    mode="markers",
                    marker=dict(color="red", size=8),
                    name="Detected peaks"
                ))
            # noise region
            fig.add_vrect(x0=noise_start, x1=noise_end, fillcolor="grey", opacity=0.2, line_width=0)
            fig.update_yaxes(autorange="reversed")  # invert for chromatogram look
            fig.update_layout(height=420, margin=dict(l=20,r=20,t=20,b=20), clickmode="event+select")

            st_plot = st.plotly_chart(fig, use_container_width=True)

            # try to get click events
            if PLOTLY_EVENTS:
                try:
                    clicked = plotly_events(fig, click_event=True, select_event=False, override_height=420)
                    if clicked:
                        clicked_x = clicked[0].get("x")
                        # find nearest df index
                        selected_peak_index = int(np.argmin(np.abs(df["X"].values - clicked_x)))
                except Exception:
                    selected_peak_index = None
        else:
            # fallback matplotlib
            figm, ax = plt.subplots(figsize=(10,3))
            ax.plot(df["X"], df["Y_smooth"], label="Smoothed")
            if len(metrics) > 0:
                ax.plot([m["retention_time"] for m in metrics], [m["peak_value"] for m in metrics], "r^", label="Peaks")
            ax.axvspan(noise_start, noise_end, color="grey", alpha=0.2)
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.invert_yaxis()
            ax.legend()
            st.pyplot(figm)
            selected_peak_index = None

        # peaks table & selection
        st.subheader(T["peaks_table"])
        dfm = pd.DataFrame(metrics)
        if not dfm.empty:
            # display top columns nicely
            dfm_display = dfm[["retention_time","H","h","W","S/N_classic","S/N_USP"]].copy()
            dfm_display = dfm_display.round(6)
            sel = st.selectbox("Select peak (table)", options=dfm.index.tolist(),
                               format_func=lambda i: f"#{i+1}  t={dfm.loc[i,'retention_time']:.6g}  H={dfm.loc[i,'H']:.6g}")
            selected_peak_index = metrics[sel]["peak_index"]
            st.dataframe(dfm_display, height=200)
        else:
            st.info(T["no_signal"])

        # if still no selection, choose top H
        if selected_peak_index is None:
            selected_peak_index = metrics[0]["peak_index"]

        # compute selected peak summary
        sel_idx = int(selected_peak_index)
        sel_ret = float(df["X"].iloc[sel_idx])
        sel_peak = float(df["Y_smooth"].iloc[sel_idx])
        sel_H = float(sel_peak - baseline)
        widths_sel = peak_widths(df["Y_smooth"].values, [sel_idx], rel_height=0.5)
        width_samples_sel = float(widths_sel[0][0]) if len(widths_sel[0])>0 else np.nan
        dx = float(np.median(np.diff(df["X"].values))) if len(df)>1 else 1.0
        sel_W = width_samples_sel * dx
        sel_h = noise_std
        sel_SN_classic = sel_H / sel_h if sel_h != 0 else float("nan")
        sel_SN_USP = 2*sel_H / sel_h if sel_h != 0 else float("nan")

        st.subheader(T["selected_peak"])
        cols = st.columns(4)
        cols[0].metric("tR", f"{sel_ret:.6g}")
        cols[1].metric("H", f"{sel_H:.6g}")
        cols[2].metric("h (σ)", f"{sel_h:.6g}")
        cols[3].metric("W", f"{sel_W:.6g}")
        st.write(f"{T['sn_classic']}: {sel_SN_classic:.6g}   |   {T['sn_usp']}: {sel_SN_USP:.6g}")

        # export CSV always available
        csv_buf = io.StringIO()
        pd.DataFrame(metrics).to_csv(csv_buf, index=False)
        csv_bytes = csv_buf.getvalue().encode("utf-8")
        col_csv_btn.download_button(label=T["export_csv"], data=csv_bytes, file_name="sn_peaks.csv", mime="text/csv")

        # export PDF when possible
        if FPDF_AVAILABLE:
            try:
                # build a simple PDF with a matplotlib snapshot
                # create figure snapshot
                fig_tmp, ax_tmp = plt.subplots(figsize=(10,3))
                ax_tmp.plot(df["X"], df["Y_smooth"], label="Smoothed")
                ax_tmp.plot(df["X"].iloc[sel_idx], df["Y_smooth"].iloc[sel_idx], "r^", label="Selected peak")
                ax_tmp.axvspan(noise_start, noise_end, alpha=0.2, color="grey")
                ax_tmp.hlines([baseline, baseline + sel_H/2], xmin=df["X"].min(), xmax=df["X"].max(), linestyles="--", colors=["green","orange"])
                ax_tmp.set_xlabel("X"); ax_tmp.set_ylabel("Y")
                ax_tmp.invert_yaxis()
                ax_tmp.legend()
                tmp_png = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                fig_tmp.savefig(tmp_png.name, bbox_inches="tight")
                plt.close(fig_tmp)

                # create pdf
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 8, "S/N Report", ln=True, align="C")
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
                pdf.ln(4)
                pdf.cell(0, 6, f"Selected peak tR: {sel_ret:.6g}", ln=True)
                pdf.cell(0, 6, f"H: {sel_H:.6g}", ln=True)
                pdf.cell(0, 6, f"h (σ): {sel_h:.6g}", ln=True)
                pdf.cell(0, 6, f"W: {sel_W:.6g}", ln=True)
                pdf.cell(0, 6, f"{T['sn_classic']}: {sel_SN_classic:.6g}", ln=True)
                pdf.cell(0, 6, f"{T['sn_usp']}: {sel_SN_USP:.6g}", ln=True)
                pdf.ln(6)
                pdf.image(tmp_png.name, x=10, w=pdf.w - 20)
                tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                pdf.output(tmp_pdf.name)
                with open(tmp_pdf.name, "rb") as f:
                    pdf_bytes = f.read()
                col_pdf_btn.download_button(label=T["export_pdf"], data=pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")
                # cleanup
                try:
                    os.unlink(tmp_png.name)
                    os.unlink(tmp_pdf.name)
                except Exception:
                    pass
            except Exception as e:
                col_pdf_btn.write(f"PDF error: {e}")
        else:
            col_pdf_btn.write("fpdf not installed — PDF export unavailable.")

# End of sn_panel_full

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