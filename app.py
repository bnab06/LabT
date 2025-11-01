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

import streamlit as st

# -------------------------
# Login screen
# -------------------------
def login_screen():
    # Header
    st.title("LabT - Login / Connexion")
    st.write("")

    # Langue
    if "lang" not in st.session_state:
        st.session_state.lang = "FR"
    lang = st.selectbox(
        "Language / Langue",
        ["FR", "EN"],
        index=0 if st.session_state.lang == "FR" else 1,
        key="login_lang"
    )
    st.session_state.lang = lang

    # Formulaire login
    if "login_attempt" not in st.session_state:
        st.session_state.login_attempt = 0

    with st.form("login_form_main", clear_on_submit=False):
        username = st.text_input("Nom d'utilisateur / Username", key="username_login_main")
        password = st.text_input("Mot de passe / Password", type="password", key="password_login_main")
        submitted = st.form_submit_button("Connexion / Login")

    if submitted:
        st.session_state.login_attempt += 1
        uname = (username or "").strip()
        if not uname:
            st.error("Nom d'utilisateur vide / Invalid username")
        else:
            matched = find_user_key(uname)
            if matched and USERS[matched]["password"] == (password or ""):
                st.session_state.user = matched
                st.session_state.role = USERS[matched].get("role", "user")
                st.session_state.login_success = True
            else:
                st.error("Identifiants invalides / Invalid credentials")
                st.session_state.login_success = False

    # Affichage après connexion réussie
    if st.session_state.get("login_success"):
        st.success(f"Bienvenue / Welcome {st.session_state.user}")
        st.button("Continuer / Continue", key="continue_after_login")
        # Ici tu peux rediriger vers l'app principale
        main_app()


# -------------------------
# Logout function
# -------------------------
def logout():
    if "user" in st.session_state:
        del st.session_state.user
    if "role" in st.session_state:
        del st.session_state.role
    if "login_success" in st.session_state:
        del st.session_state.login_success
    st.session_state.login_attempt = 0
    st.experimental_rerun()  # rerun propre après déconnexion


# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header("Admin Panel / Panneau admin")
    col_left, col_right = st.columns([2, 1])

    # Liste des utilisateurs existants
    with col_left:
        st.subheader("Existing users / Utilisateurs existants")
        users_list = list(USERS.keys())
        sel = st.selectbox("Select user", users_list, key="admin_sel_user_main")
        if sel:
            info = USERS.get(sel, {})
            st.write(f"Username: **{sel}**")
            st.write(f"Role: **{info.get('role','user')}**")
            if st.button("Modify selected user", key=f"mod_user_{sel}"):
                with st.expander(f"Modify {sel}", expanded=True):
                    new_pwd = st.text_input(f"New password for {sel}", type="password", key=f"newpwd_{sel}")
                    new_role = st.selectbox(
                        "Role",
                        ["user", "admin"],
                        index=0 if info.get("role", "user") == "user" else 1,
                        key=f"newrole_{sel}"
                    )
                    if st.button("Save changes", key=f"save_{sel}"):
                        if new_pwd:
                            USERS[sel]["password"] = new_pwd
                        USERS[sel]["role"] = new_role
                        save_users(USERS)
                        st.success(f"Updated {sel}")

            if st.button("Delete selected user", key=f"del_{sel}"):
                if sel.lower() == "admin":
                    st.warning("Cannot delete admin")
                else:
                    USERS.pop(sel)
                    save_users(USERS)
                    st.success(f"{sel} deleted")

    # Ajouter un nouvel utilisateur
    with col_right:
        st.subheader("Add user / Ajouter utilisateur")
        with st.form("form_add_user_main"):
            new_user = st.text_input("Username / Nom d'utilisateur", key="add_username_main")
            new_pass = st.text_input("Password / Mot de passe", type="password", key="add_password_main")
            role = st.selectbox("Role", ["user", "admin"], key="add_role_main")
            add_sub = st.form_submit_button("Add / Ajouter")
        if add_sub:
            if not new_user.strip() or not new_pass.strip():
                st.warning("Enter username and password / Entrez nom et mot de passe")
            else:
                if find_user_key(new_user) is not None:
                    st.warning("User exists / Utilisateur existe déjà")
                else:
                    USERS[new_user.strip()] = {"password": new_pass.strip(), "role": role}
                    save_users(USERS)
                    st.success(f"User {new_user.strip()} added")


# -------------------------
# Run application
# -------------------------
def run():
    if "user" in st.session_state:
        # Si connecté → afficher app
        main_app()
    else:
        # Sinon → login
        login_screen()

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
    """
    Module S/N intégré LabT après login
    """

    import re, io, os
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from scipy.ndimage import gaussian_filter1d
    from scipy.signal import find_peaks
    from datetime import datetime
    from PIL import Image
    from fpdf import FPDF
    import streamlit as st

    # --- traduction simple fr/en ---
    try:
        _  # si déjà défini
    except NameError:
        def _(fr, en=None):
            return fr if en is None else fr

    st.header(_("S/N", "S/N"))

    uploaded = st.file_uploader(_("Upload chromatogram", "Upload chromatogram"),
                                type=["csv","png","jpg","jpeg","pdf"])
    if uploaded is None:
        st.info(_("Manual S/N calculation", "Manual S/N calculation"))
        H = st.number_input("H (peak height)", value=0.0, format="%.6f")
        h = st.number_input("h (noise)", value=0.0, format="%.6f")
        slope_input = st.number_input("Slope", value=0.0, format="%.6f")
        sn_classic = H / h if h != 0 else float("nan")
        sn_usp = 2*H/h if h != 0 else float("nan")
        st.write(f"S/N Classic: {sn_classic:.4f}")
        st.write(f"S/N USP: {sn_usp:.4f}")
        if slope_input:
            lod = 3.3*h/slope_input
            loq = 10*h/slope_input
            st.write(f"LOD: {lod:.6f}")
            st.write(f"LOQ: {loq:.6f}")
        return

    name = uploaded.name.lower()
    df = None

    def extract_xy_from_image(image):
        try:
            import pytesseract
            text = pytesseract.image_to_string(image)
            lines = text.splitlines()
            data = []
            for line in lines:
                line_clean = re.sub(r"[^\d\.,\- ]"," ", line)
                parts = line_clean.split()
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",",".")) 
                        y = float(parts[1].replace(",",".")) 
                        data.append((x,y))
                    except: continue
            if data:
                return pd.DataFrame(data, columns=["X","Y"]).sort_values("X").reset_index(drop=True)
        except Exception: pass
        # fallback: projection verticale
        arr = np.array(image.convert("L"))
        signal = arr.max(axis=0).astype(float)
        signal_smooth = gaussian_filter1d(signal, sigma=1)
        return pd.DataFrame({"X": np.arange(len(signal_smooth)), "Y": signal_smooth})

    # --- Lecture fichier ---
    if name.endswith(".csv"):
        uploaded.seek(0)
        try:
            df0 = pd.read_csv(uploaded)
        except:
            uploaded.seek(0)
            df0 = pd.read_csv(uploaded, sep=";", engine="python")
        cols_low = [c.lower() for c in df0.columns]
        if "time" in cols_low and "signal" in cols_low:
            df = df0.rename(columns={df0.columns[cols_low.index("time")]:"X",
                                     df0.columns[cols_low.index("signal")]:"Y"})
        else:
            df = df0.iloc[:, :2].copy()
            df.columns = ["X","Y"]
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

    elif name.endswith((".png",".jpg",".jpeg")):
        uploaded.seek(0)
        img = Image.open(uploaded).convert("RGB")
        st.subheader(_("Original image", "Original image"))
        st.image(img, use_column_width=True)
        df = extract_xy_from_image(img)

    elif name.endswith(".pdf"):
        uploaded.seek(0)
        try:
            from pdf2image import convert_from_bytes
            pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
            img = pages[0]
        except Exception:
            img = Image.new("L",(800,600), color=255)
        st.subheader(_("Original image", "Original image"))
        st.image(img, use_column_width=True)
        df = extract_xy_from_image(img)

    if df is None or df.empty:
        st.error(_("No valid signal detected", "No valid signal detected"))
        return

    df = df.dropna().sort_values("X").reset_index(drop=True)

    # --- Sélection région bruit ---
    st.subheader(_("Select region for noise estimation", "Select region for noise estimation"))
    x_min, x_max = float(df["X"].min()), float(df["X"].max())
    default_start = x_min + 0.25*(x_max-x_min)
    default_end = x_min + 0.75*(x_max-x_min)
    start, end = st.slider(_("Select X range","Select X range"),
                            min_value=float(x_min),
                            max_value=float(x_max),
                            value=(float(default_start), float(default_end)))
    region = df[(df["X"]>=start)&(df["X"]<=end)]
    if region.shape[0]<2:
        st.warning(_("Region too small for noise estimation","Region too small for noise estimation"))

    # --- Détection pic principal ---
    y = df["Y"].values
    x = df["X"].values
    peak_idx = np.argmax(y)
    peak_x = x[peak_idx]
    peak_y = y[peak_idx]

    # Bruit et baseline
    noise_std = region["Y"].std(ddof=0) if not region.empty else np.std(y)
    baseline = region["Y"].mean() if not region.empty else np.mean(y)
    height = peak_y - baseline

    # Largeur à mi-hauteur
    half_height = baseline + height/2
    left_idx = np.where(y[:peak_idx]<=half_height)[0]
    right_idx = np.where(y[peak_idx:]<=half_height)[0]
    W = x[peak_idx] - x[left_idx[-1]] if len(left_idx)>0 else np.nan
    if len(right_idx)>0:
        W += x[peak_idx+right_idx[0]] - x[peak_idx]

    # --- S/N ---
    sn_classic = peak_y / noise_std
    sn_usp = height / noise_std
    st.write(f"S/N Classic: {sn_classic:.4f}")
    st.write(f"S/N USP: {sn_usp:.4f}")
    st.write(f"Peak X (Retention time): {peak_x:.4f}")
    st.write(f"H: {height:.4f}, Noise h: {noise_std:.4f}, Width W: {W:.4f}")

    # --- Plot chromatogramme ---
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(x,y, label="Chromatogram")
    ax.axvspan(start,end,alpha=0.25,label="Noise region")
    ax.plot(peak_x, peak_y,"r^", label="Main peak")
    ax.axhline(baseline, color="green", linestyle="--", label="Baseline")
    ax.axhline(half_height,color="orange",linestyle="--", label="Half height")
    ax.set_xlabel(_("Time / Temps","Time / Temps"))
    ax.set_ylabel(_("Signal","Signal"))
    ax.legend()
    st.pyplot(fig)

    # --- Export CSV ---
    csv_buf = io.StringIO()
    df.to_csv(csv_buf,index=False)
    st.download_button(_("Download CSV","Download CSV"), csv_buf.getvalue(), "sn_region.csv", "text/csv")

    # --- Export PDF ---
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,_("S/N Analysis Report","S/N Analysis Report"),0,1,"C")
    pdf.ln(5)
    pdf.set_font("Arial","",12)
    pdf.cell(0,8,f"S/N Classic: {sn_classic:.4f}",0,1)
    pdf.cell(0,8,f"S/N USP: {sn_usp:.4f}",0,1)
    pdf.cell(0,8,f"Peak X (Retention time): {peak_x:.4f}",0,1)
    pdf.cell(0,8,f"H: {height:.4f}, Noise h: {noise_std:.4f}, Width W: {W:.4f}",0,1)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format="PNG")
    img_buf.seek(0)
    pdf.image(img_buf, x=10, y=50, w=270)
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    st.download_button(_("Download PDF","Download PDF"), pdf_output, "sn_report.pdf", "application/pdf")

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