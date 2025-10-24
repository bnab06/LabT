# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import io, json, os
from datetime import datetime
from scipy import stats
from PIL import Image

# -------------------------
# Configuration / constants
# -------------------------
USERS_FILE = "users.json"
DEFAULT_UNIT = "µg/mL"
ALLOWED_CHROM_TYPES = ["csv", "png", "pdf"]
# ensure session state keys exist
if "lang" not in st.session_state:
    st.session_state["lang"] = "EN"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "exported_slope" not in st.session_state:
    st.session_state["exported_slope"] = None
if "exported_unit" not in st.session_state:
    st.session_state["exported_unit"] = DEFAULT_UNIT

# ========================
# 🈹 BILINGUE - Français / English
# ========================
def T(en, fr):
    """Traduction simple: EN default, FR alternative."""
    return fr if st.session_state.get("lang", "EN") == "FR" else en

def language_selector():
    lang = st.selectbox("🌐 Language / Langue", ["EN", "FR"], index=0 if st.session_state.get("lang","EN")=="EN" else 1, key="lang_select_box")
    st.session_state.lang = lang

# ========================
# 🔐 USERS (file-based simple auth)
# ========================
def load_users():
    """Charge users depuis le fichier users.json ; crée un jeu par défaut si absent."""
    if not os.path.exists(USERS_FILE):
        default = {"admin": "admin123", "user1": "user123"}
        with open(USERS_FILE, "w") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # si fichier corrompu, recréer un minimal
        default = {"admin": "admin123"}
        with open(USERS_FILE, "w") as f:
            json.dump(default, f, indent=2)
        return default

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ------------------------
# Authentication UI
# ------------------------
def login_area():
    st.title("LabT")
    st.write(T("Please log in to continue.", "Veuillez vous connecter pour continuer."))

    col1, col2 = st.columns([2,3])
    with col1:
        username = st.text_input(T("Username", "Nom d’utilisateur"), key="login_user")
    with col2:
        password = st.text_input(T("Password", "Mot de passe"), type="password", key="login_pass")

    if st.button(T("Login", "Connexion"), key="btn_login"):
        users = load_users()
        uname = (username or "").strip().lower()
        if not uname:
            st.error(T("Please enter a username.", "Veuillez entrer un nom d’utilisateur."))
            return
        if uname in users and users[uname] == password:
            st.session_state.logged_in = True
            st.session_state.user = uname
            st.success(T("Logged in successfully.", "Connecté avec succès."))
        else:
            st.error(T("Invalid username or password", "Nom d’utilisateur ou mot de passe invalide"))

# ------------------------
# Profile area (change password) - separated from main menu
# ------------------------
def profile_area():
    st.header(T("Profile", "Profil"))
    st.write(T("Change your password here (discreet).", "Changez votre mot de passe ici (discret)."))

    users = load_users()
    user = st.session_state.user
    col1, col2 = st.columns(2)
    with col1:
        old = st.text_input(T("Old password", "Ancien mot de passe"), type="password", key="old_pw_profile")
    with col2:
        new = st.text_input(T("New password", "Nouveau mot de passe"), type="password", key="new_pw_profile")
    confirm = st.text_input(T("Confirm new password", "Confirmer le nouveau mot de passe"), type="password", key="confirm_pw_profile")

    if st.button(T("Update password", "Mettre à jour le mot de passe"), key="btn_update_pw"):
        if users.get(user) != old:
            st.error(T("Old password incorrect", "Ancien mot de passe incorrect"))
        elif not new:
            st.error(T("New password must not be empty", "Le nouveau mot de passe ne doit pas être vide"))
        elif new != confirm:
            st.error(T("Passwords do not match", "Les mots de passe ne correspondent pas"))
        else:
            users[user] = new
            save_users(users)
            st.success(T("Password updated", "Mot de passe mis à jour"))

# ------------------------
# Admin: add / delete / modify users
# ------------------------
def admin_area():
    st.header(T("Admin - User Management", "Admin - Gestion des utilisateurs"))
    st.info(T("Admin can add, delete, modify users. The users file is not printed here for security.", "L’admin peut ajouter, supprimer, modifier des utilisateurs. Le fichier users n'est pas affiché ici."))
    users = load_users()

    # Add user
    st.subheader(T("Add user", "Ajouter un utilisateur"))
    new_uname = st.text_input(T("New username", "Nom d’utilisateur (nouveau)"), key="admin_new_user")
    new_pw = st.text_input(T("Password", "Mot de passe"), type="password", key="admin_new_pw")
    if st.button(T("Add user", "Ajouter"), key="btn_admin_add"):
        if not new_uname:
            st.error(T("Please enter a username", "Veuillez entrer un nom d’utilisateur"))
        else:
            nu = new_uname.strip().lower()
            if nu in users:
                st.error(T("User already exists", "L’utilisateur existe déjà"))
            else:
                users[nu] = new_pw or ""
                save_users(users)
                st.success(T("User added", "Utilisateur ajouté"))

    # Modify user
    st.subheader(T("Modify user", "Modifier un utilisateur"))
    mod_user = st.selectbox(T("Select user", "Sélectionner utilisateur"), sorted(list(users.keys())), key="admin_mod_select")
    mod_pw = st.text_input(T("New password (leave blank to keep)", "Nouveau mot de passe (laisser vide pour conserver)"), type="password", key="admin_mod_pw")
    if st.button(T("Modify", "Modifier"), key="btn_admin_mod"):
        if mod_user:
            if mod_pw:
                users[mod_user] = mod_pw
                save_users(users)
                st.success(T("Password updated", "Mot de passe mis à jour"))
            else:
                st.info(T("No change made", "Aucun changement effectué"))

    # Delete user
    st.subheader(T("Delete user", "Supprimer un utilisateur"))
    del_user = st.selectbox(T("User to delete", "Utilisateur à supprimer"), sorted(list(users.keys())), key="admin_del_select")
    if st.button(T("Delete", "Supprimer"), key="btn_admin_del"):
        if del_user == "admin":
            st.error(T("Cannot delete admin", "Impossible de supprimer admin"))
        else:
            users.pop(del_user, None)
            save_users(users)
            st.success(T("User deleted", "Utilisateur supprimé"))

# ------------------------
# Utility: regression & plotting for linearity
# ------------------------
def compute_linearity_from_df(df):
    """From df with at least 2 columns, returns x,y arrays and linear regression results"""
    x = df.iloc[:,0].values.astype(float)
    y = df.iloc[:,1].values.astype(float)
    # remove NaNs
    mask = ~np.isnan(x) & ~np.isnan(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2:
        raise ValueError(T("At least two valid points are required.", "Au moins deux points valides sont requis."))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r2 = r_value**2
    return x, y, slope, intercept, r2

def plot_linearity(x, y, slope, intercept):
    fig, ax = plt.subplots()
    ax.scatter(x, y, label=T("Data","Données"))
    xs = np.linspace(np.min(x), np.max(x), 100)
    ax.plot(xs, slope*xs + intercept, color="red", label=f"y={slope:.4g}x+{intercept:.4g}")
    ax.set_xlabel(T("Concentration", "Concentration"))
    ax.set_ylabel(T("Signal", "Signal"))
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)

# ------------------------
# Linearity tab
# ------------------------
def linearity_tab():
    st.header(T("Linearity", "Linéarité"))
    st.write(T("Choose data input method: CSV upload or manual entry (comma-separated).", "Choisissez la méthode d'entrée: CSV ou saisie manuelle (séparées par des virgules)."))

    unit = st.selectbox(T("Concentration unit", "Unité de concentration"), [DEFAULT_UNIT, "mg/mL", "ng/mL"], index=0, key="lin_unit")
    st.session_state["exported_unit"] = unit  # default for export

    input_mode = st.radio(T("Input", "Saisie"), [T("Upload CSV", "Importer CSV"), T("Manual input", "Saisie manuelle")], index=0, key="lin_input_mode")

    df = None
    if input_mode == T("Upload CSV", "Importer CSV"):
        file = st.file_uploader(T("Upload a CSV with at least two columns: concentration,signal", "Importer un CSV avec au moins deux colonnes: concentration,signal"), type="csv", key="lin_csv")
        if file is not None:
            try:
                df = pd.read_csv(file)
            except Exception as e:
                st.error(T("Error reading CSV", "Erreur lecture CSV") + f": {e}")
                return
            if df.shape[1] < 2:
                st.error(T("CSV must have at least two columns.", "Le CSV doit contenir au moins deux colonnes."))
                return
    else:
        st.write(T("Enter concentration values (comma-separated) in first box and corresponding signal values in second box.", "Entrez les valeurs de concentration (séparées par des virgules) dans la première, et les signaux correspondants dans la seconde."))
        col1, col2 = st.columns(2)
        with col1:
            conc_text = st.text_area(T("Concentrations", "Concentrations (ex: 0,1,2,5)"), key="lin_manual_conc")
        with col2:
            sig_text = st.text_area(T("Signals", "Signaux (ex: 10,20,30,50)"), key="lin_manual_sig")
        if conc_text and sig_text:
            try:
                conc = [float(s.strip()) for s in conc_text.split(",") if s.strip()!='']
                sig = [float(s.strip()) for s in sig_text.split(",") if s.strip()!='']
                if len(conc) != len(sig):
                    st.error(T("Concentration and signal lists must have the same length.", "Les listes concentration et signal doivent avoir la même longueur."))
                    return
                df = pd.DataFrame({"Concentration": conc, "Signal": sig})
            except Exception as e:
                st.error(T("Error parsing manual input", "Erreur de parsing de la saisie") + f": {e}")
                return

    if df is None:
        st.info(T("Provide data to compute linearity.", "Fournissez des données pour calculer la linéarité."))
        return

    # show data
    st.dataframe(df)

    # compute regression
    try:
        x, y, slope, intercept, r2 = compute_linearity_from_df(df)
    except Exception as e:
        st.error(T("Linearity calculation error:", "Erreur calcul linéarité:") + f" {e}")
        return

    st.write(T("Equation", "Équation"), f": y = {slope:.6g} x + {intercept:.6g}")
    st.write("R²:", round(r2, 6))
    st.write(T("Slope (will be exportable to S/N tab)", "Pente (exportable vers S/N)"), ":", slope)

    # plot
    plot_linearity(x, y, slope, intercept)

    # store slope in session for export to S/N
    st.session_state["exported_slope"] = slope

    # Automatic calculation of unknown (no button)
    st.subheader(T("Calculate unknown", "Calculer l'inconnu"))
    calc_choice = st.selectbox(T("What is unknown?", "Quel est l'inconnu?"), [T("Unknown concentration", "Concentration inconnue"), T("Unknown signal", "Signal inconnu")], key="lin_calc_choice")
    if calc_choice == T("Unknown concentration", "Concentration inconnue"):
        sig_val = st.number_input(T("Enter signal value", "Entrer la valeur du signal"), key="lin_calc_signal")
        if sig_val is not None and slope != 0:
            conc_calc = (sig_val - intercept) / slope
            st.success(f"{T('Calculated concentration','Concentration calculée')}: {conc_calc:.6g} {unit}")
    else:
        conc_val = st.number_input(T("Enter concentration value", "Entrer la valeur de concentration"), key="lin_calc_conc")
        if conc_val is not None:
            sig_calc = slope * conc_val + intercept
            st.success(f"{T('Calculated signal','Signal calculé')}: {sig_calc:.6g}")

    # Export PDF for linearity
    if st.button(T("Export linearity report (PDF)", "Exporter rapport linéarité (PDF)"), key="btn_export_lin"):
        company = st.text_input(T("Company name (will appear in PDF)", "Nom de la compagnie (apparaîtra dans le PDF)"), key="lin_company_name")
        # ask company if not provided now
        if not company:
            st.warning(T("Please enter company name to include in the report", "Veuillez entrer le nom de la compagnie pour le rapport"))
        else:
            pdf_bytes = build_linearity_pdf(company, st.session_state.get("user",""), slope, intercept, r2, df, unit)
            st.download_button(T("Download linearity PDF", "Télécharger le PDF de linéarité"), data=pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")

# ------------------------
# Build PDF helpers
# ------------------------
def build_linearity_pdf(company, user, slope, intercept, r2, df, unit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, company, ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"{T('Generated by','Généré par')}: {user}", ln=True)
    pdf.cell(0, 8, f"{T('Date','Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 8, T("Linearity results", "Résultats de linéarité"), ln=True)
    pdf.cell(0, 8, f"y = {slope:.6g} x + {intercept:.6g}", ln=True)
    pdf.cell(0, 8, f"R² = {r2:.6g}", ln=True)
    pdf.cell(0, 8, f"{T('Concentration unit','Unité de concentration')}: {unit}", ln=True)
    pdf.ln(6)

    # plot image
    plt.figure(figsize=(6,3.5))
    plt.scatter(df.iloc[:,0], df.iloc[:,1])
    xs = np.linspace(np.min(df.iloc[:,0].values.astype(float)), np.max(df.iloc[:,0].values.astype(float)), 100)
    plt.plot(xs, slope*xs + intercept, color="red")
    plt.xlabel(T("Concentration", "Concentration"))
    plt.ylabel(T("Signal", "Signal"))
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    pdf.image(buf, x=15, w=180)
    # attach a results table
    pdf.add_page()
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, T("Data (Concentration, Signal)", "Données (Concentration, Signal)"), ln=True)
    for i, row in df.iterrows():
        pdf.cell(0, 6, f"{row.iloc[0]}, {row.iloc[1]}", ln=True)
    out = pdf.output(dest="S").encode("latin-1")
    return out

# ------------------------
# S/N calculations, LOD, LOQ
# ------------------------
def sn_tab():
    st.header("S/N, LOD, LOQ")
    st.write(T("Upload a chromatogram CSV, or paste digitized data manually. PNG/PDF preview available but automatic digitization is not implemented — see instructions below.", 
               "Importer un chromatogramme CSV, ou coller des données digitizées manuellement. Aperçu PNG/PDF disponible mais digitization automatique non implémentée — voir instructions ci-dessous."))

    # slope exported from linearity available
    exported_slope = st.session_state.get("exported_slope", None)
    if exported_slope is None:
        st.info(T("No slope exported from linearity yet. You can still compute S/N using signal values; export slope from linearity to compute LOD/LOQ in concentration.", 
                  "Aucune pente exportée depuis la linéarité. Vous pouvez calculer S/N depuis les signaux ; exportez la pente depuis linéarité pour LOD/LOQ en concentration."))

    # Input method
    mode = st.radio(T("Input type", "Type d'entrée"), [T("Upload CSV", "Importer CSV"), T("Paste digitized data", "Coller données digitizées"), T("Preview image/pdf", "Aperçu image/pdf")], index=0, key="sn_input_mode")

    df = None
    image_uploaded = None
    if mode == T("Upload CSV", "Importer CSV"):
        file = st.file_uploader(T("Upload CSV chromatogram with two columns (time,signal)", "Importer CSV chromatogramme (time,signal)"), type="csv", key="sn_csv")
        if file is not None:
            try:
                df = pd.read_csv(file)
                if df.shape[1] < 2:
                    st.error(T("CSV must have at least two columns.", "Le CSV doit contenir au moins deux colonnes."))
                    return
                # assume first two columns are time, signal
                df = df.iloc[:, :2]
                df.columns = ["Time", "Signal"]
            except Exception as e:
                st.error(T("Error reading CSV", "Erreur lecture CSV") + f": {e}")
                return
    elif mode == T("Paste digitized data", "Coller données digitizées"):
        st.write(T("Paste two comma-separated lists: times and signals. This is the manual 'digitize' mode.", 
                   "Collez deux listes séparées par des virgules: temps et signaux. Mode 'digitize' manuel."))
        times_txt = st.text_area(T("Times (comma-separated)", "Temps (séparés par des virgules)"), key="sn_times")
        sigs_txt = st.text_area(T("Signals (comma-separated)", "Signaux (séparés par des virgules)"), key="sn_sigs")
        if times_txt and sigs_txt:
            try:
                times = [float(s.strip()) for s in times_txt.split(",") if s.strip()!='']
                sigs = [float(s.strip()) for s in sigs_txt.split(",") if s.strip()!='']
                if len(times) != len(sigs):
                    st.error(T("Times and signals must have same length", "Les temps et signaux doivent avoir la même longueur"))
                    return
                df = pd.DataFrame({"Time": times, "Signal": sigs})
            except Exception as e:
                st.error(T("Error parsing data", "Erreur de parsing") + f": {e}")
                return
    else:  # preview image/pdf
        file_img = st.file_uploader(T("Upload PNG or PDF for preview (CSV recommended for calculations)", "Importer PNG ou PDF pour aperçu (CSV recommandé pour calculs)"), type=["png","pdf","jpg","jpeg"], key="sn_img")
        if file_img is not None:
            # show preview (PIL open) for images; pdf preview note
            try:
                if hasattr(file_img, "type") and file_img.type in ("image/png","image/jpeg"):
                    image = Image.open(file_img)
                    st.image(image, caption=T("Preview of uploaded image", "Aperçu de l'image"))
                    st.info(T("Automatic digitizing from image is not implemented. Please use 'Paste digitized data' or convert to CSV and upload.", 
                              "La digitalisation automatique d'image n'est pas implémentée. Utilisez 'Coller données digitizées' ou convertissez en CSV."))
                else:
                    st.info(T("PDF preview not implemented — please convert to CSV for calculations or paste digitized data.", 
                              "Aperçu PDF non implémenté — convertissez en CSV pour les calculs ou collez des données digitalisées."))
            except Exception as e:
                st.error(T("File preview error", "Erreur d'aperçu") + f": {e}")
            return

    if df is None:
        st.info(T("Provide chromatogram data to compute S/N.", "Fournissez des données chromatographiques pour calculer S/N."))
        return

    # convert time to numeric if possible
    try:
        df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
        df["Signal"] = pd.to_numeric(df["Signal"], errors="coerce")
    except Exception as e:
        st.error(T("Error converting data to numeric", "Erreur conversion numérique") + f": {e}")
        return

    if df["Time"].isnull().all() or df["Signal"].isnull().all():
        st.error(T("CSV must contain numeric time and signal columns.", "Le CSV doit contenir des colonnes temporelles et de signal numériques."))
        return

    df = df.dropna(subset=["Time","Signal"]).reset_index(drop=True)

    # show chromatogram
    st.subheader(T("Chromatogram", "Chromatogramme"))
    fig, ax = plt.subplots()
    ax.plot(df["Time"], df["Signal"], label="Signal")
    ax.set_xlabel("Time")
    ax.set_ylabel("Signal")
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)

    # Select region by index or time
    st.subheader(T("Select region for baseline / peak (for noise & signal)", "Sélectionnez la zone pour baseline / pic (bruit & signal)"))
    min_time = float(np.min(df["Time"]))
    max_time = float(np.max(df["Time"]))
    col1, col2 = st.columns(2)
    with col1:
        t0 = st.number_input(T("Region start time", "Début zone (time)"), value=min_time, min_value=min_time, max_value=max_time, key="sn_t0")
    with col2:
        t1 = st.number_input(T("Region end time", "Fin zone (time)"), value=max_time, min_value=min_time, max_value=max_time, key="sn_t1")

    if t0 >= t1:
        st.error(T("Region start must be less than region end", "Le début doit être inférieur à la fin"))
        return

    region_mask = (df["Time"] >= t0) & (df["Time"] <= t1)
    region = df.loc[region_mask]
    if region.empty:
        st.error(T("Selected region contains no data points", "La zone sélectionnée ne contient aucun point"))
        return

    # compute baseline (noise) using user choice: use portion (left baseline) or full region stdev
    baseline_method = st.selectbox(T("Noise baseline method", "Méthode baseline bruit"), [T("STD of selected region","Écart-type de la région sélectionnée"), T("STD of left part (first 10%)", "Écart-type de la partie gauche (10%)")], key="sn_baseline_method")
    if baseline_method == T("STD of left part (first 10%)", "Écart-type de la partie gauche (10%)"):
        left_count = max(1, int(len(region) * 0.1))
        noise_region = region.iloc[:left_count]["Signal"]
    else:
        noise_region = region["Signal"]

    sigma = float(np.std(noise_region, ddof=1)) if len(noise_region)>1 else float(np.std(noise_region))
    signal_max = float(region["Signal"].max())
    # Classical S/N
    sn_classic = signal_max / sigma if sigma != 0 else np.inf

    # USP S/N: we'll use (signal_max - mean_noise)/std_noise
    mean_noise = float(np.mean(noise_region))
    sn_usp = (signal_max - mean_noise) / (np.std(noise_region, ddof=1) if len(noise_region)>1 else np.std(noise_region)) if np.std(noise_region) != 0 else np.inf

    st.write(T("Noise (std)", "Bruit (écart-type)"), ":", f"{sigma:.6g}")
    st.write(T("Signal (max in region)", "Signal (max dans la région)"), ":", f"{signal_max:.6g}")
    st.write(T("S/N (classical)", "S/N (classique)"), ":", f"{sn_classic:.3f}")
    st.write(T("S/N (USP-like)", "S/N (type USP)"), ":", f"{sn_usp:.3f}")

    # LOD/LOQ calculations:
    # classical formulas: LOD = 3.3 * sigma / slope ; LOQ = 10 * sigma / slope
    st.subheader(T("LOD / LOQ calculations", "Calculs LOD / LOQ"))
    # user can choose whether sigma is baseline std or residual std from linearity
    sigma_choice = st.selectbox(T("Sigma used for LOD/LOQ", "Sigma à utiliser pour LOD/LOQ"), [T("Baseline std (from selected region)", "Bruit baseline (de la région sélectionnée)"), T("Residual std from linearity regression", "Écart-type des résidus de la linéarité (si available)")], key="sn_sigma_choice")

    sigma_for_lod = sigma
    if sigma_choice == T("Residual std from linearity regression", "Écart-type des résidus de la linéarité (si available)"):
        # we compute residual std if slope exported and a linearity dataframe exist in session
        # we will try to use a linearity df if present in session_state (not persisted), otherwise fallback
        lin_df = st.session_state.get("last_linearity_df", None)
        slope_from_lin = st.session_state.get("exported_slope", None)
        if lin_df is None or slope_from_lin is None:
            st.warning(T("No linearity residuals available; using baseline sigma instead.", "Pas de linéarité disponible ; utilisation du sigma baseline."))
        else:
            # compute residuals
            x = lin_df.iloc[:,0].astype(float).values
            y = lin_df.iloc[:,1].astype(float).values
            residuals = y - (slope_from_lin * x + st.session_state.get("exported_intercept", 0.0))
            sigma_for_lod = float(np.std(residuals, ddof=1) if len(residuals)>1 else np.std(residuals))
    st.write(T("Sigma used", "Sigma utilisé"), ":", f"{sigma_for_lod:.6g}")

    slope_for_calc = st.session_state.get("exported_slope", None)
    if slope_for_calc is None:
        st.warning(T("No slope exported from linearity. LOD/LOQ in concentration require slope. Export slope from Linearity tab.", 
                     "Aucune pente exportée depuis la linéarité. LOD/LOQ en concentration nécessitent la pente. Exportez-la depuis la tab Linéarité."))
    else:
        lod = 3.3 * sigma_for_lod / slope_for_calc if slope_for_calc != 0 else np.inf
        loq = 10 * sigma_for_lod / slope_for_calc if slope_for_calc != 0 else np.inf
        st.write(T("LOD (concentration)", "LOD (concentration)"), ":", f"{lod:.6g} {st.session_state.get('exported_unit', DEFAULT_UNIT)}")
        st.write(T("LOQ (concentration)", "LOQ (concentration)"), ":", f"{loq:.6g} {st.session_state.get('exported_unit', DEFAULT_UNIT)}")

    # Export S/N report PDF
    if st.button(T("Export S/N report (PDF)", "Exporter rapport S/N (PDF)"), key="btn_export_sn"):
        company = st.text_input(T("Company name (will appear in PDF)", "Nom de la compagnie (apparaîtra dans le PDF)"), key="sn_company")
        if not company:
            st.warning(T("Please enter company name to include in the report", "Veuillez entrer le nom de la compagnie pour le rapport"))
        else:
            pdf_bytes = build_sn_pdf(company=company, user=st.session_state.get("user",""), df=df, region=(t0,t1), sigma=sigma, signal_max=signal_max, sn_classic=sn_classic, sn_usp=sn_usp, lod=locals().get("lod",None), loq=locals().get("loq",None), unit=st.session_state.get("exported_unit",DEFAULT_UNIT))
            st.download_button(T("Download S/N report", "Télécharger le rapport S/N"), data=pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")

def build_sn_pdf(company, user, df, region, sigma, signal_max, sn_classic, sn_usp, lod, loq, unit):
    t0, t1 = region
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, company, ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"{T('Generated by','Généré par')}: {user}", ln=True)
    pdf.cell(0, 8, f"{T('Date','Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 8, T("S/N results", "Résultats S/N"), ln=True)
    pdf.cell(0, 8, f"{T('Selected region','Zone sélectionnée')}: {t0} - {t1}", ln=True)
    pdf.cell(0, 8, f"{T('Noise (std)','Bruit (écart-type)')}: {sigma:.6g}", ln=True)
    pdf.cell(0, 8, f"{T('Signal (max)','Signal (max)')}: {signal_max:.6g}", ln=True)
    pdf.cell(0, 8, f"S/N (classical): {sn_classic:.3f}", ln=True)
    pdf.cell(0, 8, f"S/N (USP-like): {sn_usp:.3f}", ln=True)
    if lod is not None and loq is not None:
        pdf.cell(0, 8, f"LOD: {lod:.6g} {unit}", ln=True)
        pdf.cell(0, 8, f"LOQ: {loq:.6g} {unit}", ln=True)

    # chromatogram snapshot
    plt.figure(figsize=(6,3.5))
    plt.plot(df["Time"], df["Signal"])
    plt.axvspan(t0, t1, color='orange', alpha=0.2)
    plt.xlabel("Time")
    plt.ylabel("Signal")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    pdf.image(buf, x=15, w=180)

    out = pdf.output(dest="S").encode("latin-1")
    return out

# ------------------------
# App main
# ------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    # do not call experimental_rerun to avoid compatibility issues

def main():
    st.set_page_config(page_title="LabT", layout="wide")
    language_selector()

    if not st.session_state.get("logged_in", False):
        login_area()
        return

    # after login
    user = st.session_state.get("user", None)
    st.sidebar.title("LabT")
    st.sidebar.write(f"{T('User', 'Utilisateur')}: {user}")
    # provide logout in sidebar
    if st.sidebar.button(T("Logout", "Déconnexion"), key="btn_logout"):
        logout()
        st.experimental_rerun()

    # main menu
    if user == "admin":
        st.title(T("Admin console", "Console Admin"))
        admin_area()
        st.markdown("---")
        if st.button(T("Go to profile (change password)", "Aller au profil (changer mot de passe)"), key="btn_admin_profile"):
            st.session_state["show_profile"] = True
        if st.session_state.get("show_profile", False):
            profile_area()
    else:
        st.title("LabT")
        # top controls: quick access to profile
        col_left, col_right = st.columns([3,1])
        with col_right:
            if st.button(T("Profile", "Profil"), key="btn_profile_top"):
                st.session_state["show_profile"] = not st.session_state.get("show_profile", False)

        if st.session_state.get("show_profile", False):
            profile_area()
            st.markdown("---")

        # tabs: Linéarité and S/N
        tab = st.radio("", [T("Linearity", "Linéarité"), T("S/N", "S/N")], index=0, key="main_tabs")
        if tab == T("Linearity", "Linéarité"):
            linearity_tab()
        else:
            sn_tab()

    # persist last linearity df if available (so sn_tab can read residuals if user previously computed)
    # We avoid writing huge objects to session_state, only a small one:
    # if we have exported slope and intercept, and in the last run had a dataframe in local variable,
    # the functions above set st.session_state["last_linearity_df"] and exported_intercept when computing
    # To support that we set them when compute_linearity_from_df finishes (we set in linearity_tab)
    # (Already assigned earlier: but ensure keys exist)
    if "last_linearity_df" not in st.session_state:
        st.session_state["last_linearity_df"] = None
    if "exported_intercept" not in st.session_state:
        st.session_state["exported_intercept"] = None

if __name__ == "__main__":
    main()