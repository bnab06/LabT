# app.py
# LabT - Linéarité & S/N (bilingue) - Version corrigée
# Python 3.11 recommended (see requirements.txt)

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# ----------------------------
# Configuration / Defaults
# ----------------------------
st.set_page_config(page_title="LabT", layout="wide")

USERS_FILE = "users.json"

DEFAULT_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user1": {"password": "user123", "role": "user"},
    "user2": {"password": "user456", "role": "user"},
}

# Helper to rerun safely (works across Streamlit versions)
def safe_rerun():
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
            return
        except Exception:
            pass
    st.rerun()

# ----------------------------
# Users management (lowercase keys)
# ----------------------------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        users_norm = {k.lower(): v for k, v in DEFAULT_USERS.items()}
        with open(USERS_FILE, "w") as f:
            json.dump(users_norm, f, indent=4)

def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def normalize_username(u):
    if u is None:
        return ""
    return u.strip().lower()

def authenticate(username, password):
    users = load_users()
    un = normalize_username(username)
    if un in users and users[un]["password"] == password:
        return users[un]["role"]
    return None

def add_user(username, password, role="user"):
    if not username or not password:
        return False, "username and password required"
    users = load_users()
    un = normalize_username(username)
    if un in users:
        return False, "user exists"
    users[un] = {"password": password, "role": role}
    save_users(users)
    return True, "added"

def delete_user(username):
    users = load_users()
    un = normalize_username(username)
    if un in users:
        del users[un]
        save_users(users)
        return True
    return False

def modify_user(username, password=None, role=None):
    users = load_users()
    un = normalize_username(username)
    if un not in users:
        return False
    if password:
        users[un]["password"] = password
    if role:
        users[un]["role"] = role
    save_users(users)
    return True

def change_own_password(username, new_password):
    return modify_user(username, password=new_password)

# ----------------------------
# Math / Analysis helpers
# ----------------------------
def fit_linearity(concs, signals):
    # returns slope, intercept, r2
    x = np.array(concs, dtype=float)
    y = np.array(signals, dtype=float)
    if len(x) < 2:
        raise ValueError("Need at least two points")
    slope, intercept = np.polyfit(x, y, 1)
    ypred = slope * x + intercept
    ss_res = np.sum((y - ypred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0
    return slope, intercept, r2

def unknown_from_conc(slope, intercept, signal_value):
    # returns concentration = (signal - intercept)/slope
    if slope == 0:
        raise ValueError("slope is zero")
    return (signal_value - intercept) / slope

def unknown_from_signal(slope, intercept, conc_value):
    return slope * conc_value + intercept

def sn_classic(signal_array, noise_region=None):
    s = np.array(signal_array, dtype=float)
    if noise_region is None:
        # default: last 10% as noise
        n = int(max(1, 0.1 * len(s)))
        noise = s[-n:]
    else:
        noise = np.array(noise_region, dtype=float)
    peak = np.max(s)
    noise_std = np.std(noise, ddof=1) if len(noise) > 1 else np.std(noise)
    if noise_std == 0:
        return np.nan, peak, noise_std
    return peak / noise_std, peak, noise_std

def sn_usp(peak_region, noise_region):
    p = np.array(peak_region, dtype=float)
    n = np.array(noise_region, dtype=float)
    # USP: amplitude (peak height above baseline) / std(noise)
    amplitude = np.max(p) - np.min(p)
    noise_std = np.std(n, ddof=1) if len(n) > 1 else np.std(n)
    if noise_std == 0:
        return np.nan, amplitude, noise_std
    return amplitude / noise_std, amplitude, noise_std

def lod_loq_from_residuals(concs, signals, slope):
    # use residual std dev sigma, LOD=3.3*sigma/slope, LOQ=10*sigma/slope
    x = np.array(concs, dtype=float)
    y = np.array(signals, dtype=float)
    ypred = slope * x + (np.mean(y) - slope * np.mean(x))
    residuals = y - ypred
    sigma = np.std(residuals, ddof=1)
    if slope == 0:
        return np.nan, np.nan
    lod = 3.3 * sigma / abs(slope)
    loq = 10.0 * sigma / abs(slope)
    return lod, loq

def lod_loq_from_sn(noise_std, slope, factor=3.3):
    # approximate: LOD = factor * noise / slope
    if slope == 0:
        return np.nan, np.nan
    lod = factor * noise_std / abs(slope)
    loq = 10.0 * noise_std / abs(slope)
    return lod, loq

# ----------------------------
# PDF export (text + embedded matplotlib PNG)
# ----------------------------
def generate_pdf_report(title, company_name, username, summary_lines, fig=None, out_filename="LabT_Report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, title, ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Company: {company_name}", ln=True)
    pdf.cell(0, 7, f"User: {username}", ln=True)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 7, "App: LabT", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    for line in summary_lines:
        pdf.multi_cell(0, 6, line)
    pdf.ln(4)

    # add figure if provided (matplotlib fig)
    if fig is not None:
        # Save to buffer
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        # FPDF requires a filename; we can write to a temporary file
        tmp_img = "tmp_report_plot.png"
        with open(tmp_img, "wb") as f:
            f.write(buf.read())
        # Insert image (width fits page width minus margins)
        pdf.image(tmp_img, x=10, w=pdf.w - 20)
        try:
            os.remove(tmp_img)
        except Exception:
            pass

    pdf.output(out_filename)
    return out_filename

# ----------------------------
# UI components (bilingual)
# ----------------------------
TEXT = {
    "fr": {
        "title": "🔬 LabT - Analyse",
        "login": "Connexion",
        "username": "Nom d'utilisateur",
        "password": "Mot de passe",
        "login_btn": "Se connecter",
        "logout": "Se déconnecter",
        "wrong": "Nom d'utilisateur ou mot de passe incorrect",
        "admin_panel": "Gestion des utilisateurs (admin)",
        "add_user": "Ajouter utilisateur",
        "modify_user": "Modifier utilisateur",
        "delete_user": "Supprimer utilisateur",
        "user_list": "Utilisateurs existants",
        "change_password": "Changer mon mot de passe",
        "company": "Nom de la compagnie",
        "upload_csv": "Téléverser un CSV (chromatogramme ou calibration)",
        "linearity": "Courbe de linéarité",
        "plot_line": "Tracer la courbe",
        "compute_unknown": "Calculer l'inconnu",
        "unknown_conc": "Concentration inconnue",
        "unknown_signal": "Signal inconnu",
        "sn_classic": "Calcul S/N classique",
        "sn_usp": "Calcul S/N USP",
        "lod_loq": "Calcul LOD / LOQ",
        "export_pdf": "Exporter le rapport PDF",
        "download_pdf": "Télécharger le PDF",
        "choose_lang": "Langue"
    },
    "en": {
        "title": "🔬 LabT - Analysis",
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "login_btn": "Sign in",
        "logout": "Logout",
        "wrong": "Wrong username or password",
        "admin_panel": "User management (admin)",
        "add_user": "Add user",
        "modify_user": "Modify user",
        "delete_user": "Delete user",
        "user_list": "Existing users",
        "change_password": "Change my password",
        "company": "Company name",
        "upload_csv": "Upload a CSV (chromatogram or calibration)",
        "linearity": "Linearity curve",
        "plot_line": "Plot curve",
        "compute_unknown": "Compute unknown",
        "unknown_conc": "Unknown concentration",
        "unknown_signal": "Unknown signal",
        "sn_classic": "Classic S/N",
        "sn_usp": "USP S/N",
        "lod_loq": "Compute LOD / LOQ",
        "export_pdf": "Export PDF report",
        "download_pdf": "Download PDF",
        "choose_lang": "Language"
    }
}

# ----------------------------
# Main app
# ----------------------------
def app():
    ensure_users_file()

    # initialize session state keys
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "role" not in st.session_state:
        st.session_state.role = ""
    if "lang" not in st.session_state:
        # default English first (user requested english first earlier)
        st.session_state.lang = "en"
    if "page" not in st.session_state:
        st.session_state.page = "login"

    # Language selector on top
    col1, col2 = st.columns([1, 6])
    with col1:
        lang_choice = st.selectbox(TEXT[st.session_state.lang]["choose_lang"], ["English", "Français"] if st.session_state.lang=="en" else ["Français", "English"])
        # Normalize selection to 'en' or 'fr'
        if lang_choice.startswith("English"):
            st.session_state.lang = "en"
        else:
            st.session_state.lang = "fr"

    txt = TEXT[st.session_state.lang]

    # If not logged -> show login
    if not st.session_state.logged_in:
        st.title(txt["title"])
        st.subheader(txt["login"])
        username_input = st.text_input(txt["username"])
        password_input = st.text_input(txt["password"], type="password")
        if st.button(txt["login_btn"]):
            role = authenticate(username_input, password_input)
            if role:
                st.session_state.logged_in = True
                st.session_state.username = normalize_username(username_input)
                st.session_state.role = role
                # after login, go to main menu
                st.session_state.page = "main_menu"
                safe_rerun()
            else:
                st.error(txt["wrong"])
        return

    # Logged in
    st.markdown(f"**{txt['title']}** — {st.session_state.username} ({st.session_state.role})")
    # Logout button
    if st.button(txt["logout"]):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.page = "login"
        safe_rerun()
        return

    # Admin page: only user management
    if st.session_state.role == "admin":
        st.header(txt["admin_panel"])
        users = load_users()
        st.write(txt["user_list"] + ":")
        for u, d in users.items():
            st.write(f"- {u} ({d.get('role', 'user')})")

        st.subheader(txt["add_user"])
        new_u = st.text_input("New username / Nouveau nom d'utilisateur", key="admin_new_u")
        new_p = st.text_input("New password / Nouveau mot de passe", type="password", key="admin_new_p")
        new_r = st.selectbox("Role", ["user", "admin"], key="admin_new_r")
        if st.button(txt["add_user"]):
            ok, msg = add_user(new_u, new_p, new_r)
            if ok:
                st.success("User added / Utilisateur ajouté")
                safe_rerun()
            else:
                st.warning(msg)

        st.subheader(txt["modify_user"])
        mod_u = st.text_input("Username to modify / Nom d'utilisateur à modifier", key="admin_mod_u")
        mod_p = st.text_input("New password (leave empty to keep) / Nouveau mot de passe (laisser vide pour conserver)", type="password", key="admin_mod_p")
        mod_r = st.selectbox("New role / Nouveau rôle", ["", "user", "admin"], index=0, key="admin_mod_r")
        if st.button(txt["modify_user"]):
            if mod_u:
                role_arg = mod_r if mod_r != "" else None
                ok = modify_user(mod_u, password=mod_p if mod_p else None, role=role_arg)
                if ok:
                    st.success("User modified / Utilisateur modifié")
                    safe_rerun()
                else:
                    st.warning("User not found / Utilisateur introuvable")

        st.subheader(txt["delete_user"])
        del_u = st.text_input("Username to delete / Nom d'utilisateur à supprimer", key="admin_del_u")
        if st.button(txt["delete_user"]):
            if del_u.lower() == st.session_state.username:
                st.warning("Can't delete yourself / Ne pouvez pas vous supprimer")
            else:
                ok = delete_user(del_u)
                if ok:
                    st.success("Deleted / Supprimé")
                    safe_rerun()
                else:
                    st.warning("User not found / Utilisateur introuvable")
        return

    # If role is user -> main tools
    st.header("LabT - Tools")

    st.write(f"**{txt['company']}**")
    company_name = st.text_input(txt["company"], value="", key="company_name")

    # option: show username and allow change password
    st.subheader(txt["change_password"])
    new_pw = st.text_input("New password / Nouveau mot de passe", type="password", key="new_pw")
    if st.button("Update / Mettre à jour"):
        if new_pw:
            change_own_password(st.session_state.username, new_pw)
            st.success("Password updated / Mot de passe mis à jour")
        else:
            st.warning("Enter a new password / Entrez un nouveau mot de passe")

    # File upload
    st.subheader(txt["upload_csv"])
    uploaded = st.file_uploader("", type=["csv"], key="file_uploader")
    df = None
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            st.success("CSV read successfully / CSV lu avec succés")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            df = None

    # If df is chromatogram (Time & Signal) or calibration (Concentration & Signal)
    if df is not None:
        st.write("Preview / Aperçu")
        st.dataframe(df.head())

        # allow user to choose columns
        cols = list(df.columns)
        st.write("Select columns / Sélectionnez les colonnes")
        col_x = st.selectbox("X / Time or Concentration", cols, key="col_x")
        col_y = st.selectbox("Y / Signal", cols, key="col_y")

        xvals = pd.to_numeric(df[col_x], errors="coerce")
        yvals = pd.to_numeric(df[col_y], errors="coerce")
        valid_mask = (~np.isnan(xvals)) & (~np.isnan(yvals))
        xvals = xvals[valid_mask].to_numpy()
        yvals = yvals[valid_mask].to_numpy()

        # Plot chromatogram / scatter
        fig1, ax1 = plt.subplots(figsize=(8, 3))
        ax1.plot(xvals, yvals, label="Signal")
        ax1.set_xlabel(col_x)
        ax1.set_ylabel(col_y)
        ax1.legend()
        st.pyplot(fig1)

        # Linéarité if chosen (user may choose that the x values are concentrations)
        st.subheader(txt["linearity"])
        use_linearity = st.checkbox("Use this dataset as calibration / Utiliser ces données comme étalon")
        slope = intercept = r2 = None
        if use_linearity:
            try:
                slope, intercept, r2 = fit_linearity(xvals, yvals)
                st.success(f"Slope: {slope:.6f}, Intercept: {intercept:.6f}, R²: {r2:.6f}")
            except Exception as e:
                st.error(f"Linearity error: {e}")

        # Compute unknown: choose whether to compute concentration from signal or signal from concentration
        st.subheader(txt["compute_unknown"])
        unknown_mode = st.radio("Mode / Mode", [txt["unknown_conc"], txt["unknown_signal"]])
        if unknown_mode == txt["unknown_conc"]:
            sig_val = st.number_input("Signal value / Valeur signal", value=float(np.nan) if np.isnan(np.mean(yvals)) else float(np.mean(yvals)))
            compute_btn = st.button("Compute concentration / Calculer concentration")
            if compute_btn:
                if slope is None:
                    st.warning("No linearity available. Use linearity first or supply slope/intercept.")
                else:
                    try:
                        conc = unknown_from_conc(slope, intercept, sig_val)
                        st.info(f"{txt['unknown_conc']}: {conc:.6f}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            conc_val = st.number_input("Concentration value / Valeur concentration", value=0.0)
            compute_btn2 = st.button("Compute signal / Calculer signal")
            if compute_btn2:
                if slope is None:
                    st.warning("No linearity available. Use linearity first or supply slope/intercept.")
                else:
                    try:
                        sig = unknown_from_signal(slope, intercept, conc_val)
                        st.info(f"{txt['unknown_signal']}: {sig:.6f}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # S/N calculations
        st.subheader("S/N")
        sn_choice = st.radio("Choose / Choisir", ["Classic S/N", "USP S/N"])
        if sn_choice == "Classic S/N":
            # ask for noise region selection
            with st.expander("Classic S/N options (select noise region)"):
                default_noise_pct = st.slider("Noise region length (%) of total", 1, 50, 10)
                # use last default_noise_pct% as noise region
                n = max(1, int(len(yvals) * default_noise_pct / 100.0))
                noise_region = yvals[-n:]
                sn_val, peak_val, noise_std = sn_classic(yvals, noise_region=noise_region)
                st.write(f"Peak: {peak_val:.6f}, Noise std: {noise_std:.6f}")
                st.success(f"Classic S/N = {sn_val:.3f}")
        else:
            # USP S/N: choose peak region (start/end) and noise region (start/end)
            st.write("Define peak region and noise region (indices based on the plotted data)")
            i1 = st.number_input("Peak start index", min_value=0, max_value=max(0, len(yvals)-1), value=0)
            i2 = st.number_input("Peak end index", min_value=0, max_value=max(0, len(yvals)-1), value=min(len(yvals)-1, max(0, len(yvals)//5)))
            j1 = st.number_input("Noise start index", min_value=0, max_value=max(0, len(yvals)-1), value=max(0, len(yvals)//5))
            j2 = st.number_input("Noise end index", min_value=0, max_value=max(0, len(yvals)-1), value=min(len(yvals)-1, max(0, len(yvals)//5 + 10)))
            # ensure valid
            i1, i2 = int(i1), int(i2)
            j1, j2 = int(j1), int(j2)
            if i1 < 0: i1 = 0
            if i2 >= len(yvals): i2 = len(yvals)-1
            if j1 < 0: j1 = 0
            if j2 >= len(yvals): j2 = len(yvals)-1
            if i2 < i1 or j2 < j1:
                st.warning("Invalid regions")
            else:
                peak_region = yvals[i1:i2+1] if i2>=i1 else np.array([yvals[i1]])
                noise_region = yvals[j1:j2+1] if j2>=j1 else np.array([yvals[j1]])
                snusp_val, amplitude, noise_std2 = sn_usp(peak_region, noise_region)
                st.write(f"Amplitude: {amplitude:.6f}, Noise std: {noise_std2:.6f}")
                st.success(f"USP S/N = {snusp_val:.3f}")

        # LOD/LOQ calculations
        st.subheader("LOD / LOQ")
        lod_method = st.selectbox("Method / Méthode", ["From residuals (linearity)", "From S/N (using noise)"])
        if lod_method.startswith("From residuals"):
            if slope is None:
                st.warning("Linearity not fitted: check 'Use this dataset as calibration'.")
            else:
                lod_val, loq_val = lod_loq_from_residuals(xvals, yvals, slope)
                st.info(f"LOD = {lod_val:.6f}, LOQ = {loq_val:.6f}")
        else:
            # use noise std (ask which noise to use)
            use_noise_from = st.selectbox("Noise source", ["last X% of signal", "custom indices"])
            if use_noise_from == "last X% of signal":
                pct = st.slider("Noise window (%)", 1, 50, 10)
                n = max(1, int(len(yvals)*pct/100.0))
                noise_region = yvals[-n:]
                noise_std = np.std(noise_region, ddof=1) if len(noise_region)>1 else np.std(noise_region)
            else:
                s1 = st.number_input("Noise start idx", min_value=0, max_value=max(0,len(yvals)-1), value=0, key="noise_j1")
                s2 = st.number_input("Noise end idx", min_value=0, max_value=max(0,len(yvals)-1), value=min(10, max(0,len(yvals)-1)), key="noise_j2")
                s1, s2 = int(s1), int(s2)
                nr = yvals[s1:s2+1] if s2>=s1 else np.array([yvals[s1]])
                noise_std = np.std(nr, ddof=1) if len(nr)>1 else np.std(nr)
            if slope is None:
                st.warning("Linearity not fitted: slope unknown -> cannot convert to concentration. You can still get LOD/LOQ in signal units.")
                lod_val = 3.3 * noise_std
                loq_val = 10.0 * noise_std
            else:
                lod_val, loq_val = lod_loq_from_sn(noise_std, slope, factor=3.3)
            st.info(f"LOD = {lod_val:.6f}, LOQ = {loq_val:.6f} ({'in concentration' if slope is not None else 'in signal units'})")

        # Export report
        st.subheader("Report / Rapport")
        company_input = company_name if company_name else " "
        if st.button(txt["export_pdf"]):
            # require company name
            if not company_input.strip():
                st.warning("Please enter company name before exporting / Entrez le nom de la compagnie")
            else:
                summary = []
                summary.append(f"User: {st.session_state.username}")
                summary.append(f"Company: {company_input}")
                summary.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if use_linearity and slope is not None:
                    summary.append(f"Linearity: slope={slope:.6f}, intercept={intercept:.6f}, R2={r2:.6f}")
                # Add S/N summary
                try:
                    sn_summary = ""
                    if sn_choice == "Classic S/N":
                        sn_val = sn_classic(yvals, noise_region=yvals[-max(1,int(0.1*len(yvals))):])[0]
                        sn_summary = f"Classic S/N: {sn_val:.3f}"
                    else:
                        sn_summary = f"USP S/N: {snusp_val:.3f}"
                    summary.append(sn_summary)
                except Exception:
                    pass

                # create small figure for PDF (replot)
                fig_pdf, ax_pdf = plt.subplots(figsize=(6, 2.5))
                ax_pdf.plot(xvals, yvals, label=col_y)
                ax_pdf.set_xlabel(col_x)
                ax_pdf.set_ylabel(col_y)
                ax_pdf.set_title("Chromatogram / Courbe")
                ax_pdf.legend()
                plt.tight_layout()

                # generate pdf
                out_file = generate_pdf_report("LabT Report", company_input, st.session_state.username, summary, fig=fig_pdf)
                plt.close(fig_pdf)
                # provide download
                try:
                    with open(out_file, "rb") as f:
                        st.download_button("⬇️ Download report (PDF)", f, file_name=out_file, mime="application/pdf")
                except Exception as e:
                    st.error(f"Error creating PDF: {e}")

    else:
        st.info("No CSV loaded yet / Aucun CSV chargé")

if __name__ == "__main__":
    app()