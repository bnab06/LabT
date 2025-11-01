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
    """
    Full S/N panel with OCR/projection fallback, peak detection, and PDF export.
    """
    import io, os, re
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from PIL import Image
    from datetime import datetime
    from scipy.ndimage import gaussian_filter1d
    from scipy.signal import find_peaks
    from fpdf import FPDF

    st.header("Calcul du rapport Signal/Bruit (S/N)")

    uploaded = st.file_uploader("Importer un chromatogramme (CSV, image ou PDF)",
                                type=["csv", "png", "jpg", "jpeg", "pdf"],
                                key="sn_uploader")

    # --- Mode manuel si aucun fichier
    if uploaded is None:
        st.info("Mode manuel : entrez les valeurs pour calculer S/N.")
        H = st.number_input("Hauteur du pic (H)", value=0.0)
        h = st.number_input("Bruit (h)", value=0.0)
        slope_auto = float(st.session_state.get("linear_slope", 0.0) or 0.0)
        slope_input = st.number_input("Pente (slope)", value=slope_auto, format="%.6f")

        sn_classic = H / h if h else float("nan")
        sn_usp = 2 * H / h if h else float("nan")

        st.write(f"S/N (classique) : **{sn_classic:.4f}**")
        st.write(f"S/N (USP) : **{sn_usp:.4f}**")

        if slope_input:
            lod = 3.3 * h / slope_input
            loq = 10 * h / slope_input
            st.write(f"LOD : {lod:.6f}")
            st.write(f"LOQ : {loq:.6f}")
        return

    # --- Lecture du fichier
    name = uploaded.name.lower()
    df = None

    def extract_xy_from_image_pytesseract(image):
        """OCR extraction or vertical projection fallback."""
        import pytesseract
        try:
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
                return pd.DataFrame(data, columns=["X", "Y"]).sort_values("X").reset_index(drop=True)
        except Exception:
            pass

        # Projection fallback
        arr = np.array(image.convert("L"))
        signal = arr.max(axis=0).astype(float)
        signal_smooth = gaussian_filter1d(signal, sigma=2)
        return pd.DataFrame({"X": np.arange(len(signal_smooth)), "Y": signal_smooth})

    # --- CSV
    if name.endswith(".csv"):
        uploaded.seek(0)
        try:
            df = pd.read_csv(uploaded)
        except:
            uploaded.seek(0)
            df = pd.read_csv(uploaded, sep=";")

        if df.shape[1] >= 2:
            df.columns = ["X", "Y"] + list(df.columns[2:])
        else:
            st.error("Fichier CSV invalide (au moins 2 colonnes nécessaires).")
            return

    # --- IMAGE
    elif name.endswith((".png", ".jpg", ".jpeg")):
        from PIL import Image
        img = Image.open(uploaded)
        st.image(img, use_column_width=True)
        df = extract_xy_from_image_pytesseract(img)

    # --- PDF
    elif name.endswith(".pdf"):
        from pdf2image import convert_from_bytes
        pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
        img = pages[0]
        st.image(img, use_column_width=True)
        df = extract_xy_from_image_pytesseract(img)

    if df is None or df.empty:
        st.error("OCR/image projection failed: impossible d’obtenir un signal numérique.")
        return

    df = df.dropna().sort_values("X").reset_index(drop=True)
    x_min, x_max = df["X"].min(), df["X"].max()

    # --- Slider de sélection
    st.subheader("Sélection de la zone d’analyse")
    if x_min == x_max:
        st.warning("Signal plat ou OCR invalide : le slider est remplacé par une plage artificielle.")
        df["X"] = np.arange(len(df))
        x_min, x_max = df["X"].min(), df["X"].max()

    try:
        start, end = st.slider(
            "Plage X à analyser",
            float(x_min), float(x_max),
            (float(x_min + 0.25 * (x_max - x_min)),
             float(x_min + 0.75 * (x_max - x_min)))
        )
    except:
        start, end = x_min, x_max

    region = df[(df["X"] >= start) & (df["X"] <= end)]
    if region.shape[0] < 3:
        st.warning("Région trop petite pour détecter un pic.")
        return

    # --- Détection des pics
    st.subheader("Détection de pics")
    height_factor = st.slider("Facteur de hauteur (multiplicateur du bruit σ)", 0.5, 10.0, 3.0, step=0.1)
    min_distance_slider = st.slider("Distance minimale entre pics", 1, max(1, len(region)//2), max(1, len(region)//100))

    y = region["Y"].values
    baseline = np.median(y)
    noise_std = np.std(y)
    threshold = baseline + height_factor * noise_std

    peaks, _ = find_peaks(y, height=threshold, distance=int(min_distance_slider))
    n_peaks = len(peaks)

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(region["X"], region["Y"], label="Signal")
    if n_peaks > 0:
        ax.plot(region["X"].iloc[peaks], region["Y"].iloc[peaks], "ro", label="Pics détectés")
    ax.axhline(threshold, color="gray", linestyle="--", label=f"Seuil ({height_factor:.1f}×σ)")
    ax.legend()
    st.pyplot(fig)

    st.write(f"**Pics détectés :** {n_peaks}")

    # --- Calcul S/N, LOD, LOQ
    if n_peaks > 0:
        peak_val = float(region["Y"].iloc[peaks].max())
    else:
        peak_val = float(region["Y"].max())

    sn_classic = peak_val / noise_std if noise_std else 0
    st.write(f"S/N (classique) : **{sn_classic:.3f}**")

    slope_auto = float(st.session_state.get("linear_slope", 0.0) or 0.0)
    if slope_auto != 0:
        lod = 3.3 * noise_std / slope_auto
        loq = 10 * noise_std / slope_auto
        st.write(f"LOD : {lod:.6f}")
        st.write(f"LOQ : {loq:.6f}")
    else:
        lod = loq = None

    # --- Export PDF
    def export_pdf_sn(region, peaks_info, sn_classic, slope_auto=None, lod=None, loq=None):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Rapport de calcul S/N, LOD et LOQ", ln=True, align="C")

        pdf.set_font("Arial", "", 11)
        pdf.ln(5)
        pdf.cell(0, 10, f"Date : {datetime.now():%Y-%m-%d %H:%M:%S}", ln=True)
        pdf.cell(0, 8, f"Nombre total de points : {len(region)}", ln=True)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Pics détectés :", ln=True)
        pdf.set_font("Arial", "", 11)
        if peaks_info:
            for i, (x, y) in enumerate(peaks_info, 1):
                pdf.cell(0, 8, f"Pic {i} : X={x:.3f}, Y={y:.3f}", ln=True)
        else:
            pdf.cell(0, 8, "Aucun pic détecté.", ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Résultats analytiques :", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"S/N (classique) : {sn_classic:.3f}", ln=True)
        if slope_auto:
            pdf.cell(0, 8, f"Pente (slope) : {slope_auto:.6f}", ln=True)
        if lod is not None:
            pdf.cell(0, 8, f"LOD : {lod:.6f}", ln=True)
        if loq is not None:
            pdf.cell(0, 8, f"LOQ : {loq:.6f}", ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 8, "Généré automatiquement par LabT", ln=True, align="C")

        path = "/mnt/data/SN_Report.pdf"
        pdf.output(path)
        return path

    if st.button("📄 Exporter le rapport PDF"):
        peaks_info = [(region["X"].iloc[i], region["Y"].iloc[i]) for i in peaks] if n_peaks > 0 else []
        pdf_path = export_pdf_sn(region, peaks_info, sn_classic, slope_auto, lod, loq)
        st.success("✅ Rapport PDF généré avec succès.")
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Télécharger le rapport", f, file_name="SN_Report.pdf")
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