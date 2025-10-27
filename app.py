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
if "force_rerun" not in st.session_state:
    st.session_state.force_rerun = False
# -------------------------
# Minimal admin panel
# -------------------------
def admin_panel():
    st.info("Admin panel (fonctionnalité à compléter)")

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
# S/N panel full with original-scale extraction
# -------------------------
def sn_panel_full():
    st.header(t("sn"))
    st.write(t("digitize_info"))
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_uploader")

    if uploaded is None:
        st.info("Upload a file or use manual S/N input.")
        sn_manual_mode = True
    else:
        sn_manual_mode = False

    unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0, key="sn_unit")

    # Manual input
    if sn_manual_mode:
        st.subheader("Manual S/N calculation")
        H = st.number_input("H (peak height)", value=1.0)
        h = st.number_input("h (noise)", value=0.1)
        slope_input = st.number_input("Slope (optional for conc. calculation)", value=float(st.session_state.linear_slope or 1.0))
        if st.button("Compute S/N"):
            sn_classic = H / h if h != 0 else float("nan")
            sn_usp = 2 * H / h if h != 0 else float("nan")
            st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
            st.write(f"{t('sn_usp')}: {sn_usp:.4f}")
            if slope_input != 0:
                lod = 3.3 * h / slope_input
                loq = 10 * h / slope_input
                st.write(f"{t('lod')} ({unit}): {lod:.4f}")
                st.write(f"{t('loq')} ({unit}): {loq:.4f}")
        return

    ext = uploaded.name.split(".")[-1].lower()
    signal = None
    time_index = None

    # CSV
    if ext == "csv":
        try:
            uploaded.seek(0)
            df = pd.read_csv(uploaded)
            cols_low = [c.lower() for c in df.columns]
            if "time" in cols_low and "signal" in cols_low:
                time_index = df.iloc[:, cols_low.index("time")].values
                signal = pd.to_numeric(df.iloc[:, cols_low.index("signal")], errors="coerce").fillna(0).values
            elif len(df.columns) >= 2:
                time_index = df.iloc[:, 0].values
                signal = pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0).values
            else:
                st.error("CSV must have at least two columns (time, signal).")
                return
            st.subheader("Raw data preview")
            st.dataframe(df.head(50))
        except Exception as e:
            st.error(f"CSV error: {e}")
            return

    # Image (PNG/JPG)
    elif ext in ("png", "jpg", "jpeg"):
        try:
            uploaded.seek(0)
            img = Image.open(uploaded).convert("RGB")
            st.image(img, caption=uploaded.name, use_column_width=True)
            arr = np.array(img.convert("L"))
            signal = arr.max(axis=0).astype(float)
            time_index = np.arange(len(signal))
        except Exception as e:
            st.error(f"Image error: {e}")
            return

    # PDF
    elif ext == "pdf":
        if convert_from_bytes is None:
            st.warning("PDF digitizing requires pdf2image + poppler.")
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
            signal = arr.max(axis=0).astype(float)
            time_index = np.arange(len(signal))
        except Exception as e:
            st.error(f"PDF error: {e}")
            return
    else:
        st.error("Unsupported file type")
        return

    # Region selection sliders
    if signal is not None:
        n = len(signal)
        st.subheader(t("select_region"))
        start, end = st.slider("", 0, n - 1, (0, n-1), key="sn_region_slider")
        region = signal[start:end+1]
        if len(region) < 2:
            st.warning("Select a larger region")
            return

        peak = float(np.max(region))
        baseline = float(np.mean(region))
        height = peak - baseline
        noise_std = float(np.std(region, ddof=0))

        sn_classic = peak / noise_std if noise_std != 0 else float("nan")
        sn_usp = height / noise_std if noise_std != 0 else float("nan")

        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")

        if st.session_state.linear_slope is not None:
            slope = st.session_state.linear_slope
            if slope != 0:
                lod = 3.3 * noise_std / slope
                loq = 10 * noise_std / slope
                st.write(f"{t('lod')} ({unit}): {lod:.4f}")
                st.write(f"{t('loq')} ({unit}): {loq:.4f}")

        # Export CSV
        csv_buf = io.StringIO()
        pd.DataFrame({"Point": np.arange(start, end+1), "Signal": region}).to_csv(csv_buf, index=False)
        st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv")

        # Export PDF
        if st.button(t("export_sn_pdf"), key="sn_export_pdf"):
            ffig, axf = plt.subplots(figsize=(7,3))
            axf.plot(time_index[start:end+1], region)
            axf.set_title("Selected region")
            axf.set_xlabel("Time (original)")
            axf.set_ylabel("Signal")
            buf = io.BytesIO()
            ffig.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            lines = [
                f"File: {uploaded.name}",
                f"User: {st.session_state.user or 'Unknown'}",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"{t('sn_classic')}: {sn_classic:.4f}",
                f"{t('sn_usp')}: {sn_usp:.4f}"
            ]
            if st.session_state.linear_slope is not None and noise_std != 0:
                slope = st.session_state.linear_slope
                if slope != 0:
                    lines.append(f"Slope (linearity): {slope:.4f}")
                    lines.append(f"{t('lod')} ({unit}): {lod:.4f}")
                    lines.append(f"{t('loq')} ({unit}): {loq:.4f}")
            try:
                import os
                logo_path = LOGO_FILE if os.path.exists(LOGO_FILE) else None
            except Exception:
                logo_path = None
            pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=buf, logo_path=logo_path)
            st.download_button("Download S/N PDF", pdfb, file_name="sn_report.pdf", mime="application/pdf")


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