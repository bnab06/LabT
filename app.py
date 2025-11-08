# app.py
# LabT - full application (login/admin/linearity/SN/feedback)
# - BILINGUE FR/EN
# - Pas de sidebar
# - S/N : calcul sur IMAGE ORIGINALE (sélection zone bruit avec slider à 2 poignées)
# - Admin only manages users (no access to calculations)
# - Linearity left unchanged (original behavior preserved)
# Requirements: streamlit, pandas, numpy, matplotlib, pillow, fpdf, scipy
# Optional: pdf2image + poppler (for PDF -> PNG conversion), pytesseract (OCR best-effort)

import streamlit as st
import json
import os
import io
import tempfile
from datetime import datetime
from fpdf import FPDF
from PIL import Image, ImageDraw
import numpy as np

# optional
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# plotting
import matplotlib.pyplot as plt

# small signal helpers
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

# ---------- Page config ----------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

# ---------- Files / constants ----------
USERS_FILE = "users.json"
FEEDBACK_FILE = "feedback.json"
LOGO_FILE = "logo_labt.png"

# ---------- Translations ----------
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
        "no_users":"Aucun utilisateur configuré",
        "access_denied":"Accès refusé",
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
        "no_users":"No users configured",
        "access_denied":"Access denied",
    }
}

def t(key):
    lang = st.session_state.get("lang","FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(key, key)

# ---------- Session defaults ----------
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

# ---------- Users file helpers ----------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        default = {
            "admin": {"password": "admin", "role": "admin", "access": ["linearity","sn"]},
            "user": {"password": "user", "role": "user", "access": ["linearity","sn"]},
        }
        with open(USERS_FILE,"w",encoding="utf-8") as f:
            json.dump(default,f,indent=4,ensure_ascii=False)

def load_users():
    ensure_users_file()
    try:
        with open(USERS_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    with open(USERS_FILE,"w",encoding="utf-8") as f:
        json.dump(users,f,indent=4,ensure_ascii=False)

USERS = load_users()

def user_list():
    return list(USERS.keys()) if USERS else []

def find_user_key_case_insensitive(name):
    if name is None: return None
    for u in USERS.keys():
        if u.lower() == name.strip().lower():
            return u
    return None

# ---------- Feedback ----------
def load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE,"w",encoding="utf-8") as f:
            json.dump([],f,indent=2,ensure_ascii=False)
    try:
        with open(FEEDBACK_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_feedback(list_feedback):
    with open(FEEDBACK_FILE,"w",encoding="utf-8") as f:
        json.dump(list_feedback,f,indent=2,ensure_ascii=False)

# ---------- OCR helper (kept but optional) ----------
def extract_xy_from_image_pytesseract(img: Image.Image):
    """
    Try to extract numeric X,Y pairs from image text via pytesseract.
    Returns DataFrame-like list of tuples (x,y) or empty list.
    (This is best-effort and not used by the S/N image-based flow.)
    """
    if pytesseract is None:
        return []
    try:
        text = pytesseract.image_to_string(img)
    except Exception:
        return []
    rows = []
    for line in text.splitlines():
        if not line.strip(): continue
        # try separators
        for sep in [",",";", "\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip()!=""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",",".")); y = float(parts[1].replace(",","."))
                        rows.append((x,y)); break
                    except Exception:
                        pass
        else:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",",".")); y = float(parts[1].replace(",","."))
                    rows.append((x,y))
                except Exception:
                    pass
    return rows

# ---------- PDF -> PNG helper ----------
def pdf_to_pil_image(uploaded_file):
    """
    Convert uploaded PDF (file-like) to PIL image using pdf2image if available.
    Returns (PIL.Image or None, error_message or None)
    """
    if convert_from_bytes is None:
        return None, t("could_not_convert_pdf")
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1, dpi=200)
        return pages[0], None
    except Exception:
        return None, t("could_not_convert_pdf")

# ---------- PDF report generator ----------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=8, w=25)
            pdf.set_xy(40, 10)
        except Exception:
            pdf.set_xy(10,10)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,title,ln=1,align="C")
    pdf.ln(4)
    pdf.set_font("Arial","",11)
    for line in lines:
        pdf.multi_cell(0,7,line)
    if img_bytes is not None:
        try:
            if isinstance(img_bytes, io.BytesIO):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes.getvalue()); tmpname = tmpf.name
                pdf.ln(4); pdf.image(tmpname, x=20, w=170)
            elif isinstance(img_bytes, bytes):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes); tmpname = tmpf.name
                pdf.ln(4); pdf.image(tmpname, x=20, w=170)
            else:
                if isinstance(img_bytes, str) and os.path.exists(img_bytes):
                    pdf.ln(4); pdf.image(img_bytes, x=20, w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# ---------- Header ----------
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
                with open(LOGO_FILE,"wb") as f:
                    f.write(data)
                st.success("Logo saved")
            except Exception as e:
                st.warning(f"Logo save error: {e}")

# ---------- Login screen ----------
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
        st.error(t("no_users")); return

    # dropdown of users (not raw json)
    uname = st.selectbox(t("username"), users, key="login_user_select")
    pwd = st.text_input(t("password"), type="password", key="login_password")
    if st.button(t("login"), key="login_btn"):
        matched = find_user_key_case_insensitive(uname)
        if matched and USERS.get(matched, {}).get("password") == (pwd or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            st.session_state.page = "linearity"  # open linearity by default
            st.success(f"{t('login')} OK")
            return
        else:
            st.error(t("invalid"))

    st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

# ---------- Logout ----------
def logout():
    for k in ["user","role","page","linear_slope"]:
        if k in st.session_state:
            del st.session_state[k]
    st.session_state.page = "login"

# ---------- Admin panel ----------
def admin_panel():
    st.header(t("admin"))
    st.write("Gérer les utilisateurs et leurs droits (linéarité / S/N).")
    users = user_list()
    if not users:
        st.info(t("no_users")); return

    action = st.selectbox("Action", ["Modifier utilisateur","Ajouter utilisateur","Supprimer utilisateur"], key="admin_action")
    if action == "Modifier utilisateur":
        sel = st.selectbox("Sélectionner utilisateur", users, key="admin_modify_select")
        if sel:
            info = USERS.get(sel,{})
            with st.form(f"form_modify_{sel}"):
                st.write(f"Username: **{sel}**")
                new_pwd = st.text_input("Nouveau mot de passe (laisser vide pour conserver)", type="password", key=f"pwd_{sel}")
                new_role = st.selectbox("Role", ["user","admin"], index=0 if info.get("role","user")=="user" else 1, key=f"role_{sel}")
                acc_line = st.checkbox("Accès linéarité", value=("linearity" in info.get("access",[])), key=f"acc_lin_{sel}")
                acc_sn = st.checkbox("Accès S/N", value=("sn" in info.get("access",[])), key=f"acc_sn_{sel}")
                if st.form_submit_button("Enregistrer"):
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

    elif action == "Supprimer utilisateur":
        sel = st.selectbox("Sélectionner", users, key="admin_del_select")
        if st.button("Supprimer"):
            if sel.lower() == "admin":
                st.warning("Cannot delete admin")
            else:
                USERS.pop(sel, None)
                save_users(USERS)
                st.success(f"{sel} deleted")

# ---------- Access helper ----------
def has_access(module_name):
    # Admin should NOT automatically have calculation access.
    user = st.session_state.get("user")
    if not user:
        return False
    return module_name in USERS.get(user, {}).get("access", [])

# ---------- Linearity panel (kept original behaviour) ----------
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
                try:
                    df0 = __import__("pandas").read_csv(uploaded)
                except Exception:
                    uploaded.seek(0)
                    df0 = __import__("pandas").read_csv(uploaded, sep=';', engine='python')
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
        try:
            concs = [float(c.replace(",",".").strip()) for c in conc_input.split(",") if c.strip()!=""]
            sigs = [float(s.replace(",",".").strip()) for s in sig_input.split(",") if s.strip()!=""]
            if len(concs) != len(sigs):
                st.error("Number of concentrations and signals must match.")
            elif len(concs) < 2:
                st.warning("At least two pairs are required.")
            else:
                import pandas as pd
                df = pd.DataFrame({"Concentration":concs, "Signal":sigs})
        except Exception as e:
            if conc_input.strip() or sig_input.strip():
                st.error(f"Manual parse error: {e}")

    unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="lin_unit")

    if df is None:
        st.info("Please provide data (CSV or manual).")
        return

    import pandas as pd
    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"])
        df["Signal"] = pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Concentration and Signal must be numeric.")
        return

    if len(df) < 2:
        st.warning("At least 2 points are required.")
        return

    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred)**2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values))**2)
    r2 = float(1 - ss_res/ss_tot) if ss_tot != 0 else 0.0

    st.session_state.linear_slope = slope

    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.4f}")

    fig, ax = plt.subplots(figsize=(7,3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope*xs + intercept, color="black", label="Fit")
    ax.set_xlabel(f"{t('concentration')} ({unit})")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # automatic compute unknown
    calc_choice = st.radio("Calculate", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_calc_choice")
    val = st.number_input("Enter value", format="%.6f", key="lin_unknown", value=0.0)
    try:
        if calc_choice.startswith(t("signal")):
            if slope == 0:
                st.error("Slope is zero, cannot compute concentration.")
            else:
                conc = (float(val) - intercept) / slope
                st.success(f"Concentration = {conc:.6f} {unit}")
        else:
            sigp = slope * float(val) + intercept
            st.success(f"Signal = {sigp:.6f}")
    except Exception as e:
        st.error(f"Compute error: {e}")

    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Linearity:** \( y = slope \cdot X + intercept \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")

    if st.button(t("generate_pdf"), key="lin_pdf"):
        if not company or company.strip()=="":
            st.warning(t("company_missing"))
        else:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight"); buf.seek(0)
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

# ---------- S/N panel (image-based) ----------
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))

    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_uploader")
    manual_mode = st.checkbox(t("manual_sn"), value=False, key="sn_manual_toggle")

    # Manual mode (H,h)
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

    # CSV path (numerical X,Y)
    if name.endswith(".csv"):
        try:
            uploaded.seek(0)
            try:
                import pandas as pd
                df0 = pd.read_csv(uploaded)
            except Exception:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded, sep=";", engine="python")
            if df0.shape[1] < 2:
                st.error("CSV must contain at least two columns."); return
            cols_low = [c.lower() for c in df0.columns]
            if "time" in cols_low and "signal" in cols_low:
                df = df0.rename(columns={df0.columns[cols_low.index("time")]: "X",
                                         df0.columns[cols_low.index("signal")]: "Y"})
            else:
                df = df0.iloc[:, :2].copy(); df.columns = ["X","Y"]
            df["X"] = pd.to_numeric(df["X"], errors="coerce")
            df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
            # Use CSV numeric plot — no image overlay
            st.subheader("CSV chromatogram")
            st.line_chart(df.rename(columns={"X":"index"}).set_index("index")["Y"])
        except Exception as e:
            st.error(f"Could not read CSV: {e}"); return

    # Image path
    elif name.endswith((".png",".jpg",".jpeg")):
        try:
            uploaded.seek(0)
            pil_img = Image.open(uploaded).convert("RGB")
            orig_image = pil_img.copy()
            st.subheader("Original image")
            st.image(orig_image, use_column_width=True)
            # For the calculation we compute vertical projection (max per column)
            gray = orig_image.convert("L")
            arr = np.array(gray).astype(float)
            # If background is dark (mean < 127) invert so peaks are positive
            if arr.mean() < 127:
                arr = 255 - arr
            # vertical projection (max per column) -> signal (higher = peak)
            signal = arr.max(axis=0).astype(float)
            xvals = np.arange(len(signal))
            df = __import__("pandas").DataFrame({"X": xvals, "Y": signal})
        except Exception as e:
            st.error(f"Image error: {e}"); return

    # PDF path -> convert to image first
    elif name.endswith(".pdf"):
        pil_img, err = pdf_to_pil_image(uploaded)
        if pil_img is None:
            st.error(err); return
        orig_image = pil_img.convert("RGB")
        st.subheader("Original image (from PDF)")
        st.image(orig_image, use_column_width=True)
        gray = orig_image.convert("L")
        arr = np.array(gray).astype(float)
        if arr.mean() < 127:
            arr = 255 - arr
        signal = arr.max(axis=0).astype(float)
        xvals = np.arange(len(signal))
        df = __import__("pandas").DataFrame({"X": xvals, "Y": signal})

    else:
        st.error("Unsupported file type."); return

    # ensure numeric and sorted
    df = df.dropna().sort_values("X").reset_index(drop=True)
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    if x_min == x_max:
        st.warning("Signal plat ou OCR invalide : les valeurs X sont identiques. Utilisation d'un axe X artificiel.")
        df["X"] = np.arange(len(df)); x_min, x_max = 0.0, float(len(df)-1)

    # noise region selection (slider with 2 handles)
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
        region = df

    # peak detection controls
    st.subheader("Peak detection settings")
    threshold_factor = st.slider(t("threshold"), 0.0, 10.0, 3.0, step=0.1, key="sn_threshold_factor")
    min_distance = st.number_input(t("min_distance"), value=5, min_value=1, step=1, key="sn_min_distance")

    # main peak = global max on Y (independent of noise region)
    x_arr = df["X"].values; y_arr = df["Y"].values
    peak_idx = int(np.argmax(y_arr))
    peak_x = float(x_arr[peak_idx]); peak_y = float(y_arr[peak_idx])

    # baseline/noise from region
    noise_std = float(region["Y"].std(ddof=0)) if not region.empty else float(np.std(y_arr))
    baseline = float(region["Y"].mean()) if not region.empty else float(np.mean(y_arr))
    height = peak_y - baseline
    half_height = baseline + height / 2.0

    # FWHM approx
    left_idxs = np.where(y_arr[:peak_idx] <= half_height)[0]
    right_idxs = np.where(y_arr[peak_idx:] <= half_height)[0]
    W = np.nan
    try:
        if len(left_idxs) > 0:
            left_x = x_arr[left_idxs[-1]]; W = peak_x - left_x
        if len(right_idxs) > 0:
            right_x = x_arr[peak_idx + right_idxs[0]]
            W = (W if not np.isnan(W) else 0.0) + (right_x - peak_x)
    except Exception:
        W = np.nan

    noise_val = noise_std if noise_std != 0 else 1e-12
    sn_classic = peak_y / noise_val
    sn_usp = height / noise_val

    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
    st.write(f"Peak retention (X): {peak_x:.4f}")
    st.write(f"H (height): {height:.4f}, noise h (std): {noise_std:.4f}, W (approx FWHM): {W:.4f}")

    # slope for LOD/LOQ
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

    # prepare figure: display original image if present, otherwise plot computed signal (CSV)
    fig, ax = plt.subplots(figsize=(10,4))
    if orig_image is not None:
        # show image and overlay region + markers
        ax.imshow(orig_image)
        # map start/end (which are indices) to image pixel columns. Our projection used columns = X indexes, so map directly.
        ax.axvspan(start, end, alpha=0.25, color="yellow", label=t("noise_region"))
        # draw baseline & half height as horizontal lines in image-coordinates (but image Y axis is top->down)
        # Our projection signal values are positive upwards; to visualize baseline/half height on image,
        # we draw markers at the column location where projection equals those values:
        # find column index for main peak
        peak_col = int(peak_x)
        ax.plot([peak_col], [0], marker="o", color="red")  # a tiny marker at top to indicate column (visual aid)
        # mark peak column with a vertical line
        ax.axvline(peak_col, color="red", linestyle="--", linewidth=1)
        # Put a red dot at visually estimated peak location: find the row (pixel) of the maximum in that column
        col_arr = np.array(orig_image.convert("L"))[:, peak_col]
        # if inverted earlier in processing mean <127 then arr was inverted for calculation; but keep original image display
        peak_row = int(np.argmin(col_arr))  # darker -> lower value, but if image light background etc, use argmin as rough
        # safe bounds
        peak_row = max(0, min(peak_row, orig_image.size[1]-1))
        ax.plot([peak_col], [peak_row], marker="o", markersize=8, color="red", label="Main peak")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("Original image with overlays")
    else:
        # CSV case: show numerical chart with same X
        ax.plot(df["X"], df["Y"], color="black")
        ax.axvspan(start, end, alpha=0.25, color="yellow", label=t("noise_region"))
        ax.axhline(baseline, color="green", linestyle="--", label="Baseline")
        ax.axhline(half_height, color="orange", linestyle="--", label="Half height")
        ax.plot([peak_x],[peak_y], marker="o", markersize=8, color="red", label="Main peak")
        ax.set_xlabel("X"); ax.set_ylabel("Y")
        ax.legend()
    st.pyplot(fig)

    # detect peaks in region (optional)
    threshold_abs = baseline + threshold_factor * noise_std
    try:
        y_region = region["Y"].values
        peaks_idx_rel, props = find_peaks(y_region, height=threshold_abs, distance=int(min_distance))
        peaks_x = region["X"].values[peaks_idx_rel] if len(peaks_idx_rel) else np.array([])
        peaks_y = y_region[peaks_idx_rel] if len(peaks_idx_rel) else np.array([])
    except Exception:
        peaks_x = np.array([]); peaks_y = np.array([])

    st.write(f"Peaks detected in region: {len(peaks_x)}")
    if len(peaks_x):
        import pandas as pd
        st.dataframe(pd.DataFrame({"X": peaks_x, "Y": peaks_y}))

    # Export CSV of projection (or original df)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv", key="sn_csv_dl")

    # Export processed image: create a PNG combining original + overlays (PIL)
    try:
        if orig_image is not None:
            pil_out = orig_image.copy()
            draw = ImageDraw.Draw(pil_out, "RGBA")
            # draw semi-transparent rectangle for noise region
            w = pil_out.width; h = pil_out.height
            # compute rectangle in pixels: slider values correspond to column indices (X)
            x0 = int(start); x1 = int(end)
            x0 = max(0, min(x0, w-1)); x1 = max(0, min(x1, w-1))
            draw.rectangle([x0, 0, x1, h], fill=(255,255,0,60))
            # draw vertical line at peak column
            peak_col = int(peak_x)
            draw.line([(peak_col,0),(peak_col,h)], fill=(255,0,0,180), width=2)
            # draw red circle at peak row
            try:
                col_arr = np.array(orig_image.convert("L"))[:, peak_col]
                peak_row = int(np.argmin(col_arr))
                draw.ellipse([peak_col-6, peak_row-6, peak_col+6, peak_row+6], fill=(255,0,0,255))
            except Exception:
                pass
            # save to buffer
            out_buf = io.BytesIO()
            pil_out.save(out_buf, format="PNG"); out_buf.seek(0)
            st.download_button(t("download_image"), out_buf.getvalue(), file_name="sn_processed.png", mime="image/png", key="sn_img_dl")
        else:
            # create figure PNG
            buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); buf.seek(0)
            st.download_button(t("download_image"), buf.getvalue(), file_name="sn_processed.png", mime="image/png", key="sn_img_dl2")
    except Exception:
        pass

    # export PDF report with embedded processed image
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
        # embed the PNG created above if present
        try:
            if orig_image is not None:
                # reuse pil_out buffer
                pdf_buf = io.BytesIO()
                pil_out.save(pdf_buf, format="PNG"); pdf_buf.seek(0)
                pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=pdf_buf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
            else:
                buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); buf.seek(0)
                pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=buf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
            st.download_button(t("download_pdf"), pdfb, file_name="sn_report.pdf", mime="application/pdf", key="sn_pdf_dl")
        except Exception:
            st.error("PDF export failed.")

    # formulas expander
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
        **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

# ---------- Feedback ----------
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

# ---------- Main app ----------
def main_app():
    header_area()
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang_main")
        st.session_state.lang = lang

    user = st.session_state.get("user"); role = st.session_state.get("role","user")
    st.markdown(f"### 👋 {'Bonjour' if st.session_state.lang=='FR' else 'Hello'}, **{user}** !")

    # top tabs (as horizontal buttons)
    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1:
        if st.button(t("linearity"), key="btn_linearity"):
            st.session_state.page = "linearity"
    with c2:
        if st.button(t("sn"), key="btn_sn"):
            st.session_state.page = "sn"
    with c3:
        # show admin only if user role = admin
        if role == "admin":
            if st.button(t("admin"), key="btn_admin"):
                st.session_state.page = "admin"
    with c4:
        if st.button(t("logout"), key="btn_logout"):
            logout(); return

    st.markdown("---")
    page = st.session_state.get("page","linearity")
    if page == "linearity":
        if has_access("linearity"):
            linearity_panel()
        else:
            st.warning(t("access_denied"))
    elif page == "sn":
        if has_access("sn"):
            sn_panel_full()
        else:
            st.warning(t("access_denied"))
    elif page == "admin":
        if st.session_state.get("role") == "admin":
            admin_panel()
        else:
            st.warning("Admin only.")
    elif page == "feedback":
        feedback_panel()
    else:
        st.info("Select a module above.")

# ---------- Entrypoint ----------
def run_app():
    if st.session_state.get("user"):
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run_app()