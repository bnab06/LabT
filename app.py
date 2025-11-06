# -----------------------------
# app.py  — PART 1 (core + login/admin/navigation + utils)
# Paste PART 2 then PART 3 after this
# -----------------------------
import streamlit as st
import json
import os
import io
import tempfile
from datetime import datetime
from fpdf import FPDF
from PIL import Image
import numpy as np

# Optional imports (best-effort)
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
FEEDBACK_FILE = "feedback.json"
LOGO_FILE = "logo_labt.png"

# -------------------------
# Translations (single source)
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
        "digitize_info":"Digitizing : OCR tenté si pytesseract disponible (best-effort)",
        "export_sn_pdf":"Exporter S/N PDF",
        "download_original_pdf":"Télécharger PDF original",
        "change_pwd":"Changer mot de passe (hors session)",
        "compute":"Compute",
        "company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport.",
        "select_section":"Section",
        "upload_logo":"Uploader un logo (optionnel)",
        "manual_sn":"Calcul manuel S/N",
        "noise_region":"Zone bruit",
        "threshold":"Seuil (sensibilité)",
        "min_distance":"Min distance entre pics",
        "upload_feedback":"Envoyer un feedback",
        "view_feedback":"Gérer feedbacks (admin)",
        "reply":"Répondre",
        "unit_choice":"Unité (LOD/LOQ)",
        "download_image":"Télécharger image traitée",
        "could_not_convert_pdf":"Impossible de convertir le PDF (poppler absent). Importez un PNG/JPG.",
        "no_users":"Aucun utilisateur configuré"
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
        "upload_logo":"Upload logo (optional)",
        "manual_sn":"Manual S/N calculation",
        "noise_region":"Noise region",
        "threshold":"Threshold (sensitivity)",
        "min_distance":"Min distance between peaks",
        "upload_feedback":"Send feedback",
        "view_feedback":"Manage feedbacks (admin)",
        "reply":"Reply",
        "unit_choice":"Unit (LOD/LOQ)",
        "download_image":"Download processed image",
        "could_not_convert_pdf":"Could not convert PDF (poppler missing). Upload PNG/JPG.",
        "no_users":"No users configured"
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
if "page" not in st.session_state:
    st.session_state.page = "login"
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

# -------------------------
# Users storage helpers (JSON on disk)
# -------------------------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        default = {
            "admin": {"password": "admin", "role": "admin", "access": ["linearity","sn"]},
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
# Feedback storage
# -------------------------
def load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_feedback(list_feedback):
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(list_feedback, f, indent=2, ensure_ascii=False)

# -------------------------
# PDF helper (wrapped)
# -------------------------
def pdf_to_png_bytes(uploaded_file):
    """
    Try convert PDF bytes -> PIL.Image (first page). Returns (pil_image, msg)
    If convert_from_bytes not available or fails, returns (None, error_msg).
    """
    if convert_from_bytes is None:
        return None, t("could_not_convert_pdf")
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1, dpi=200)
        pil_img = pages[0]
        return pil_img, None
    except Exception:
        return None, t("could_not_convert_pdf")

# -------------------------
# PDF generator (report)
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
                if isinstance(img_bytes, str) and os.path.exists(img_bytes):
                    pdf.ln(4)
                    pdf.image(img_bytes, x=20, w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# -------------------------
# Header area (title + logo upload)
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
# Login screen (uses dropdown of users)
# -------------------------
def login_screen():
    header_area()
    st.write("")
    cols = st.columns([2,1])
    with cols[1]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="login_lang")
        st.session_state.lang = lang

    st.markdown("### 🔐 " + t("login"))
    users = user_list()
    if not users:
        st.error(t("no_users"))
        return

    # user selection dropdown (not raw JSON)
    uname = st.selectbox(t("username"), users, key="login_user_select")
    pwd = st.text_input(t("password"), type="password", key="login_password")
    if st.button(t("login"), key="login_btn"):
        matched = find_user_key_case_insensitive(uname)
        if matched and USERS.get(matched, {}).get("password") == (pwd or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role", "user")
            # set page to main app
            st.session_state.page = "main"
            st.success(f"{t('login')} OK")
            return
        else:
            st.error(t("invalid"))

    st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

# -------------------------
# Logout helper
# -------------------------
def logout():
    for k in ["user", "role", "page", "linear_slope"]:
        if k in st.session_state:
            del st.session_state[k]
    st.session_state.page = "login"

# -------------------------
# Admin panel (user management + privileges)
# -------------------------
def admin_panel():
    st.header(t("admin"))
    st.write("Gérer les utilisateurs et leurs droits (linéarité / S/N).")
    cols = st.columns([2,1])
    with cols[0]:
        users = user_list()
        sel = st.selectbox("Sélectionner utilisateur", users, key="admin_sel_user")
        if sel:
            info = USERS.get(sel, {})
            st.write(f"Username: **{sel}**")
            st.write(f"Role: **{info.get('role','user')}**")
            st.write(f"Rights: **{', '.join(info.get('access', []))}**")
            if st.button("Modifier cet utilisateur", key=f"modify_{sel}"):
                # show expanders to edit
                with st.expander(f"Modifier {sel}", expanded=True):
                    new_pwd = st.text_input("Nouveau mot de passe (laisser vide pour conserver)", type="password", key=f"pwd_{sel}")
                    new_role = st.selectbox("Role", ["user","admin"], index=0 if info.get("role","user")=="user" else 1, key=f"role_{sel}")
                    acc_line = st.checkbox("Accès linéarité", value=("linearity" in info.get("access", [])), key=f"acc_lin_{sel}")
                    acc_sn = st.checkbox("Accès S/N", value=("sn" in info.get("access", [])), key=f"acc_sn_{sel}")
                    if st.button("Enregistrer", key=f"save_{sel}"):
                        if new_pwd:
                            USERS[sel]["password"] = new_pwd
                        USERS[sel]["role"] = new_role
                        new_access = []
                        if acc_line: new_access.append("linearity")
                        if acc_sn: new_access.append("sn")
                        USERS[sel]["access"] = new_access
                        save_users(USERS)
                        st.success(f"{sel} mis à jour.")
    with cols[1]:
        st.subheader(t("add_user"))
        with st.form("form_add_user", clear_on_submit=True):
            new_user = st.text_input(t("enter_username"), key="add_username")
            new_pass = st.text_input(t("enter_password"), type="password", key="add_password")
            role = st.selectbox("Role", ["user","admin"], key="add_role")
            acc_lin = st.checkbox("Accès linéarité", value=True, key="add_acc_lin")
            acc_sn = st.checkbox("Accès S/N", value=True, key="add_acc_sn")
            submitted = st.form_submit_button("Add")
            if submitted:
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

    st.markdown("---")
    # delete user
    st.subheader("Supprimer utilisateur")
    users_del = user_list()
    if users_del:
        del_sel = st.selectbox("Sélectionner", users_del, key="del_sel")
        if st.button("Supprimer", key="del_btn"):
            if del_sel.lower() == "admin":
                st.warning("Cannot delete admin")
            else:
                USERS.pop(del_sel, None)
                save_users(USERS)
                st.success(f"{del_sel} deleted")

# -------------------------
# Small helper: ensure logged-in and allowed to view a module
# -------------------------
def has_access(module_name):
    if st.session_state.get("role") == "admin":
        return True
    user = st.session_state.get("user")
    if not user:
        return False
    access = USERS.get(user, {}).get("access", [])
    return module_name in access

# -------------------------
# End of PART 1
# -------------------------
# -----------------------------
# app.py  — PART 2 (linearity_panel, sn_panel_full, feedback)
# Paste immediately after PART 1
# -----------------------------
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from PIL import Image

# -------------------------
# Helper: extract XY from image using pytesseract (best-effort)
# Returns DataFrame with X,Y columns (empty DF if not found)
# -------------------------
def extract_xy_from_image_pytesseract(pil_img: Image.Image):
    import pandas as _pd
    if pytesseract is None:
        return _pd.DataFrame(columns=["X","Y"])
    try:
        # Try to extract coordinate pairs from OCR text (if the image contains numbers)
        text = pytesseract.image_to_string(pil_img)
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # try common separators
            for sep in [",", ";", "\t"]:
                if sep in line:
                    parts = [p.strip() for p in line.split(sep) if p.strip() != ""]
                    if len(parts) >= 2:
                        try:
                            x = float(parts[0].replace(",","."))
                            y = float(parts[1].replace(",","."))
                            rows.append((x,y))
                            break
                        except Exception:
                            pass
            else:
                # fallback split by whitespace
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",","."))
                        y = float(parts[1].replace(",","."))
                        rows.append((x,y))
                    except Exception:
                        pass
        if rows:
            df = _pd.DataFrame(rows, columns=["X","Y"]).sort_values("X").reset_index(drop=True)
            return df
    except Exception:
        pass
    # If OCR didn't find coordinate pairs, return empty df to trigger fallback
    return pd.DataFrame(columns=["X","Y"])

# -------------------------
# Linearity panel
# (Kept as the original behaviour; unchanged logic + manual input)
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
    ax.plot(xs, slope*xs + intercept, color="black", label="Fit")  # solid line
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
# S/N panel (improved)
# - Works on original image (no re-draw), uses grayscale detection where needed.
# - Offers manual S/N and automatic detection (peak = global max on Y).
# - PDF->PNG conversion best-effort.
# -------------------------
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))

    # File upload
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_uploader")
    # Manual mode toggle
    manual_mode = st.checkbox(t("manual_sn"), value=False, key="sn_manual_toggle")

    # Manual S/N block
    if manual_mode:
        st.subheader(t("manual_sn"))
        H = st.number_input("H (peak height)", value=0.0, format="%.6f", key="manual_H_sn")
        h = st.number_input("h (noise)", value=0.0, format="%.6f", key="manual_h_sn")
        slope_choice = st.radio("Slope source", ("From linearity", "Manual input"), key="manual_slope_choice")
        slope_val = None
        if slope_choice == "From linearity":
            slope_val = st.session_state.get("linear_slope", None)
            if slope_val is None:
                st.warning("No slope available from linearity.")
                slope_val = st.number_input("Enter slope manually", value=0.0, format="%.6f", key="manual_slope_missing")
        else:
            slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="manual_slope_sn")

        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2 * H / h if h != 0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        if slope_val and slope_val != 0:
            lod = 3.3 * h / slope_val
            loq = 10 * h / slope_val
            unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"], index=0, key="manual_unit_choice")
            st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
            st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
        return

    if uploaded is None:
        st.info("Upload a chromatogram (CSV or image) to compute S/N, or use manual mode.")
        return

    name = uploaded.name.lower()
    df = None
    orig_image = None
    # --- CSV handling ---
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

    # --- IMAGE (PNG/JPG) handling ---
    elif name.endswith((".png",".jpg",".jpeg")):
        try:
            uploaded.seek(0)
            pil_img = Image.open(uploaded).convert("RGB")
            orig_image = pil_img.copy()
            st.subheader("Original image")
            st.image(orig_image, use_column_width=True)
            # try OCR -> XY detection
            df = extract_xy_from_image_pytesseract(orig_image)
            if df.empty:
                # fallback: vertical projection (use columns -> signal)
                arr = np.array(orig_image.convert("L"))
                signal = arr.max(axis=0).astype(float)
                df = pd.DataFrame({"X": np.arange(len(signal)), "Y": signal})
        except Exception as e:
            st.error(f"Image error: {e}")
            return

    # --- PDF handling (convert to PNG first) ---
    elif name.endswith(".pdf"):
        uploaded.seek(0)
        pil_img, err = pdf_to_png_bytes(uploaded)
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

    # Ensure df sorted and numeric
    df = df.dropna().sort_values("X").reset_index(drop=True)
    # If X values are constant (flat), create artificial X axis but warn
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    if x_min == x_max:
        st.warning("Signal plat ou OCR invalide : les valeurs X sont identiques. Utilisation d'un axe X artificiel.")
        df["X"] = np.arange(len(df))
        x_min, x_max = 0.0, float(len(df)-1)

    # Selection region for noise (two-handle slider)
    st.subheader(t("noise_region"))
    default_start = x_min + 0.25*(x_max-x_min)
    default_end = x_min + 0.75*(x_max-x_min)
    try:
        start, end = st.slider(t("select_region"),
                               min_value=float(x_min),
                               max_value=float(x_max),
                               value=(float(default_start), float(default_end)),
                               key="sn_range_slider")
    except Exception as e:
        st.warning(f"Slider initialization issue: {e}")
        start, end = float(x_min), float(x_max)

    region = df[(df["X"] >= start) & (df["X"] <= end)].copy()
    if region.shape[0] < 2:
        st.warning("Région trop petite pour estimer le bruit — calcul automatique utilisé.")
        region = df  # fallback: use full signal to compute noise

    # Peak detection sensitivity controls
    st.subheader("Peak detection settings")
    threshold_factor = st.slider(t("threshold"), 0.0, 10.0, 3.0, step=0.1, key="sn_threshold_factor")
    min_distance = st.number_input(t("min_distance"), value=5, min_value=1, step=1, key="sn_min_distance")

    # Compute main peak as global max on Y (per your request)
    x_arr = df["X"].values
    y_arr = df["Y"].values
    peak_idx = int(np.argmax(y_arr))
    peak_x = float(x_arr[peak_idx])
    peak_y = float(y_arr[peak_idx])

    # Baseline and noise computed from selected region
    noise_std = float(region["Y"].std(ddof=0)) if not region.empty else float(np.std(y_arr))
    baseline = float(region["Y"].mean()) if not region.empty else float(np.mean(y_arr))
    height = peak_y - baseline

    # FWHM (approx) — half height crossing points
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

    # Compute S/N
    noise_val = noise_std if noise_std != 0 else 1e-12
    sn_classic = peak_y / noise_val
    sn_usp = height / noise_val

    # Display numeric results
    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
    st.write(f"Peak retention (X): {peak_x:.4f}")
    st.write(f"H (height): {height:.4f}, noise h (std): {noise_std:.4f}, W (approx FWHM): {W:.4f}")

    # Offer slope for LOD/LOQ
    slope_auto = st.session_state.get("linear_slope", None)
    st.write("Slope used for LOD/LOQ:")
    slope_choice = st.radio("Slope source", ("From linearity", "Manual input"), key="sn_slope_choice")
    slope_val = None
    if slope_choice == "From linearity":
        slope_val = slope_auto
        if slope_val is None:
            st.warning("No slope from linearity available.")
            slope_val = st.number_input("Enter slope manually", value=0.0, format="%.6f", key="sn_slope_manual_when_missing")
    else:
        slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="sn_slope_manual")

    if slope_val and slope_val != 0:
        unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"], index=0, key="sn_unit_choice")
        lod = 3.3 * noise_std / slope_val
        loq = 10 * noise_std / slope_val
        st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
        st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
    else:
        st.info("Slope not provided -> LOD/LOQ in concentration cannot be computed.")

    # Plot original-style chromatogram preserving axis scales (black line, background white)
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.set_facecolor("white")
    ax.plot(df["X"], df["Y"], color="black", label="Chromatogram")
    ax.axvspan(start, end, alpha=0.2, color="gray", label=t("noise_region"))
    ax.axhline(baseline, color="green", linestyle="--", label="Baseline")
    ax.axhline(half_height, color="orange", linestyle="--", label="Half height")
    ax.plot([peak_x], [peak_y], marker="o", markersize=8, color="red", label="Main peak")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    st.pyplot(fig)

    # Peak-finding on region based on threshold and min_distance (optional)
    threshold_abs = baseline + threshold_factor * noise_std
    try:
        y_region = region["Y"].values
        peaks_idx, props = find_peaks(y_region, height=threshold_abs, distance=int(min_distance))
        peaks_x = region["X"].values[peaks_idx] if len(peaks_idx) else np.array([])
        peaks_y = y_region[peaks_idx] if len(peaks_idx) else np.array([])
    except Exception:
        peaks_x = np.array([])
        peaks_y = np.array([])

    st.write(f"Peaks detected in region: {len(peaks_x)}")
    if len(peaks_x):
        st.dataframe(pd.DataFrame({"X": peaks_x, "Y": peaks_y}))

    # Export region CSV
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv", key="sn_csv_dl")

    # Export processed image (matplotlib figure) to PNG
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    st.download_button(t("download_image"), img_buf.getvalue(), file_name="sn_processed.png", mime="image/png", key="sn_img_dl")

    # Export PDF report (with figures)
    if st.button(t("export_sn_pdf"), key="export_sn_pdf_btn"):
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
        st.download_button(t("download_pdf"), pdfb, file_name="sn_report.pdf", mime="application/pdf", key="sn_pdf_dl")

    # small formulas expander (discrete)
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
        **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

# -------------------------
# Feedback module (simple)
# -------------------------
def feedback_panel():
    st.header("Feedback & support")
    st.write("Envoyez vos commentaires / suggestions. L'admin peut lire et répondre.")
    with st.form("feedback_form", clear_on_submit=True):
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
                with st.form(f"reply_form_{i}", clear_on_submit=False):
                    r = st.text_input(t("reply"), key=f"reply_input_{i}")
                    if st.form_submit_button("Send reply", key=f"reply_btn_{i}"):
                        feeds[i]["reply"] = r
                        save_feedback(feeds)
                        st.success("Reply saved.")
# -----------------------------
# app.py  — PART 3 (main_app + run)
# Paste after PART 1 and PART 2
# -----------------------------
# Main app layout and routing
def main_app():
    header_area()
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang_main")
        st.session_state.lang = lang

    user = st.session_state.get("user")
    role = st.session_state.get("role", "user")
    st.markdown(f"### 👋 {'Bonjour' if st.session_state.lang=='FR' else 'Hello'}, **{user}** !")

    # top buttons: Linearity / S/N horizontally
    cols2 = st.columns([1,1,1,1])
    with cols2[0]:
        if st.button(t("linearity"), key="btn_linearity"):
            st.session_state.page = "linearity"
    with cols2[1]:
        if st.button(t("sn"), key="btn_sn"):
            st.session_state.page = "sn"
    with cols2[2]:
        if st.button(t("admin"), key="btn_admin") and role == "admin":
            st.session_state.page = "admin"
    with cols2[3]:
        if st.button(t("logout"), key="btn_logout"):
            logout()
            return

    st.markdown("---")
    # route
    page = st.session_state.get("page", "linearity")
    if page == "linearity":
        if has_access("linearity"):
            linearity_panel()
        else:
            st.warning("Access denied to linearity.")
    elif page == "sn":
        if has_access("sn"):
            sn_panel_full()
        else:
            st.warning("Access denied to S/N.")
    elif page == "admin":
        if role == "admin":
            admin_panel()
        else:
            st.warning("Admin only.")
    elif page == "feedback":
        feedback_panel()
    else:
        st.info("Select a module above.")

# Entrypoint
def run_app():
    if st.session_state.get("user"):
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run_app()
# -------------------------
# End of PART 3