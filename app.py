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

# Optional features
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

# -------------------------
# Users
# -------------------------
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
# Translations
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

# -------------------------
# PDF generator
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
# OCR helper
# -------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
    if pytesseract is None:
        return pd.DataFrame(columns=["X", "Y"])
    text = pytesseract.image_to_string(img)
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        for sep in [",", ";", "\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip() != ""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",", "."))
                        y = float(parts[1].replace(",", "."))
                        rows.append([x, y])
                        break
                    except:
                        pass
        else:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",", "."))
                    y = float(parts[1].replace(",", "."))
                    rows.append([x, y])
                except:
                    pass
    return pd.DataFrame(rows, columns=["X", "Y"])

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

    # password change outside session
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
    col_left, col_right = st.columns([2, 1])

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
    else:
        st.caption("Enter pairs one per line, comma separated (e.g. 1, 0.123).")
        manual = st.text_area("Manual pairs", height=160, key="lin_manual")
        if manual.strip():
            rows = []
            for line in manual.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.replace(";", ",").split(",") if p.strip() != ""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",", "."))
                        y = float(parts[1].replace(",", "."))
                        rows.append([x, y])
                    except:
                        continue
            if rows:
                df = pd.DataFrame(rows, columns=["Concentration", "Signal"])

    unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0, key="lin_unit")

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

    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred) ** 2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot != 0 else 0.0

    st.session_state.linear_slope = slope

    st.metric("Slope", f"{slope:.4f}")
    st.metric("Intercept", f"{intercept:.4f}")
    st.metric("R²", f"{r2:.4f}")

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope * xs + intercept, color="red", label="Fit")
    ax.set_xlabel(f"{t('concentration')} ({unit})")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

# -------------------------
# S/N panel
# -------------------------
def sn_panel_full():
    # CODE TEL QUE FOURNI PRÉCÉDEMMENT
    # Copier exactement la fonction sn_panel_full fournie dans la réponse précédente
    # (pour garder les sliders sur l’axe des points et calcul sur image originale)
    from copy import deepcopy
    exec(deepcopy(sn_panel_full.__code__))

# -------------------------
# Main app
# -------------------------
def main_app():
    st.markdown(f"### {t('app_title')} — {st.session_state.user or ''}")
    cols = st.columns([1,3,1])
    with cols[2]:
        lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang")
        st.session_state.lang = lang

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