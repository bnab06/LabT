# app_final.py
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
# Page config
# -------------------------
st.set_page_config(page_title="LabT", layout="wide", initial_sidebar_state="collapsed")

USERS_FILE = "users.json"
LOGO_FILE = "logo_labt.png"

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
        "company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport."
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
        "company_missing":"Please enter company name before generating the report."
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
# Helper fig->bytes
# -------------------------
def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

# -------------------------
# OCR helper
# -------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
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
        for sep in [",",";","\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip() != ""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",","."))
                        y = float(parts[1].replace(",","."))
                        rows.append([x,y])
                        break
                    except:
                        pass
        else:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",","."))
                    y = float(parts[1].replace(",","."))
                    rows.append([x,y])
                except:
                    pass
    return pd.DataFrame(rows, columns=["X","Y"])

# -------------------------
# Login screen
# -------------------------
def login_screen():
    st.markdown(f"<h1 style='margin-bottom:0.1rem;'>{t('app_title')}</h1>", unsafe_allow_html=True)
    st.write("")
    lang = st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1)
    st.session_state.lang = lang

    with st.form("login_form"):
        cols = st.columns([2,1])
        with cols[0]:
            username = st.text_input(t("username"), key="username_login")
        with cols[1]:
            password = st.text_input(t("password"), type="password", key="password_login")
        submitted = st.form_submit_button(t("login"))

    if submitted:
        uname = (username or "").strip()
        matched = next((u for u in USERS if u.lower()==uname.lower()), None)
        if matched and USERS[matched]["password"] == (password or ""):
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role","user")
            return
        else:
            st.error(t("invalid"))

# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header(t("admin"))
    col_left, col_right = st.columns([2,1])
    with col_left:
        st.subheader("Existing users")
        users_list = list(USERS.keys())
        sel = st.selectbox("Select user", users_list)
        if sel:
            info = USERS.get(sel, {})
            st.write(f"Username: **{sel}**")
            st.write(f"Role: **{info.get('role','user')}**")
            if st.button("Delete selected user"):
                if sel.lower()=="admin":
                    st.warning("Cannot delete admin")
                else:
                    USERS.pop(sel)
                    save_users(USERS)
                    st.success(f"{sel} deleted")
                    st.experimental_rerun()
    with col_right:
        st.subheader(t("add_user"))
        with st.form("form_add_user"):
            new_user = st.text_input(t("enter_username"))
            new_pass = st.text_input(t("enter_password"), type="password")
            role = st.selectbox("Role", ["user","admin"])
            add_sub = st.form_submit_button("Add")
        if add_sub:
            if new_user.strip() and new_pass.strip() and new_user not in USERS:
                USERS[new_user.strip()] = {"password":new_pass.strip(),"role":role}
                save_users(USERS)
                st.success(f"User {new_user.strip()} added")
                st.experimental_rerun()

# -------------------------
# Linearity panel
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"))
    if not company:
        st.warning(t("company_missing"))
        return

    mode = st.radio("Input mode", [t("input_csv"), t("input_manual")])
    df = None
    if mode==t("input_csv"):
        uploaded = st.file_uploader("Upload CSV with concentration, signal", type=["csv"])
        if uploaded:
            try:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded)
                cols_low = [c.lower() for c in df0.columns]
                if "concentration" in cols_low and "signal" in cols_low:
                    df = df0.rename(columns={df0.columns[cols_low.index("concentration")]:"Concentration",
                                             df0.columns[cols_low.index("signal")]:"Signal"})
                elif len(df0.columns)>=2:
                    df = df0.iloc[:,:2].copy()
                    df.columns=["Concentration","Signal"]
                else:
                    st.error("CSV must contain at least two columns (concentration, signal).")
            except Exception as e:
                st.error(f"CSV error: {e}")
    else:
        cols = st.columns(2)
        conc_input = cols[0].text_area("Concentrations (comma separated)")
        sig_input = cols[1].text_area("Signals (comma separated)")
        if conc_input.strip() and sig_input.strip():
            try:
                concs = [float(c.replace(",",".")) for c in conc_input.split(",") if c.strip()!=""]
                sigs = [float(s.replace(",",".")) for s in sig_input.split(",") if s.strip()!=""]
                if len(concs)==len(sigs) and len(concs)>=2:
                    df = pd.DataFrame({"Concentration":concs,"Signal":sigs})
            except:
                st.error("Manual parse error")

    if df is None:
        return
    df["Concentration"]=pd.to_numeric(df["Concentration"])
    df["Signal"]=pd.to_numeric(df["Signal"])
    coeffs = np.polyfit(df["Concentration"], df["Signal"], 1)
    slope, intercept = coeffs
    y_pred = np.polyval(coeffs, df["Concentration"])
    r2 = float(1 - np.sum((df["Signal"]-y_pred)**2)/np.sum((df["Signal"]-np.mean(df["Signal"]))**2))
    st.session_state.linear_slope = slope

    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.4f}")

    fig, ax = plt.subplots(figsize=(7,3))
    ax.scatter(df["Concentration"], df["Signal"])
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope*xs + intercept, color="red")
    ax.set_xlabel("Concentration")
    ax.set_ylabel("Signal")
    st.pyplot(fig)

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")

    pdf_lines = [f"{t('company')}: {company}", f"Slope: {slope:.6f}", f"Intercept: {intercept:.6f}", f"R²: {r2:.4f}"]
    pdf_bytes = generate_pdf_bytes("Linearity Report", pdf_lines, img_bytes=fig_to_bytes(fig), logo_path=LOGO_FILE)
    st.download_button(t("download_pdf"), pdf_bytes, file_name="linearity.pdf", mime="application/pdf")

# -------------------------
# S/N panel
# -------------------------
def sn_panel():
    st.header(t("sn"))
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"])
    if not uploaded:
        return

    df = None
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        try:
            uploaded.seek(0)
            df0 = pd.read_csv(uploaded)
            if df0.shape[1]<2:
                st.error("CSV must have at least two columns")
                return
            df = df0.iloc[:,:2]
            df.columns=["Time","Signal"]
        except Exception as e:
            st.error(f"CSV read error: {e}")
            return
    elif name.endswith((".png",".jpg",".jpeg")):
        img = Image.open(uploaded)
        df = extract_xy_from_image_pytesseract(img)
    elif name.endswith(".pdf") and convert_from_bytes is not None:
        try:
            pages = convert_from_bytes(uploaded.read(), dpi=200)
            img = pages[0]
            df = extract_xy_from_image_pytesseract(img)
        except Exception as e:
            st.error(f"PDF read error: {e}")
            return
    else:
        st.warning("Unsupported format")
        return

    if df is None or df.empty:
        st.warning("No data extracted")
        return

    min_val, max_val = float(df["Time"].min()), float(df["Time"].max())
    region = st.slider(t("select_region"), min_val, max_val, (min_val,max_val))
    df_sel = df[(df["Time"]>=region[0]) & (df["Time"]<=region[1])].copy()
    if df_sel.empty:
        st.warning("No points in selected region")
        return

    sn_classic = df_sel["Signal"].max()/df_sel["Signal"].std() if df_sel["Signal"].std()!=0 else 0
    h = df_sel["Signal"].max()-df_sel["Signal"].min()
    sigma = df_sel["Signal"].std()
    sn_usp = h/sigma if sigma!=0 else 0
    slope = st.session_state.linear_slope or 1.0
    lod = 3*sigma/slope
    loq = 10*sigma/slope

    st.metric(t("sn_classic"), f"{sn_classic:.3f}")
    st.metric(t("sn_usp"), f"{sn_usp:.3f}")
    st.metric(t("lod"), f"{lod:.6f}")
    st.metric(t("loq"), f"{loq:.6f}")

    fig, ax = plt.subplots(figsize=(7,3))
    ax.plot(df["Time"], df["Signal"], label="Full")
    ax.plot(df_sel["Time"], df_sel["Signal"], color="red", label="Selected")
    ax.set_xlabel("Time")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    csv_buf = io.StringIO()
    df_sel.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv")

    pdf_lines = [f"S/N Classic: {sn_classic:.3f}", f"S/N USP: {sn_usp:.3f}", f"LOD: {lod:.6f}", f"LOQ: {loq:.6f}"]
    pdf_bytes = generate_pdf_bytes("S/N Report", pdf_lines, img_bytes=fig_to_bytes(fig), logo_path=LOGO_FILE)
    st.download_button(t("export_sn_pdf"), pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")

# -------------------------
# Main app
# -------------------------
def main():
    if st.session_state.user is None:
        login_screen()
        return

    tabs = st.tabs([t("linearity"), t("sn"), t("admin")])
    with tabs[0]:
        linearity_panel()
    with tabs[1]:
        sn_panel()
    with tabs[2]:
        if st.session_state.role=="admin":
            admin_panel()
        else:
            st.warning("Access denied")

main()