# app.py — LabT (complete)
# Requirements (example): streamlit, pandas, numpy, matplotlib, pillow, fpdf, pdf2image (optional), pytesseract (optional), scipy
# Configure EMAIL_* below for Gmail notifications if tu veux activer l'envoi d'emails.

import streamlit as st
import json, os, io, tempfile, smtplib
from datetime import datetime
from email.message import EmailMessage
from fpdf import FPDF
from PIL import Image, ImageOps, ImageDraw
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Optional best-effort imports
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

# -----------------------
# CONFIG: Email / SMTP (Gmail)
# Fill these fields before using email features.
# For Gmail you may need an app password (recommended).
EMAIL_ENABLED = False  # set True to enable sending
EMAIL_SMTP = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "your.email@gmail.com"
EMAIL_PASSWORD = "your_app_password"  # use app password, don't commit real creds

# Files
USERS_FILE = "users.json"
FEEDBACK_FILE = "feedback.json"
LOGO_FILE = "logo_labt.png"

# Streamlit page
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

# -----------------------
# Translations
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
        "retention_time":"Temps de rétention"
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
        "retention_time":"Retention time"
    }
}
def t(k):
    lang = st.session_state.get("lang","FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(k, k)

# -----------------------
# Session defaults
if "lang" not in st.session_state: st.session_state.lang = "FR"
if "user" not in st.session_state: st.session_state.user = None
if "role" not in st.session_state: st.session_state.role = None
if "page" not in st.session_state: st.session_state.page = "login"
if "linear_slope" not in st.session_state: st.session_state.linear_slope = None

# -----------------------
# Storage helpers (users + feedback)
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        default = {
            "admin": {"password":"admin","role":"admin","access":["linearity","sn"]},
            "user": {"password":"user","role":"user","access":["linearity","sn"]}
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

def load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE,"w",encoding="utf-8") as f:
            json.dump([],f,indent=2,ensure_ascii=False)
    try:
        with open(FEEDBACK_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_feedback(feeds):
    with open(FEEDBACK_FILE,"w",encoding="utf-8") as f:
        json.dump(feeds,f,indent=2,ensure_ascii=False)

USERS = load_users()

def user_list():
    return list(USERS.keys()) if USERS else []

def find_user_key_case_insensitive(name):
    if name is None: return None
    for u in USERS:
        if u.lower() == str(name).strip().lower():
            return u
    return None

# -----------------------
# Email helper
def send_email(subject, body, to_addrs):
    if not EMAIL_ENABLED:
        return False, "Email disabled in config"
    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_USER
        msg["To"] = to_addrs if isinstance(to_addrs,str) else ", ".join(to_addrs)
        msg["Subject"] = subject
        msg.set_content(body)
        server = smtplib.SMTP(EMAIL_SMTP, EMAIL_PORT, timeout=30)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "OK"
    except Exception as e:
        return False, str(e)

# -----------------------
# PDF -> PNG helper
def pdf_to_pil_firstpage(uploaded_file):
    if convert_from_bytes is None:
        return None, t("could_not_convert_pdf")
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1, dpi=200)
        return pages[0], None
    except Exception as e:
        return None, t("could_not_convert_pdf")

# -----------------------
# OCR fallback extractor (if user wants to OCR numbers)
def extract_xy_from_image_pytesseract(pil_img):
    """
    Try to extract X,Y numeric pairs using pytesseract. Returns DataFrame or empty DF.
    Best-effort — but we will NOT rely on OCR for S/N calculations (we compute on image pixels).
    """
    if pytesseract is None:
        return pd.DataFrame(columns=["X","Y"])
    try:
        txt = pytesseract.image_to_string(pil_img)
    except Exception:
        return pd.DataFrame(columns=["X","Y"])
    rows = []
    for line in txt.splitlines():
        if not line.strip(): continue
        # try typical separators
        for sep in [",",";","\t"," "]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip()!=""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",",".")); y = float(parts[1].replace(",","."))
                        rows.append([x,y])
                        break
                    except Exception:
                        pass
    if rows:
        return pd.DataFrame(rows,columns=["X","Y"]).sort_values("X").reset_index(drop=True)
    return pd.DataFrame(columns=["X","Y"])

# -----------------------
# PDF report writer
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=8, w=25)
            pdf.set_xy(40,10)
        except Exception:
            pass
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,title,ln=1,align="C")
    pdf.ln(4)
    pdf.set_font("Arial","",11)
    for line in lines:
        pdf.multi_cell(0,7,line)
    if img_bytes:
        try:
            if isinstance(img_bytes, io.BytesIO):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes.getvalue()); tmpn = tmpf.name
                pdf.ln(4); pdf.image(tmpn,x=20,w=170)
            elif isinstance(img_bytes, bytes):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
                    tmpf.write(img_bytes); tmpn = tmpf.name
                pdf.ln(4); pdf.image(tmpn,x=20,w=170)
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# -----------------------
# Header area
def header_area():
    cols = st.columns([3,1])
    with cols[0]:
        st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    with cols[1]:
        upl = st.file_uploader(t("upload_logo"), type=["png","jpg","jpeg"], key="logo_box")
        if upl is not None:
            try:
                with open(LOGO_FILE,"wb") as f:
                    f.write(upl.read())
                st.success("Logo saved")
            except Exception as e:
                st.warning(f"Logo save error: {e}")

# -----------------------
# LOGIN screen (bilingual, dropdown of users)
def login_screen():
    header_area()
    cols = st.columns([2,1])
    with cols[1]:
        lang = st.selectbox("",["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="login_lang")
        st.session_state.lang = lang
    st.markdown("### 🔐 " + t("login"))
    users = user_list()
    if not users:
        st.error(t("no_users"))
        return
    uname = st.selectbox(t("username"), users, key="login_user")
    pwd = st.text_input(t("password"), type="password", key="login_pwd")
    if st.button(t("login")):
        matched = find_user_key_case_insensitive(uname)
        if matched and USERS.get(matched,{}).get("password") == (pwd or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            st.session_state.page = "linearity"  # open default
            st.success(f"{t('login')} OK")
            # optional email notify
            if EMAIL_ENABLED:
                send_email("LabT login", f"User {matched} logged in at {datetime.now().isoformat()}", EMAIL_USER)
            return
        else:
            st.error(t("invalid"))
    st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

# -----------------------
# Logout
def logout():
    for k in ["user","role","page","linear_slope"]:
        if k in st.session_state: del st.session_state[k]
    st.session_state.page = "login"

# -----------------------
# Admin panel (single select action UI)
def admin_panel():
    st.header(t("admin"))
    st.write("Gérer utilisateurs & privilèges (linéarité / S/N). Admin n'a pas accès aux calculs.")
    users = user_list()
    if not users:
        st.info(t("no_users"))
        return
    action = st.selectbox("Action", ["Afficher utilisateur","Modifier utilisateur","Ajouter utilisateur","Supprimer utilisateur"])
    if action == "Afficher utilisateur":
        sel = st.selectbox("Sélectionner utilisateur", users, key="admin_view")
        if sel:
            info = USERS.get(sel,{})
            st.json({sel: info})
    elif action == "Modifier utilisateur":
        sel = st.selectbox("Sélectionner utilisateur", users, key="admin_modify")
        if sel:
            info = USERS.get(sel,{})
            with st.form("modify_form"):
                new_pwd = st.text_input("Nouveau mot de passe (laisser vide pour conserver)", type="password")
                new_role = st.selectbox("Role", ["user","admin"], index=0 if info.get("role","user")=="user" else 1)
                acc_line = st.checkbox("Accès linéarité", value=("linearity" in info.get("access",[])))
                acc_sn = st.checkbox("Accès S/N", value=("sn" in info.get("access",[])))
                save = st.form_submit_button("Enregistrer")
                if save:
                    if new_pwd: USERS[sel]["password"]=new_pwd
                    USERS[sel]["role"]=new_role
                    new_access=[]
                    if acc_line: new_access.append("linearity")
                    if acc_sn: new_access.append("sn")
                    USERS[sel]["access"]=new_access
                    save_users(USERS)
                    st.success("Modifications enregistrées")
    elif action == "Ajouter utilisateur":
        with st.form("add_form"):
            new_user = st.text_input("Nom d'utilisateur")
            new_pass = st.text_input("Mot de passe", type="password")
            role = st.selectbox("Role", ["user","admin"])
            acc_line = st.checkbox("Accès linéarité", value=True)
            acc_sn = st.checkbox("Accès S/N", value=True)
            add = st.form_submit_button("Ajouter")
            if add:
                if not new_user.strip() or not new_pass.strip():
                    st.warning("Utilisateur et mot de passe requis")
                elif find_user_key_case_insensitive(new_user) is not None:
                    st.warning("Utilisateur existe")
                else:
                    access=[]
                    if acc_line: access.append("linearity")
                    if acc_sn: access.append("sn")
                    USERS[new_user.strip()] = {"password":new_pass.strip(),"role":role,"access":access}
                    save_users(USERS)
                    st.success("Utilisateur ajouté")
                    if EMAIL_ENABLED:
                        send_email("LabT user added", f"User {new_user} added by {st.session_state.get('user')}", EMAIL_USER)
    elif action == "Supprimer utilisateur":
        sel = st.selectbox("Sélectionner", users, key="admin_del")
        if st.button("Supprimer"):
            if sel.lower() == "admin":
                st.warning("Impossible de supprimer admin principal")
            else:
                USERS.pop(sel,None)
                save_users(USERS)
                st.success("Utilisateur supprimé")
                if EMAIL_ENABLED:
                    send_email("LabT user removed", f"User {sel} removed by {st.session_state.get('user')}", EMAIL_USER)

# -----------------------
# Small access helper
def has_access(module_name):
    if st.session_state.get("role") == "admin":
        return False  # admin should NOT have access to calculation modules per spec
    user = st.session_state.get("user")
    if not user: return False
    return module_name in USERS.get(user,{}).get("access",[])

# -----------------------
# Linearity module (unchanged logic, plus unit dropdown and export)
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name")
    mode = st.radio("Input mode",[t("input_csv"), t("input_manual")], key="lin_input_mode")
    df = None

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
                    df = df0.iloc[:,:2].copy()
                    df.columns = ["Concentration","Signal"]
                else:
                    st.error("CSV must contain at least two columns")
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
            concs = [float(c.replace(",",".")) for c in conc_input.split(",") if c.strip()!=""]
            sigs = [float(s.replace(",",".")) for s in sig_input.split(",") if s.strip()!=""]
            if len(concs) != len(sigs):
                st.error("Number of concentrations and signals must match")
            elif len(concs) < 2:
                st.warning("At least two pairs required")
            else:
                df = pd.DataFrame({"Concentration":concs,"Signal":sigs})
        except Exception as e:
            if conc_input.strip() or sig_input.strip():
                st.error(f"Manual parse error: {e}")

    unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="lin_unit")

    if df is None:
        st.info("Please provide data")
        return

    try:
        df["Concentration"]=pd.to_numeric(df["Concentration"])
        df["Signal"]=pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Concentration/Signal must be numeric")
        return

    if len(df) < 2:
        st.warning("At least 2 points required")
        return

    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0]); intercept = float(coeffs[1])
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
    ax.plot(xs, slope*xs + intercept, color="black", label="Fit")  # solid
    ax.set_xlabel(f"{t('concentration')} ({unit})"); ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # automatic compute unknown (both ways) without extra button
    calc_choice = st.radio("Calculate", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_calc_choice")
    val = st.number_input("Enter value", format="%.6f", key="lin_unknown", value=0.0)
    try:
        if calc_choice.startswith(t("signal")):
            if slope == 0:
                st.error("Slope is zero")
            else:
                conc = (float(val) - intercept)/slope
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

    csv_buf = io.StringIO(); df.to_csv(csv_buf,index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")
    if st.button(t("generate_pdf")):
        if not company or company.strip()=="":
            st.warning(t("company_missing"))
        else:
            buf = io.BytesIO(); fig.savefig(buf,format="png",bbox_inches="tight"); buf.seek(0)
            lines = [
                f"Company: {company or 'N/A'}",
                f"User: {st.session_state.user or 'Unknown'}",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Slope: {slope:.6f}",
                f"Intercept: {intercept:.6f}",
                f"R²: {r2:.6f}"
            ]
            pdfb = generate_pdf_bytes("Linearity report", lines, img_bytes=buf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
            st.download_button(t("download_pdf"), pdfb, file_name="linearity_report.pdf", mime="application/pdf")

# -----------------------
# S/N panel: operate ON ORIGINAL IMAGE (no re-draw)
# - compute vertical projection from image pixels
# - preserve original colors for display; overlay markers on top
def sn_panel():
    st.header(t("sn"))
    st.write(t("digitize_info"))
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_upload")
    manual_mode = st.checkbox(t("manual_sn"), value=False)

    if manual_mode:
        st.subheader(t("manual_sn"))
        H = st.number_input("H (peak height)", value=0.0, format="%.6f")
        h = st.number_input("h (noise)", value=0.0, format="%.6f")
        slope_src = st.radio("Slope source", ("From linearity","Manual input"))
        if slope_src == "From linearity":
            slope_val = st.session_state.get("linear_slope", None)
            if slope_val is None:
                st.warning("No slope from linearity. Enter manual.")
                slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="manual_slope_enter")
        else:
            slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="manual_slope")
        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2*H / h if h != 0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        if slope_val and slope_val != 0:
            unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"])
            lod = 3.3 * h / slope_val; loq = 10 * h / slope_val
            st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
            st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
        return

    if uploaded is None:
        st.info("Upload a chromatogram (image or CSV) or use manual mode")
        return

    name = uploaded.name.lower()
    orig_img = None
    df = None

    # CSV handling (numerical)
    if name.endswith(".csv"):
        try:
            uploaded.seek(0)
            try:
                df0 = pd.read_csv(uploaded)
            except Exception:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded, sep=";", engine="python")
            if df0.shape[1] < 2:
                st.error("CSV must have at least 2 columns (time, signal)")
                return
            cols_low = [c.lower() for c in df0.columns]
            if "time" in cols_low and "signal" in cols_low:
                df = df0.rename(columns={df0.columns[cols_low.index("time")]:"X", df0.columns[cols_low.index("signal")]:"Y"})
            else:
                df = df0.iloc[:,:2].copy(); df.columns = ["X","Y"]
            df["X"] = pd.to_numeric(df["X"],errors="coerce")
            df["Y"] = pd.to_numeric(df["Y"],errors="coerce")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            return

    # Image handling: preserve original image, compute vertical projection
    elif name.endswith((".png",".jpg",".jpeg")):
        try:
            uploaded.seek(0)
            pil = Image.open(uploaded).convert("RGB")
            orig_img = pil.copy()
            st.subheader("Original image")
            st.image(orig_img, use_column_width=True)
            # compute vertical projection (max intensity per column on grayscale)
            gray = orig_img.convert("L")
            arr = np.array(gray).astype(float)
            # we want peaks up -> if image has dark peaks on light bg, invert appropriately
            # Determine whether peaks are dark or bright by checking which side has higher variance
            left_mean = arr.mean()
            # compute column-wise max (to represent peak height)
            signal = arr.max(axis=0).astype(float)
            # smoothing to reduce pixel noise
            signal_smooth = gaussian_filter1d(signal, sigma=1)
            # X axis = pixel column indices
            df = pd.DataFrame({"X": np.arange(len(signal_smooth)), "Y": signal_smooth})
        except Exception as e:
            st.error(f"Image error: {e}")
            return

    # PDF handling -> convert to image
    elif name.endswith(".pdf"):
        pil_img, err = pdf_to_pil_firstpage(uploaded)
        if pil_img is None:
            st.error(err); return
        orig_img = pil_img.convert("RGB")
        st.subheader("Original image (from PDF)")
        st.image(orig_img, use_column_width=True)
        gray = orig_img.convert("L"); arr = np.array(gray).astype(float)
        signal = arr.max(axis=0).astype(float)
        signal_smooth = gaussian_filter1d(signal, sigma=1)
        df = pd.DataFrame({"X": np.arange(len(signal_smooth)), "Y": signal_smooth})
    else:
        st.error("Unsupported file type"); return

    if df is None or df.empty:
        st.error("No valid signal detected"); return

    # Ensure sorted numeric
    df = df.dropna().sort_values("X").reset_index(drop=True)
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    if x_min == x_max:
        df["X"] = np.arange(len(df)); x_min, x_max = 0.0, float(len(df)-1)
        st.warning("Signal plat ou OCR invalide : axe X artificiel utilisé.")

    # Region selection (two handles)
    st.subheader(t("noise_region"))
    default_start = x_min + 0.25*(x_max-x_min)
    default_end = x_min + 0.75*(x_max-x_min)
    try:
        start, end = st.slider(t("select_region"),
                               min_value=float(x_min),
                               max_value=float(x_max),
                               value=(float(default_start), float(default_end)),
                               key="sn_slider")
    except Exception as e:
        st.warning(f"Slider error: {e}")
        start, end = float(x_min), float(x_max)

    region = df[(df["X"]>=start) & (df["X"]<=end)].copy()
    if region.shape[0] < 2:
        st.warning("Région trop petite pour estimer le bruit — utilisation du signal complet pour bruit.")
        region = df

    # Peak detection controls
    st.subheader("Peak detection")
    threshold_factor = st.slider(t("threshold"), min_value=0.0, max_value=10.0, value=3.0, step=0.1, key="sn_thresh")
    min_distance = st.number_input(t("min_distance"), value=5, min_value=1, step=1, key="sn_min_dist")

    # Main peak = global max Y (user requested)
    x_arr = df["X"].values; y_arr = df["Y"].values
    peak_idx = int(np.argmax(y_arr))
    peak_x = float(x_arr[peak_idx]); peak_y = float(y_arr[peak_idx])

    # noise & baseline from selected region
    noise_std = float(region["Y"].std(ddof=0)) if not region.empty else float(np.std(y_arr))
    baseline = float(region["Y"].mean()) if not region.empty else float(np.mean(y_arr))
    height = peak_y - baseline

    # FWHM approximate
    half_h = baseline + height/2.0
    left_idxs = np.where(y_arr[:peak_idx] <= half_h)[0]
    right_idxs = np.where(y_arr[peak_idx:] <= half_h)[0]
    W = np.nan
    try:
        if len(left_idxs)>0:
            left_x = x_arr[left_idxs[-1]]; W = peak_x - left_x
        if len(right_idxs)>0:
            right_x = x_arr[peak_idx + right_idxs[0]]
            W = (W if not np.isnan(W) else 0.0) + (right_x - peak_x)
    except Exception:
        W = np.nan

    # Compute S/N
    noise_val = noise_std if noise_std != 0 else 1e-12
    sn_classic = peak_y / noise_val
    sn_usp = height / noise_val

    # Show numeric results (with retention time as X in pixel units)
    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
    st.write(f"{t('retention_time')}: {peak_x:.4f} (pixel index)")
    st.write(f"H: {height:.4f}, noise h (std): {noise_std:.4f}, W (approx FWHM): {W if not np.isnan(W) else 'NaN'}")

    # slope source for LOD/LOQ
    st.write("Slope used for LOD/LOQ:")
    slope_choice = st.radio("Slope source", ("From linearity","Manual input"), key="sn_slope_choice")
    if slope_choice == "From linearity":
        slope_val = st.session_state.get("linear_slope", None)
        if slope_val is None:
            st.warning("No slope in linearity. Enter manual below.")
            slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="sn_slope_missing")
    else:
        slope_val = st.number_input("Slope (manual)", value=0.0, format="%.6f", key="sn_slope_manual2")

    if slope_val and slope_val != 0:
        unit_choice = st.selectbox(t("unit_choice"), ["µg/mL","mg/mL","ng/mL"], key="sn_unit")
        lod = 3.3 * noise_std / slope_val; loq = 10 * noise_std / slope_val
        st.write(f"{t('lod')} ({unit_choice}): {lod:.6f}")
        st.write(f"{t('loq')} ({unit_choice}): {loq:.6f}")
    else:
        st.info("Slope not provided → LOD/LOQ in concentration cannot be computed.")

    # Detect peaks in region using threshold and min_distance
    threshold_abs = baseline + threshold_factor * noise_std
    try:
        y_region = region["Y"].values
        peaks_idx, props = find_peaks(y_region, height=threshold_abs, distance=int(min_distance))
        peaks_x = region["X"].values[peaks_idx] if len(peaks_idx) else np.array([])
        peaks_y = y_region[peaks_idx] if len(peaks_idx) else np.array([])
    except Exception:
        peaks_x = np.array([]); peaks_y = np.array([])

    st.write(f"Peaks detected in region: {len(peaks_x)}")
    if len(peaks_x):
        st.dataframe(pd.DataFrame({"X": peaks_x, "Y": peaks_y}))

    # Overlay markers on ORIGINAL image (if available) and allow download of processed image
    if orig_img is not None:
        # Create an annotated copy
        ann = orig_img.convert("RGBA")
        draw = ImageDraw.Draw(ann)
        # Map signal x (pixel column) to image width (already in pixel units)
        # Draw vertical span for noise region
        w_img, h_img = ann.size
        # Determine scale: df.X in [0 .. ncols-1] maps to [0 .. w_img-1]
        ncols = int(df["X"].max())+1 if df["X"].max()>=0 else len(df)
        # compute mapping function
        def map_x(xval):
            return int((xval - df["X"].min())/(df["X"].max()-df["X"].min())*(w_img-1)) if df["X"].max() != df["X"].min() else int(w_img/2)
        # draw semi-transparent rectangle for noise region
        x1 = map_x(start); x2 = map_x(end)
        draw.rectangle([x1,0,x2,h_img], fill=(100,100,100,64))
        # draw baseline and half-height as horizontal lines at approximate y positions on image:
        # Map Y (signal) to vertical pixel: we computed signal as brightness (0..255). For mapping:
        y_min = float(np.min(df["Y"])); y_max = float(np.max(df["Y"]))
        def map_y(yval):
            # bigger signal -> higher pixel (towards top) because image axis origin top-left
            # We want peak top near top -> invert mapping so bigger y -> smaller pixel index
            if y_max == y_min: return int(h_img/2)
            return int((1.0 - (yval - y_min)/(y_max - y_min))*(h_img-1))
        y_baseline_px = map_y(baseline)
        y_half_px = map_y(half_h)
        draw.line([(0,y_baseline_px),(w_img,y_baseline_px)], fill=(0,255,0,200), width=2)
        draw.line([(0,y_half_px),(w_img,y_half_px)], fill=(255,165,0,200), width=2)
        # draw main peak point (red)
        peak_px_x = map_x(peak_x); peak_px_y = map_y(peak_y)
        r = 6
        draw.ellipse([(peak_px_x-r, peak_px_y-r),(peak_px_x+r, peak_px_y+r)], fill=(255,0,0,255))
        # convert for display
        st.subheader("Annotated (computed) image")
        st.image(ann, use_column_width=True)

        # Save processed image to buffer and offer download
        proc_buf = io.BytesIO()
        ann.save(proc_buf, format="PNG")
        proc_buf.seek(0)
        st.download_button(t("download_image"), proc_buf.getvalue(), file_name="sn_annotated.png", mime="image/png")

    # export CSV of projection
    csvbuf = io.StringIO(); df.to_csv(csvbuf,index=False)
    st.download_button(t("download_csv"), csvbuf.getvalue(), file_name="sn_projection.csv", mime="text/csv")

    # Export PDF report
    if st.button(t("export_sn_pdf")):
        lines = [
            f"File: {uploaded.name}",
            f"User: {st.session_state.get('user','Unknown')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{t('sn_classic')}: {sn_classic:.4f}",
            f"{t('sn_usp')}: {sn_usp:.4f}",
            f"{t('retention_time')}: {peak_x:.4f}",
            f"H: {height:.4f}, noise: {noise_std:.4f}, W: {W if not np.isnan(W) else 'NaN'}"
        ]
        # attach annotated image if present
        img_buf = io.BytesIO()
        if orig_img is not None:
            if 'proc_buf' in locals():
                img_buf = proc_buf
            else:
                tmp = io.BytesIO(); ann.save(tmp, format="PNG"); tmp.seek(0); img_buf = tmp
        pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=img_buf, logo_path=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
        st.download_button(t("download_pdf"), pdfb, file_name="sn_report.pdf", mime="application/pdf")

    # formulas expander
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
        **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

# -----------------------
# Feedback panel
def feedback_panel():
    st.header("Feedback & support")
    st.write("Envoyez vos commentaires. L'admin peut lire/répondre.")
    with st.form("fb_form", clear_on_submit=True):
        name = st.text_input("Votre nom (optionnel)", value=st.session_state.get("user",""))
        msg = st.text_area("Message", height=120)
        sub = st.form_submit_button(t("upload_feedback"))
        if sub:
            if not msg.strip():
                st.warning("Message vide")
            else:
                feeds = load_feedback()
                feeds.append({"sender": name or st.session_state.get("user","anonymous"),
                              "message": msg, "time": datetime.now().isoformat(), "reply": ""})
                save_feedback(feeds)
                st.success("Feedback envoyé")
                if EMAIL_ENABLED:
                    send_email("New LabT feedback", f"From {name}\n\n{msg}", EMAIL_USER)
    # Admin view
    if st.session_state.get("role") == "admin":
        st.markdown("---")
        st.subheader(t("view_feedback"))
        feeds = load_feedback()
        if not feeds:
            st.info("No feedback yet.")
        else:
            for i,f in enumerate(feeds):
                st.write(f"**{f['sender']}** ({f['time']})")
                st.write(f"{f['message']}")
                if f.get("reply"):
                    st.info(f"Reply: {f['reply']}")
                with st.form(f"reply_form_{i}", clear_on_submit=False):
                    r = st.text_input(t("reply"), key=f"reply_input_{i}")
                    if st.form_submit_button("Send reply"):
                        feeds[i]["reply"] = r
                        save_feedback(feeds)
                        st.success("Reply saved")
                        if EMAIL_ENABLED:
                            send_email("Feedback replied", f"Reply to {f['sender']}:\n\n{r}", EMAIL_USER)

# -----------------------
# Main app (horizontal menu)
def main_app():
    header_area()
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("",["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang")
        st.session_state.lang = lang
    user = st.session_state.get("user")
    role = st.session_state.get("role","user")
    st.markdown(f"### 👋 {'Bonjour' if st.session_state.lang=='FR' else 'Hello'}, **{user}** !")

    # top horizontal selection as requested (dropdown version requested earlier — you asked horizontal; using selectbox for compactness)
    choice = st.selectbox("Module", [t("linearity"), t("sn"), t("admin"), "Feedback", t("logout")], key="top_choice")
    if choice == t("linearity"):
        if has_access("linearity"): linearity_panel()
        else: st.warning("Access denied to linearity.")
    elif choice == t("sn"):
        if has_access("sn"): sn_panel()
        else: st.warning("Access denied to S/N.")
    elif choice == "Feedback":
        feedback_panel()
    elif choice == t("admin"):
        if role == "admin": admin_panel()
        else: st.warning("Admin only")
    elif choice == t("logout"):
        logout(); st.success("Logged out"); st.experimental_rerun()

# -----------------------
# Entrypoint
def run():
    if st.session_state.get("user"):
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run()