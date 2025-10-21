# app.py
# LabT - Application Streamlit complète (bilingue FR/EN)
# - Admin: gestion des utilisateurs (add / modify / delete)
# - User: linéarité (manual or CSV), S/N (CSV), LOQ/LOD conversions
# - Export PDF (text + embedded PNG plots)
# Requirements: see requirements.txt (streamlit, numpy, pandas, matplotlib, plotly optional, fpdf)

import streamlit as st
import json
import os
import hashlib
from datetime import datetime
from io import BytesIO
import base64

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

# ---------------------------
# Configuration / Defaults
# ---------------------------
USERS_FILE = "users.json"
LOGO_FILE = "logo.png"
DEFAULT_UNIT = "µg/mL"  # default concentration unit for linearity

# Initialize session state safely
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
# Keep linearity slope/intercept persistently
if "linearity" not in st.session_state:
    st.session_state.linearity = {"slope": None, "intercept": None, "unit": DEFAULT_UNIT, "r2": None, "x": None, "y": None}
# track language: default English first (as you requested earlier)
if "lang" not in st.session_state:
    st.session_state.lang = "en"  # "en" or "fr"

# ---------------------------
# Utils - hashing, users
# ---------------------------
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def create_default_users():
    users = {
        "admin": {"password": hash_password("admin"), "role": "admin"},
        "user1": {"password": hash_password("user1"), "role": "user"},
        "user2": {"password": hash_password("user2"), "role": "user"},
    }
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def load_users():
    if not os.path.exists(USERS_FILE):
        create_default_users()
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users_dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f, indent=4)

def find_user_case_insensitive(username: str, users: dict):
    if username is None:
        return None, None
    username_clean = username.strip().lower()
    for uname, info in users.items():
        if uname.strip().lower() == username_clean:
            return uname, info
    return None, None

# ---------------------------
# Messages helper (bilingual)
# ---------------------------
def t(fr, en):
    return en if st.session_state.lang == "en" else fr

# ---------------------------
# Login / Logout
# ---------------------------
def do_login(selected_user: str, password: str):
    users = load_users()
    uname_match, info = find_user_case_insensitive(selected_user, users)
    if uname_match and info and info["password"] == hash_password(password or ""):
        st.session_state.logged_in = True
        st.session_state.username = uname_match
        st.session_state.role = info["role"]
        # keep linearity cleared? keep as is so S/N can use slope if available
        st.success(t("Connexion réussie ✅", "Login successful ✅"))
        # no explicit rerun here; we rely on callback flow
    else:
        st.error(t("Nom d’utilisateur ou mot de passe incorrect ❌", "Wrong username or password ❌"))

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    # do not clear linearity
    st.experimental_rerun()

# ---------------------------
# PDF Generation helpers
# ---------------------------
def pil_figure_to_bytes(fig):
    """Return PNG bytes from a matplotlib figure."""
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf.read()

def generate_pdf_report(title, text_lines, image_bytes_list=None, company="", username=""):
    """
    Generate a PDF with fpdf.
    - text_lines: list of strings (each is a paragraph/line)
    - image_bytes_list: list of PNG bytes to insert (centered)
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Header / logo
    if os.path.exists(LOGO_FILE):
        try:
            pdf.image(LOGO_FILE, x=10, y=8, w=30)
        except Exception:
            pass
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Company: {company or 'N/A'}", ln=True)
    pdf.cell(0, 6, f"User: {username or 'N/A'}", ln=True)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 6, "App: LabT", ln=True)
    pdf.ln(6)
    pdf.set_font("Arial", "", 11)
    for line in text_lines:
        pdf.multi_cell(0, 6, line)
        pdf.ln(1)
    # Images
    if image_bytes_list:
        for img_b in image_bytes_list:
            # write temp to bytesIO and use FPDF.image via temporary file
            tmp_name = f"_tmp_{datetime.now().timestamp()}.png"
            with open(tmp_name, "wb") as f:
                f.write(img_b)
            try:
                pdf.add_page()
                pdf.image(tmp_name, x=15, w=180)
            except Exception:
                pass
            try:
                os.remove(tmp_name)
            except Exception:
                pass
    # Save
    fname = f"{title}_{(username or 'user')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(fname)
    return fname

def offer_file_download(file_path, label):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{os.path.basename(file_path)}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---------------------------
# Pages
# ---------------------------

# Login page
def page_login():
    st.title(t("🔬 LabT - Connexion", "🔬 LabT - Login"))
    users = load_users()
    # select user (show keys); but actual check uses case-insensitive logic
    # provide text_input to allow typing too
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_user = st.text_input(t("Nom d’utilisateur", "Username"), key="login_username")
    with col2:
        # language selector (EN / FR)
        lang_choice = st.selectbox("Language / Langue", ["English", "Français"], index=0 if st.session_state.lang=="en" else 1, key="lang_select")
        st.session_state.lang = "en" if lang_choice == "English" else "fr"

    password = st.text_input(t("Mot de passe", "Password"), type="password", key="login_password")
    # one-click login using on_click callback
    st.button(t("Se connecter", "Login"), on_click=do_login, args=(selected_user, password))

# Admin page: manage users
def page_admin_manage_users():
    st.header(t("👥 Gestion des utilisateurs", "👥 User management"))
    st.write(t("Vous êtes connecté en tant que", "You are logged in as"), f"**{st.session_state.username}**")
    users = load_users()

    action = st.selectbox(t("Action", "Action"), [t("Ajouter","Add"), t("Modifier","Modify"), t("Supprimer","Delete")], key="admin_action")
    username = st.text_input(t("Nom d’utilisateur / Username", "Username"), key="admin_username")
    password = st.text_input(t("Mot de passe (laisser vide si inchangé)", "Password (leave empty if unchanged)"), key="admin_password")
    role = st.selectbox(t("Rôle", "Role"), ["user", "admin"], index=0, key="admin_role")

    def admin_apply():
        nonlocal users
        if action == t("Ajouter","Add"):
            if not username or not password:
                st.warning(t("Tous les champs doivent être remplis pour ajouter.", "All fields must be filled to add."))
                return
            # case-insensitive check
            uname_found, _ = find_user_case_insensitive(username, users)
            if uname_found:
                st.warning(t("Utilisateur déjà existant.", "User already exists."))
                return
            users[username] = {"password": hash_password(password), "role": role}
            save_users(users)
            st.success(t("Utilisateur ajouté ✅", "User added ✅"))
        elif action == t("Modifier","Modify"):
            if not username:
                st.warning(t("Veuillez saisir le nom d’utilisateur à modifier.", "Please enter username to modify."))
                return
            uname_found, info = find_user_case_insensitive(username, users)
            if not uname_found:
                st.warning(t("Utilisateur introuvable.", "User not found."))
                return
            # modify
            if password:
                users[uname_found]["password"] = hash_password(password)
            users[uname_found]["role"] = role
            save_users(users)
            st.success(t("Utilisateur modifié ✅", "User modified ✅"))
        elif action == t("Supprimer","Delete"):
            if not username:
                st.warning(t("Veuillez saisir le nom d’utilisateur à supprimer.", "Please enter username to delete."))
                return
            uname_found, info = find_user_case_insensitive(username, users)
            if not uname_found:
                st.warning(t("Utilisateur introuvable.", "User not found."))
                return
            # prevent deleting admin self accidentally
            if uname_found == st.session_state.username:
                st.warning(t("Vous ne pouvez pas supprimer l’utilisateur connecté.", "You cannot delete the logged-in user."))
                return
            del users[uname_found]
            save_users(users)
            st.success(t("Utilisateur supprimé ✅", "User deleted ✅"))

    st.button(t("Valider", "Apply"), on_click=admin_apply)
    st.button(t("⬅️ Déconnexion", "⬅️ Logout"), on_click=logout)

# User: change password
def page_user_change_password():
    st.subheader(t("🔑 Changer mot de passe", "🔑 Change password"))
    old_pw = st.text_input(t("Ancien mot de passe", "Old password"), type="password", key="old_pw")
    new_pw = st.text_input(t("Nouveau mot de passe", "New password"), type="password", key="new_pw")
    confirm_pw = st.text_input(t("Confirmer nouveau mot de passe", "Confirm new password"), type="password", key="confirm_pw")

    def do_change():
        users = load_users()
        uname_found, info = find_user_case_insensitive(st.session_state.username, users)
        if not uname_found:
            st.error(t("Utilisateur introuvable.", "User not found."))
            return
        if info["password"] != hash_password(old_pw or ""):
            st.error(t("Ancien mot de passe incorrect.", "Old password incorrect."))
            return
        if not new_pw:
            st.warning(t("Nouveau mot de passe vide.", "New password empty."))
            return
        if new_pw != confirm_pw:
            st.warning(t("Les mots de passe ne correspondent pas.", "Passwords do not match."))
            return
        users[uname_found]["password"] = hash_password(new_pw)
        save_users(users)
        st.success(t("Mot de passe changé ✅", "Password changed ✅"))

    st.button(t("Changer le mot de passe", "Change password"), on_click=do_change)

# Linearity page
def page_linearity():
    st.header(t("📈 Courbe de linéarité / Linearity curve", "📈 Linearity curve"))
    st.write(t("Vous êtes connecté en tant que", "You are logged in as"), f"**{st.session_state.username}**")
    # choose input: manual or csv
    input_mode = st.radio(t("Mode d'entrée", "Input mode"), [t("Saisie manuelle","Manual input"), t("Téléverser un CSV","Upload CSV")], index=0 if "manual" in st.session_state.get("linearity_mode","manual") else 1, key="linearity_mode_radio")
    company_name = st.text_input(t("Nom de la compagnie pour le rapport PDF (obligatoire pour export)", "Company name for PDF report (required to export)"), key="linearity_company")

    conc = resp = None
    if input_mode == t("Saisie manuelle","Manual input"):
        conc_input = st.text_area(t("Concentrations séparées par des virgules (ex: 1, 2, 5)", "Concentrations separated by commas (e.g. 1,2,5)"),
                                   key="conc_input")
        resp_input = st.text_area(t("Signaux correspondants séparés par des virgules", "Corresponding signals separated by commas"),
                                   key="resp_input")
        unit = st.selectbox(t("Unité de concentration", "Concentration unit"), ["µg/mL", "mg/L", "g/L"], index=0, key="unit_select")
        if conc_input and resp_input:
            try:
                conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()!=''])
                resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()!=''])
            except Exception as e:
                st.error(t("Erreur de conversion des entrées. Vérifiez le format.", "Error parsing inputs. Check format."))
                return
    else:
        uploaded = st.file_uploader(t("Téléverser fichier CSV (colonnes: Concentration, Signal)", "Upload CSV file (columns: Concentration, Signal)"), type=["csv"], key="linearity_csv")
        unit = st.selectbox(t("Unité de concentration", "Concentration unit (CSV)"), ["µg/mL","mg/L","g/L"], index=0, key="unit_select_csv")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                # normalize columns case-insensitive
                cols = {c.lower(): c for c in df.columns}
                if "concentration" not in cols or "signal" not in cols:
                    st.error(t("CSV doit contenir les colonnes: Concentration et Signal", "CSV must contain columns: Concentration and Signal"))
                    return
                conc = df[cols["concentration"]].astype(float).values
                resp = df[cols["signal"]].astype(float).values
            except Exception as e:
                st.error(t("Erreur lecture CSV:","CSV read error:") + str(e))
                return

    if conc is not None and resp is not None:
        if len(conc) != len(resp) or len(conc) == 0:
            st.error(t("Listes vides ou de tailles différentes.", "Lists empty or of different lengths."))
            return
        # compute linear regression
        try:
            slope, intercept = np.polyfit(conc, resp, 1)
            # r2
            r2 = np.corrcoef(conc, resp)[0,1]**2
        except Exception as e:
            st.error(t("Erreur dans le calcul de la droite.", "Error computing regression.") + str(e))
            return

        # store in session_state so other pages can use
        st.session_state.linearity = {"slope": float(slope), "intercept": float(intercept), "unit": unit, "r2": float(r2), "x": conc.tolist(), "y": resp.tolist()}

        # Plot with matplotlib to produce PNG for PDF embedding (avoids kaleido)
        fig, ax = plt.subplots()
        ax.scatter(conc, resp, label=t("Points","Points"))
        xs = np.linspace(min(conc), max(conc), 200)
        ax.plot(xs, slope*xs + intercept, label=f"{t('Droite','Line')}: y={slope:.4f}x+{intercept:.4f}")
        ax.set_xlabel(f"{t('Concentration','Concentration')} ({unit})")
        ax.set_ylabel(t("Signal","Signal"))
        ax.set_title(t("Courbe de linéarité","Linearity curve"))
        ax.legend()
        st.pyplot(fig)

        st.success(t(f"Équation: y = {slope:.4f}x + {intercept:.4f}  (R² = {r2:.4f})", f"Equation: y = {slope:.4f}x + {intercept:.4f}  (R² = {r2:.4f})"))

        # Unknown calculation should update instantly without replot/reset:
        col_a, col_b = st.columns(2)
        with col_a:
            unknown_type = st.selectbox(t("Type d'inconnu", "Unknown type"), [t("Concentration inconnue","Unknown concentration"), t("Signal inconnu","Unknown signal")], key="unknown_type_select")
        with col_b:
            unknown_value = st.number_input(t("Valeur inconnue","Unknown value"), value=0.0, step=0.1, key="unknown_value_input", on_change=None)

        # compute result immediately (no rerun needed)
        if slope != 0:
            if unknown_type == t("Concentration inconnue","Unknown concentration"):
                result_conc = (unknown_value - intercept) / slope
                st.info(t(f"🔹 Concentration inconnue = {result_conc:.4f} {unit}", f"🔹 Unknown concentration = {result_conc:.4f} {unit}"))
            else:
                result_signal = slope * unknown_value + intercept
                st.info(t(f"🔹 Signal inconnu = {result_signal:.4f}", f"🔹 Unknown signal = {result_signal:.4f}"))

        # Export PDF
        def export_linearity_pdf():
            if not company_name:
                st.warning(t("Veuillez saisir le nom de la compagnie avant d’exporter.", "Please enter company name before exporting."))
                return
            text_lines = [
                t("Courbe de linéarité", "Linearity curve"),
                f"{t('Equation','Equation')}: y = {slope:.4f}x + {intercept:.4f}",
                f"R²: {r2:.4f}",
                f"{t('Unité de concentration','Concentration unit')}: {unit}",
                f"{t('Utilisateur','User')}: {st.session_state.username}",
            ]
            img_bytes = pil_figure_to_bytes(fig)
            pdf_file = generate_pdf_report("Linearity_Report", text_lines, image_bytes_list=[img_bytes], company=company_name, username=st.session_state.username)
            st.success(t("PDF généré:", "PDF generated:") + " " + pdf_file)
            offer_file_download(pdf_file, t("⬇️ Télécharger le PDF", "⬇️ Download PDF"))

        st.button(t("Exporter le rapport PDF", "Export PDF"), on_click=export_linearity_pdf)

    st.button(t("⬅️ Retour / Logout", "⬅️ Logout"), on_click=logout)

# S/N page
def page_sn():
    st.header(t("📊 Calcul du rapport signal/bruit (S/N)", "📊 Signal-to-noise calculations (S/N)"))
    st.write(t("Vous êtes connecté en tant que", "You are logged in as"), f"**{st.session_state.username}**")

    company_name = st.text_input(t("Nom de la compagnie pour le rapport PDF (obligatoire pour export)", "Company name for PDF report (required to export)"), key="sn_company")

    uploaded = st.file_uploader(t("Téléverser un chromatogramme CSV (colonnes: Time, Signal)", "Upload chromatogram CSV (columns: Time, Signal)"), type=["csv"], key="sn_csv")
    st.write(t("Choisir la méthode de bruit baseline pour USP S/N ou saisir zone", "Choose baseline method for USP S/N or enter zone"))
    baseline_choice = st.selectbox(t("Baseline method", "Baseline region choice"), [t("Premier 10% du signal (par défaut)", "First 10% (default)"), t("Définir des limites manuelles (time start/end)", "Manual time start/end")], key="sn_baseline_choice")

    time_start = time_end = None
    if baseline_choice == t("Définir des limites manuelles (time start/end)", "Manual time start/end"):
        col1, col2 = st.columns(2)
        with col1:
            time_start = st.number_input(t("Time start", "Time start"), value=0.0, key="sn_time_start")
        with col2:
            time_end = st.number_input(t("Time end", "Time end"), value=0.0, key="sn_time_end")

    # Use linearity slope if available for conversion to concentration LOQ/LOD
    use_linearity_for_conversion = st.checkbox(t("Utiliser la pente de la linéarité pour convertir LOQ/LOD en concentration", "Use linearity slope to convert LOQ/LOD to concentration"), value=("slope" in st.session_state.linearity and st.session_state.linearity["slope"] is not None), key="sn_use_linearity")

    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            cols = {c.lower(): c for c in df.columns}
            if "time" not in cols or "signal" not in cols:
                st.error(t("CSV doit contenir les colonnes : Time et Signal", "CSV must contain columns: Time and Signal"))
                return
            df.columns = [c.strip() for c in df.columns]
            time_vals = df[cols["time"]].astype(float).values
            sig_vals = df[cols["signal"]].astype(float).values

            # plot chromatogram
            fig, ax = plt.subplots()
            ax.plot(time_vals, sig_vals, label="Signal")
            ax.set_xlabel(t("Time","Time"))
            ax.set_ylabel(t("Signal","Signal"))
            ax.set_title(t("Chromatogramme","Chromatogram"))
            ax.legend()
            st.pyplot(fig)

            # S/N classic (peak / noise std)
            peak = np.max(sig_vals)
            noise_std = np.std(sig_vals)  # whole signal
            sn_classic = peak / noise_std if noise_std != 0 else np.nan

            # USP S/N: use baseline region
            if baseline_choice == t("Premier 10% du signal (par défaut)", "First 10% (default)"):
                n_baseline = max(1, int(0.1 * len(sig_vals)))
                baseline_vals = sig_vals[:n_baseline]
            else:
                # manual time selection
                if time_end <= time_start:
                    st.warning(t("Time end doit être > time start pour la zone manuelle.", "Time end must be > time start for manual zone."))
                    return
                mask = (time_vals >= time_start) & (time_vals <= time_end)
                if mask.sum() == 0:
                    st.warning(t("Aucune donnée dans la plage de temps sélectionnée.", "No data in selected time range."))
                    return
                baseline_vals = sig_vals[mask]
            noise_usp = np.std(baseline_vals)
            sn_usp = peak / noise_usp if noise_usp != 0 else np.nan

            # LOD/LOQ: classical definition
            LOD_signal = 3 * noise_std
            LOQ_signal = 10 * noise_std

            # convert to concentration if slope available and user wants it
            slope = st.session_state.linearity.get("slope")
            unit = st.session_state.linearity.get("unit")
            sn_conc = sn_usp_conc = None
            LOD_conc = LOQ_conc = None
            if use_linearity_for_conversion and slope and slope != 0:
                # Convert signals to concentration using slope (c = signal / slope) ignoring intercept for small signals
                # More correct: use (signal - intercept)/slope but for noise based LOD use noise/slope
                LOD_conc = LOD_signal / slope
                LOQ_conc = LOQ_signal / slope
                # S/N in concentration: peak/slope divided by noise/slope => same numeric as signal S/N, but show units
                sn_conc = (peak / slope) / (noise_std / slope) if slope!=0 else np.nan
                sn_usp_conc = (peak / slope) / (noise_usp / slope) if slope!=0 else np.nan

            # Display
            st.success(t(f"Rapport S/N (classique) = {sn_classic:.2f}", f"S/N (classic) = {sn_classic:.2f}"))
            st.info(t(f"USP S/N = {sn_usp:.2f} (bruit baseline = {noise_usp:.4f})", f"USP S/N = {sn_usp:.2f} (baseline noise = {noise_usp:.4f})"))
            st.write(t(f"LOD (signal) = {LOD_signal:.4f}, LOQ (signal) = {LOQ_signal:.4f}", f"LOD (signal) = {LOD_signal:.4f}, LOQ (signal) = {LOQ_signal:.4f}"))

            if LOD_conc is not None:
                st.write(t(f"LOD en concentration = {LOD_conc:.4f} {unit}, LOQ en concentration = {LOQ_conc:.4f} {unit}", f"LOD in concentration = {LOD_conc:.4f} {unit}, LOQ in concentration = {LOQ_conc:.4f} {unit}"))

            if sn_conc is not None:
                st.info(t(f"S/N (en concentration) = {sn_conc:.4f} {unit}", f"S/N (in concentration) = {sn_conc:.4f} {unit}"))
                st.info(t(f"USP S/N (en concentration) = {sn_usp_conc:.4f} {unit}", f"USP S/N (in concentration) = {sn_usp_conc:.4f} {unit}"))

            # Export PDF for S/N
            def export_sn_pdf():
                if not company_name:
                    st.warning(t("Veuillez saisir le nom de la compagnie avant d’exporter.", "Please enter company name before exporting."))
                    return
                text_lines = [
                    t("Analyse Signal-to-Noise", "Signal-to-Noise analysis"),
                    f"{t('Signal max','Peak signal')}: {peak:.4f}",
                    f"{t('Noise (std)','Noise (std)')}: {noise_std:.4f}",
                    f"S/N (classic): {sn_classic:.4f}",
                    f"USP S/N: {sn_usp:.4f}",
                    f"LOD(signal): {LOD_signal:.4f}, LOQ(signal): {LOQ_signal:.4f}",
                ]
                if LOD_conc is not None:
                    text_lines.append(f"{t('LOD (conc)','LOD (conc)')}: {LOD_conc:.4f} {unit} | {t('LOQ (conc)','LOQ (conc)')}: {LOQ_conc:.4f} {unit}")
                # save chromatogram figure as image bytes
                img_bytes = pil_figure_to_bytes(fig)
                pdf_file = generate_pdf_report("SN_Report", text_lines, image_bytes_list=[img_bytes], company=company_name, username=st.session_state.username)
                st.success(t("PDF généré:", "PDF generated:") + " " + pdf_file)
                offer_file_download(pdf_file, t("⬇️ Télécharger le PDF", "⬇️ Download PDF"))

            st.button(t("Exporter le rapport PDF", "Export PDF"), on_click=export_sn_pdf)

        except Exception as e:
            st.error(t("Erreur de lecture CSV :", "CSV read error:") + str(e))

    st.button(t("⬅️ Retour / Logout", "⬅️ Logout"), on_click=logout)

# Main menu for users
def page_main_menu():
    st.title(t("🧪 LabT - Menu principal", "🧪 LabT - Main menu"))
    st.write(t("Vous êtes connecté en tant que", "You are logged in as"), f"**{st.session_state.username}**")
    # bilingual selection at top
    lang_choice = st.selectbox("Language / Langue", ["English", "Français"], index=0 if st.session_state.lang=="en" else 1, key="main_lang")
    st.session_state.lang = "en" if lang_choice == "English" else "fr"

    if st.session_state.role == "admin":
        page_admin_manage_users()
    elif st.session_state.role == "user":
        choice = st.selectbox(t("Choisir une option", "Choose an option"), [t("Courbe de linéarité","Linearity curve"), t("Calcul S/N","S/N calculation"), t("Changer mot de passe","Change password")], key="user_menu_choice")
        if choice == t("Courbe de linéarité","Linearity curve"):
            page_linearity()
        elif choice == t("Calcul S/N","S/N calculation"):
            page_sn()
        else:
            page_user_change_password()
    else:
        st.error(t("Rôle inconnu.", "Unknown role."))

# ---------------------------
# App entry
# ---------------------------
def main():
    st.set_page_config(page_title="LabT", layout="wide")
    # Top bar with small info
    if not st.session_state.logged_in:
        page_login()
    else:
        page_main_menu()

if __name__ == "__main__":
    main()