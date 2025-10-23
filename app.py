# app.py
"""
LABT - Linearity & S/N app (bilingual FR/EN)
Requirements: see requirements.txt
Author: generated helper
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime
from fpdf import FPDF
from PIL import Image, UnidentifiedImageError
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from scipy import stats

# ---------------------------
# Configuration / constants
# ---------------------------
USERS_FILE = "users.json"
DEFAULT_UNIT = "µg/mL"  # default concentration unit
UNITS = ["µg/mL", "mg/L"]

# ---------------------------
# Helpers: users management
# ---------------------------
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # default: one admin + one user (passwords in plain text for simplicity — change for production)
        data = {
            "admin": {"password": "admin123", "role": "admin"},
            "user": {"password": "user123", "role": "user"}
        }
        save_users(data)
        return data

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def add_user(username, password, role="user"):
    users = load_users()
    username_key = username.lower()
    users[username_key] = {"password": password, "role": role}
    save_users(users)

def delete_user(username):
    users = load_users()
    username_key = username.lower()
    if username_key in users:
        del users[username_key]
        save_users(users)
        return True
    return False

def modify_user(username, password=None, role=None):
    users = load_users()
    username_key = username.lower()
    if username_key in users:
        if password:
            users[username_key]["password"] = password
        if role:
            users[username_key]["role"] = role
        save_users(users)
        return True
    return False

# ---------------------------
# Auth (simple)
# ---------------------------
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "language" not in st.session_state:
        st.session_state.language = "FR"  # default FR
    if "linearity_slope" not in st.session_state:
        st.session_state.linearity_slope = None
    if "linearity_intercept" not in st.session_state:
        st.session_state.linearity_intercept = None
    if "linearity_units" not in st.session_state:
        st.session_state.linearity_units = DEFAULT_UNIT

def login_form():
    st.markdown("### 🔐 Login")
    username = st.text_input("Utilisateur / Username", value="", key="login_username")
    password = st.text_input("Mot de passe / Password", type="password", key="login_password")
    if st.button("Se connecter / Log in"):
        users = load_users()
        key = username.lower()
        if key in users and users[key]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = key
            st.success(f"{'Connecté' if st.session_state.language=='FR' else 'Logged in'}: {key}")
        else:
            st.error("Utilisateur ou mot de passe invalide / Invalid username or password")

def logout():
    # clear only runtime session keys, keep language
    lang = st.session_state.language
    st.session_state.clear()
    st.session_state.language = lang
    st.session_state.logged_in = False
    st.success("Déconnecté / Logged out")

# ---------------------------
# Utility: bilingual text helper
# ---------------------------
def T(fr, en=None):
    if en is None:
        en = fr
    return fr if st.session_state.language == "FR" else en

# ---------------------------
# Math / calculation helpers
# ---------------------------
def linear_regression_from_xy(x, y):
    # Ensure arrays
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        raise ValueError("Two or more points required / Au moins deux points requis")
    # use scipy.stats.linregress
    res = stats.linregress(x, y)
    slope = res.slope
    intercept = res.intercept
    rvalue = res.rvalue
    r2 = rvalue**2
    return slope, intercept, r2, res

def predict_from_slope_intercept(slope, intercept, value, predict_concentration=True):
    # if predict_concentration True: value is signal -> return concentration
    if predict_concentration:
        # signal = slope * conc + intercept => conc = (signal - intercept)/slope
        if slope == 0:
            raise ZeroDivisionError("Slope is zero")
        return (value - intercept) / slope
    else:
        # predict signal from concentration
        return slope * value + intercept

# ---------------------------
# PDF export helpers
# ---------------------------
def export_linearity_pdf(company_name, slope, intercept, r2, unit, data_df=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Linearity report - {company_name}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 7, f"Slope: {slope:.6g}", ln=True)
    pdf.cell(0, 7, f"Intercept: {intercept:.6g}", ln=True)
    pdf.cell(0, 7, f"R²: {r2:.6g}", ln=True)
    pdf.cell(0, 7, f"Units: {unit}", ln=True)
    pdf.ln(6)
    if data_df is not None:
        pdf.cell(0, 7, "Data (first 10 rows):", ln=True)
        pdf.ln(2)
        # write header
        header = " | ".join(list(data_df.columns[:3].astype(str))) if not data_df.empty else ""
        if header:
            pdf.multi_cell(0, 6, header)
        for i, row in data_df.head(10).iterrows():
            pdf.multi_cell(0, 6, " | ".join([str(x) for x in row.values]))
    bio = io.BytesIO()
    pdf.output(bio)
    bio.seek(0)
    return bio

def export_sn_pdf(company_name, report_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"S/N report - {company_name}", ln=True)
    pdf.ln(4)
    pdf.multi_cell(0, 6, report_text)
    bio = io.BytesIO()
    pdf.output(bio)
    bio.seek(0)
    return bio

# ---------------------------
# UI: Linearity tab
# ---------------------------
def linearity_tab():
    st.header(T("Linéarité", "Linearity"))
    st.markdown(T(
        "Choisissez la source : CSV (au moins 2 colonnes) ou saisie manuelle (valeurs séparées par des virgules).",
        "Choose source: CSV (at least 2 columns) or manual input (comma-separated values)."
    ))
    col1, col2 = st.columns(2)
    with col1:
        src = st.radio(T("Source", "Source"), [T("CSV", "CSV"), T("Saisie manuelle", "Manual entry")], index=0, key="lin_src")
    with col2:
        unit = st.selectbox(T("Unité de concentration", "Concentration unit"), UNITS, index=UNITS.index(st.session_state.get("linearity_units", DEFAULT_UNIT)))
        st.session_state.linearity_units = unit

    df = None
    if src == T("CSV", "CSV"):
        uploaded = st.file_uploader(T("Importer fichier CSV (2 colonnes au minimum)", "Upload CSV (min 2 columns)"), type=["csv"], key="lin_csv")
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                if df.shape[1] < 2:
                    st.error(T("Le CSV doit contenir au moins 2 colonnes.", "CSV must contain at least 2 columns."))
                    df = None
                else:
                    st.success(T("CSV chargé.", "CSV loaded."))
                    st.dataframe(df.head(10))
            except Exception as e:
                st.error(T(f"Erreur lecture CSV : {e}", f"CSV read error: {e}"))
                df = None
    else:
        st.write(T("Entrez x (concentration) séparées par des virgules, puis y (signal) séparées par des virgules.", "Enter x (concentration) comma-separated, then y (signal) comma-separated."))
        x_text = st.text_area(T("x (concentration)", "x (concentration)"), key="lin_x_text", placeholder="e.g. 0.5,1,2,5")
        y_text = st.text_area(T("y (signal)", "y (signal)"), key="lin_y_text", placeholder="e.g. 10,20,40,80")
        if x_text and y_text:
            try:
                x_vals = [float(s.strip()) for s in x_text.split(",") if s.strip() != ""]
                y_vals = [float(s.strip()) for s in y_text.split(",") if s.strip() != ""]
                if len(x_vals) != len(y_vals):
                    st.error(T("Les nombres de x et y doivent être égaux.", "Number of x and y must match."))
                elif len(x_vals) < 2:
                    st.error(T("Au moins deux points requis.", "At least two points required."))
                else:
                    df = pd.DataFrame({"x": x_vals, "y": y_vals})
                    st.dataframe(df)
            except Exception as e:
                st.error(T(f"Erreur parsing manuelle : {e}", f"Manual parse error: {e}"))

    # If df available, compute regression automatically
    slope = intercept = r2 = None
    if df is not None:
        # assume first two columns: x, y
        try:
            x = df.iloc[:, 0].astype(float).values
            y = df.iloc[:, 1].astype(float).values
            slope, intercept, r2, res = linear_regression_from_xy(x, y)
            st.session_state.linearity_slope = slope
            st.session_state.linearity_intercept = intercept
            st.success(T(f"Calcul fait. pente={slope:.6g} intercept={intercept:.6g} R²={r2:.6g}",
                         f"Computed. slope={slope:.6g} intercept={intercept:.6g} R²={r2:.6g}"))
            # plot
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.scatter(x, y, label="data")
            xs = np.linspace(np.min(x), np.max(x), 100)
            ax.plot(xs, slope * xs + intercept, label="fit", linestyle='--')
            ax.set_xlabel(T("Concentration (" + unit + ")", "Concentration (" + unit + ")"))
            ax.set_ylabel("Signal")
            ax.legend()
            st.pyplot(fig)
        except Exception as e:
            st.error(T(f"Erreur calcul linéarité : {e}", f"Linearity calculation error: {e}"))

    # Predict unknown automatically (no separate button)
    st.markdown("**" + T("Calcul automatique de la valeur inconnue", "Automatic unknown value calculation") + "**")
    unknown_choice = st.selectbox(T("Que voulez-vous calculer ?", "What do you want to calculate?"),
                                  [T("Concentration inconnue à partir du signal", "Unknown concentration from signal"),
                                   T("Signal inconnu à partir de la concentration", "Unknown signal from concentration")], key="lin_unknown_choice")
    col_a, col_b = st.columns([2, 1])
    if unknown_choice == T("Concentration inconnue à partir du signal", "Unknown concentration from signal"):
        signal_val = col_a.number_input(T("Signal (enter)", "Signal (enter)"), value=0.0, key="lin_signal_val")
        if st.session_state.linearity_slope is not None:
            try:
                conc = predict_from_slope_intercept(st.session_state.linearity_slope, st.session_state.linearity_intercept, signal_val, predict_concentration=True)
                col_b.success(T(f"Concentration inconnue: {conc:.6g} {unit}", f"Unknown conc: {conc:.6g} {unit}"))
            except Exception as e:
                col_b.error(T(f"Erreur calcul concentration: {e}", f"Concentration calculation error: {e}"))
        else:
            col_b.info(T("Importer / calculer la linéarité d'abord.", "Please compute or import linearity first."))
    else:
        conc_val = col_a.number_input(T("Concentration (enter)", "Concentration (enter)"), value=0.0, key="lin_conc_val")
        if st.session_state.linearity_slope is not None:
            try:
                sig = predict_from_slope_intercept(st.session_state.linearity_slope, st.session_state.linearity_intercept, conc_val, predict_concentration=False)
                col_b.success(T(f"Signal prédit: {sig:.6g}", f"Predicted signal: {sig:.6g}"))
            except Exception as e:
                col_b.error(T(f"Erreur calcul signal: {e}", f"Signal calculation error: {e}"))
        else:
            col_b.info(T("Importer / calculer la linéarité d'abord.", "Please compute or import linearity first."))

    st.markdown("---")
    st.write(T("Exporter le rapport de linéarité (PDF).", "Export linearity report (PDF)."))
    company_name = st.text_input(T("Nom de la compagnie (obligatoire pour export)", "Company name (required for export)"), key="lin_company")
    if st.button(T("Exporter PDF", "Export PDF")):
        if not company_name.strip():
            st.warning(T("Veuillez entrer le nom de la compagnie avant d'exporter.", "Please enter company name before export."))
        elif st.session_state.linearity_slope is None:
            st.warning(T("Aucun calcul de linéarité disponible.", "No linearity calculation available."))
        else:
            pdf_bytes = export_linearity_pdf(company_name, st.session_state.linearity_slope, st.session_state.linearity_intercept, r2 if r2 is not None else 0.0, unit, data_df=df)
            st.download_button(label=T("Télécharger le PDF", "Download PDF"), data=pdf_bytes, file_name=f"linearity_{company_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf")

# ---------------------------
# UI: Signal-to-noise tab
# ---------------------------
def sn_tab():
    st.header(T("S/N - Signal / Noise", "S/N - Signal / Noise"))
    st.markdown(T("Importer un CSV avec deux colonnes (time, signal) pour calculer S/N. Vous pouvez aussi importer une image/PDF pour aperçu, mais le calcul nécessite un CSV.", 
                  "Upload a CSV with two columns (time, signal) to compute S/N. You may upload an image/PDF for preview, but calculation requires CSV."))
    company_name = st.text_input(T("Nom de la compagnie (obligatoire pour export)", "Company name (required for export)"), key="sn_company")

    uploaded_csv = st.file_uploader(T("Importer CSV (time, signal)", "Upload CSV (time, signal)"), type=["csv"], key="sn_csv")
    uploaded_img = st.file_uploader(T("Importer image (PNG/JPG) pour aperçu (optionnel)", "Upload image (PNG/JPG) for preview (optional)"), type=["png","jpg","jpeg"], key="sn_img")
    uploaded_pdf = st.file_uploader(T("Importer PDF pour aperçu (optionnel)", "Upload PDF for preview (optional)"), type=["pdf"], key="sn_pdf")

    df = None
    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv)
            if df.shape[1] < 2:
                st.error(T("Le CSV doit contenir au moins deux colonnes.", "CSV must have at least two columns."))
                df = None
            else:
                st.success(T("CSV chargé.", "CSV loaded."))
                st.dataframe(df.head(10))
        except Exception as e:
            st.error(T(f"Erreur lecture CSV : {e}", f"CSV read error: {e}"))
            df = None

    # preview image
    if uploaded_img is not None:
        try:
            img = Image.open(uploaded_img)
            st.image(img, caption=T("Aperçu image", "Image preview"), use_column_width=True)
        except UnidentifiedImageError:
            st.error(T("Impossible d'ouvrir l'image.", "Unable to open image."))

    if uploaded_pdf is not None:
        st.info(T("Aperçu PDF non implémenté dans l'app. Convertissez en image ou CSV pour aperçu/calcul.", "PDF preview not implemented. Convert to image or CSV for preview/calculation."))

    # If CSV present, allow user to select portion for noise calculation
    if df is not None:
        # assume time in col0, signal in col1
        time = df.iloc[:,0].astype(float).values
        signal = df.iloc[:,1].astype(float).values
        st.markdown(T("Sélectionnez la portion du signal utilisée pour estimer le bruit.", "Select the portion of the signal used to estimate noise."))
        idx_min = st.number_input(T("Index de début (0-based)", "Start index (0-based)"), min_value=0, max_value=len(signal)-1, value=0)
        idx_max = st.number_input(T("Index de fin", "End index"), min_value=0, max_value=len(signal)-1, value=len(signal)-1)
        if idx_min >= idx_max:
            st.warning(T("L'index de fin doit être supérieur à l'index de début.", "End index must be greater than start index."))
        else:
            noise_segment = signal[int(idx_min):int(idx_max)+1]
            noise_std = float(np.std(noise_segment, ddof=1)) if len(noise_segment)>1 else float(np.std(noise_segment))
            # signal of interest: user chooses a peak index
            peak_index = st.number_input(T("Index du signal (peak) à utiliser", "Peak index to use for signal"), min_value=0, max_value=len(signal)-1, value=int(len(signal)/2))
            sig_val = float(signal[int(peak_index)])
            st.write(T(f"Signal choisi: {sig_val:.6g}", f"Selected signal: {sig_val:.6g}"))
            st.write(T(f"Bruit (std) sur la portion choisie: {noise_std:.6g}", f"Noise (std) on chosen segment: {noise_std:.6g}"))
            # classic S/N: signal / noise_std
            if noise_std == 0:
                st.error(T("Bruit calculé = 0, impossible de calculer S/N.", "Noise is zero; cannot compute S/N."))
            else:
                sn_classic = sig_val / noise_std
                # USP S/N uses peak-to-peak noise? A common approach: S/N_USP = (signal_peak - baseline) / (2*noise_std)
                # We'll implement a standard variant: (peak - baseline) / (noise_std)
                # baseline: mean of noise segment
                baseline = float(np.mean(noise_segment))
                sn_usp = (sig_val - baseline) / noise_std if noise_std != 0 else np.nan
                st.success(T(f"S/N classique: {sn_classic:.4g}", f"Classic S/N: {sn_classic:.4g}"))
                st.success(T(f"S/N (USP-like): {sn_usp:.4g}", f"S/N (USP-like): {sn_usp:.4g}"))

                # LOD / LOQ from slope if available
                slope = st.session_state.linearity_slope
                if slope is not None and slope != 0:
                    lod = (3.3 * noise_std) / slope
                    loq = (10 * noise_std) / slope
                    st.write(T(f"LOD (concentration): {lod:.6g} {st.session_state.linearity_units}", f"LOD (conc): {lod:.6g} {st.session_state.linearity_units}"))
                    st.write(T(f"LOQ (concentration): {loq:.6g} {st.session_state.linearity_units}", f"LOQ (conc): {loq:.6g} {st.session_state.linearity_units}"))
                else:
                    st.info(T("Pente non disponible — importer/ calculer la linéarité pour LOD/LOQ en concentration.", "Slope not available — compute/import linearity for LOD/LOQ in concentration."))

                # Prepare report text and PDF
                report_text = f"Selected signal: {sig_val:.6g}\nNoise std: {noise_std:.6g}\nClassic S/N: {sn_classic:.6g}\nUSP-like S/N: {sn_usp:.6g}\n"
                if slope is not None:
                    report_text += f"LOD (conc): {lod:.6g} {st.session_state.linearity_units}\nLOQ (conc): {loq:.6g} {st.session_state.linearity_units}\n"

                if st.button(T("Exporter rapport S/N (PDF)", "Export S/N report (PDF)")):
                    if not company_name.strip():
                        st.warning(T("Veuillez entrer le nom de la compagnie avant d'exporter.", "Please enter company name before export."))
                    else:
                        pdf_bytes = export_sn_pdf(company_name, report_text)
                        st.download_button(label=T("Télécharger le PDF", "Download PDF"), data=pdf_bytes, file_name=f"SN_report_{company_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf")

    else:
        st.info(T("Importer un CSV pour effectuer les calculs S/N.", "Upload a CSV to perform S/N calculations."))

# ---------------------------
# UI: Admin panel (users)
# ---------------------------
def admin_panel():
    st.header(T("Administration des utilisateurs", "User administration"))
    st.markdown(T("Ajouter, supprimer ou modifier des utilisateurs. L'admin ne peut pas supprimer son propre compte ici pour éviter blocage.", "Add, delete or modify users. Admin cannot delete own account here to avoid lockout."))

    users = load_users()
    df_users = pd.DataFrame([{ "username": k, "role": v["role"] } for k,v in users.items()])
    st.dataframe(df_users)

    st.subheader(T("Ajouter un utilisateur", "Add user"))
    new_username = st.text_input(T("Nom d'utilisateur", "Username"), key="admin_new_user")
    new_password = st.text_input(T("Mot de passe", "Password"), key="admin_new_pass")
    new_role = st.selectbox(T("Rôle", "Role"), ["user","admin"], index=0, key="admin_new_role")
    if st.button(T("Ajouter", "Add user")):
        if not new_username or not new_password:
            st.error(T("Nom d'utilisateur et mot de passe requis.", "Username and password required."))
        else:
            add_user(new_username, new_password, new_role)
            st.success(T("Utilisateur ajouté.", "User added."))
            st.experimental_rerun()

    st.subheader(T("Supprimer un utilisateur", "Delete user"))
    del_user = st.text_input(T("Nom d'utilisateur à supprimer", "Username to delete"), key="admin_del_user")
    if st.button(T("Supprimer", "Delete")):
        current = st.session_state.username
        if del_user.lower() == current:
            st.error(T("Vous ne pouvez pas supprimer l'utilisateur connecté.", "You cannot delete the currently logged-in user."))
        else:
            ok = delete_user(del_user)
            if ok:
                st.success(T("Utilisateur supprimé.", "User deleted."))
                st.experimental_rerun()
            else:
                st.error(T("Utilisateur non trouvé.", "User not found."))

    st.subheader(T("Modifier un utilisateur", "Modify user"))
    mod_username = st.text_input(T("Nom d'utilisateur à modifier", "Username to modify"), key="admin_mod_user")
    mod_password = st.text_input(T("Nouveau mot de passe (laisser vide pour ne pas changer)", "New password (leave blank to keep)"), key="admin_mod_pass")
    mod_role = st.selectbox(T("Nouveau rôle", "New role"), ["user","admin"], key="admin_mod_role")
    if st.button(T("Modifier", "Modify")):
        if not mod_username:
            st.error(T("Nom d'utilisateur requis.", "Username required."))
        else:
            ok = modify_user(mod_username, password=mod_password if mod_password else None, role=mod_role)
            if ok:
                st.success(T("Utilisateur modifié.", "User modified."))
                st.experimental_rerun()
            else:
                st.error(T("Utilisateur non trouvé.", "User not found."))

# ---------------------------
# UI: user change password (discrete)
# ---------------------------
def user_change_password_section():
    st.markdown("----")
    st.subheader(T("Changer mot de passe", "Change password"))
    st.markdown(T("Section discrète pour les utilisateurs.", "Discrete section for users."))
    old = st.text_input(T("Ancien mot de passe", "Old password"), type="password", key="chg_old")
    newp = st.text_input(T("Nouveau mot de passe", "New password"), type="password", key="chg_new")
    if st.button(T("Changer mot de passe", "Change password"), key="chg_confirm"):
        users = load_users()
        username = st.session_state.username
        if username and username in users and users[username]["password"] == old:
            users[username]["password"] = newp
            save_users(users)
            st.success(T("Mot de passe changé.", "Password changed."))
        else:
            st.error(T("Ancien mot de passe incorrect.", "Old password incorrect."))

# ---------------------------
# Main UI
# ---------------------------
def main():
    init_session()

    # top language selector
    lang = st.selectbox("Lang / Langue", options=["FR","EN"], index=0 if st.session_state.language=="FR" else 1, key="top_lang")
    st.session_state.language = lang

    st.title(T("LABT - Linéarité et S/N", "LABT - Linearity & S/N"))

    if not st.session_state.logged_in:
        login_form()
        st.stop()

    # logged in
    st.sidebar.empty()  # ensure no sidebar used
    st.write(T(f"Bienvenue {st.session_state.username}", f"Welcome {st.session_state.username}"))
    # Menu
    menu = st.radio(T("Menu principal", "Main menu"), [T("Linéarité","Linearity"), T("S/N","S/N"), T("Admin","Admin")], index=0, key="main_menu")
    if menu == T("Linéarité","Linearity"):
        linearity_tab()
    elif menu == T("S/N","S/N"):
        sn_tab()
    else:
        # Admin restricted
        users = load_users()
        if st.session_state.username in users and users[st.session_state.username]["role"] == "admin":
            admin_panel()
        else:
            st.error(T("Accès refusé: vous n'êtes pas admin.", "Access denied: not admin."))

    # change password discrete
    user_change_password_section()

    # logout button (small)
    if st.button(T("Déconnexion", "Logout")):
        st.session_state.logged_in = False
        logout()
        st.experimental_rerun()

if __name__ == "__main__":
    main()