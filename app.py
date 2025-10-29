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

# Page config
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
        default = {"admin":{"password":"admin123","role":"admin"},"user":{"password":"user123","role":"user"}}
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
        "app_title":"LabT","powered":"Powered by BnB","username":"Utilisateur","password":"Mot de passe",
        "login":"Connexion","logout":"Déconnexion","invalid":"Identifiants invalides",
        "linearity":"Linéarité","sn":"S/N","admin":"Admin","company":"Nom de la compagnie",
        "input_csv":"CSV","input_manual":"Saisie manuelle","concentration":"Concentration","signal":"Signal",
        "unit":"Unité","generate_pdf":"Générer PDF","download_pdf":"Télécharger PDF","download_csv":"Télécharger CSV",
        "sn_classic":"S/N Classique","sn_usp":"S/N USP","lod":"LOD (conc.)","loq":"LOQ (conc.)","formulas":"Formules",
        "select_region":"Sélectionner la zone","add_user":"Ajouter utilisateur","delete_user":"Supprimer utilisateur",
        "modify_user":"Modifier mot de passe","enter_username":"Nom d'utilisateur","enter_password":"Mot de passe (simple)",
        "upload_chrom":"Importer chromatogramme (CSV, PNG, JPG, PDF)","digitize_info":"Digitizing : OCR tenté si pytesseract installé (best-effort)",
        "export_sn_pdf":"Exporter S/N PDF","download_original_pdf":"Télécharger PDF original","change_pwd":"Changer mot de passe (hors session)",
        "compute":"Compute","company_missing":"Veuillez saisir le nom de la compagnie avant de générer le rapport.",
        "select_section":"Section"
    },
    "EN": {
        "app_title":"LabT","powered":"Powered by BnB","username":"Username","password":"Password",
        "login":"Login","logout":"Logout","invalid":"Invalid credentials",
        "linearity":"Linearity","sn":"S/N","admin":"Admin","company":"Company name",
        "input_csv":"CSV","input_manual":"Manual input","concentration":"Concentration","signal":"Signal",
        "unit":"Unit","generate_pdf":"Generate PDF","download_pdf":"Download PDF","download_csv":"Download CSV",
        "sn_classic":"S/N Classic","sn_usp":"S/N USP","lod":"LOD (conc.)","loq":"LOQ (conc.)","formulas":"Formulas",
        "select_region":"Select region","add_user":"Add user","delete_user":"Delete user",
        "modify_user":"Modify password","enter_username":"Username","enter_password":"Password (simple)",
        "upload_chrom":"Upload chromatogram (CSV, PNG, JPG, PDF)","digitize_info":"Digitizing: OCR attempted if pytesseract available (best-effort)",
        "export_sn_pdf":"Export S/N PDF","download_original_pdf":"Download original PDF","change_pwd":"Change password (outside session)",
        "compute":"Compute","company_missing":"Please enter company name before generating the report.",
        "select_section":"Section"
    }
}

def t(key):
    lang = st.session_state.get("lang","FR")
    return TEXTS.get(lang,TEXTS["FR"]).get(key,key)

# -------------------------
# Session defaults
# -------------------------
for k,v in {"lang":"FR","user":None,"role":None,"linear_slope":None}.items():
    if k not in st.session_state: st.session_state[k]=v

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
        except Exception:
            pass
    return pdf.output(dest="S").encode("latin1")

# -------------------------
# OCR helper
# -------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
    if pytesseract is None: return pd.DataFrame(columns=["X","Y"])
    try: text = pytesseract.image_to_string(img)
    except Exception: return pd.DataFrame(columns=["X","Y"])
    rows=[]
    for line in text.splitlines():
        if not line.strip(): continue
        for sep in [",",";","\t"]:
            if sep in line:
                parts=[p.strip() for p in line.split(sep) if p.strip()!=""]
                if len(parts)>=2:
                    try:
                        x=float(parts[0].replace(",","."))
                        y=float(parts[1].replace(",","."))
                        rows.append([x,y]); break
                    except: pass
        else:
            parts=line.split()
            if len(parts)>=2:
                try: x=float(parts[0].replace(",","."))
                y=float(parts[1].replace(",","."))
                rows.append([x,y])
                except: pass
    return pd.DataFrame(rows, columns=["X","Y"])

# -------------------------
# Login
# -------------------------
def login_screen():
    st.markdown(f"<h1>{t('app_title')}</h1>", unsafe_allow_html=True)
    lang = st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="login_lang")
    st.session_state.lang = lang

    with st.form("login_form", clear_on_submit=False):
        cols = st.columns([2,1])
        with cols[0]: username = st.text_input(t("username"), key="username_login")
        with cols[1]: password = st.text_input(t("password"), type="password", key="password_login")
        submitted = st.form_submit_button(t("login"))

    if submitted:
        uname = (username or "").strip()
        matched = next((u for u in USERS if u.lower()==uname.lower()), None)
        if matched and USERS[matched]["password"]==(password or ""):
            st.session_state.user=matched
            st.session_state.role=USERS[matched].get("role","user")
            return
        st.error(t("invalid"))

# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header(t("admin"))
    st.subheader(t("add_user"))
    with st.form("form_add_user"):
        new_user = st.text_input(t("enter_username"), key="add_username")
        new_pass = st.text_input(t("enter_password"), type="password", key="add_password")
        role = st.selectbox("Role", ["user","admin"], key="add_role")
        add_sub = st.form_submit_button("Add")
    if add_sub:
        if not new_user.strip() or not new_pass.strip():
            st.warning("Enter username and password")
        elif any(u.lower()==new_user.strip().lower() for u in USERS):
            st.warning("User exists")
        else:
            USERS[new_user.strip()]={"password":new_pass.strip(),"role":role}
            save_users(USERS)
            st.success(f"User {new_user.strip()} added")
            st.rerun()

# -------------------------
# Linearity panel
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name")
    mode = st.radio("Input mode",[t("input_csv"), t("input_manual")], key="lin_input_mode")
    df=None

    if mode==t("input_csv"):
        uploaded = st.file_uploader("Upload CSV with two columns (conc, signal)", type=["csv"], key="lin_csv")
        if uploaded:
            df0=pd.read_csv(uploaded)
            if len(df0.columns)>=2:
                df=df0.iloc[:,:2].copy()
                df.columns=["Concentration","Signal"]
    else:
        conc_input=st.text_area("Concentrations (comma separated)", height=120, key="lin_manual_conc")
        sig_input=st.text_area("Signals (comma separated)", height=120, key="lin_manual_sig")
        if st.button("Load manual pairs"):
            try:
                concs=[float(c.replace(",",".").strip()) for c in conc_input.split(",") if c.strip()]
                sigs=[float(s.replace(",",".").strip()) for s in sig_input.split(",") if s.strip()]
                if len(concs)!=len(sigs): st.error("Number mismatch")
                elif len(concs)<2: st.warning("At least two pairs required")
                else: df=pd.DataFrame({"Concentration":concs,"Signal":sigs})
            except Exception as e: st.error(f"Parse error: {e}")

    if df is None: st.info("Provide data"); return
    df["Concentration"]=pd.to_numeric(df["Concentration"])
    df["Signal"]=pd.to_numeric(df["Signal"])
    coeffs=np.polyfit(df["Concentration"].values, df["Signal"].values,1)
    slope=float(coeffs[0]); intercept=float(coeffs[1])
    y_pred=np.polyval(coeffs, df["Concentration"].values)
    ss_res=np.sum((df["Signal"].values-y_pred)**2)
    ss_tot=np.sum((df["Signal"].values-np.mean(df["Signal"].values))**2)
    r2=float(1-ss_res/ss_tot) if ss_tot!=0 else 0.0
    st.session_state.linear_slope=slope

    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.4f}")

    fig, ax=plt.subplots(figsize=(7,3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs=np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope*xs+intercept, color="red", label="Fit")
    ax.set_xlabel(f"{t('concentration')}")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # Single unknown field
    val=st.number_input("Enter unknown value (signal or conc.)", format="%.6f", key="lin_unknown")
    choice=st.radio("Convert", [f"{t('signal')} → {t('concentration')}", f"{t('concentration')} → {t('signal')}"], key="lin_choice")
    try:
        if choice.startswith(t("signal")): conc=(val-intercept)/slope; st.success(f"Concentration={conc:.6f}")
        else: sigp=slope*val+intercept; st.success(f"Predicted signal={sigp:.6f}")
    except: st.error("Cannot compute")

    if st.button(t("generate_pdf"), key="lin_pdf"):
        if not company or company.strip()=="": st.warning(t("company_missing"))
        else:
            buf=io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); buf.seek(0)
            lines=[f"Company: {company}", f"User: {st.session_state.user}", f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"Slope: {slope:.6f}", f"Intercept: {intercept:.6f}", f"R²: {r2:.6f}"]
            logo_path=LOGO_FILE if True else None
            pdf_bytes=generate_pdf_bytes("Linearity report", lines, img_bytes=buf, logo_path=logo_path)
            st.download_button(t("download_pdf"), pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")

# -------------------------
# S/N panel
# -------------------------
def sn_panel():
    st.header(t("sn"))
    st.write(t("digitize_info"))
    uploaded=st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_uploader")
    df=None
    if uploaded:
        ext=uploaded.name.split(".")[-1].lower()
        if ext=="csv":
            df0=pd.read_csv(uploaded)
            if len(df0.columns)>=2: df=pd.DataFrame({"X":df0.iloc[:,0].values,"Y":df0.iloc[:,1].values})
        elif ext in ["png","jpg","jpeg"]:
            img=Image.open(uploaded).convert("RGB"); df=extract_xy_from_image_pytesseract(img)
            if df.empty: arr=np.array(img.convert("L")); df=pd.DataFrame({"X":np.arange(len(arr.max(axis=0))), "Y":arr.max(axis=0)})
        elif ext=="pdf" and convert_from_bytes:
            pages=convert_from_bytes(uploaded.read(), first_page=1, last_page=1, dpi=200)
            if pages: df=extract_xy_from_image_pytesseract(pages[0])
    if df is None:
        st.info("Manual S/N input")
        H=st.number_input("H (peak height)", value=0.0, format="%.6f")
        h=st.number_input("h (noise)", value=0.0, format="%.6f")
        slope_input=st.number_input("Slope (optional)", value=float(st.session_state.linear_slope or 0.0), format="%.6f")
        sn_classic=H/h if h!=0 else float("nan"); sn_usp=2*H/h if h!=0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}"); st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        if slope_input!=0:
            lod=3.3*h/slope_input; loq=10*h/slope_input
            st.write(f"{t('lod')}: {lod:.6f}"); st.write(f"{t('loq')}: {loq:.6f}")
        return

    df=df.dropna().sort_values("X").reset_index(drop=True)
    st.subheader(t("select_region"))
    x_min=float(df["X"].min()); x_max=float(df["X"].max())
    start,end=st.slider("", min_value=x_min,max_value=x_max,value=(x_min+0.25*(x_max-x_min), x_min+0.75*(x_max-x_min)), step=(x_max-x_min)/100.0, key="sn_region_slider")
    region=df[(df["X"]>=start)&(df["X"]<=end)]
    fig, ax=plt.subplots(figsize=(10,3))
    ax.plot(df["X"], df["Y"], label="Chromatogram"); ax.axvspan(start,end,color="orange",alpha=0.3,label="Selected region")
    ax.set_xlabel("X"); ax.set_ylabel("Signal"); ax.legend(); st.pyplot(fig)
    if region.shape[0]>=2:
        peak=float(region["Y"].max()); baseline=float(region["Y"].mean()); height=peak-baseline
        noise_std=float(region["Y"].std(ddof=0))
        unit=st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="sn_unit_region")
        sn_classic=peak/noise_std if noise_std!=0 else float("nan")
        sn_usp=height/noise_std if noise_std!=0 else float("nan")
        st.write(f"{t('sn_classic')}: {sn_classic:.4f}"); st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
        slope_for_conversion=st.session_state.linear_slope
        user_slope=st.number_input("Optional slope for conc. conversion", value=0.0, format="%.6f", key="sn_user_slope")
        slope_to_use=slope_for_conversion if slope_for_conversion else (user_slope if user_slope!=0 else None)
        if slope_to_use:
            lod=3.3*noise_std/slope_to_use; loq=10*noise_std/slope_to_use
            st.write(f"{t('lod')} ({unit}): {lod:.6f}"); st.write(f"{t('loq')} ({unit}): {loq:.6f}")
        csv_buf=io.StringIO(); pd.DataFrame({"X":region["X"],"Signal":region["Y"]}).to_csv(csv_buf,index=False)
        st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv")
        if st.button(t("export_sn_pdf")):
            company=st.text_input(t("company"), key="sn_company_name")
            if not company or company.strip()=="": st.warning(t("company_missing"))
            else:
                img_buf=io.BytesIO(); fig.savefig(img_buf, format="png", bbox_inches="tight"); img_buf.seek(0)
                lines=[f"Company: {company}", f"User: {st.session_state.user}", f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"S/N classic: {sn_classic:.4f}", f"S/N USP: {sn_usp:.4f}"]
                pdf_bytes=generate_pdf_bytes("S/N report", lines, img_bytes=img_buf, logo_path=LOGO_FILE)
                st.download_button(t("download_pdf"), pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")

# -------------------------
# Main
# -------------------------
def main():
    if st.session_state.user is None:
        login_screen()
        return

    # Header + logout
    st.markdown(f"<h4>{t('app_title')} — {st.session_state.user} ({st.session_state.role})</h4>", unsafe_allow_html=True)
    st.button(t("logout"), on_click=lambda: st.session_state.update({"user":None, "role":None, "linear_slope":None}))

    # Language selector
    lang = st.selectbox("", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="top_lang")
    st.session_state.lang = lang

    # Sections per role
    sections=[]
    if st.session_state.role=="admin": sections.append(t("admin"))
    elif st.session_state.role=="user": sections.extend([t("linearity"), t("sn")])
    if not sections: st.warning("No sections"); return

    # Horizontal tabs
    tabs=st.tabs(sections)
    for i, sec in enumerate(sections):
        with tabs[i]:
            if sec==t("admin") and st.session_state.role=="admin": admin_panel()
            elif sec==t("linearity") and st.session_state.role=="user": linearity_panel()
            elif sec==t("sn") and st.session_state.role=="user": sn_panel()

if __name__=="__main__":
    main()