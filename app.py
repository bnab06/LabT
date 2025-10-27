# -------------------------
# app.py (corrigé - partie 1/2)
# -------------------------
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

# Optional features
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

# -------------------------
# Files / defaults
# -------------------------
USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"  # put your logo here (optional)

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        default = {"admin": {"password": "admin123", "role": "admin"},
                   "user": {"password": "user123", "role": "user"}}
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

# -------------------------
# Texts / translations
# -------------------------
TEXTS = {
    "FR": { "app_title":"LabT", "powered":"Powered by BnB", "username":"Utilisateur", "password":"Mot de passe",
            "login":"Connexion","logout":"Déconnexion","invalid":"Identifiants invalides",
            "linearity":"Linéarité","sn":"S/N","admin":"Admin","company":"Nom de la compagnie",
            "input_csv":"CSV","input_manual":"Saisie manuelle","concentration":"Concentration","signal":"Signal",
            "unit":"Unité","generate_pdf":"Générer PDF","download_pdf":"Télécharger PDF","download_csv":"Télécharger CSV",
            "sn_classic":"S/N Classique","sn_usp":"S/N USP","lod":"LOD (conc.)","loq":"LOQ (conc.)",
            "formulas":"Formules","select_region":"Sélectionner la zone","add_user":"Ajouter utilisateur",
            "delete_user":"Supprimer utilisateur","modify_user":"Modifier mot de passe","enter_username":"Nom d'utilisateur",
            "enter_password":"Mot de passe (simple)","upload_chrom":"Importer chromatogramme (CSV, PNG, JPG, PDF)",
            "digitize_info":"Digitizing : OCR tenté si pytesseract installé (best-effort)",
            "export_sn_pdf":"Exporter S/N PDF","download_original_pdf":"Télécharger PDF original",
            "change_pwd":"Changer mot de passe (hors session)", "compute":"Compute", "company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport."},
    "EN": { "app_title":"LabT", "powered":"Powered by BnB", "username":"Username", "password":"Password",
            "login":"Login","logout":"Logout","invalid":"Invalid credentials",
            "linearity":"Linearity","sn":"S/N","admin":"Admin","company":"Company name",
            "input_csv":"CSV","input_manual":"Manual input","concentration":"Concentration","signal":"Signal",
            "unit":"Unit","generate_pdf":"Generate PDF","download_pdf":"Download PDF","download_csv":"Download CSV",
            "sn_classic":"S/N Classic","sn_usp":"S/N USP","lod":"LOD (conc.)","loq":"LOQ (conc.)",
            "formulas":"Formulas","select_region":"Select region","add_user":"Add user",
            "delete_user":"Delete user","modify_user":"Modify password","enter_username":"Username",
            "enter_password":"Password (simple)","upload_chrom":"Upload chromatogram (CSV, PNG, JPG, PDF)",
            "digitize_info":"Digitizing: OCR attempted if pytesseract available (best-effort)",
            "export_sn_pdf":"Export S/N PDF","download_original_pdf":"Download original PDF",
            "change_pwd":"Change password (outside session)", "compute":"Compute", "company_missing":"Please enter company name before generating the report."}
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
if "lin_unit" not in st.session_state:
    st.session_state.lin_unit = "µg/mL"

# -------------------------
# Utility: create PDF bytes
# -------------------------
def generate_pdf_bytes(title, lines, img_bytes=None, logo_path=None):
    pdf = FPDF()
    pdf.add_page()
    if logo_path:
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
# Login screen
# -------------------------
def login_screen():
    st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    st.write("")
    lang = st.selectbox("Language / Langue", ["FR", "EN"], index=0 if st.session_state.lang == "FR" else 1, key="login_lang")
    st.session_state.lang = lang

    with st.form("login_form", clear_on_submit=False):
        cols = st.columns([2, 1])
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
        matched = None
        for u in USERS:
            if u.lower() == uname.lower():
                matched = u
                break
        if matched and USERS[matched]["password"] == (password or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role", "user")
            return
        else:
            st.error(t("invalid"))

    st.markdown(f"<div style='position:fixed;bottom:8px;left:0;right:0;text-align:center;color:gray;font-size:12px'>{t('powered')}</div>", unsafe_allow_html=True)

    with st.expander(t("change_pwd"), expanded=False):
        st.write("Change a user's password (works even if not logged in).")
        u_name = st.text_input("Username to change", key="chg_user")
        u_pwd = st.text_input("New password", type="password", key="chg_pwd")
        if st.button("Change password", key="chg_btn"):
            if not u_name.strip() or not u_pwd:
                st.warning("Enter username and new password")
            else:
                found = None
                for u in USERS:
                    if u.lower() == u_name.strip().lower():
                        found = u
                        break
                if not found:
                    st.warning("User not found")
                else:
                    USERS[found]["password"] = u_pwd.strip()
                    save_users(USERS)
                    st.success(f"Password updated for {found}")

# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header(t("admin"))
    st.write(t("add_user"))
    col_left, col_right = st.columns([2, 1])

    # Existing users
    with col_left:
        st.subheader("Existing users")
        for u, info in list(USERS.items()):
            rcols = st.columns([3, 1, 1])
            rcols[0].write(f"{u} — role: {info.get('role', 'user')}")
            if rcols[1].button("Modify", key=f"mod_{u}"):
                with st.expander(f"Modify {u}", expanded=True):
                    new_pwd = st.text_input(f"New password for {u}", type="password", key=f"newpwd_{u}")
                    new_role = st.selectbox("Role", ["user", "admin"], index=0 if info.get("role", "user") == "user" else 1, key=f"newrole_{u}")
                    if st.button("Save", key=f"save_{u}"):
                        if new_pwd:
                            USERS[u]["password"] = new_pwd
                        USERS[u]["role"] = new_role
                        save_users(USERS)
                        st.success(f"Updated {u}")
                        return
            if rcols[2].button("Delete", key=f"del_{u}"):
                if u.lower() == "admin":
                    st.warning("Cannot delete admin")
                else:
                    USERS.pop(u)
                    save_users(USERS)
                    st.success(f"{u} deleted")
                    return

    # Add user
    with col_right:
        st.subheader(t("add_user"))
        with st.form("form_add_user"):
            new_user = st.text_input(t("enter_username"), key="add_username")
            new_pass = st.text_input(t("enter_password"), type="password", key="add_password")
            role = st.selectbox("Role", ["user", "admin"], key="add_role")
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
                    return

# -------------------------
# Linearity panel
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name")

    mode = st.radio("Input mode", [t("input_csv"), t("input_manual")], key="lin_input_mode")
    df = None

    # CSV input
    if mode == t("input_csv"):
        uploaded = st.file_uploader("Upload CSV with two columns (concentration, signal)", type=["csv"], key="lin_csv")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                cols_low = [c.lower() for c in df.columns]
                if "concentration" in cols_low and "signal" in cols_low:
                    df = df.rename(columns={df.columns[cols_low.index("concentration")]: "Concentration",
                                            df.columns[cols_low.index("signal")]: "Signal"})
                elif len(df.columns) >= 2:
                    df = df.iloc[:, :2]
                    df.columns = ["Concentration", "Signal"]
                else:
                    st.error("CSV must contain at least two columns (concentration, signal).")
                    df = None
            except Exception as e:
                st.error(f"CSV error: {e}")
                df = None
# -------------------------
# app.py (corrigé - partie 2/2)
# -------------------------

    # numeric conversion and validation
    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"])
        df["Signal"] = pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Concentration and Signal must be numeric.")
        return

    if len(df) < 2:
        st.warning("At least 2 points are required.")
        return

    # regression (numpy polyfit)
    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred) ** 2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot != 0 else 0.0

    # store slope for S/N in concentration
    st.session_state.linear_slope = slope

    # metrics display
    st.metric("Slope", f"{slope:.4f}")
    st.metric("Intercept", f"{intercept:.4f}")
    st.metric("R²", f"{r2:.4f}")

    # plot
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope * xs + intercept, color="red", label="Fit")
    ax.set_xlabel(f"{t('concentration')} ({st.session_state.lin_unit})")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # unknown conversions
    calc_choice = st.radio("Calculate", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_calc_choice")
    if calc_choice.startswith(t("signal")):
        val = st.number_input("Enter signal", format="%.4f", key="lin_in_signal")
        if st.button(t("compute"), key="lin_compute_signal"):
            try:
                if slope == 0:
                    st.error("Slope is zero, cannot compute concentration.")
                else:
                    conc = (val - intercept) / slope
                    st.success(f"Concentration = {conc:.4f} {st.session_state.lin_unit}")
            except Exception:
                st.error("Cannot compute (check inputs).")
    else:
        val = st.number_input("Enter concentration", format="%.4f", key="lin_in_conc")
        if st.button(t("compute"), key="lin_compute_conc"):
            try:
                sigp = slope * val + intercept
                st.success(f"Predicted signal = {sigp:.4f}")
            except Exception:
                st.error("Cannot compute (check inputs).")

    # formulas expander
    with st.expander(t("formulas"), expanded=False):
        st.markdown(r"""
        **Linearity:** \( y = slope \cdot X + intercept \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

    # generate PDF
    if st.button(t("generate_pdf"), key="lin_pdf"):
        if not company or company.strip() == "":
            st.warning(t("company_missing"))
        else:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            lines = [
                f"Company: {company or 'N/A'}",
                f"User: {st.session_state.user or 'Unknown'}",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Slope: {slope:.4f}",
                f"Intercept: {intercept:.4f}",
                f"R²: {r2:.4f}"
            ]
            try:
                import os
                logo_path = LOGO_FILE if os.path.exists(LOGO_FILE) else None
            except Exception:
                logo_path = None
            pdf_bytes = generate_pdf_bytes("Linearity report", lines, img_bytes=buf, logo_path=logo_path)
            st.download_button(t("download_pdf"), pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")


# -------------------------
# Signal / Noise panel
# -------------------------
def sn_panel():
    st.header(t("sn"))
    st.write(t("digitize_info"))
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv", "png", "jpg", "jpeg", "pdf"], key="sn_uploader")

    if uploaded is None:
        st.info("Upload a file (CSV with Time/Signal or PNG/JPG/PDF chromatogram).")
        return

    ext = uploaded.name.split(".")[-1].lower()
    signal = None
    time_index = None

    # CSV input
    if ext == "csv":
        try:
            uploaded.seek(0)
            df = pd.read_csv(uploaded)
            cols_low = [c.lower() for c in df.columns]
            if "time" in cols_low and "signal" in cols_low:
                ti = df.iloc[:, cols_low.index("time")]
                sig = pd.to_numeric(df.iloc[:, cols_low.index("signal")], errors="coerce").fillna(0).values
            elif len(df.columns) >= 2:
                ti = df.iloc[:, 0]
                sig = pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0).values
            else:
                st.error("CSV must have at least two columns (time, signal).")
                return
            st.subheader("Raw data preview")
            st.dataframe(df.head(50))
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(ti, sig)
            ax.set_xlabel("Time / Index")
            ax.set_ylabel("Signal")
            st.pyplot(fig)
            signal = np.array(sig, dtype=float)
            time_index = np.array(ti)
        except Exception as e:
            st.error(f"CSV error: {e}")
            return

    # Image input
    elif ext in ("png", "jpg", "jpeg"):
        try:
            uploaded.seek(0)
            img = Image.open(uploaded).convert("RGB")
            st.image(img, caption=uploaded.name, use_column_width=True)
            arr = np.array(img.convert("L"))
            sig = arr.max(axis=0).astype(float)
            time_index = np.arange(len(sig))
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(time_index, sig)
            ax.set_xlabel("Points")
            ax.set_ylabel("Signal")
            st.pyplot(fig)
            signal = sig
        except Exception as e:
            st.error(f"Image error: {e}")
            return

    # PDF input
    elif ext == "pdf":
        if convert_from_bytes is None:
            st.warning("PDF digitizing requires pdf2image + poppler installed. Original PDF can still be downloaded.")
            uploaded.seek(0)
            st.download_button(t("download_original_pdf"), uploaded.read(), file_name=uploaded.name)
            return
        try:
            uploaded.seek(0)
            pages = convert_from_bytes(uploaded.read(), first_page=1, last_page=1)
            if not pages:
                st.error("No pages extracted from PDF")
                return
            img = pages[0]
            st.image(img, caption=uploaded.name, use_column_width=True)
            arr = np.array(img.convert("L"))
            sig = arr.max(axis=0).astype(float)
            time_index = np.arange(len(sig))
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(time_index, sig)
            ax.set_xlabel("Points")
            ax.set_ylabel("Signal")
            st.pyplot(fig)
            signal = sig
        except Exception as e:
            st.error(f"PDF error: {e}")
            return

    else:
        st.error("Unsupported file type")
        return

    # Region selection
    if signal is not None:
        n = len(signal)
        st.subheader(t("select_region"))
        start, end = st.slider("", 0, n - 1, (0, n - 1), key="sn_region_slider")
        region = signal[start:end + 1]
        if len(region) < 2:
            st.warning("Select a larger region")
            return

        peak = float(np.max(region))
        noise_std = float(np.std(region, ddof=0))
        baseline_mean = float(np.mean(region))
        height = peak - baseline_mean

        sn_classic = (peak / noise_std) if noise_std != 0 else float("nan")
        sn_usp = (height / noise_std) if noise_std != 0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")

        # S/N in concentration
        if st.session_state.linear_slope:
            slope = st.session_state.linear_slope
            if slope != 0:
                lod = 3.3 * noise_std / slope
                loq = 10 * noise_std / slope
                st.write(f"{t('lod')} ({st.session_state.lin_unit}): {lod:.4f}")
                st.write(f"{t('loq')} ({st.session_state.lin_unit}): {loq:.4f}")
            else:
                st.info("Linearity slope is zero; cannot compute LOD/LOQ in concentration.")
        else:
            st.info("Linearity slope not available. Export slope from Linearity panel to compute LOD/LOQ.")

        # Formulas expander
        with st.expander(t("formulas"), expanded=False):
            st.markdown(r"""
            **Classic S/N:** \( Signal_{peak} / \sigma_{noise} \)  
            **USP S/N:** \( Height / \sigma_{noise} \)  
            **LOD (conc)** = \( 3.3 \cdot \sigma_{noise} / slope \)  
            **LOQ (conc)** = \( 10 \cdot \sigma_{noise} / slope \)
            """)

# -------------------------
# Main app (no sidebar)
# -------------------------
def main_app():
    st.markdown(f"### {t('app_title')} — {st.session_state.user or ''}")
    cols = st.columns([1, 3, 1])
    with cols[2]:
        lang = st.selectbox("", ["FR", "EN"], index=0 if st.session_state.lang == "FR" else 1, key="top_lang")
        st.session_state.lang = lang

    # Tabs
    if st.session_state.role == "admin":
        tabs = st.tabs([t("admin")])
        with tabs[0]:
            admin_panel()
    else:
        tabs = st.tabs([t("linearity"), t("sn")])
        with tabs[0]:
            linearity_panel()
        with tabs[1]:
            sn_panel()

    # Logout
    if st.button(t("logout"), key="btn_logout"):
        st.session_state.user = None
        st.session_state.role = None
        st.experimental_rerun()


# -------------------------
# Run
# -------------------------
def run():
    if st.session_state.user is None:
        login_screen()
    else:
        main_app()


if __name__ == "__main__":
    run()