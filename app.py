# app.py
# LabT - Linearity & S/N tool (bilingual FR/EN) with user management and basic digitizing
# Paste this file into your repo root.

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import io, os, json
from PIL import Image, ImageOps

# try optional libs for PDF/image handling
try:
    import fitz  # pymupdf
except Exception:
    fitz = None
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

# optional: SciPy for regressions (we also implement fallback)
try:
    from scipy import stats
except Exception:
    stats = None

# -------------------------
# Configuration
# -------------------------
USERS_FILE = "users.json"
DEFAULT_USERS = {"admin": {"password": "admin", "role": "admin"}}
DEFAULT_UNIT = "µg/mL"

# -------------------------
# Utilitaires i18n
# -------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "EN"  # default

def T(en, fr):
    return fr if st.session_state.lang == "FR" else en

def language_selector():
    st.selectbox("🌐 Language / Langue", ["EN", "FR"], index=0 if st.session_state.lang=="EN" else 1,
                 key="lang_selectbox", on_change=_on_change_lang)

def _on_change_lang():
    # store language selection
    st.session_state.lang = st.session_state.get("lang_selectbox", "EN")

# -------------------------
# Users management
# -------------------------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump(DEFAULT_USERS, f, indent=2)

def load_users():
    ensure_users_file()
    try:
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
        # migrate simple format to structured format if needed
        if isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
            new = {k: {"password": v, "role": ("admin" if k=="admin" else "user")} for k,v in data.items()}
            save_users(new)
            return new
        return data
    except Exception:
        save_users(DEFAULT_USERS)
        return DEFAULT_USERS.copy()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def add_user_form():
    st.subheader(T("Add user", "Ajouter un utilisateur"))
    new_user = st.text_input(T("Username", "Nom d'utilisateur"), key="add_user_name")
    new_pass = st.text_input(T("Password", "Mot de passe"), type="password", key="add_user_pass")
    role = st.selectbox(T("Role", "Rôle"), ["user", "admin"], key="add_user_role")
    if st.button(T("Create user", "Créer utilisateur"), key="btn_add_user"):
        users = load_users()
        uname = new_user.strip().lower()
        if uname == "" or new_pass.strip() == "":
            st.error(T("Enter username and password", "Entrer nom et mot de passe"))
            return
        if uname in users:
            st.error(T("User already exists", "L'utilisateur existe déjà"))
            return
        users[uname] = {"password": new_pass, "role": role}
        save_users(users)
        st.success(T("User added", "Utilisateur ajouté"))

def edit_user_form():
    st.subheader(T("Edit / Delete user", "Modifier / Supprimer un utilisateur"))
    users = load_users()
    user_list = sorted(users.keys())
    sel = st.selectbox(T("Select user", "Sélectionner utilisateur"), user_list, key="sel_user")
    if sel:
        col1, col2 = st.columns(2)
        with col1:
            new_pass = st.text_input(T("New password", "Nouveau mot de passe"), type="password", key=f"edit_pass_{sel}")
        with col2:
            new_role = st.selectbox(T("Role", "Rôle"), ["user","admin"], index=0 if users[sel].get("role","user")=="user" else 1, key=f"edit_role_{sel}")
        if st.button(T("Update user", "Mettre à jour"), key=f"btn_update_{sel}"):
            users[sel]["password"] = new_pass if new_pass.strip()!="" else users[sel]["password"]
            users[sel]["role"] = new_role
            save_users(users)
            st.success(T("User updated", "Utilisateur mis à jour"))
        if st.button(T("Delete user", "Supprimer utilisateur"), key=f"btn_delete_{sel}"):
            if sel == "admin":
                st.error(T("Cannot delete admin", "Impossible de supprimer admin"))
            else:
                users.pop(sel, None)
                save_users(users)
                st.success(T("User deleted", "Utilisateur supprimé"))

# -------------------------
# Auth (login/logout/profile)
# -------------------------
def login_page():
    st.title("LabT")
    st.write(T("Please log in to continue.", "Veuillez vous connecter pour continuer."))
    username = st.text_input(T("Username", "Nom d'utilisateur"), key="login_usr")
    password = st.text_input(T("Password", "Mot de passe"), type="password", key="login_pwd")
    if st.button(T("Login", "Connexion"), key="btn_login"):
        users = load_users()
        uname = username.strip().lower()
        if uname in users and users[uname]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = uname
            st.session_state.role = users[uname].get("role","user")
            st.experimental_rerun()
        else:
            st.error(T("Invalid username or password", "Utilisateur ou mot de passe invalide"))

def logout_action():
    # single click logout placed in top-right via st.sidebar
    if st.sidebar.button(T("Logout", "Déconnexion"), key="logout_btn"):
        for k in list(st.session_state.keys()):
            # keep language choice
            if k not in ("lang",):
                st.session_state.pop(k, None)
        st.experimental_rerun()

def profile_change_password():
    st.subheader(T("Change your password", "Changer votre mot de passe"))
    old = st.text_input(T("Old password", "Ancien mot de passe"), type="password", key="profile_old")
    new = st.text_input(T("New password", "Nouveau mot de passe"), type="password", key="profile_new")
    confirm = st.text_input(T("Confirm", "Confirmer"), type="password", key="profile_confirm")
    if st.button(T("Change password", "Changer mot de passe"), key="profile_change_btn"):
        users = load_users()
        uname = st.session_state.user
        if users[uname]["password"] != old:
            st.error(T("Incorrect old password", "Ancien mot de passe incorrect"))
            return
        if new != confirm:
            st.error(T("Passwords do not match", "Les mots de passe ne correspondent pas"))
            return
        users[uname]["password"] = new
        save_users(users)
        st.success(T("Password updated", "Mot de passe mis à jour"))

# -------------------------
# Linearity tools
# -------------------------
def compute_regression(x, y):
    # uses scipy if available, else np.polyfit
    try:
        if stats is not None:
            slope, intercept, r_value, p, stderr = stats.linregress(x, y)
            return float(slope), float(intercept), float(r_value**2)
        else:
            p = np.polyfit(x, y, 1)
            slope = float(p[0])
            intercept = float(p[1])
            # compute r2
            ypred = slope*np.array(x)+intercept
            ss_res = np.sum((np.array(y)-ypred)**2)
            ss_tot = np.sum((np.array(y)-np.mean(y))**2)
            r2 = 1 - ss_res/ss_tot if ss_tot!=0 else 0.0
            return slope, intercept, r2
    except Exception as e:
        raise

def linearity_section():
    st.header(T("Linearity / Linéarité", "Linearity / Linéarité"))
    mode = st.radio(T("Data source", "Source de données"), [T("CSV upload", "Importer CSV"), T("Manual entry", "Saisie manuelle")], horizontal=True, key="lin_mode")
    df = None
    if mode == T("CSV upload", "Importer CSV"):
        uploaded = st.file_uploader(T("CSV with at least two columns (conc, signal)", "CSV contenant au moins deux colonnes (conc, signal)"), type="csv", key="lin_csv")
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                if df.shape[1] < 2:
                    st.error(T("CSV must have at least two columns.", "Le CSV doit contenir au moins deux colonnes."))
                    return None
                # take first two columns
                df = df.iloc[:,0:2].copy()
                df.columns = ["Concentration","Signal"]
            except Exception as e:
                st.error(T("Error reading CSV:", "Erreur lecture CSV:") + f" {e}")
                return None
    else:
        # manual entry: two comma-separated lists
        conc_txt = st.text_area(T("Enter concentrations separated by commas", "Entrer concentrations séparées par des virgules"), key="manual_conc")
        sig_txt = st.text_area(T("Enter signals separated by commas", "Entrer signaux séparés par des virgules"), key="manual_sig")
        if conc_txt.strip() != "" and sig_txt.strip() != "":
            try:
                conc = [float(s.strip()) for s in conc_txt.split(",") if s.strip()!=""]
                sig = [float(s.strip()) for s in sig_txt.split(",") if s.strip()!=""]
                if len(conc) != len(sig) or len(conc) < 2:
                    st.error(T("Provide same number of values and at least 2 points.", "Fournir le même nombre de valeurs et au moins 2 points."))
                    return None
                df = pd.DataFrame({"Concentration":conc,"Signal":sig})
            except Exception as e:
                st.error(T("Parsing error:", "Erreur de parsing:") + f" {e}")
                return None

    if df is None:
        return None

    st.dataframe(df)
    # regression
    try:
        slope, intercept, r2 = compute_regression(df["Concentration"].values, df["Signal"].values)
    except Exception as e:
        st.error(T("Linearity calculation error:", "Erreur calcul linéarité:") + f" {e}")
        return None

    st.markdown(f"**{T('Slope','Pente')}:** {slope:.6g}")
    st.markdown(f"**{T('Intercept','Ordonnée à l\'origine')}:** {intercept:.6g}")
    st.markdown(f"**R²:** {r2:.6g}")

    # plot
    fig, ax = plt.subplots()
    ax.scatter(df["Concentration"], df["Signal"], label=T("Data","Données"))
    xs = np.linspace(min(df["Concentration"]), max(df["Concentration"]), 200)
    ax.plot(xs, slope*xs + intercept, color="red", label=f"y={slope:.4g}x+{intercept:.4g}")
    ax.set_xlabel(T("Concentration", "Concentration"))
    ax.set_ylabel(T("Signal", "Signal"))
    ax.legend()
    st.pyplot(fig)

    # store slope for S/N tab
    st.session_state["linearity_slope"] = float(slope)
    st.session_state["linearity_intercept"] = float(intercept)
    st.session_state["linearity_r2"] = float(r2)
    st.session_state["linearity_df"] = df.to_dict(orient="list")

    # calculate unknown concentration or signal automatically (no separate button)
    calc_choice = st.selectbox(T("Calculate", "Calculer"), [T("Unknown concentration", "Concentration inconnue"), T("Unknown signal", "Signal inconnu")], key="calc_choice")
    if calc_choice == T("Unknown concentration", "Concentration inconnue"):
        sig_val = st.number_input(T("Enter signal", "Entrer le signal"), key="calc_sig")
        if sig_val != 0 or st.session_state.get("calc_sig",None) is not None:
            try:
                conc_calc = (sig_val - intercept) / slope
                st.success(T("Calculated concentration:","Concentration calculée:") + f" {conc_calc:.6g}")
                st.session_state["last_calculated_conc"] = float(conc_calc)
            except Exception as e:
                st.error(T("Could not compute concentration:", "Impossible de calculer la concentration:") + f" {e}")
    else:
        conc_val = st.number_input(T("Enter concentration", "Entrer la concentration"), key="calc_conc")
        if conc_val != 0 or st.session_state.get("calc_conc",None) is not None:
            sig_calc = slope * conc_val + intercept
            st.success(T("Calculated signal:", "Signal calculé:") + f" {sig_calc:.6g}")
            st.session_state["last_calculated_signal"] = float(sig_calc)

    # export PDF - ask company name at export time
    unit = st.selectbox(T("Concentration unit", "Unité de concentration"), ["µg/mL", "mg/mL", "ng/mL"], index=0, key="unit_select")
    company_name = st.text_input(T("Company name (required for PDF export)", "Nom de la compagnie (requis pour l'export PDF)"), key="company_name")
    if st.button(T("Export linearity report (PDF)", "Exporter rapport linéarité (PDF)"), key="export_lin_pdf"):
        if company_name.strip() == "":
            st.warning(T("Please enter company name before export.","Veuillez entrer le nom de la compagnie avant export."))
        else:
            pdf_bytes = export_linearity_pdf(company_name, df, slope, intercept, r2, unit)
            st.download_button(T("Download PDF", "Télécharger PDF"), data=pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")

# -------------------------
# S/N tools
# -------------------------
def load_image_from_pdf_bytes(pdf_bytes):
    # convert first page to image - requires pymupdf or pdf2image
    if fitz is not None:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pix = doc[0].get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes()))
        return img
    elif convert_from_bytes is not None:
        pages = convert_from_bytes(pdf_bytes, dpi=200)
        return pages[0]
    else:
        raise RuntimeError(T("PDF handling libraries not available", "Librairies PDF non disponibles"))

def sn_section():
    st.header(T("S/N, LOD, LOQ", "S/N, LOD, LOQ"))
    uploaded = st.file_uploader(T("Upload chromatogram (CSV, PNG, JPG, PDF)", "Importer chromatogramme (CSV, PNG, JPG, PDF)"),
                                type=["csv","png","jpg","jpeg","pdf"], key="sn_upload")
    if uploaded is None:
        return None

    # If CSV: expect two columns time,signal
    df = None
    image = None
    file_bytes = uploaded.read()
    uploaded.seek(0)
    if uploaded.type in ("text/csv", "application/vnd.ms-excel") or uploaded.name.lower().endswith(".csv"):
        try:
            uploaded.seek(0)
            df = pd.read_csv(uploaded)
            if df.shape[1] < 2:
                st.error(T("CSV must have at least two columns.", "Le CSV doit contenir au moins deux colonnes."))
                return
            df = df.iloc[:,0:2].copy()
            df.columns = ["Time","Signal"]
        except Exception as e:
            st.error(T("Error reading CSV:", "Erreur lecture CSV:") + f" {e}")
            return
    else:
        # image or pdf
        try:
            if uploaded.type == "application/pdf" or uploaded.name.lower().endswith(".pdf"):
                if fitz is None and convert_from_bytes is None:
                    st.error(T("PDF preview not implemented (missing libs)", "Aperçu PDF non implémenté (libs manquantes)"))
                    return
                image = load_image_from_pdf_bytes(file_bytes)
            else:
                image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        except Exception as e:
            st.error(T("Image/PDF preview error:", "Erreur aperçu image/pdf:") + f" {e}")
            return

    # If df provided: show line plot and allow selection via slider
    if df is not None:
        st.subheader(T("Chromatogram (CSV)", "Chromatogramme (CSV)"))
        st.line_chart(df.set_index("Time")["Signal"])
        min_t, max_t = float(df["Time"].min()), float(df["Time"].max())
        sel = st.slider(T("Select time window for noise/peak", "Sélectionner la fenêtre temporelle pour bruit/pic"), min_value=min_t, max_value=max_t, value=(min_t, max_t), key="sn_time_slider")
        left, right = sel
        # subset
        subset = df[(df["Time"] >= left) & (df["Time"] <= right)]
        if subset.empty:
            st.warning(T("No data in selected window", "Aucune donnée dans la fenêtre sélectionnée"))
            return
        # compute baseline noise as std in left part: offer user to mark baseline window fraction
        baseline_frac = st.slider(T("Baseline window fraction (left part)", "Fraction fenêtre baseline (partie gauche)"), min_value=0.0, max_value=0.9, value=0.2, step=0.05, key="baseline_frac")
        # baseline computed on first fraction of subset
        nbase = max(1, int(len(subset)*baseline_frac))
        baseline_region = subset.iloc[:nbase]
        baseline_mean = float(baseline_region["Signal"].mean())
        baseline_std = float(baseline_region["Signal"].std(ddof=1) if len(baseline_region)>1 else 0.0)
        peak_signal = float(subset["Signal"].max())
        peak_time = float(subset.loc[subset["Signal"].idxmax(),"Time"])

        st.markdown(f"- {T('Baseline mean','Baseline moyenne')}: {baseline_mean:.6g}")
        st.markdown(f"- {T('Baseline std','Baseline écart-type')}: {baseline_std:.6g}")
        st.markdown(f"- {T('Peak signal','Signal pic')}: {peak_signal:.6g} (t={peak_time:.3g})")

        # S/N calculations
        # Classic: (peak - baseline_mean) / baseline_std
        sn_classic = (peak_signal - baseline_mean) / baseline_std if baseline_std>0 else np.nan
        # USP variant: peak height / (2 * RMS_noise) OR use amplitude/p-p of noise: here we use (peak-baseline)/ (2*std)
        sn_usp = (peak_signal - baseline_mean) / (2*baseline_std) if baseline_std>0 else np.nan

        st.markdown(f"**S/N (classic):** {sn_classic:.3g}")
        st.markdown(f"**S/N (USP-style):** {sn_usp:.3g}")

        # allow slope import from linearity
        use_slope = st.checkbox(T("Use linearity slope to compute LOD/LOQ in concentration", "Utiliser la pente de linéarité pour calculer LOD/LOQ en concentration"), key="use_slope")
        slope = st.session_state.get("linearity_slope", None)
        if use_slope and slope is None:
            st.warning(T("No slope found. Compute linearity first.", "Aucune pente disponible. Calculer la linéarité d'abord."))
        # LOD/LOQ signal-level
        lod_signal = 3 * baseline_std
        loq_signal = 10 * baseline_std
        st.markdown(f"- {T('LOD (signal-level)','LOD (signal)')}: {lod_signal:.6g}")
        st.markdown(f"- {T('LOQ (signal-level)','LOQ (signal)')}: {loq_signal:.6g}")

        if use_slope and slope:
            # convert to concentration
            lod_conc = lod_signal / slope
            loq_conc = loq_signal / slope
            st.markdown(f"- {T('LOD (conc)','LOD (concentration)')}: {lod_conc:.6g}")
            st.markdown(f"- {T('LOQ (conc)','LOQ (concentration)')}: {loq_conc:.6g}")

        # Export report option
        company = st.text_input(T("Company name for PDF (required to export)", "Nom de la compagnie pour PDF (requis)"), key="sn_company")
        if st.button(T("Export S/N report (PDF)", "Exporter rapport S/N (PDF)"), key="export_sn_pdf"):
            if company.strip()=="":
                st.warning(T("Please enter company name before export.", "Veuillez entrer le nom de la compagnie avant export."))
            else:
                pdfb = export_sn_pdf(company=company, baseline_mean=baseline_mean, baseline_std=baseline_std,
                                     peak_signal=peak_signal, peak_time=peak_time, sn_classic=sn_classic, sn_usp=sn_usp,
                                     lod_signal=lod_signal, loq_signal=loq_signal,
                                     slope=slope if slope else None)
                st.download_button(T("Download PDF", "Télécharger PDF"), data=pdfb, file_name="sn_report.pdf", mime="application/pdf")

    elif image is not None:
        st.subheader(T("Chromatogram (image/pdf)", "Chromatogramme (image/pdf)"))
        # show image and convert to grayscale signal by summing vertical intensities (simple digitize)
        st.image(image, use_column_width=True)
        st.info(T("Digitizing: automatic extraction by collapsing image vertically to obtain a signal. Use sliders to choose range.", 
                  "Digitalisation: extraction automatique par sommation verticale. Utilisez les sliders pour choisir la zone."))
        # convert to grayscale and derive "signal" by inverting brightness (assuming peaks dark or light)
        img_gray = ImageOps.grayscale(image)
        arr = np.array(img_gray).astype(float)
        # collapse vertically: take inverted mean across rows to represent signal at each x
        col_vals = 255 - arr.mean(axis=0)  # invert so peaks are high if dark on light bg
        x = np.linspace(0, len(col_vals)-1, len(col_vals))
        # Rescale to a pseudo time axis:
        time_axis = np.linspace(0, 1, len(col_vals))  # normalized units; user can map externally
        df_img = pd.DataFrame({"Time": time_axis, "Signal": col_vals})
        st.line_chart(df_img.set_index("Time")["Signal"])
        # slider on normalized time
        left = st.slider(T("Select normalized time window (0-1)", "Sélectionner fenêtre temps normalisée (0-1)"), min_value=0.0, max_value=1.0, value=(0.0,1.0), key="img_window")
        l, r = left
        subset = df_img[(df_img["Time"]>=l)&(df_img["Time"]<=r)]
        if subset.empty:
            st.warning(T("No data in selected window", "Aucune donnée dans la fenêtre sélectionnée"))
            return
        baseline_frac = st.slider(T("Baseline fraction (left portion)", "Fraction baseline (portion gauche)"), min_value=0.0, max_value=0.9, value=0.15, step=0.01, key="img_baseline_frac")
        nbase = max(1, int(len(subset)*baseline_frac))
        baseline_region = subset.iloc[:nbase]
        baseline_mean = float(baseline_region["Signal"].mean())
        baseline_std = float(baseline_region["Signal"].std(ddof=1) if len(baseline_region)>1 else 0.0)
        peak_signal = float(subset["Signal"].max())
        peak_idx = subset["Signal"].idxmax()
        peak_time = float(subset.loc[peak_idx,"Time"])
        st.markdown(f"- {T('Baseline mean','Baseline moyenne')}: {baseline_mean:.6g}")
        st.markdown(f"- {T('Baseline std','Baseline écart-type')}: {baseline_std:.6g}")
        st.markdown(f"- {T('Peak signal','Signal pic')}: {peak_signal:.6g} (t={peak_time:.3g})")

        sn_classic = (peak_signal - baseline_mean) / baseline_std if baseline_std>0 else np.nan
        sn_usp = (peak_signal - baseline_mean) / (2*baseline_std) if baseline_std>0 else np.nan
        st.markdown(f"**S/N (classic):** {sn_classic:.3g}")
        st.markdown(f"**S/N (USP-style):** {sn_usp:.3g}")

        # slope usage
        use_slope = st.checkbox(T("Use linearity slope to compute LOD/LOQ in concentration", "Utiliser la pente de linéarité pour calculer LOD/LOQ en concentration"), key="img_use_slope")
        slope = st.session_state.get("linearity_slope", None)
        lod_signal = 3 * baseline_std
        loq_signal = 10 * baseline_std
        st.markdown(f"- {T('LOD (signal-level)','LOD (signal)')}: {lod_signal:.6g}")
        st.markdown(f"- {T('LOQ (signal-level)','LOQ (signal)')}: {loq_signal:.6g}")
        if use_slope and slope:
            st.markdown(f"- {T('LOD (conc)','LOD (concentration)')}: {lod_signal/slope:.6g}")
            st.markdown(f"- {T('LOQ (conc)','LOQ (concentration)')}: {loq_signal/slope:.6g}")

        company = st.text_input(T("Company name for PDF (required)", "Nom de la compagnie pour PDF (requis)"), key="img_company")
        if st.button(T("Export S/N report (PDF)", "Exporter rapport S/N (PDF)"), key="img_export_sn_pdf"):
            if company.strip()=="":
                st.warning(T("Please enter company name before export.", "Veuillez entrer le nom de la compagnie avant export."))
            else:
                pdfb = export_sn_pdf(company=company, baseline_mean=baseline_mean, baseline_std=baseline_std,
                                     peak_signal=peak_signal, peak_time=peak_time, sn_classic=sn_classic, sn_usp=sn_usp,
                                     lod_signal=lod_signal, loq_signal=loq_signal, slope=slope if slope else None)
                st.download_button(T("Download PDF", "Télécharger PDF"), data=pdfb, file_name="sn_report.pdf", mime="application/pdf")

# -------------------------
# PDF exports (linearity & sn)
# -------------------------
def export_linearity_pdf(company, df, slope, intercept, r2, unit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, company, ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"{T('Generated by','Généré par')} {st.session_state.get('user','')}", ln=True)
    pdf.cell(0, 8, f"{T('Date','Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 8, f"{T('Linearity results','Résultats linéarité')}", ln=True)
    pdf.cell(0, 8, f"{T('Slope','Pente')}: {slope:.6g}", ln=True)
    pdf.cell(0, 8, f"{T('Intercept','Ordonnée')}: {intercept:.6g}", ln=True)
    pdf.cell(0, 8, f"R²: {r2:.6g}", ln=True)
    # plot image
    plt.figure(figsize=(6,3))
    plt.scatter(df["Concentration"], df["Signal"])
    xs = np.linspace(min(df["Concentration"]), max(df["Concentration"]), 200)
    plt.plot(xs, slope*xs + intercept, color="red")
    plt.xlabel("Concentration ("+DEFAULT_UNIT+")")
    plt.ylabel("Signal")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="PNG")
    plt.close()
    buf.seek(0)
    pdf.image(buf, x=15, w=180)
    out = pdf.output(dest="S").encode("latin-1")
    return out

def export_sn_pdf(company, baseline_mean, baseline_std, peak_signal, peak_time, sn_classic, sn_usp, lod_signal, loq_signal, slope=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0,10,company,ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0,8,f"{T('Generated by','Généré par')} {st.session_state.get('user','')}", ln=True)
    pdf.cell(0,8, f"{T('Date','Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)
    pdf.cell(0,8, T("S/N results","Résultats S/N"), ln=True)
    pdf.cell(0,8, f"{T('Baseline mean','Baseline moyenne')}: {baseline_mean:.6g}", ln=True)
    pdf.cell(0,8, f"{T('Baseline std','Baseline écart-type')}: {baseline_std:.6g}", ln=True)
    pdf.cell(0,8, f"{T('Peak signal','Signal pic')}: {peak_signal:.6g} (t={peak_time:.6g})", ln=True)
    pdf.cell(0,8, f"S/N (classic): {sn_classic:.6g}", ln=True)
    pdf.cell(0,8, f"S/N (USP-style): {sn_usp:.6g}", ln=True)
    pdf.cell(0,8, f"LOD (signal): {lod_signal:.6g}", ln=True)
    pdf.cell(0,8, f"LOQ (signal): {loq_signal:.6g}", ln=True)
    if slope:
        pdf.cell(0,8, f"LOD (conc): {lod_signal/slope:.6g}", ln=True)
        pdf.cell(0,8, f"LOQ (conc): {loq_signal/slope:.6g}", ln=True)
    out = pdf.output(dest="S").encode("latin-1")
    return out

# -------------------------
# Main app layout
# -------------------------
def app_main():
    st.sidebar.title("LabT")
    language_selector()
    st.sidebar.write("")  # spacing
    # logout placed in sidebar
    logout_action()

    st.title("LabT - Linearity & S/N Tool")
    st.write(T("Two modules: Linearity and S/N. Admin can manage users.", "Deux modules : Linéarité et S/N. L'admin gère les utilisateurs."))

    if st.session_state.get("role") == "admin":
        st.header(T("Administration", "Administration"))
        st.subheader(T("User management (add, edit, delete)", "Gestion utilisateurs (ajout, modification, suppression)"))
        add_user_form()
        st.markdown("---")
        edit_user_form()
        st.markdown("---")
        st.info(T("Admin cannot access calculations; log in as a normal user to use them.", "L'admin n'a pas accès aux calculs ; connectez-vous en utilisateur normal pour utiliser l'application."))
        # hide users.json content intentionally
    else:
        # two panels: lineaire / sn
        tab = st.radio("", [T("Linearity","Linéarité"), T("S/N","S/N")], horizontal=True, key="main_tab")
        if tab == T("Linearity","Linéarité"):
            linearity_section()
        else:
            sn_section()

        st.markdown("---")
        st.header(T("Profile", "Profil"))
        st.write(f"{T('Logged in as','Connecté en tant que')}: **{st.session_state.get('user','')}**")
        # keep change password separate as requested
        if st.button(T("Change password (profile)", "Changer mot de passe (profil)"), key="btn_open_change"):
            st.session_state.show_profile_change = True
        if st.session_state.get("show_profile_change", False):
            profile_change_password()

# -------------------------
# Entrypoint
# -------------------------
def main():
    # ensure users file present
    ensure_users_file()
    if not st.session_state.get("logged_in", False):
        login_page()
    else:
        app_main()

if __name__ == "__main__":
    main()