# ---------------- Part 1: imports & helpers ----------------
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
import io, os, json, tempfile
from datetime import datetime

# Optional third-party features
try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except Exception:
    convert_from_bytes = None
    HAS_PDF2IMAGE = False

try:
    import pytesseract
    HAS_TESSERACT = True
except Exception:
    pytesseract = None
    HAS_TESSERACT = False

# PDF writer fallback (FPDF may raise ImportError in some envs)
try:
    from fpdf import FPDF
    HAS_FPDF = True
except Exception:
    FPDF = None
    HAS_FPDF = False

# App config
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
FEEDBACK_FILE = "feedback.json"
LOGO_FILE = "logo_labt.png"

# --- translations dictionary (FR/EN) ---
TEXTS = {
    "FR": {
        "app_title": "LabT",
        "powered": "Powered by BnB",
        "username": "Utilisateur",
        "password": "Mot de passe",
        "login": "Connexion",
        "logout": "Déconnexion",
        "invalid": "Identifiants invalides",
        "linearity": "Linéarité",
        "sn": "S/N",
        "admin": "Admin",
        "company": "Nom de la compagnie",
        "input_csv": "CSV",
        "input_manual": "Saisie manuelle",
        "concentration": "Concentration",
        "signal": "Signal",
        "unit": "Unité",
        "generate_pdf": "Générer PDF",
        "download_pdf": "Télécharger PDF",
        "download_csv": "Télécharger CSV",
        "sn_classic": "S/N Classique",
        "sn_usp": "S/N USP",
        "lod": "LOD (conc.)",
        "loq": "LOQ (conc.)",
        "formulas": "Formules",
        "select_region": "Sélectionner la zone (bruit)",
        "add_user": "Ajouter utilisateur",
        "enter_username": "Nom d'utilisateur",
        "enter_password": "Mot de passe (simple)",
        "upload_chrom": "Importer chromatogramme (CSV, PNG, JPG, PDF)",
        "digitize_info": "Digitizing : OCR tenté si pytesseract disponible (best-effort). Si PDF et poppler manquant, téléverse PNG.",
        "export_sn_pdf": "Exporter S/N PDF",
        "download_original_pdf": "Télécharger PDF original",
        "change_pwd": "Changer mot de passe (hors session)",
        "compute": "Compute",
        "company_missing": "Veuillez saisir le nom de la compagnie avant de générer le rapport.",
        "upload_logo": "Uploader un logo (optionnel)",
        "manual_sn": "Calcul manuel S/N",
        "noise_region_small": "Région trop petite pour estimer le bruit — utilisation d'une estimation globale.",
        "image_process_failed": "Image processing failed: convert PDF to PNG or install poppler.",
        "download_processed_image": "Télécharger image traitée"
    },
    "EN": {
        "app_title": "LabT",
        "powered": "Powered by BnB",
        "username": "Username",
        "password": "Password",
        "login": "Login",
        "logout": "Logout",
        "invalid": "Invalid credentials",
        "linearity": "Linearity",
        "sn": "S/N",
        "admin": "Admin",
        "company": "Company name",
        "input_csv": "CSV",
        "input_manual": "Manual input",
        "concentration": "Concentration",
        "signal": "Signal",
        "unit": "Unit",
        "generate_pdf": "Generate PDF",
        "download_pdf": "Download PDF",
        "download_csv": "Download CSV",
        "sn_classic": "S/N Classic",
        "sn_usp": "S/N USP",
        "lod": "LOD (conc.)",
        "loq": "LOQ (conc.)",
        "formulas": "Formulas",
        "select_region": "Select region (noise)",
        "add_user": "Add user",
        "enter_username": "Username",
        "enter_password": "Password (simple)",
        "upload_chrom": "Upload chromatogram (CSV, PNG, JPG, PDF)",
        "digitize_info": "Digitizing: OCR attempted if pytesseract available (best-effort). If PDF and poppler missing, upload PNG.",
        "export_sn_pdf": "Export S/N PDF",
        "download_original_pdf": "Download original PDF",
        "change_pwd": "Change password (outside session)",
        "compute": "Compute",
        "company_missing": "Please enter company name before generating the report.",
        "upload_logo": "Upload logo (optional)",
        "manual_sn": "Manual S/N calculation",
        "noise_region_small": "Selected region too small to estimate noise — using global estimate.",
        "image_process_failed": "Image processing failed: convert PDF to PNG or install poppler.",
        "download_processed_image": "Download processed image"
    }
}

def t(key):
    lang = st.session_state.get("lang", "FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(key, key)

# ----------------- user storage -----------------
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # default
    default = {"admin":{"password":"admin","role":"admin","access":["linearity","sn"]},
               "user":{"password":"user","role":"user","access":["linearity","sn"]}}
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return default

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

USERS = load_users()

# ----------------- feedback storage -----------------
def load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_feedback(feedback_list):
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedback_list, f, indent=2, ensure_ascii=False)

# ---------------- PDF helper ----------------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    if not HAS_FPDF:
        return None
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

# ---------------- OCR / image digitize ----------------
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

def extract_xy_from_image_best_effort(image: Image.Image):
    """
    Try OCR for numeric X,Y pairs. If not possible, use vertical projection.
    Returns DataFrame with columns X,Y.
    """
    # try OCR
    if HAS_TESSERACT:
        try:
            text = pytesseract.image_to_string(image)
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
            if rows:
                df = pd.DataFrame(rows, columns=["X","Y"]).sort_values("X").reset_index(drop=True)
                return df
        except Exception:
            pass

    # fallback: vertical projection (use luminance)
    arr = np.array(image.convert("L"))
    # projection along vertical axis -> gives 1D signal (width)
    signal = arr.max(axis=0).astype(float)
    # smooth a bit
    signal_smooth = gaussian_filter1d(signal, sigma=1.0)
    df = pd.DataFrame({"X": np.arange(len(signal_smooth)), "Y": signal_smooth})
    return df
# ---------------- Part 2: Login, admin, feedback ----------------

# session defaults
if "lang" not in st.session_state:
    st.session_state.lang = "FR"
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

def header_area():
    c0, c1 = st.columns([3,1])
    with c0:
        st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    with c1:
        upl = st.file_uploader(t("upload_logo"), type=["png","jpg","jpeg"], key="upload_logo")
        if upl is not None:
            try:
                upl.seek(0)
                with open(LOGO_FILE, "wb") as f:
                    f.write(upl.read())
                st.success("Logo saved")
            except Exception as e:
                st.warning(f"Logo save error: {e}")

def find_user_key(username):
    if username is None:
        return None
    for u in USERS.keys():
        if u.lower() == username.strip().lower():
            return u
    return None

# --- Login screen (kept bilingual and minimal changes; add powered by BnB)
def login_screen():
    header_area()
    st.write("")  # spacing
    cols = st.columns([2,1])
    with cols[0]:
        lang = st.selectbox("Language / Langue", ["FR","EN"],
                            index=0 if st.session_state.get("lang","FR")=="FR" else 1, key="login_lang")
        st.session_state.lang = lang

    st.markdown(f"### 🔐 {t('login')}")
    uname = st.text_input(t("username"), key="login_username")
    pwd = st.text_input(t("password"), type="password", key="login_password")
    if st.button(t("login"), key="login_btn"):
        matched = find_user_key(uname)
        if matched and USERS.get(matched,{}).get("password","") == (pwd or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            # set default access if absent
            if "access" not in USERS[matched]:
                USERS[matched]["access"] = ["linearity","sn"]
                save_users(USERS)
            # navigate to main
            st.success(f"{t('login')} OK")
            st.session_state.page = "home"
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
        else:
            st.error(t("invalid"))

    st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

    # small expander to change password outside session (same as original)
    with st.expander(t("change_pwd"), expanded=False):
        u = st.text_input("Username to change", key="chg_user")
        new = st.text_input("New password", type="password", key="chg_pwd")
        if st.button("Change password", key="chg_btn"):
            found = find_user_key(u)
            if not found:
                st.warning("User not found")
            else:
                USERS[found]["password"] = new
                save_users(USERS)
                st.success(f"Password updated for {found}")

# --- logout helper ---
def logout():
    for k in ["user","role","page"]:
        if k in st.session_state:
            st.session_state.pop(k)
    # return to login
    st.session_state.page = "login"
    # use st.rerun to refresh
    st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

# --- admin panel: manage users, grant/revoke access to modules ---
def admin_panel():
    st.header(t("admin"))
    colL, colR = st.columns([2,1])
    with colL:
        st.subheader("Existing users")
        users_list = list(USERS.keys())
        sel = st.selectbox("Select user", users_list, key="admin_sel_user")
        if sel:
            info = USERS.get(sel, {})
            st.write(f"Username: **{sel}**")
            st.write(f"Role: **{info.get('role','user')}**")
            # access control for modules
            access = info.get("access", ["linearity","sn"])
            st.write("Module access:")
            lin_check = st.checkbox("Linéarité", "lin_access_"+sel, value=("linearity" in access))
            sn_check = st.checkbox("S/N", "sn_access_"+sel, value=("sn" in access))
            new_role = st.selectbox("Role", ["user","admin"], index=0 if info.get("role","user")=="user" else 1, key=f"newrole_{sel}")
            if st.button("Save changes", key=f"save_{sel}"):
                USERS[sel]["role"] = new_role
                new_access = []
                if lin_check: new_access.append("linearity")
                if sn_check: new_access.append("sn")
                USERS[sel]["access"] = new_access
                save_users(USERS)
                st.success("Updated")
                # avoid double element ids by rerun
                st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
            if sel.lower() != "admin" and st.button("Delete selected user", key=f"del_{sel}"):
                USERS.pop(sel, None)
                save_users(USERS)
                st.success(f"{sel} deleted")
                st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

    with colR:
        st.subheader(t("add_user"))
        with st.form("form_add_user", clear_on_submit=True):
            new_user = st.text_input(t("enter_username"), key="add_username")
            new_pass = st.text_input(t("enter_password"), type="password", key="add_password")
            role = st.selectbox("Role", ["user","admin"], key="add_role")
            add_sub = st.form_submit_button("Add")
            if add_sub:
                if not new_user.strip() or not new_pass.strip():
                    st.warning("Enter username and password")
                elif find_user_key(new_user) is not None:
                    st.warning("User exists")
                else:
                    USERS[new_user.strip()] = {"password": new_pass.strip(), "role": role, "access":["linearity","sn"]}
                    save_users(USERS)
                    st.success(f"User {new_user.strip()} added")
                    st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

# --- feedback panel (discrete button access) ---
def feedback_panel(discrete=False):
    # discrete True -> render as small button/expander ; else full panel
    if discrete:
        if st.button("Feedback / Suggestions", key="fb_small"):
            st.session_state.show_feedback_form = True
    if st.session_state.get("show_feedback_form"):
        st.subheader("Send feedback / Envoyer un feedback")
        fb_name = st.text_input("Your name (optional)", key="fb_name")
        fb_text = st.text_area("Feedback / Suggestion", height=160, key="fb_text")
        if st.button("Send feedback", key="fb_send"):
            fb = {"from": fb_name or st.session_state.get("user","anonymous"),
                  "user": st.session_state.get("user"),
                  "text": fb_text,
                  "ts": datetime.now().isoformat(),
                  "reply": None}
            feeds = load_feedback()
            feeds.append(fb)
            save_feedback(feeds)
            st.success("Feedback sent. Admin will be able to read and reply.")
            st.session_state.show_feedback_form = False
    # Admin read/respond
    if st.session_state.get("role") == "admin":
        st.markdown("---")
        st.subheader("Feedbacks (admin)")
        feeds = load_feedback()
        if not feeds:
            st.info("No feedback yet.")
        else:
            for i,fb in enumerate(feeds):
                st.markdown(f"**{i+1}. From:** {fb.get('from')} — @{fb.get('ts')}")
                st.write(fb.get("text"))
                if fb.get("reply"):
                    st.info(f"Reply: {fb.get('reply')}")
                if st.text_input(f"Reply to #{i+1}", key=f"reply_input_{i}"):
                    pass
                if st.button(f"Send reply #{i+1}", key=f"reply_btn_{i}"):
                    reply_text = st.session_state.get(f"reply_input_{i}","")
                    feeds[i]["reply"] = reply_text
                    save_feedback(feeds)
                    st.success("Reply saved.")
# ---------------- Part 3: main app, linearity (kept as original), S/N improvements ----------------

# --- linearity panel: kept functionally as before, minimal formatting changes ---
def linearity_panel():
    # Keep logic exactly as original (you requested no changes to linearity computation)
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

    # numeric check & fit
    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"])
        df["Signal"] = pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Concentration and Signal must be numeric.")
        return
    if len(df) < 2:
        st.warning("At least 2 points are required.")
        return

    # Fit linear regression (store slope)
    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0]); intercept = float(coeffs[1])
    st.session_state.linear_slope = slope

    # metrics
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred)**2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values))**2)
    r2 = float(1 - ss_res/ss_tot) if ss_tot != 0 else 0.0
    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.4f}")

    # plot (solid line as requested)
    fig, ax = plt.subplots(figsize=(7,3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope*xs + intercept, color="black", linestyle='-', linewidth=2, label="Fit")
    ax.set_xlabel(f"{t('concentration')} ({unit})")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # compute unknowns both ways (signal->conc and conc->signal)
    calc_choice = st.radio("Calculate", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_calc_choice")
    val = st.number_input("Enter value", format="%.6f", key="lin_unknown")
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

    # export
    csv_buf = io.StringIO(); df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")
    if st.button(t("generate_pdf"), key="lin_pdf"):
        if not company or company.strip()=="":
            st.warning(t("company_missing"))
        else:
            buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); buf.seek(0)
            lines = [f"Company: {company or 'N/A'}",
                     f"User: {st.session_state.user or 'Unknown'}",
                     f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                     f"Slope: {slope:.6f}", f"Intercept: {intercept:.6f}", f"R²: {r2:.6f}"]
            logo_path = LOGO_FILE if os.path.exists(LOGO_FILE) else None
            pdf_bytes = generate_pdf_bytes("Linearity report", lines, img_bytes=buf, logo_path=logo_path)
            if pdf_bytes:
                st.download_button(t("download_pdf"), pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")
            else:
                st.warning("PDF export not available (fpdf missing).")

# --- S/N panel: robust, many options requested ---
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))

    # uploader
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_uploader")

    # Manual mode if nothing uploaded
    if uploaded is None:
        st.subheader(t("manual_sn"))
        H = st.number_input("H (peak height)", value=0.0, format="%.6f", key="manual_H")
        h = st.number_input("h (noise)", value=0.0, format="%.6f", key="manual_h")
        slope_manual = st.number_input("Slope (manual) - optional", value=st.session_state.get("linear_slope") or 0.0, format="%.6f", key="manual_slope")
        unit_choice = st.selectbox("Unit for LOD/LOQ", ["µg/mL","mg/mL","ng/mL"], key="sn_unit_manual")
        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2 * H / h if h != 0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        if slope_manual:
            lod_sig = 3.3 * h
            loq_sig = 10 * h
            lod_conc = lod_sig / slope_manual
            loq_conc = loq_sig / slope_manual
            st.write(f"LOD (signal): {lod_sig:.6f}")
            st.write(f"LOQ (signal): {loq_sig:.6f}")
            st.write(f"LOD ({unit_choice}): {lod_conc:.6f}")
            st.write(f"LOQ ({unit_choice}): {loq_conc:.6f}")
        return

    name = uploaded.name.lower()
    df = None
    orig_image = None

    # CSV path
    if name.endswith(".csv"):
        try:
            uploaded.seek(0)
            try:
                df0 = pd.read_csv(uploaded)
            except Exception:
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
        except Exception as e:
            st.error(f"CSV read error: {e}")
            return

    # Image path (png/jpg)
    elif name.endswith((".png",".jpg",".jpeg")):
        try:
            uploaded.seek(0)
            orig_image = Image.open(uploaded).convert("RGB")
            st.subheader("Original image")
            st.image(orig_image, use_column_width=True)
            df = extract_xy_from_image_best_effort(orig_image)
        except Exception as e:
            st.error(f"Image error: {e}")
            return

    # PDF path: try convert, else ask user to upload PNG
    elif name.endswith(".pdf"):
        if not HAS_PDF2IMAGE:
            st.error(t("image_process_failed"))
            st.info("Please convert your PDF to PNG and upload the PNG.")
            return
        try:
            uploaded.seek(0)
            pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
            orig_image = pages[0].convert("RGB")
            st.subheader("Original image (from PDF)")
            st.image(orig_image, use_column_width=True)
            df = extract_xy_from_image_best_effort(orig_image)
        except Exception as e:
            st.error(f"PDF error: {e}")
            return
    else:
        st.error("Unsupported file type.")
        return

    if df is None or df.empty:
        st.warning("No numeric signal extracted from image/CSV.")
        return

    # Ensure numeric sorted
    df = df.dropna().sort_values("X").reset_index(drop=True)

    # If X constant (flat) -> create artificial X
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    if x_min == x_max:
        st.warning("Signal plat ou OCR invalide : les valeurs X sont identiques. Utilisation d'un axe X artificiel.")
        df["X"] = np.arange(len(df))

    # REGION selection (two handles slider)
    st.subheader(t("select_region"))
    default_start = float(df["X"].min() + 0.25 * (df["X"].max() - df["X"].min()))
    default_end = float(df["X"].min() + 0.75 * (df["X"].max() - df["X"].min()))
    # ensure valid min/max
    try:
        start, end = st.slider("Select X range (noise)", min_value=float(df["X"].min()), max_value=float(df["X"].max()), value=(default_start, default_end), key="sn_range")
    except Exception as e:
        st.warning(f"Slider initialization issue: {e}")
        start, end = float(df["X"].min()), float(df["X"].max())

    region = df[(df["X"] >= start) & (df["X"] <= end)].copy()
    if region.shape[0] < 2:
        st.warning(t("noise_region_small"))

    # Peak detection: MAIN peak should be detected on entire chromatogram (independent of noise region)
    y_all = df["Y"].values
    x_all = df["X"].values
    peak_idx = int(np.argmax(y_all))
    peak_x = float(x_all[peak_idx])
    peak_y = float(y_all[peak_idx])

    # Baseline & noise: computed from selected region if possible, else from global
    if region.shape[0] >= 2:
        noise_std = float(region["Y"].std(ddof=0))
        baseline = float(region["Y"].mean())
    else:
        noise_std = float(df["Y"].std(ddof=0))
        baseline = float(df["Y"].mean())

    if noise_std == 0 or np.isnan(noise_std):
        noise_std = 1e-12

    height = peak_y - baseline

    # FWHM (W1/2)
    half_height = baseline + height / 2.0
    # find left crossing
    left_idxs = np.where(y_all[:peak_idx] <= half_height)[0]
    right_idxs = np.where(y_all[peak_idx:] <= half_height)[0]
    W = np.nan
    if len(left_idxs) > 0:
        left_x = x_all[left_idxs[-1]]
        W = peak_x - left_x
    if len(right_idxs) > 0:
        right_x = x_all[peak_idx + right_idxs[0]]
        if np.isnan(W):
            W = right_x - peak_x
        else:
            W = W + (right_x - peak_x)

    # S/N calculations
    sn_classic = peak_y / noise_std
    sn_usp = height / noise_std

    # allow user to override slope or use linearity slope
    st.subheader("LOD/LOQ & slope")
    slope_choice = st.radio("Slope source", ["Use linearity slope" if st.session_state.get("linear_slope") else "No linearity slope available", "Enter slope manually"], key="slope_choice")
    if slope_choice.startswith("Use") and st.session_state.get("linear_slope"):
        slope_to_use = float(st.session_state.linear_slope)
    else:
        slope_to_use = st.number_input("Enter slope manually", value=0.0, format="%.6f", key="sn_slope_manual")

    # show S/N results
    st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
    st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
    st.write(f"Peak retention (X): {peak_x:.6f}")
    st.write(f"H (height): {height:.6f} ; Noise (σ): {noise_std:.6f} ; W1/2: {W if not np.isnan(W) else 'n/a'}")

    # compute LOD/LOQ both in signal units and concentration (if slope present)
    unit_choice = st.selectbox("Unit for LOD/LOQ", ["µg/mL","mg/mL","ng/mL"], key="sn_unit")
    lod_sig = 3.3 * noise_std
    loq_sig = 10 * noise_std
    st.write(f"LOD (signal): {lod_sig:.6f}")
    st.write(f"LOQ (signal): {loq_sig:.6f}")
    if slope_to_use and slope_to_use != 0:
        lod_conc = lod_sig / slope_to_use
        loq_conc = loq_sig / slope_to_use
        st.write(f"LOD ({unit_choice}): {lod_conc:.6f}")
        st.write(f"LOQ ({unit_choice}): {loq_conc:.6f}")
    else:
        st.info("Slope missing — LOD/LOQ in concentration not computed.")

    # Plot: we must preserve original image display and *for calculation* use inverted image (baseline bottom, peaks up).
    # If we have orig_image, show it, and also create a processed image (invert vertical if needed)
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(df["X"], df["Y"], color="black", label="Chromatogram (processed view)")
    # mark noise region
    ax.axvspan(start, end, alpha=0.25, color="gray", label="Noise region")
    # mark baseline and half-height
    ax.axhline(baseline, color="green", linestyle="--", label="Baseline")
    ax.axhline(half_height, color="orange", linestyle="--", label="Half height")
    # mark main peak top
    ax.plot(peak_x, peak_y, marker="o", markersize=8, color="red", label="Main peak")
    ax.set_xlabel("Retention time (X)")
    ax.set_ylabel("Signal (Y)")
    ax.legend()
    st.pyplot(fig)

    # allow user to download processed image (rendered figure)
    buf_img = io.BytesIO()
    fig.savefig(buf_img, format="png", bbox_inches="tight")
    buf_img.seek(0)
    st.download_button(t("download_processed_image"), data=buf_img, file_name="sn_processed.png", mime="image/png")

    # CSV export of df
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv")

    # PDF export report (if fpdf available)
    if st.button(t("export_sn_pdf")):
        lines = [
            f"File: {uploaded.name}",
            f"User: {st.session_state.get('user','Unknown')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{t('sn_classic')}: {sn_classic:.6f}",
            f"{t('sn_usp')}: {sn_usp:.6f}",
            f"Peak X: {peak_x:.6f}",
            f"H: {height:.6f}, Noise: {noise_std:.6f}, W1/2: {W if not np.isnan(W) else 'n/a'}"
        ]
        if slope_to_use and slope_to_use != 0:
            lines += [f"Slope: {slope_to_use:.6f}", f"LOD ({unit_choice}): {lod_conc:.6f}", f"LOQ ({unit_choice}): {loq_conc:.6f}"]
        pdf_bytes = generate_pdf_bytes("S/N Report", lines, img_bytes=buf_img, logo_path=(LOGO_FILE if os.path.exists(LOGO_FILE) else None))
        if pdf_bytes:
            st.download_button(t("download_pdf"), pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")
        else:
            st.warning("PDF export not available (fpdf missing).")

    # small expander for formulas
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
        **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \)  
        **LOD (signal)** = \( 3.3 \cdot \sigma_{noise} \)  
        **LOQ (signal)** = \( 10 \cdot \sigma_{noise} \)  
        **LOD (conc)** = \( \dfrac{3.3 \cdot \sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( \dfrac{10 \cdot \sigma_{noise}}{slope} \)
        """)

# ---------------- main_app wiring ----------------
def main_app():
    header_area()
    # top language selector and logout
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang")
        st.session_state.lang = lang

    user = st.session_state.get("user")
    role = st.session_state.get("role","user")
    st.markdown(f"### 👋 {'Bonjour' if st.session_state.get('lang','FR')=='FR' else 'Hello'}, **{user}** !")

    # tabs: linéarité and s/n; admin gets only admin tab
    if role == "admin":
        tab_admin, tab_feedback = st.tabs([t("admin"), "Feedbacks"])
        with tab_admin:
            admin_panel()
        with tab_feedback:
            feedback_panel()
    else:
        tab_lin, tab_sn, tab_fb = st.tabs([t("linearity"), t("sn"), "Feedback"])
        with tab_lin:
            # check access
            access = USERS.get(user,{}).get("access", ["linearity","sn"])
            if "linearity" in access:
                linearity_panel()
            else:
                st.warning("Access to Linearity disabled for your account.")
        with tab_sn:
            access = USERS.get(user,{}).get("access", ["linearity","sn"])
            if "sn" in access:
                sn_panel_full()
            else:
                st.warning("Access to S/N disabled for your account.")
        with tab_fb:
            feedback_panel(discrete=True)

    # logout button (single click) and change password small button
    c1, c2, c3 = st.columns([1,1,6])
    with c1:
        if st.button(t("logout")):
            logout()
    with c2:
        if st.button("Change my password"):
            # small inline change
            newpwd = st.text_input("New password", type="password", key="selfchg_pwd")
            if newpwd and st.button("Save new password", key="selfchg_save"):
                usr = st.session_state.get("user")
                if usr:
                    USERS[usr]["password"] = newpwd
                    save_users(USERS)
                    st.success("Password changed.")
    # show admin-read feedbacks link for users if admin replied earlier? (already in admin panel)

# ---------------- run app ----------------
def run():
    # route to login or main
    if st.session_state.get("user"):
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run()