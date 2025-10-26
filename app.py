# app.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
from datetime import datetime
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt

# Optional imports (only used when available)
try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# ---------------------------
# Config page (once at top)
# ---------------------------
st.set_page_config(page_title="LabT", layout="wide")

# ---------------------------
# Helpers: files & users
# ---------------------------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception:
        # fallback default
        return {"admin": {"password": "admin123", "role": "admin"},
                "user": {"password": "user123", "role": "user"}}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

# ---------------------------
# Translations (simple)
# ---------------------------
TEXTS = {
    "FR": {
        "app_title": "LabT",
        "powered": "Powered by BnB",
        "login": "Utilisateur",
        "password": "Mot de passe",
        "login_btn": "Connexion",
        "logout": "Déconnexion",
        "invalid": "Identifiants invalides",
        "menu_linearity": "Linéarité",
        "menu_sn": "S/N",
        "menu_admin": "Admin",
        "company": "Nom de la compagnie",
        "input_csv": "CSV",
        "input_manual": "Saisie manuelle",
        "concentration": "Concentration",
        "signal": "Signal",
        "unit": "Unité",
        "generate_pdf": "Générer rapport PDF",
        "download_pdf": "Télécharger PDF",
        "download_csv": "Télécharger CSV",
        "sn_classic": "S/N Classique",
        "sn_usp": "S/N USP",
        "lod": "LOD (concentration)",
        "loq": "LOQ (concentration)",
        "formulas": "Afficher formules",
        "select_region": "Sélectionner zone",
        "add_user": "Ajouter utilisateur",
        "del_user": "Supprimer utilisateur",
        "modify_user": "Modifier mot de passe",
        "enter_username": "Nom d'utilisateur",
        "enter_password": "Mot de passe (simple)",
        "ok": "OK",
        "upload_chrom": "Importer chromatogramme (CSV, PNG, PDF)",
        "digitize_info": "Digitizing: OCR attempted if PyTesseract available",
    },
    "EN": {
        "app_title": "LabT",
        "powered": "Powered by BnB",
        "login": "Username",
        "password": "Password",
        "login_btn": "Login",
        "logout": "Logout",
        "invalid": "Invalid credentials",
        "menu_linearity": "Linearity",
        "menu_sn": "Signal / Noise",
        "menu_admin": "Admin",
        "company": "Company name",
        "input_csv": "CSV",
        "input_manual": "Manual input",
        "concentration": "Concentration",
        "signal": "Signal",
        "unit": "Unit",
        "generate_pdf": "Generate PDF report",
        "download_pdf": "Download PDF",
        "download_csv": "Download CSV",
        "sn_classic": "S/N Classic",
        "sn_usp": "S/N USP",
        "lod": "LOD (conc.)",
        "loq": "LOQ (conc.)",
        "formulas": "Show formulas",
        "select_region": "Select region",
        "add_user": "Add user",
        "del_user": "Delete user",
        "modify_user": "Modify password",
        "enter_username": "Username",
        "enter_password": "Password (simple)",
        "ok": "OK",
        "upload_chrom": "Upload chromatogram (CSV, PNG, PDF)",
        "digitize_info": "Digitizing: OCR attempted if PyTesseract available",
    }
}

def t(key):
    lang = st.session_state.get("lang", "FR")
    return TEXTS.get(lang, TEXTS["FR"]).get(key, key)

# ---------------------------
# Session defaults
# ---------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "FR"            # default FR
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "linear_slope" not in st.session_state:
    st.session_state.linear_slope = None

USERS = load_users()

# ---------------------------
# Authentication (no app shown before login)
# ---------------------------
def login_screen():
    st.markdown("<h1 style='margin-bottom:0.1rem;'>%s</h1>" % t("app_title"), unsafe_allow_html=True)
    st.write("")  # spacing
    lang = st.selectbox("Language / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="lang_select")
    st.session_state.lang = lang
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(t("login"), key="login_username")
    with col2:
        password = st.text_input(t("password"), type="password", key="login_password")

    if st.button(t("login_btn"), key="login_button"):
        # case-insensitive username
        uname = username.strip()
        if not uname:
            st.error(t("invalid"))
            return
        matched = None
        for u in USERS:
            if u.lower() == uname.lower():
                matched = u
                break
        if matched and USERS[matched]["password"] == password:
            st.session_state.user = matched
            st.session_state.role = USERS[matched]["role"]
            st.experimental_rerun()  # safe here to refresh to main_app
        else:
            st.error(t("invalid"))

    st.markdown("<div style='position:fixed;bottom:10px;left:0;right:0;text-align:center;color:gray;'>%s</div>" % t("powered"), unsafe_allow_html=True)

# ---------------------------
# Admin: manage users (buttons)
# ---------------------------
def admin_panel():
    st.header(t("menu_admin"))
    st.write(t("manage_users"))
    st.write("")  # spacing

    col_a, col_b = st.columns([2,3])
    with col_a:
        st.subheader("Existing users")
        for u,info in list(USERS.items()):
            row_cols = st.columns([3,1,1])
            row_cols[0].write(f"{u}  — role: {info.get('role','user')}")
            # Modify password
            if row_cols[1].button("Modify", key=f"modify_{u}"):
                new_pwd = st.text_input(f"New password for {u}", type="password", key=f"pwd_{u}")
                if st.button("Save", key=f"save_{u}"):
                    if new_pwd:
                        USERS[u]["password"] = new_pwd
                        save_users(USERS)
                        st.success(f"Password updated for {u}")
                        st.experimental_rerun()
            # Delete (except admin)
            if row_cols[2].button("Delete", key=f"delete_{u}"):
                if u == "admin":
                    st.warning("Cannot delete admin")
                else:
                    USERS.pop(u)
                    save_users(USERS)
                    st.success(f"{u} deleted")
                    st.experimental_rerun()

    with col_b:
        st.subheader(t("add_user"))
        new_user = st.text_input(t("enter_username"), key="new_user")
        new_pass = st.text_input(t("enter_password"), type="password", key="new_pass")
        role = st.selectbox("Role", ["user","admin"], key="new_role")
        if st.button("Add", key="add_user_btn"):
            if new_user.strip() == "" or new_pass.strip() == "":
                st.warning("Please enter username and password")
            else:
                if new_user in USERS:
                    st.warning("User exists")
                else:
                    USERS[new_user] = {"password": new_pass, "role": role}
                    save_users(USERS)
                    st.success(f"User {new_user} added")
                    st.experimental_rerun()

# ---------------------------
# Utility: PDF generation (returns bytes)
# ---------------------------
def generate_pdf_bytes(title, lines, img_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=1, align="C")
    pdf.set_font("Arial", "", 11)
    pdf.ln(4)
    for line in lines:
        pdf.multi_cell(0, 7, line)
    if img_bytes is not None:
        try:
            # put image centered, width max 170
            pdf.ln(4)
            pdf.image(img_bytes, x=20, w=170)
        except Exception:
            pass
    out = pdf.output(dest="S").encode("latin1")
    return out

# ---------------------------
# Linearity panel
# ---------------------------
def linearity_panel():
    st.header(t("menu_linearity"))
    company = st.text_input(t("company"), key="company_name")
    # Input choice
    input_mode = st.radio("Input mode", [t("input_csv"), t("input_manual")], key="linear_input_mode")
    df = None

    if input_mode == t("input_csv"):
        uploaded = st.file_uploader("Upload CSV with two columns: concentration,signal", type=["csv"], key="lin_csv")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                # normalize column names if possible
                cols_lower = [c.lower() for c in df.columns]
                if "x" in cols_lower and "y" in cols_lower:
                    df.columns = ["Concentration","Signal"]
                elif len(df.columns) >= 2:
                    df = df.iloc[:, :2]
                    df.columns = ["Concentration","Signal"]
            except Exception as e:
                st.error(f"CSV error: {e}")
                df = None
    else:
        st.caption("Enter values separated by commas; either on one line or several lines (concentration,signal).")
        manual = st.text_area("Manual pairs (one pair per line, comma separated) e.g. 1, 0.123", height=120, key="lin_manual")
        if manual.strip():
            rows = []
            for line in manual.splitlines():
                parts = line.replace(";",",").split(",")
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].strip())
                        y = float(parts[1].strip())
                        rows.append([x,y])
                    except:
                        continue
            if rows:
                df = pd.DataFrame(rows, columns=["Concentration","Signal"])

    unit = st.selectbox(t("unit"), ["µg/mL", "mg/mL", "ng/mL"], index=0, key="unit_select")

    if df is None:
        st.info("Please load data (CSV) or enter manually.")
        return

    if len(df) < 2:
        st.warning("Enter at least 2 points.")
        return

    # Ensure numeric and drop NaNs
    df = df.dropna().reset_index(drop=True)
    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"])
        df["Signal"] = pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Data must be numeric.")
        return

    # Linear regression (simple, sklearn optional)
    X = df["Concentration"].values.reshape(-1,1)
    Y = df["Signal"].values
    # compute slope/intercept via polyfit for robustness
    coeffs = np.polyfit(df["Concentration"], df["Signal"], 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"])
    # r2
    ss_res = np.sum((df["Signal"] - y_pred)**2)
    ss_tot = np.sum((df["Signal"] - np.mean(df["Signal"]))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot != 0 else 0.0

    # store slope exportable to S/N
    st.session_state.linear_slope = slope

    # Display results with 4 decimals
    st.metric("Slope", f"{slope:.4f}")
    st.metric("Intercept", f"{intercept:.4f}")
    st.metric("R²", f"{r2:.4f}")

    # Plot (matplotlib)
    fig, ax = plt.subplots(figsize=(6,3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 100)
    ax.plot(xs, slope*xs + intercept, color="red", label="Fit")
    ax.set_xlabel(f"Concentration ({unit})")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)

    # Unknown conversion live (no extra button)
    calc_choice = st.radio("Calculate", ["Signal → Concentration", "Concentration → Signal"], key="lin_calc_choice")
    if calc_choice.startswith("Signal"):
        val = st.number_input("Enter signal", format="%.4f", key="lin_unknown_signal")
        if val is not None:
            try:
                conc = (val - intercept) / slope
                st.success(f"Concentration = {conc:.4f} {unit}")
            except Exception:
                st.error("Cannot compute (division by zero or invalid slope).")
    else:
        val = st.number_input("Enter concentration", format="%.4f", key="lin_unknown_conc")
        if val is not None:
            sigp = slope*val + intercept
            st.success(f"Predicted signal = {sigp:.4f}")

    # Show formulas optionally
    with st.expander(t("formulas")):
        st.markdown(r"""
        **Linearity equation:** \( y = slope \cdot X + intercept \)  
        **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
        **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
        """)

    # Export PDF report with chart embedded (save chart to bytes via PIL)
    if st.button(t("generate_pdf")):
        # Convert matplotlib fig to PNG bytes
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        pdf_lines = [
            f"Company: {company or 'N/A'}",
            f"Generated by: {st.session_state.user or 'Unknown'}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Slope: {slope:.4f}",
            f"Intercept: {intercept:.4f}",
            f"R²: {r2:.4f}",
        ]
        pdf_bytes = generate_pdf_bytes("Linearity report", pdf_lines, img_bytes=buf)
        st.download_button(t("download_pdf"), data=pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")

# ---------------------------
# Simple digitize helper (OCR attempt)
# ---------------------------
def extract_xy_from_image_pytesseract(img: Image.Image):
    """
    Try to extract pairs from OCRed text lines: best-effort.
    Returns DataFrame with columns X, Y or empty DF.
    """
    if pytesseract is None:
        return pd.DataFrame(columns=["X","Y"])
    text = pytesseract.image_to_string(img)
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        # common separators: comma, whitespace, tab, semicolon
        for sep in [",", "\t", ";"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep) if p.strip()!=""]
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(",","."))
                        y = float(parts[1].replace(",","."))
                        rows.append([x,y])
                        break
                    except:
                        pass
        else:
            # try whitespace split
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(",","."))
                    y = float(parts[1].replace(",","."))
                    rows.append([x,y])
                except:
                    pass
    return pd.DataFrame(rows, columns=["X","Y"])

# ---------------------------
# Signal / Noise panel
# ---------------------------
def sn_panel():
    st.header(t("menu_sn"))
    st.write(t("digitize_info"))
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_file")
    signal = None
    time_index = None

    if uploaded is None:
        st.info("Upload a file (CSV with Time/Signal or PNG/PDF chromatogram).")
        return

    ext = uploaded.name.split(".")[-1].lower()

    # CSV: expect two columns (time, signal) or (Signal)
    if ext == "csv":
        try:
            df = pd.read_csv(uploaded)
            # try to find time/signal columns
            cols_low = [c.lower() for c in df.columns]
            if "time" in cols_low and "signal" in cols_low:
                df.columns = [c.strip() for c in df.columns]
                time_index = df.iloc[:, cols_low.index("time")]
                signal = df.iloc[:, cols_low.index("signal")].values
            elif len(df.columns) >= 2:
                time_index = df.iloc[:,0]
                signal = pd.to_numeric(df.iloc[:,1], errors="coerce").fillna(0).values
            else:
                st.error("CSV format not recognized (need at least 2 columns).")
                return
            st.write("Raw data preview:")
            st.dataframe(df.head(50))
            # plot raw
            fig, ax = plt.subplots(figsize=(6,3))
            ax.plot(time_index, signal)
            ax.set_xlabel("Time / points")
            ax.set_ylabel("Signal")
            st.pyplot(fig)
        except Exception as e:
            st.error(f"CSV error: {e}")
            return

    # PNG/JPG: show original, attempt digitize with OCR if available
    elif ext in ("png","jpg","jpeg"):
        try:
            img = Image.open(uploaded).convert("RGB")
            st.image(img, caption=uploaded.name, use_column_width=True)
            # simple digitize: vertical projection (very approximate)
            arr = np.array(img.convert("L"))
            # use max over rows (vertical chromatogram-ish) as signal
            signal = arr.max(axis=0).astype(float)
            time_index = np.arange(len(signal))
            fig, ax = plt.subplots(figsize=(6,3))
            ax.plot(time_index, signal)
            ax.set_xlabel("Points")
            ax.set_ylabel("Signal")
            st.pyplot(fig)
            # Try OCR extraction of pairs (best-effort)
            df_ocr = extract_xy_from_image_pytesseract(img) if pytesseract else pd.DataFrame()
            if not df_ocr.empty:
                st.info("OCR extracted data (best-effort):")
                st.dataframe(df_ocr.head(20))
        except Exception as e:
            st.error(f"Image processing error: {e}")
            return

    # PDF: attempt convert_from_path when available (poppler needed)
    elif ext == "pdf":
        if convert_from_path is None:
            st.warning("PDF digitizing requires pdf2image + poppler installed in the environment.")
            # offer download original for user to open locally
            uploaded.seek(0)
            st.download_button("Download original PDF", uploaded.read(), file_name=uploaded.name)
            return
        try:
            # convert first page to image
            tmp_images = convert_from_path(uploaded, first_page=1, last_page=1)
            if len(tmp_images) == 0:
                st.error("No pages extracted from PDF")
                return
            img = tmp_images[0]
            st.image(img, caption=uploaded.name, use_column_width=True)
            arr = np.array(img.convert("L"))
            signal = arr.max(axis=0).astype(float)
            time_index = np.arange(len(signal))
            fig, ax = plt.subplots(figsize=(6,3))
            ax.plot(time_index, signal)
            ax.set_xlabel("Points")
            ax.set_ylabel("Signal")
            st.pyplot(fig)
            # OCR attempt
            df_ocr = extract_xy_from_image_pytesseract(img) if pytesseract else pd.DataFrame()
            if not df_ocr.empty:
                st.info("OCR extracted data (best-effort):")
                st.dataframe(df_ocr.head(20))
        except Exception as e:
            st.error(f"PDF processing error: {e}")
            return

    else:
        st.error("Unsupported file type")
        return

    # If we have signal vector, let user choose region (sliders)
    if signal is not None:
        n = len(signal)
        st.subheader(t("select_region"))
        # default region half
        default_start = 0
        default_end = n-1
        start, end = st.slider("", 0, n-1, (default_start, default_end), key="sn_slider")
        region = signal[start:end+1]
        if len(region) < 2:
            st.warning("Select a larger region")
            return

        # metrics
        peak = float(np.max(region))
        noise_std = float(np.std(region))
        sn_classic = (peak / noise_std) if noise_std != 0 else float("nan")
        # USP: height / std(noise). Height chosen as peak minus baseline approx = peak - mean(noise)
        # For this demo, use (peak - baseline_mean)/noise_std
        baseline_mean = float(np.mean(region))
        height = peak - baseline_mean
        sn_usp = (height / noise_std) if noise_std != 0 else float("nan")

        st.write(f"{t('sn_classic')}: {sn_classic:.4f}")
        st.write(f"{t('sn_usp')}: {sn_usp:.4f}")

        # LOQ/LOD in concentration if slope exported
        if st.session_state.linear_slope:
            slope = st.session_state.linear_slope
            sd = noise_std
            if slope != 0:
                lod = 3.3 * sd / slope
                loq = 10 * sd / slope
                st.write(f"{t('lod')}: {lod:.4f}")
                st.write(f"{t('loq')}: {loq:.4f}")
            else:
                st.info("Linearity slope is zero, cannot compute LOD/LOQ in concentration.")
        else:
            st.info("Linearity slope not available. Export slope from Linearity panel to compute LOD/LOQ in concentration.")

        # show formulas expander
        with st.expander(t("formulas")):
            st.markdown(r"""
            **Classic S/N:** \( \dfrac{Signal_{peak}}{\sigma_{noise}} \)  
            **USP S/N:** \( \dfrac{Height}{\sigma_{noise}} \) where Height ≈ (peak - baseline)  
            **LOD (conc)** = \( 3.3 \cdot \dfrac{\sigma_{noise}}{slope} \)  
            **LOQ (conc)** = \( 10 \cdot \dfrac{\sigma_{noise}}{slope} \)
            """)

        # Export CSV of selected region
        csv_buf = io.StringIO()
        pd.DataFrame({"Point": np.arange(start, end+1), "Signal": region}).to_csv(csv_buf, index=False)
        st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv")

        # Export PDF report with metrics and thumbnail plot
        if st.button("Export S/N PDF"):
            # small figure bytes
            fig2, ax2 = plt.subplots(figsize=(6,2.5))
            ax2.plot(np.arange(start, end+1), region)
            ax2.set_title("Selected region")
            ax2.set_xlabel("Point")
            ax2.set_ylabel("Signal")
            buf = io.BytesIO()
            fig2.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            lines = [
                f"File: {uploaded.name}",
                f"User: {st.session_state.user or 'Unknown'}",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"{t('sn_classic')}: {sn_classic:.4f}",
                f"{t('sn_usp')}: {sn_usp:.4f}"
            ]
            if st.session_state.linear_slope:
                lines.append(f"Slope (linearity): {st.session_state.linear_slope:.4f}")
                if slope != 0:
                    lines.append(f"{t('lod')}: {lod:.4f}")
                    lines.append(f"{t('loq')}: {loq:.4f}")
            pdfb = generate_pdf_bytes("S/N Report", lines, img_bytes=buf)
            st.download_button("Download S/N PDF", pdfb, file_name="sn_report.pdf", mime="application/pdf")

# ---------------------------
# Top-level main app
# ---------------------------
def main_app():
    st.sidebar.title(f"{t('app_title')} - {st.session_state.user}")
    # language switch
    st.sidebar.selectbox("Lang / Langue", ["FR","EN"], index=0 if st.session_state.lang=="FR" else 1, key="side_lang", on_change=lambda: st.session_state.update({"lang": st.session_state.side_lang}))
    # logout
    if st.sidebar.button(t("logout")):
        # clear session and return to login (no experimental_rerun required)
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.linear_slope = None
        st.experimental_rerun()

    if st.session_state.role == "admin":
        opt = st.sidebar.radio("Menu", [t("menu_admin")])
    else:
        opt = st.sidebar.radio("Menu", [t("menu_linearity"), t("menu_sn")])

    if opt == t("menu_admin"):
        admin_panel()
    elif opt == t("menu_linearity"):
        linearity_panel()
    elif opt == t("menu_sn"):
        sn_panel()
    else:
        st.info("Select a menu")

# ---------------------------
# App entry
# ---------------------------
def run():
    if st.session_state.user:
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    run()