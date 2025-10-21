# app.py
# LabT single-file Streamlit app
# BILINGUAL (English default / Français)
# Admin: manage users only
# User: linearity (CSV/manual), S/N (CSV), PDF export (with plots)
#
# Notes:
# - CSV must contain columns: "Time" and "Signal" (case-insensitive).
# - PNG/PDF uploads are allowed for visualization only (calculations require CSV).
# - Username matching is case-insensitive.
# - Buttons act with a single click (on_click handlers modify session_state.current_page).

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import io
from fpdf import FPDF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from PIL import Image
import base64
import math

# ----- Config -----
USERS_FILE = "users.json"
APP_NAME = "LabT"
LOGO_TEXT = "LabT"

# ----- Helpers -----
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "user1": {"password": "user1", "role": "user"},
            "user2": {"password": "user2", "role": "user"}
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)

def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def normalize_username(u):
    return u.strip().lower() if isinstance(u, str) else u

def add_message(msg_en, msg_fr=None):
    """Return pair messages based on lang"""
    lang = st.session_state.get("lang", "en")
    if lang.startswith("fr"):
        return msg_fr if msg_fr is not None else msg_en
    return msg_en

def make_download_link(file_path, label="Download"):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/octet-stream;base64,{b64}" download="{os.path.basename(file_path)}">{label}</a>'
    return href

def save_plot_to_png(fig, path):
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)

# ----- PDF generation -----
def generate_pdf_report(title, company_name, user_name, content_text, plot_png_path=None):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Header: company name big
    pdf.set_font("Arial", "B", 16)
    header = company_name if company_name else APP_NAME
    pdf.cell(0, 10, header, ln=True, align="C")
    pdf.ln(4)
    # meta
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"App: {APP_NAME}", ln=True)
    pdf.cell(0, 8, f"User: {user_name}", ln=True)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(6)
    pdf.multi_cell(0, 6, content_text)
    pdf.ln(6)
    if plot_png_path and os.path.exists(plot_png_path):
        try:
            pdf.image(plot_png_path, x=15, w=180)
        except Exception:
            pass
    fname = f"{title}_{user_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(fname)
    return fname

# ----- Initialize session_state -----
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "slope" not in st.session_state:
    st.session_state.slope = None
if "unit" not in st.session_state:
    st.session_state.unit = "µg/mL"

# ----- UI: Top bar language switch -----
def set_lang_en():
    st.session_state.lang = "en"
def set_lang_fr():
    st.session_state.lang = "fr"

st.set_page_config(page_title=f"{APP_NAME}", layout="centered")
col1, col2, col3 = st.columns([1,6,1])
with col1:
    st.write("")  # reserved for logo if needed
with col2:
    # small title
    if st.session_state.lang.startswith("fr"):
        st.title("🔬 LabT")
    else:
        st.title("🔬 LabT")
with col3:
    st.button("English", on_click=set_lang_en)
    st.button("Français", on_click=set_lang_fr)

# ----- Authentication / Navigation actions -----
def login_action(raw_username, password):
    users = load_users()
    uname = normalize_username(raw_username)
    # find key matching normalized username
    matched = None
    for k in users.keys():
        if normalize_username(k) == uname:
            matched = k
            break
    if matched and users[matched]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = matched
        st.session_state.role = users[matched]["role"]
        # landing page
        if st.session_state.role == "admin":
            st.session_state.current_page = "admin"
        else:
            st.session_state.current_page = "menu"
        # show success message (language)
        if st.session_state.lang.startswith("fr"):
            st.success(f"Connexion réussie ✅ Vous êtes connecté en tant que {matched}")
        else:
            st.success(f"Login successful ✅ / You are logged in as {matched}")
    else:
        if st.session_state.lang.startswith("fr"):
            st.error("Nom d'utilisateur ou mot de passe incorrect ❌")
        else:
            st.error("Wrong username or password ❌")

def logout_action():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = None
    st.session_state.current_page = "login"
    # no experimental_rerun — navigation controlled by page variable

# ----- Admin: manage users (add / modify / delete) -----
def admin_page():
    st.header(add_message("👥 User management", "👥 Gestion des utilisateurs"))
    st.write(add_message(f"You are logged in as **{st.session_state.username}**", f"Vous êtes connecté en tant que **{st.session_state.username}**"))
    st.markdown("---")
    users = load_users()
    # show table (but not raw passwords)
    display = {u: {"role": users[u]["role"]} for u in users}
    st.table(pd.DataFrame(display).T.rename_axis("username").reset_index())
    st.markdown("---")
    st.subheader(add_message("Add / Modify / Delete user", "Ajouter / Modifier / Supprimer un utilisateur"))
    action = st.selectbox(add_message("Action:", "Action :"), ["Add", "Modify", "Delete"] if st.session_state.lang.startswith("en") else ["Ajouter", "Modifier", "Supprimer"], key="admin_action")
    # unify action labels to internal
    if action in ["Add", "Ajouter"]:
        act = "add"
    elif action in ["Modify", "Modifier"]:
        act = "modify"
    else:
        act = "delete"
    uname = st.text_input(add_message("Username:", "Nom d'utilisateur:"), key="admin_username")
    pwd = st.text_input(add_message("Password:", "Mot de passe:"), key="admin_password")
    role = st.selectbox(add_message("Role:", "Rôle:"), ["user", "admin"], key="admin_role")
    def do_admin_action():
        if not uname:
            st.warning(add_message("Username is required.", "Le nom d'utilisateur est requis."))
            return
        users = load_users()
        # case-insensitive matching
        matched = None
        for k in list(users.keys()):
            if normalize_username(k) == normalize_username(uname):
                matched = k
                break
        if act == "add":
            if matched:
                st.warning(add_message("User already exists.", "Utilisateur déjà existant."))
            else:
                if not pwd:
                    st.warning(add_message("Password is required for adding.", "Le mot de passe est requis pour l'ajout."))
                    return
                users[uname] = {"password": pwd, "role": role}
                save_users(users)
                st.success(add_message("User added ✅", "Utilisateur ajouté ✅"))
        elif act == "modify":
            if not matched:
                st.warning(add_message("User not found.", "Utilisateur introuvable."))
            else:
                if pwd:
                    users[matched]["password"] = pwd
                users[matched]["role"] = role
                save_users(users)
                st.success(add_message("User modified ✅", "Utilisateur modifié ✅"))
        else:  # delete
            if not matched:
                st.warning(add_message("User not found.", "Utilisateur introuvable."))
            else:
                del users[matched]
                save_users(users)
                st.success(add_message("User deleted ✅", "Utilisateur supprimé ✅"))
    st.button(add_message("Confirm", "Valider"), on_click=do_admin_action)
    st.markdown("---")
    if st.button(add_message("Logout", "Déconnexion")):
        logout_action()

# ----- User pages: menu, linearity, sn -----
def page_menu():
    st.header(add_message("Main menu", "Menu principal"))
    st.write(add_message(f"You are logged in as **{st.session_state.username}**", f"Vous êtes connecté en tant que **{st.session_state.username}**"))
    options = [add_message("Linearity", "Courbe de linéarité"), add_message("Signal-to-Noise (S/N)", "Signal/bruit (S/N)"), add_message("Change password", "Changer le mot de passe")]
    choice = st.selectbox(add_message("Choose an option:", "Choisir une option :"), options, index=0)
    if choice in [add_message("Linearity", "Courbe de linéarité")]:
        st.session_state.current_page = "linearity"
    elif choice in [add_message("Signal-to-Noise (S/N)", "Signal/bruit (S/N)")]:
        st.session_state.current_page = "sn"
    else:
        st.session_state.current_page = "change_password"
    # quick logout
    if st.button(add_message("Logout", "Déconnexion")):
        logout_action()

# ---- Linearity page ----
def compute_linearity_from_arrays(conc, resp):
    slope, intercept = np.polyfit(conc, resp, 1)
    r2 = np.corrcoef(conc, resp)[0,1]**2
    return slope, intercept, r2

def page_linearity():
    st.header(add_message("📈 Linearity", "📈 Courbe de linéarité"))
    st.write(add_message("You can input concentrations and signals manually, or upload a CSV.", "Vous pouvez saisir manuellement les concentrations et signaux, ou téléverser un CSV."))
    # choice CSV or manual
    mode = st.radio(add_message("Input method:", "Méthode d'entrée :"), [add_message("CSV upload", "Importer CSV"), add_message("Manual entry", "Saisie manuelle")])
    conc = None
    resp = None
    df_line = None
    if mode == add_message("CSV upload", "Importer CSV"):
        up = st.file_uploader(add_message("Upload CSV with columns Time/Signal or Concentration/Signal", "Importer CSV avec colonnes Time/Signal ou Concentration/Signal"), type=["csv"])
        if up is not None:
            try:
                # try common separators ; let pandas sniff
                df = pd.read_csv(up, engine="python")
                cols = [c.strip().lower() for c in df.columns]
                df.columns = cols
                # possible columns: concentration & signal OR time & signal
                if "concentration" in cols and "signal" in cols:
                    conc = df["concentration"].astype(float).values
                    resp = df["signal"].astype(float).values
                    df_line = pd.DataFrame({"concentration":conc, "signal":resp})
                elif "time" in cols and "signal" in cols:
                    st.warning(add_message("CSV contains Time and Signal. For linearity please upload Concentration & Signal or use manual entry.", "Le CSV contient Time et Signal. Pour la linéarité, téléversez Concentration & Signal ou utilisez la saisie manuelle."))
                else:
                    st.error(add_message("CSV must contain 'Concentration' and 'Signal' columns (or use manual entry).", "Le CSV doit contenir les colonnes 'Concentration' et 'Signal' (ou utilisez la saisie manuelle)."))
            except Exception as e:
                st.error(add_message(f"Error reading CSV: {e}", f"Erreur de lecture CSV : {e}"))
    else:
        # manual: two comma-separated lists
        conc_text = st.text_input(add_message("Concentrations (comma-separated)", "Concentrations (séparées par des virgules)"))
        resp_text = st.text_input(add_message("Signals (comma-separated)", "Signaux (séparés par des virgules)"))
        try:
            if conc_text and resp_text:
                conc = np.array([float(x.strip()) for x in conc_text.split(",") if x.strip()!=""])
                resp = np.array([float(x.strip()) for x in resp_text.split(",") if x.strip()!=""])
                df_line = pd.DataFrame({"concentration":conc, "signal":resp})
        except Exception as e:
            st.error(add_message(f"Error parsing manual input: {e}", f"Erreur lors de l'analyse des saisies : {e}"))

    if df_line is not None and len(df_line) >= 2:
        try:
            slope, intercept, r2 = compute_linearity_from_arrays(df_line["concentration"].values, df_line["signal"].values)
            st.session_state.slope = slope
            st.session_state.unit = st.selectbox(add_message("Concentration unit:", "Unité de concentration:"), ["µg/mL", "mg/L", "g/L"], index=0)
            st.write(add_message(f"Equation: y = {slope:.6f} x + {intercept:.6f}  (R² = {r2:.4f})", f"Équation : y = {slope:.6f} x + {intercept:.6f}  (R² = {r2:.4f})"))
            # plot
            fig, ax = plt.subplots()
            ax.scatter(df_line["concentration"], df_line["signal"], label="Points")
            xs = np.linspace(df_line["concentration"].min()*0.9, df_line["concentration"].max()*1.1, 200)
            ax.plot(xs, slope*xs + intercept, label="Fit")
            ax.set_xlabel(f"Concentration ({st.session_state.unit})")
            ax.set_ylabel("Signal")
            ax.set_title("Linearity")
            ax.legend()
            st.pyplot(fig)
            # unknown calculation
            unknown_type = st.selectbox(add_message("Unknown type:", "Type d'inconnu :"), [add_message("Unknown concentration (given signal)", "Concentration inconnue (signal connu)"), add_message("Unknown signal (given concentration)", "Signal inconnu (concentration connue)")])
            unknown_val = st.number_input(add_message("Enter the known value:", "Entrez la valeur connue:"), value=0.0)
            if st.button(add_message("Calculate", "Calculer")):
                if unknown_type == add_message("Unknown concentration (given signal)", "Concentration inconnue (signal connu)"):
                    # given signal -> concentration
                    conc_res = (unknown_val - intercept)/slope if slope!=0 else float('nan')
                    st.success(add_message(f"Unknown concentration = {conc_res:.6f} {st.session_state.unit}", f"Concentration inconnue = {conc_res:.6f} {st.session_state.unit}"))
                else:
                    sig_res = slope*unknown_val + intercept
                    st.success(add_message(f"Unknown signal = {sig_res:.6f}", f"Signal inconnu = {sig_res:.6f}"))
            # export PDF
            company_name = st.text_input(add_message("Company name for report (required):", "Nom de la compagnie pour le rapport (requis):"), value="")
            def export_linearity_pdf():
                if not company_name:
                    st.warning(add_message("Please enter company name before exporting.", "Veuillez saisir le nom de la compagnie avant l'export."))
                    return
                # prepare text
                content = add_message("Linearity report\n", "Rapport de linéarité\n")
                content += add_message(f"Equation: y = {slope:.6f} x + {intercept:.6f}\nR2: {r2:.6f}\n", f"Équation: y = {slope:.6f} x + {intercept:.6f}\nR2: {r2:.6f}\n")
                if unknown_type == add_message("Unknown concentration (given signal)", "Concentration inconnue (signal connu)"):
                    if slope != 0:
                        conc_res = (unknown_val - intercept)/slope
                        content += add_message(f"Unknown concentration (from signal {unknown_val}) = {conc_res:.6f} {st.session_state.unit}\n", f"Concentration inconnue (à partir du signal {unknown_val}) = {conc_res:.6f} {st.session_state.unit}\n")
                else:
                    sig_res = slope*unknown_val + intercept
                    content += add_message(f"Unknown signal (from conc {unknown_val}) = {sig_res:.6f}\n", f"Signal inconnu (à partir de conc {unknown_val}) = {sig_res:.6f}\n")
                # save plot PNG
                png_path = f"linearity_{st.session_state.username}.png"
                save_plot_to_png(fig, png_path)
                pdf_file = generate_pdf_report("Linearity_Report", company_name, st.session_state.username, content, png_path)
                st.success(add_message("Report generated:", "Rapport généré :"))
                st.markdown(make_download_link(pdf_file, add_message("⬇️ Download PDF", "⬇️ Télécharger le PDF")), unsafe_allow_html=True)
            st.button(add_message("Export PDF report", "Exporter le rapport PDF"), on_click=export_linearity_pdf)
        except Exception as e:
            st.error(add_message(f"Error in calculations: {e}", f"Erreur dans les calculs : {e}"))
    else:
        st.info(add_message("Provide at least 2 points (concentration/signal).", "Fournissez au moins 2 points (concentration/signal)."))
    if st.button(add_message("Back to menu", "Retour au menu")):
        st.session_state.current_page = "menu"

# ---- S/N page ----
def compute_sn_from_df(df, noise_region=None):
    # df must contain columns Time and Signal (case-insensitive)
    df_cols = [c.strip().lower() for c in df.columns]
    if "signal" not in df_cols:
        raise ValueError("CSV must contain column 'Signal' (case-insensitive)")
    # find column name actual
    sig_col = df.columns[df_cols.index("signal")]
    if "time" in df_cols:
        time_col = df.columns[df_cols.index("time")]
    else:
        time_col = df.columns[df_cols.index("signal")]  # fallback index
    s = df[sig_col].astype(float).values
    t = df[time_col].astype(float).values if time_col!=sig_col else np.arange(len(s))
    # default noise : first 10% of points
    npts = max(1, int(0.1*len(s)))
    if noise_region is None:
        baseline = s[:npts]
    else:
        # noise_region: (start_idx, end_idx)
        start, end = noise_region
        start = max(0, int(start))
        end = min(len(s), int(end))
        if start>=end:
            baseline = s[:npts]
        else:
            baseline = s[start:end]
    noise_std = np.std(baseline, ddof=1) if len(baseline)>1 else np.std(baseline)
    peak = np.max(s)
    sn_classic = peak / noise_std if noise_std > 0 else float('inf')
    # USP S/N: baseline region chosen by user (same baseline)
    sn_usp = sn_classic  # same definition for now; displayed separately
    # LOD/LOQ in signal units
    lod_signal = 3 * noise_std
    loq_signal = 10 * noise_std
    return {
        "time": t, "signal": s,
        "peak": peak, "noise_std": noise_std,
        "sn_classic": sn_classic, "sn_usp": sn_usp,
        "lod_signal": lod_signal, "loq_signal": loq_signal
    }

def page_sn():
    st.header(add_message("📊 Signal-to-Noise (S/N) analysis", "📊 Analyse Signal/bruit (S/N)"))
    st.write(add_message("Upload a CSV with columns Time and Signal for calculations. You can also upload PNG/PDF for visualization only.", "Téléversez un CSV avec les colonnes Time et Signal pour les calculs. Vous pouvez aussi téléverser PNG/PDF pour visualiser uniquement."))
    company_name = st.text_input(add_message("Company name for report (required for export):", "Nom de la compagnie pour le rapport (requis pour export):"), value="")
    uploaded_file = st.file_uploader(add_message("Upload chromatogram CSV (required for calculations)", "Importer chromatogramme CSV (requis pour calculs)"), type=["csv"], key="sn_csv")
    uploaded_image = st.file_uploader(add_message("Optional: upload PNG/PDF for visual check (visual only)", "Optionnel : importer PNG/PDF pour vérification visuelle (visuel seulement)"), type=["png","jpg","jpeg","pdf"])
    df = None
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, engine="python")
            cols_low = [c.strip().lower() for c in df.columns]
            if "time" not in cols_low or "signal" not in cols_low:
                st.error(add_message("CSV must contain the columns: Time and Signal (case-insensitive)", "Le CSV doit contenir les colonnes : Time et Signal (insensible à la casse)"))
                df = None
        except Exception as e:
            st.error(add_message(f"Error reading CSV: {e}", f"Erreur de lecture CSV : {e}"))
            df = None

    # show image if provided
    if uploaded_image:
        try:
            if uploaded_image.type == "application/pdf":
                img = Image.open(uploaded_image)
            else:
                img = Image.open(uploaded_image)
            st.image(img, caption=add_message("Uploaded chromatogram (visual only)", "Chromatogramme importé (visuel seulement)"), use_column_width=True)
        except Exception as e:
            st.warning(add_message(f"Could not display image: {e}", f"Impossible d'afficher l'image : {e}"))

    if df is not None:
        # let user pick noise region by indices (slider on time)
        # convert time column
        df_cols = [c.strip().lower() for c in df.columns]
        time_col = df.columns[df_cols.index("time")]
        signal_col = df.columns[df_cols.index("signal")]
        # plot interactive with matplotlib and slider controls
        t = df[time_col].astype(float).values
        s = df[signal_col].astype(float).values
        fig, ax = plt.subplots()
        ax.plot(t, s, label="Signal")
        ax.set_xlabel("Time")
        ax.set_ylabel("Signal")
        ax.set_title("Chromatogram")
        st.pyplot(fig)

        # choose noise region indices
        st.write(add_message("Select noise baseline region (by index of data points):", "Sélectionnez la région de base pour le bruit (par index des points)"))
        start_idx = st.number_input(add_message("Start index (int)", "Index de début (int)"), min_value=0, max_value=len(s)-1, value=0, step=1, key="noise_start")
        end_idx = st.number_input(add_message("End index (int)", "Index de fin (int)"), min_value=1, max_value=len(s), value=max(1, int(0.1*len(s))), step=1, key="noise_end")
        # compute
        try:
            res = compute_sn_from_df(df, noise_region=(start_idx, end_idx))
            st.success(add_message(f"S/N (classic) = {res['sn_classic']:.2f}", f"S/N (classique) = {res['sn_classic']:.2f}"))
            st.info(add_message(f"USP S/N = {res['sn_usp']:.2f} (noise std = {res['noise_std']:.6f})", f"USP S/N = {res['sn_usp']:.2f} (std du bruit = {res['noise_std']:.6f})"))
            st.info(add_message(f"LOD (signal) = {res['lod_signal']:.6f}, LOQ (signal) = {res['loq_signal']:.6f}", f"LOD (signal) = {res['lod_signal']:.6f}, LOQ (signal) = {res['loq_signal']:.6f}"))
            # convert to concentration if slope exists
            if st.session_state.slope is not None:
                slope = st.session_state.slope
                if slope != 0:
                    lod_conc = res['lod_signal'] / slope
                    loq_conc = res['loq_signal'] / slope
                    st.info(add_message(f"LOD = {lod_conc:.6f} {st.session_state.unit}, LOQ = {loq_conc:.6f} {st.session_state.unit}", f"LOD = {lod_conc:.6f} {st.session_state.unit}, LOQ = {loq_conc:.6f} {st.session_state.unit}"))
            # export pdf
            def export_sn_pdf():
                if not company_name:
                    st.warning(add_message("Please enter company name before exporting.", "Veuillez saisir le nom de la compagnie avant l'export."))
                    return
                content = add_message("S/N analysis\n", "Analyse S/N\n")
                content += add_message(f"Peak: {res['peak']}\nNoise std: {res['noise_std']:.6f}\nS/N classic: {res['sn_classic']:.2f}\nUSP S/N: {res['sn_usp']:.2f}\nLOD (signal): {res['lod_signal']:.6f}\nLOQ (signal): {res['loq_signal']:.6f}\n", \
                                       f"Peak: {res['peak']}\nStd bruit: {res['noise_std']:.6f}\nS/N classique: {res['sn_classic']:.2f}\nUSP S/N: {res['sn_usp']:.2f}\nLOD (signal): {res['lod_signal']:.6f}\nLOQ (signal): {res['loq_signal']:.6f}\n")
                if st.session_state.slope is not None and st.session_state.slope != 0:
                    lodc = res['lod_signal'] / st.session_state.slope
                    loqc = res['loq_signal'] / st.session_state.slope
                    content += add_message(f"LOD (conc) = {lodc:.6f} {st.session_state.unit}\nLOQ (conc) = {loqc:.6f} {st.session_state.unit}\n", f"LOD (conc) = {lodc:.6f} {st.session_state.unit}\nLOQ (conc) = {loqc:.6f} {st.session_state.unit}\n")
                # save chromatogram plot as png
                png_path = f"sn_{st.session_state.username}.png"
                # generate new plot
                fig2, ax2 = plt.subplots()
                ax2.plot(res['time'], res['signal'])
                ax2.set_xlabel("Time")
                ax2.set_ylabel("Signal")
                ax2.set_title("Chromatogram")
                save_plot_to_png(fig2, png_path)
                pdf_file = generate_pdf_report("SN_Report", company_name, st.session_state.username, content, png_path)
                st.success(add_message("Report generated:", "Rapport généré :"))
                st.markdown(make_download_link(pdf_file, add_message("⬇️ Download PDF", "⬇️ Télécharger le PDF")), unsafe_allow_html=True)
            st.button(add_message("Export S/N report (PDF)", "Exporter rapport S/N (PDF)"), on_click=export_sn_pdf)
        except Exception as e:
            st.error(add_message(f"Error computing S/N: {e}", f"Erreur lors du calcul S/N : {e}"))
    else:
        st.info(add_message("Upload a valid CSV (Time and Signal) to compute S/N.", "Téléversez un CSV valide (Time et Signal) pour calculer S/N."))

    if st.button(add_message("Back to menu", "Retour au menu")):
        st.session_state.current_page = "menu"

# ---- Change password page for users ----
def page_change_password():
    st.header(add_message("🔑 Change Password", "🔑 Changer le mot de passe"))
    st.write(add_message(f"User: {st.session_state.username}", f"Utilisateur : {st.session_state.username}"))
    cur = st.text_input(add_message("Current password", "Mot de passe actuel"), type="password")
    new = st.text_input(add_message("New password", "Nouveau mot de passe"), type="password")
    confirm = st.text_input(add_message("Confirm new password", "Confirmez le nouveau mot de passe"), type="password")
    def do_change_pwd():
        if not cur or not new or not confirm:
            st.warning(add_message("All fields are required.", "Tous les champs sont requis."))
            return
        if new != confirm:
            st.warning(add_message("New passwords do not match.", "Les nouveaux mots de passe ne correspondent pas."))
            return
        users = load_users()
        uname = st.session_state.username
        if users.get(uname)["password"] != cur:
            st.error(add_message("Current password incorrect.", "Mot de passe actuel incorrect."))
            return
        users[uname]["password"] = new
        save_users(users)
        st.success(add_message("Password changed ✅", "Mot de passe modifié ✅"))
    st.button(add_message("Change password", "Changer le mot de passe"), on_click=do_change_pwd)
    if st.button(add_message("Back to menu", "Retour au menu")):
        st.session_state.current_page = "menu"

# ----- Login screen -----
def page_login():
    st.header(add_message("🔐 Login", "🔐 Connexion"))
    users = load_users()
    user_list = list(users.keys())
    # create a selectbox and a text input for username:
    raw_username = st.text_input(add_message("Username", "Nom d'utilisateur"))
    password = st.text_input(add_message("Password", "Mot de passe"), type="password")
    if st.button(add_message("Login", "Se connecter")):
        login_action(raw_username, password)
    st.markdown("---")
    st.write(add_message("If you don't have credentials, contact admin.", "Si vous n'avez pas d'identifiants, contactez l'administrateur."))

# ----- Main app controller -----
def main():
    if not st.session_state.logged_in:
        st.session_state.current_page = "login"
    # route
    page = st.session_state.current_page
    if page == "login":
        page_login()
    elif page == "admin":
        # only admin allowed
        if st.session_state.role == "admin":
            admin_page()
        else:
            st.error(add_message("Access denied.", "Accès refusé."))
            st.session_state.current_page = "menu"
    elif page == "menu":
        page_menu()
    elif page == "linearity":
        page_linearity()
    elif page == "sn":
        page_sn()
    elif page == "change_password":
        page_change_password()
    else:
        st.info("Page not found.")
        st.session_state.current_page = "menu"

if __name__ == "__main__":
    ensure_users_file()
    main()