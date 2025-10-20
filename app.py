# app.py
# LabT - Streamlit application (single-file)
# Copy this file as-is into your project.

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import json
import os
from io import BytesIO

# -----------------------------
# Configuration / Defaults
# -----------------------------
USERS_FILE = "users.json"
DEFAULT_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user1": {"password": "user123", "role": "user"},
    "user2": {"password": "user123", "role": "user"},
}
DEFAULT_CONC_UNIT = "µg/mL"  # default unit for linearity concentration

# -----------------------------
# Session-state initialization
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
# store latest linearity params
if "linearity_slope" not in st.session_state:
    st.session_state.linearity_slope = None
if "linearity_intercept" not in st.session_state:
    st.session_state.linearity_intercept = None
if "linearity_unit" not in st.session_state:
    st.session_state.linearity_unit = DEFAULT_CONC_UNIT

# -----------------------------
# Utilities : users management
# -----------------------------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump(DEFAULT_USERS, f, indent=4)

def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    # normalize keys to lowercase to enforce case-insensitive usernames
    normalized = {}
    for k, v in users.items():
        normalized[k.lower()] = v
    return normalized

def save_users(users_dict):
    # save with original style (lowercase keys stored)
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f, indent=4)

def add_user(username, password, role="user"):
    users = load_users()
    users[username.lower()] = {"password": password, "role": role}
    save_users(users)

def delete_user(username):
    users = load_users()
    key = username.lower()
    if key in users:
        del users[key]
        save_users(users)
        return True
    return False

def modify_user(username, password=None, role=None):
    users = load_users()
    key = username.lower()
    if key not in users:
        return False
    if password:
        users[key]["password"] = password
    if role:
        users[key]["role"] = role
    save_users(users)
    return True

def validate_login(username, password):
    users = load_users()
    key = (username or "").lower()
    if key in users and users[key]["password"] == password:
        return users[key]["role"]
    return None

def change_password_for_user(username, new_password):
    users = load_users()
    key = username.lower()
    if key in users:
        users[key]["password"] = new_password
        save_users(users)
        return True
    return False

# -----------------------------
# Utilities : linearity computations
# -----------------------------
def compute_linearity_from_arrays(concs, signals):
    x = np.array(concs, dtype=float)
    y = np.array(signals, dtype=float)
    if x.size == 0 or y.size == 0 or x.size != y.size:
        raise ValueError("Concentration and signal lists must be same length and non-empty.")
    # linear fit
    slope, intercept = np.polyfit(x, y, 1)
    # R^2
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else np.nan
    return slope, intercept, r2, x, y

# -----------------------------
# Utilities : S/N computations
# -----------------------------
def compute_sn_classic(signal_array, noise_slice=None):
    s = np.array(signal_array, dtype=float)
    peak = np.max(s)
    if noise_slice:
        start, end = noise_slice
        start = max(0, int(start))
        end = min(len(s), int(end))
        if end - start <= 0:
            noise_std = np.std(s[:max(1, int(0.1*len(s)))])
        else:
            noise_std = np.std(s[start:end])
    else:
        noise_std = np.std(s[:max(1, int(0.1*len(s)))])
    sn = peak / noise_std if noise_std != 0 else np.nan
    lod = 3 * noise_std
    loq = 10 * noise_std
    return sn, peak, noise_std, lod, loq

def compute_sn_usp(signal_array, baseline_slice=None):
    s = np.array(signal_array, dtype=float)
    peak = np.max(s)
    if baseline_slice:
        start, end = baseline_slice
        start = max(0, int(start))
        end = min(len(s), int(end))
        if end - start <= 0:
            noise_std = np.std(s[:max(1, int(0.1*len(s)))])
        else:
            noise_std = np.std(s[start:end])
    else:
        noise_std = np.std(s[:max(1, int(0.1*len(s)))])
    # USP often uses height/(2*sd) or other definitions — we'll provide both classic and USP (peak/(2*sd))
    sn_usp = peak / (2 * noise_std) if noise_std != 0 else np.nan
    return sn_usp, peak, noise_std

# -----------------------------
# Utilities : PDF export (uses matplotlib images)
# -----------------------------
def create_pdf_report(filename, title, results_dict, images=None, user=None, company=None):
    # images : list of (PIL/Matplotlib saved images as bytes or path)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=1, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"App: LabT", ln=1)
    pdf.cell(0, 8, f"User: {user}", ln=1)
    pdf.cell(0, 8, f"Company: {company}", ln=1)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1)
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    for k, v in results_dict.items():
        pdf.multi_cell(0, 7, f"{k}: {v}")
    pdf.ln(6)
    # add images
    if images:
        for i, im in enumerate(images):
            # im may be bytes buffer
            if isinstance(im, BytesIO):
                tmp_name = f"_tmp_plot_{i}.png"
                with open(tmp_name, "wb") as f:
                    f.write(im.getvalue())
                pdf.image(tmp_name, w=180)
                try:
                    os.remove(tmp_name)
                except:
                    pass
            elif isinstance(im, str) and os.path.exists(im):
                pdf.image(im, w=180)
    out_path = filename
    pdf.output(out_path)
    return out_path

# -----------------------------
# UI : helpers
# -----------------------------
def require_company_name(company):
    if not company or company.strip() == "":
        st.warning("Please enter company name before exporting report / Veuillez saisir le nom de la compagnie avant d'exporter le rapport.")
        return False
    return True

def plot_linearity(x, y, slope, intercept, r2, unit):
    fig, ax = plt.subplots()
    ax.scatter(x, y, label="Points")
    xs = np.linspace(np.min(x), np.max(x), 100)
    ax.plot(xs, slope * xs + intercept, color="red", label=f"Fit: y={slope:.4f}x+{intercept:.4f}")
    ax.set_xlabel(f"Concentration ({unit})")
    ax.set_ylabel("Signal")
    ax.set_title(f"Linéarité / Linearity (R²={r2:.4f})")
    ax.legend()
    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf

def plot_chromatogram(time, signal, noise_region=None):
    fig, ax = plt.subplots()
    ax.plot(time, signal, label="Signal")
    ax.set_xlabel("Time")
    ax.set_ylabel("Signal")
    if noise_region:
        start, end = noise_region
        ax.axvspan(time[int(start)] if int(start) < len(time) else time[-1],
                   time[int(end)-1] if int(end)-1 < len(time) else time[-1],
                   color='red', alpha=0.2, label="Noise region")
    ax.legend()
    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf

# -----------------------------
# UI : pages
# -----------------------------
def page_login():
    st.title("🔬 LabT - Login / Connexion")
    col1, col2 = st.columns([2, 1])
    with col1:
        username = st.text_input("Username / Nom d'utilisateur", key="login_user")
        password = st.text_input("Password / Mot de passe", type="password", key="login_pass")
    with col2:
        lang = st.selectbox("Language / Langue", ["English", "Français"], index=0, key="login_lang")
    if st.button("Login / Connexion", key="btn_login"):
        role = validate_login(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.username = username.lower()
            st.session_state.role = role
            st.success(f"Login successful ✅ / Vous êtes connecté en tant que {st.session_state.username}")
            # no explicit rerun called — Streamlit will re-run after button click automatically
        else:
            st.error("Invalid username or password / Identifiants incorrects")

def page_admin():
    st.title("Admin - User management / Gestion des utilisateurs")
    st.write("Admin can add, modify or delete users. / L'admin peut ajouter, modifier ou supprimer des utilisateurs.")
    users = load_users()
    # show users table (but not raw json) as a simple table
    user_rows = [{"username": k, "role": v["role"]} for k, v in users.items()]
    st.table(pd.DataFrame(user_rows))

    st.markdown("---")
    st.subheader("Add a new user / Ajouter un nouvel utilisateur")
    new_user = st.text_input("Username", key="admin_new_username")
    new_pass = st.text_input("Password", key="admin_new_password")
    new_role = st.selectbox("Role", ["user", "admin"], key="admin_new_role")
    if st.button("Add / Ajouter", key="admin_add"):
        if not new_user or not new_pass:
            st.warning("Both username and password are required / Nom et mot de passe requis")
        else:
            add_user(new_user, new_pass, new_role)
            st.success("User added / Utilisateur ajouté")
            st.experimental_rerun()

    st.markdown("### Modify user / Modifier utilisateur")
    mod_user = st.text_input("Existing username", key="admin_mod_username")
    mod_pass = st.text_input("New password (leave empty to keep)", key="admin_mod_password")
    mod_role = st.selectbox("New role", ["user", "admin"], key="admin_mod_role")
    if st.button("Modify / Modifier", key="admin_modify"):
        if not mod_user:
            st.warning("Username required / Nom d'utilisateur requis")
        else:
            ok = modify_user(mod_user, password=mod_pass if mod_pass else None, role=mod_role)
            if ok:
                st.success("User modified / Utilisateur modifié")
                st.experimental_rerun()
            else:
                st.error("User not found / Utilisateur introuvable")

    st.markdown("### Delete user / Supprimer utilisateur")
    del_user = st.text_input("Username to delete", key="admin_del_username")
    if st.button("Delete / Supprimer", key="admin_delete"):
        if not del_user:
            st.warning("Provide username to delete / Fournir le nom d'utilisateur à supprimer")
        else:
            ok = delete_user(del_user)
            if ok:
                st.success("User deleted / Utilisateur supprimé")
                st.experimental_rerun()
            else:
                st.error("User not found / Utilisateur introuvable")

    st.markdown("---")
    if st.button("Logout / Déconnexion", key="admin_logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.experimental_rerun()

def page_user_menu():
    st.title("🧪 LabT - Menu principal")
    st.write(f"You are connected as **{st.session_state.username}**")
    choice = st.selectbox("Choose / Choisir", ["Linearity / Linéarité", "S/N (Signal to Noise)", "Change Password / Changer mot de passe", "Logout / Déconnexion"], key="user_choice")
    if choice == "Linearity / Linéarité":
        page_linearity()
    elif choice == "S/N (Signal to Noise)":
        page_sn()
    elif choice == "Change Password / Changer mot de passe":
        page_change_password()
    elif choice == "Logout / Déconnexion":
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.experimental_rerun()

# -----------------------------
# Page: Linearity (CSV or manual)
# -----------------------------
def page_linearity():
    st.header("📈 Linearity / Linéarité")
    st.write("Choose input method / Choisir méthode d'entrée")
    method = st.radio("Method / Méthode", ["Upload CSV", "Manual entry / Saisie manuelle"], key="lin_method")
    unit = st.selectbox("Concentration unit / Unité de concentration", ["µg/mL", "mg/L", "g/L", "ppm"], index=0, key="lin_unit")
    st.session_state.linearity_unit = unit

    slope = None
    intercept = None
    r2 = None
    x = None
    y = None
    plot_buf = None

    if method == "Upload CSV":
        st.info("CSV must contain columns named 'Concentration' and 'Signal' (case-insensitive). / Le CSV doit contenir 'Concentration' et 'Signal' (insensibles à la casse).")
        csv_file = st.file_uploader("Upload CSV (Concentration,Signal)", type=["csv"], key="lin_csv")
        if csv_file:
            try:
                df = pd.read_csv(csv_file)
                # flexible column matching
                cols_lower = {c.lower(): c for c in df.columns}
                if "concentration" not in cols_lower or "signal" not in cols_lower:
                    st.error("CSV must include Concentration and Signal columns. / Le CSV doit inclure les colonnes Concentration et Signal.")
                else:
                    conc_col = cols_lower["concentration"]
                    sig_col = cols_lower["signal"]
                    df_clean = df[[conc_col, sig_col]].dropna()
                    concs = df_clean[conc_col].astype(float).values
                    sigs = df_clean[sig_col].astype(float).values
                    slope, intercept, r2, x, y = compute_linearity_from_arrays(concs, sigs)
                    st.success(f"Slope: {slope:.6f} | Intercept: {intercept:.6f} | R²: {r2:.6f}")
                    plot_buf = plot_linearity(x, y, slope, intercept, r2, unit)
                    st.image(plot_buf)
            except Exception as e:
                st.error(f"Error reading CSV / Erreur lecture CSV: {e}")

    else:
        st.info("Enter comma-separated values (example: 1,2,5,10) for concentrations and signals. / Saisir les valeurs séparées par des virgules.")
        col1, col2 = st.columns(2)
        with col1:
            conc_text = st.text_area("Concentrations (comma separated)", key="lin_manual_conc", height=80, placeholder="1, 2, 5, 10")
        with col2:
            sig_text = st.text_area("Signals (comma separated)", key="lin_manual_sig", height=80, placeholder="0.12, 0.25, 0.6, 1.2")
        if st.button("Compute linearity / Calculer linéarité", key="lin_compute"):
            try:
                concs = [float(s.strip()) for s in conc_text.split(",") if s.strip() != ""]
                sigs = [float(s.strip()) for s in sig_text.split(",") if s.strip() != ""]
                slope, intercept, r2, x, y = compute_linearity_from_arrays(concs, sigs)
                st.success(f"Slope: {slope:.6f} | Intercept: {intercept:.6f} | R²: {r2:.6f}")
                plot_buf = plot_linearity(x, y, slope, intercept, r2, unit)
                st.image(plot_buf)
            except Exception as e:
                st.error(f"Error computing linearity / Erreur: {e}")

    # if we have a computed linearity, keep it in session for S/N conversion usage
    if slope is not None:
        st.session_state.linearity_slope = slope
        st.session_state.linearity_intercept = intercept
        st.session_state.linearity_r2 = r2

    # Allow concentration <-> signal conversions if slope available
    if st.session_state.linearity_slope:
        st.markdown("---")
        st.subheader("Unknown calculation / Calcul inconnu")
        unknown_choice = st.radio("Type", ["Signal -> Concentration", "Concentration -> Signal"], key="lin_unknown_choice")
        if unknown_choice == "Signal -> Concentration":
            sig_val = st.number_input("Signal value", key="lin_unknown_signal")
            if st.button("Calculate concentration", key="lin_calc_conc"):
                try:
                    slope = st.session_state.linearity_slope
                    intercept = st.session_state.linearity_intercept
                    conc_res = (sig_val - intercept) / slope
                    st.success(f"Unknown concentration = {conc_res:.6f} {st.session_state.linearity_unit}")
                except Exception as e:
                    st.error(f"Erreur dans le calcul: {e}")
        else:
            conc_val = st.number_input("Concentration value", key="lin_unknown_conc")
            if st.button("Calculate signal", key="lin_calc_sig"):
                try:
                    slope = st.session_state.linearity_slope
                    intercept = st.session_state.linearity_intercept
                    sig_res = slope * conc_val + intercept
                    st.success(f"Unknown signal = {sig_res:.6f} (no unit)")
                except Exception as e:
                    st.error(f"Erreur dans le calcul: {e}")

    st.markdown("---")
    row = st.columns([1,1,1])
    if row[0].button("Back to menu / Retour au menu", key="lin_back"):
        st.session_state.page = "menu"
        st.experimental_rerun()

    # Export
    st.markdown("### Export report / Exporter le rapport")
    company_name = st.text_input("Company name / Nom compagnie (required for export)", key="lin_company")
    if st.button("Export PDF report / Exporter PDF", key="lin_export"):
        if not st.session_state.linearity_slope:
            st.warning("No linearity computed yet / Aucune linéarité calculée")
        elif not require_company_name(company_name):
            pass
        else:
            results = {
                "Slope": f"{st.session_state.linearity_slope:.6f}",
                "Intercept": f"{st.session_state.linearity_intercept:.6f}",
                "R2": f"{st.session_state.get('linearity_r2', np.nan):.6f}"
            }
            images = []
            if plot_buf:
                images.append(plot_buf)
            filename = f"Linearity_Report_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            out = create_pdf_report(filename, "Linearity Report / Rapport de linéarité", results, images=images, user=st.session_state.username, company=company_name)
            with open(out, "rb") as f:
                st.download_button("Download PDF / Télécharger PDF", f, file_name=out, key="lin_download")
            st.success("Report generated / Rapport généré")

# -----------------------------
# Page: Signal-to-noise
# -----------------------------
def page_sn():
    st.header("📊 Signal-to-Noise (S/N)")
    st.info("Upload chromatogram CSV with columns 'Time' and 'Signal' (case-insensitive). / Importer CSV avec colonnes Time et Signal.")
    csv_file = st.file_uploader("Chromatogram CSV", type=["csv"], key="sn_csv")
    use_linearity_for_conversion = st.checkbox("Use linearity slope to convert LOD/LOQ to concentration / Utiliser la pente de linéarité", key="sn_use_linearity")
    company_name = st.text_input("Company name for report (required for export)", key="sn_company")
    if csv_file:
        try:
            df = pd.read_csv(csv_file)
            cols_lower = {c.lower(): c for c in df.columns}
            if "time" not in cols_lower or "signal" not in cols_lower:
                st.error("CSV must contain Time and Signal columns. / Le CSV doit contenir Time et Signal.")
                return
            time_col = cols_lower["time"]
            signal_col = cols_lower["signal"]
            df_clean = df[[time_col, signal_col]].dropna()
            time_vals = df_clean[time_col].astype(float).values
            sig_vals = df_clean[signal_col].astype(float).values
            st.line_chart(pd.DataFrame({ "Signal": sig_vals }))
            st.markdown("Select noise region indices (integers) / Sélectionner la zone de bruit (indices entiers)")
            col1, col2 = st.columns(2)
            start_idx = int(col1.number_input("Noise start index", min_value=0, max_value=max(0, len(sig_vals)-1), value=0, key="sn_start"))
            end_idx = int(col2.number_input("Noise end index", min_value=0, max_value=max(0, len(sig_vals)), value=max(1, int(len(sig_vals)*0.1)), key="sn_end"))
            if end_idx <= start_idx:
                st.warning("End index should be greater than start index / L'indice de fin doit être > indice de début")
            sn_classic, peak, noise_std, lod_signal, loq_signal = compute_sn_classic(sig_vals, noise_slice=(start_idx, end_idx))
            sn_usp, _, noise_std_usp = compute_sn_usp(sig_vals, baseline_slice=(start_idx, end_idx))
            st.success(f"S/N classic: {sn_classic:.3f}")
            st.info(f"USP S/N (peak / 2σ): {sn_usp:.3f}")
            st.write(f"Peak: {peak:.6f} | Noise std: {noise_std:.6f}")
            st.write(f"LOD (signal units): {lod_signal:.6f} | LOQ (signal units): {loq_signal:.6f}")

            # If linearity usage requested and slope present
            if use_linearity_for_conversion:
                slope = st.session_state.linearity_slope
                intercept = st.session_state.linearity_intercept
                if slope is None:
                    st.warning("No linearity available. Compute linearity first to convert LOD/LOQ to concentration.")
                else:
                    # Convert using (LOD - intercept) / slope  (safer than LOD/slope)
                    try:
                        lod_conc = (lod_signal - intercept)/slope
                        loq_conc = (loq_signal - intercept)/slope
                    except Exception:
                        # fallback
                        lod_conc = lod_signal / slope
                        loq_conc = loq_signal / slope
                    st.info(f"LOD (conc): {lod_conc:.6f} {st.session_state.linearity_unit}")
                    st.info(f"LOQ (conc): {loq_conc:.6f} {st.session_state.linearity_unit}")

            # Chart with noise region highlighted
            buf_chart = plot_chromatogram(time_vals, sig_vals, noise_region=(start_idx, end_idx))
            st.image(buf_chart)

            # Export report
            if st.button("Export PDF report", key="sn_export"):
                if not require_company_name(company_name):
                    pass
                else:
                    results = {
                        "S/N classic": f"{sn_classic:.3f}",
                        "USP S/N": f"{sn_usp:.3f}",
                        "Peak": f"{peak:.6f}",
                        "Noise std": f"{noise_std:.6f}",
                        "LOD (signal)": f"{lod_signal:.6f}",
                        "LOQ (signal)": f"{loq_signal:.6f}"
                    }
                    if use_linearity_for_conversion and st.session_state.linearity_slope:
                        slope = st.session_state.linearity_slope
                        intercept = st.session_state.linearity_intercept
                        try:
                            lod_conc = (lod_signal - intercept)/slope
                            loq_conc = (loq_signal - intercept)/slope
                            results["LOD (conc)"] = f"{lod_conc:.6f} {st.session_state.linearity_unit}"
                            results["LOQ (conc)"] = f"{loq_conc:.6f} {st.session_state.linearity_unit}"
                        except Exception:
                            results["LOD (conc)"] = "Conversion error"
                            results["LOQ (conc)"] = "Conversion error"
                    images = [buf_chart]
                    filename = f"SN_Report_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    out = create_pdf_report(filename, "S/N Report / Rapport S/N", results, images=images, user=st.session_state.username, company=company_name)
                    with open(out, "rb") as f:
                        st.download_button("Download PDF / Télécharger PDF", f, file_name=out, key="sn_download")
                    st.success("Report generated / Rapport généré")

        except Exception as e:
            st.error(f"Error reading CSV / Erreur lecture CSV: {e}")
    else:
        st.info("Please upload a chromatogram CSV to compute S/N / Importer un CSV de chromatogramme pour calculer S/N")

    st.markdown("---")
    if st.button("Back to menu / Retour au menu", key="sn_back"):
        st.session_state.page = "menu"
        st.experimental_rerun()

# -----------------------------
# Page: Change password (user)
# -----------------------------
def page_change_password():
    st.header("Change your password / Changer mot de passe")
    old_pw = st.text_input("Old password / Ancien mot de passe", type="password", key="chg_old")
    new_pw = st.text_input("New password / Nouveau mot de passe", type="password", key="chg_new")
    confirm_pw = st.text_input("Confirm new password / Confirmer", type="password", key="chg_conf")
    if st.button("Change password / Changer", key="chg_btn"):
        username = st.session_state.username
        users = load_users()
        if username is None:
            st.error("No user in session")
            return
        if users.get(username.lower()) is None:
            st.error("User not found")
            return
        if users[username.lower()]["password"] != old_pw:
            st.error("Old password incorrect / Ancien mot de passe incorrect")
            return
        if new_pw != confirm_pw:
            st.error("New passwords do not match / Les nouveaux mots de passe ne correspondent pas")
            return
        change_password_for_user(username, new_pw)
        st.success("Password changed / Mot de passe changé")
        # Optionally force logout
        # st.session_state.logged_in = False

    if st.button("Back to menu / Retour au menu", key="chg_back"):
        st.session_state.page = "menu"
        st.experimental_rerun()

# -----------------------------
# Main app controller
# -----------------------------
def main():
    st.set_page_config(page_title="LabT", layout="wide")
    if not st.session_state.logged_in:
        page_login()
    else:
        # control which page
        if "page" not in st.session_state:
            st.session_state.page = "menu"
        if st.session_state.role == "admin":
            page_admin()
        else:
            # user
            if st.session_state.page == "menu":
                page_user_menu()
            elif st.session_state.page == "linearity":
                page_linearity()
            elif st.session_state.page == "sn":
                page_sn()
            elif st.session_state.page == "changepw":
                page_change_password()
            else:
                page_user_menu()

if __name__ == "__main__":
    ensure_users_file()
    main()