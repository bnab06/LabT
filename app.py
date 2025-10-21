# app.py
import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
import io
import base64

# ------------------------------
# Config / constantes
# ------------------------------
USERS_FILE = "users.json"
DEFAULT_UNIT = "µg/mL"
UNITS = ["µg/mL", "mg/L", "g/L", "ppm"]

# ------------------------------
# Utilitaires utilisateurs
# ------------------------------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        default = {
            "admin": {"password": "admin", "role": "admin"},
            "user1": {"password": "user1", "role": "user"},
            "user2": {"password": "user2", "role": "user"},
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)

def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def username_map(users):
    """Map lower() -> actual key in file"""
    return {k.lower(): k for k in users.keys()}

# ------------------------------
# Session state init
# ------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "lang" not in st.session_state:
    st.session_state.lang = "EN"  # default English
# store linearity result
if "linearity" not in st.session_state:
    st.session_state.linearity = {"slope": None, "intercept": None, "unit": DEFAULT_UNIT, "r2": None}

# ------------------------------
# Small helpers
# ------------------------------
def bilingual(text_en, text_fr):
    return text_en if st.session_state.lang == "EN" else text_fr

def make_download_link(file_path, label):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'data:application/octet-stream;base64,{b64}'
    return f'<a href="{href}" download="{os.path.basename(file_path)}">{label}</a>'

# ------------------------------
# LOGIN (1 click, case-insensitive username)
# ------------------------------
def try_login(raw_user, raw_password, lang_choice):
    users = load_users()
    mmap = username_map(users)
    user = (raw_user or "").strip().lower()
    pwd = raw_password or ""
    if user in mmap:
        real = mmap[user]
        if users[real]["password"] == pwd:
            st.session_state.logged_in = True
            st.session_state.username = real
            st.session_state.role = users[real].get("role", "user")
            st.session_state.lang = lang_choice
            return True
    st.session_state.logged_in = False
    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.experimental_rerun()

def login_page():
    st.title("🔬 LabT")
    st.subheader(bilingual("Login", "Connexion"))
    lang_choice = st.selectbox("Language / Langue", ["EN", "FR"], index=0 if st.session_state.lang=="EN" else 1, key="login_lang")
    users = load_users()
    with st.form("login_form", clear_on_submit=False):
        selected_user = st.selectbox(bilingual("Choose user", "Choisir un utilisateur"), list(users.keys()), key="login_user")
        password = st.text_input(bilingual("Password", "Mot de passe"), type="password", key="login_pass")
        submitted = st.form_submit_button(bilingual("Login / Se connecter", "Se connecter / Login"))
        if submitted:
            ok = try_login(selected_user, password, lang_choice)
            if ok:
                st.success(bilingual(f"Login successful ✅ You are logged in as {st.session_state.username}",
                                     f"Connexion réussie ✅ Vous êtes connecté en tant que {st.session_state.username}"))
                st.experimental_rerun()
            else:
                st.error(bilingual("Wrong username or password ❌", "Nom d’utilisateur ou mot de passe incorrect ❌"))

# ------------------------------
# Admin: manage users (add/modify/delete)
# ------------------------------
def admin_page():
    st.header(bilingual("👥 User management", "👥 Gestion des utilisateurs"))
    st.write(bilingual(f"You are logged in as **{st.session_state.username}**", f"Vous êtes connecté en tant que **{st.session_state.username}**"))

    users = load_users()

    # bilingual actions
    actions = [("Add", "Ajouter"), ("Modify", "Modifier"), ("Delete", "Supprimer")]
    actions_labels = [a[0] if st.session_state.lang=="EN" else a[1] for a in actions]
    action = st.selectbox(bilingual("Action", "Action"), actions_labels, key="admin_action")
    username = st.text_input(bilingual("Username", "Nom d’utilisateur"), key="admin_username")
    password = st.text_input(bilingual("Password (leave blank to keep)", "Mot de passe (laisser vide pour garder)"), key="admin_password")
    role = st.selectbox(bilingual("Role", "Rôle"), ["user", "admin"], key="admin_role")
    if st.button(bilingual("Validate", "Valider"), key="admin_validate"):
        if not username.strip():
            st.warning(bilingual("Please enter a username.", "Veuillez saisir un nom d'utilisateur."))
        else:
            uname = username.strip()
            uname_lower_map = username_map(users)
            if action == (actions_labels[0]):  # Add
                if uname_lower_map.get(uname.lower()):
                    st.warning(bilingual("User already exists.", "Utilisateur déjà existant."))
                else:
                    if not password:
                        st.warning(bilingual("Password is required to add a user.", "Le mot de passe est requis pour ajouter un utilisateur."))
                    else:
                        users[uname] = {"password": password, "role": role}
                        save_users(users)
                        st.success(bilingual("User added ✅", "Utilisateur ajouté ✅"))
            elif action == (actions_labels[1]):  # Modify
                real = uname_lower_map.get(uname.lower())
                if not real:
                    st.warning(bilingual("User not found.", "Utilisateur introuvable."))
                else:
                    if password:
                        users[real]["password"] = password
                    users[real]["role"] = role
                    save_users(users)
                    st.success(bilingual("User modified ✅", "Utilisateur modifié ✅"))
            else:  # Delete
                real = uname_lower_map.get(uname.lower())
                if not real:
                    st.warning(bilingual("User not found.", "Utilisateur introuvable."))
                else:
                    del users[real]
                    save_users(users)
                    st.success(bilingual("User deleted ✅", "Utilisateur supprimé ✅"))

    if st.button(bilingual("⬅️ Logout", "⬅️ Déconnexion"), key="admin_logout"):
        logout()

# ------------------------------
# Linearity page
# ------------------------------
def compute_linearity_from_arrays(conc, resp):
    # fit linear regression
    if len(conc) < 2:
        raise ValueError("At least two points are required")
    coeffs = np.polyfit(conc, resp, 1)
    slope, intercept = coeffs[0], coeffs[1]
    # r2
    yhat = slope * conc + intercept
    ss_res = np.sum((resp - yhat)**2)
    ss_tot = np.sum((resp - np.mean(resp))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0
    return slope, intercept, r2

def linearity_page():
    st.header("📈 " + bilingual("Linearity", "Courbe de linéarité"))
    st.write(bilingual(f"You are logged in as **{st.session_state.username}**", f"Vous êtes connecté en tant que **{st.session_state.username}**"))

    # Input mode
    mode = st.radio(bilingual("Input mode", "Mode d'entrée"), [bilingual("Manual entry", "Saisie manuelle"), "CSV"], index=0)
    conc = resp = None
    if mode == bilingual("Manual entry", "Saisie manuelle"):
        conc_input = st.text_input(bilingual("Known concentrations (comma separated)", "Concentrations connues (séparées par des virgules)"), key="lin_conc")
        resp_input = st.text_input(bilingual("Responses (comma separated)", "Réponses (séparées par des virgules)"), key="lin_resp")
        if conc_input and resp_input:
            try:
                conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()!=""])
                resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()!=""])
            except:
                st.error(bilingual("Error parsing numbers", "Erreur lors de l'analyse des nombres"))
    else:
        uploaded = st.file_uploader(bilingual("Upload CSV with columns Concentration and Signal", "Téléverser CSV avec colonnes Concentration et Signal"), type=["csv"], key="lin_upload")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                cols = [c.strip().lower() for c in df.columns]
                # try to be flexible with column names
                if "concentration" in cols and ("signal" in cols or "response" in cols or "response" in cols):
                    # map columns
                    col_map = {c.strip().lower(): c for c in df.columns}
                    conc = df[col_map[[k for k in col_map.keys() if k.lower()=="concentration"][0]]].astype(float).to_numpy()
                    sig_key = [k for k in col_map.keys() if k.lower() in ("signal","response")][0]
                    resp = df[col_map[sig_key]].astype(float).to_numpy()
                else:
                    st.error(bilingual("CSV must contain Concentration and Signal/Response columns.", "Le CSV doit contenir les colonnes Concentration et Signal/Réponse."))
            except Exception as e:
                st.error(bilingual("Error reading CSV", f"Erreur de lecture CSV: {e}"))

    # unit selection (default µg/mL)
    unit = st.selectbox(bilingual("Concentration unit", "Unité de concentration"), UNITS, index=UNITS.index(DEFAULT_UNIT))

    # store slope/unit in session_state if computed
    result_ready = False
    if conc is not None and resp is not None and len(conc) > 0:
        try:
            slope, intercept, r2 = compute_linearity_from_arrays(conc, resp)
            st.session_state.linearity["slope"] = slope
            st.session_state.linearity["intercept"] = intercept
            st.session_state.linearity["unit"] = unit
            st.session_state.linearity["r2"] = r2
            result_ready = True
        except Exception as e:
            st.error(bilingual("Error in linearity calculation", f"Erreur dans les calculs de linéarité: {e}"))

    # Plot (matplotlib)
    if result_ready:
        fig, ax = plt.subplots()
        ax.scatter(conc, resp, label=bilingual("Points","Points"))
        xs = np.linspace(np.min(conc), np.max(conc), 100)
        ax.plot(xs, st.session_state.linearity["slope"]*xs + st.session_state.linearity["intercept"], label=bilingual("Fit line","Droite de régression"))
        ax.set_xlabel(bilingual(f"Concentration ({unit})", f"Concentration ({unit})"))
        ax.set_ylabel(bilingual("Signal", "Signal"))
        ax.set_title(bilingual("Linearity plot", "Courbe de linéarité"))
        ax.legend()
        st.pyplot(fig)

        st.success(bilingual(f"Equation: y = {st.session_state.linearity['slope']:.6f} x + {st.session_state.linearity['intercept']:.6f} | R² = {st.session_state.linearity['r2']:.4f}",
                             f"Équation : y = {st.session_state.linearity['slope']:.6f} x + {st.session_state.linearity['intercept']:.6f} | R² = {st.session_state.linearity['r2']:.4f}"))

        # Unknown calculation: concentration from signal OR signal from concentration
        unknown_type = st.radio(bilingual("Unknown type", "Type d'inconnu"), [bilingual("Unknown concentration", "Concentration inconnue"), bilingual("Unknown signal", "Signal inconnu")], index=0)
        # to ensure interactive recalculation on change, use number_input (changes re-run automatically)
        unknown_value = st.number_input(bilingual("Unknown value", "Valeur inconnue"), value=0.0, step=0.01, format="%.6f", key="lin_unknown_value")
        if st.session_state.linearity["slope"] == 0:
            st.error(bilingual("Slope is zero, can't compute inverse", "La pente est nulle, impossible de calculer l'inverse"))
        else:
            if unknown_type == bilingual("Unknown concentration", "Concentration inconnue"):
                # unknown_value is signal; compute concentration
                conc_result = (unknown_value - st.session_state.linearity["intercept"]) / st.session_state.linearity["slope"]
                st.info(bilingual(f"🔹 Unknown concentration = {conc_result:.6f} {unit}", f"🔹 Concentration inconnue = {conc_result:.6f} {unit}"))
            else:
                # unknown_value is concentration; compute signal
                signal_result = st.session_state.linearity["slope"] * unknown_value + st.session_state.linearity["intercept"]
                st.info(bilingual(f"🔹 Unknown signal = {signal_result:.6f}", f"🔹 Signal inconnu = {signal_result:.6f}"))

        # export PDF
        st.markdown("---")
        company_name = st.text_input(bilingual("Company name for PDF report", "Nom de la compagnie pour le rapport PDF"), key="lin_company")
        if st.button(bilingual("Export PDF report", "Exporter le rapport PDF")):
            if not company_name.strip():
                st.warning(bilingual("Please enter company name before exporting.", "Veuillez saisir le nom de la compagnie avant d'exporter."))
            else:
                # save figure image to bytes
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                # create PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "LabT - Linearity Report", ln=True, align="C")
                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 8, f"Company: {company_name}", ln=True)
                pdf.cell(0, 8, f"User: {st.session_state.username}", ln=True)
                pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
                pdf.cell(0, 8, f"App: LabT", ln=True)
                pdf.ln(6)
                pdf.multi_cell(0, 8, f"Equation: y = {st.session_state.linearity['slope']:.6f} x + {st.session_state.linearity['intercept']:.6f}")
                pdf.multi_cell(0, 8, f"R² = {st.session_state.linearity['r2']:.6f}")
                pdf.multi_cell(0, 8, f"Unit: {unit}")
                # embed image
                img_path = f"linearity_{st.session_state.username}.png"
                with open(img_path, "wb") as f:
                    f.write(buf.getvalue())
                pdf.image(img_path, x=15, w=180)
                pdf_file = f"Linearity_Report_{st.session_state.username}.pdf"
                pdf.output(pdf_file)
                st.success(bilingual("PDF exported", "PDF exporté"))
                st.markdown(make_download_link(pdf_file, bilingual("⬇️ Download PDF", "⬇️ Télécharger le PDF")), unsafe_allow_html=True)

    st.markdown("---")
    if st.button(bilingual("⬅️ Back to menu", "⬅️ Retour au menu")):
        st.experimental_rerun()

# ------------------------------
# Signal/Noise page
# ------------------------------
def calculate_sn_from_df(df, noise_region=None):
    # df must have 'time' and 'signal' columns (lowercase)
    y = df["signal"].to_numpy()
    t = df["time"].to_numpy()
    peak = np.max(y)
    noise_std = np.std(y)  # overall noise
    # USP noise: use provided baseline region (tuple of (tmin,tmax)) or first 10% by default
    if noise_region:
        tmin, tmax = noise_region
        mask = (t >= tmin) & (t <= tmax)
        if mask.sum() < 2:
            noise_usp = np.std(y[:max(1, int(0.1*len(y)))])
        else:
            noise_usp = np.std(y[mask])
    else:
        noise_usp = np.std(y[:max(1, int(0.1*len(y)))])
    sn_classic = peak / (noise_std if noise_std != 0 else np.nan)
    sn_usp = peak / (noise_usp if noise_usp != 0 else np.nan)
    lod_signal = 3 * noise_std
    loq_signal = 10 * noise_std
    return {
        "peak": float(peak),
        "noise_std": float(noise_std),
        "noise_usp": float(noise_usp),
        "sn_classic": float(sn_classic),
        "sn_usp": float(sn_usp),
        "lod_signal": float(lod_signal),
        "loq_signal": float(loq_signal)
    }

def sn_page():
    st.header("📊 " + bilingual("Signal-to-Noise (S/N)", "Rapport Signal/Bruit (S/N)"))
    st.write(bilingual(f"You are logged in as **{st.session_state.username}**", f"Vous êtes connecté en tant que **{st.session_state.username}**"))

    company_name = st.text_input(bilingual("Company name for PDF report", "Nom de la compagnie pour le rapport PDF"), key="sn_company")

    uploaded = st.file_uploader(bilingual("Upload chromatogram CSV (Time, Signal)", "Téléverser chromatogramme CSV (Time, Signal)"), type=["csv"], key="sn_upload")
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            # normalize columns
            df.columns = [c.strip().lower() for c in df.columns]
            if "time" not in df.columns or "signal" not in df.columns:
                st.error(bilingual("CSV must contain Time and Signal columns.", "CSV doit contenir les colonnes : Time et Signal"))
                return
            df = df[["time", "signal"]]
            # show chromatogram
            fig, ax = plt.subplots()
            ax.plot(df["time"], df["signal"], label="Signal")
            ax.set_xlabel(bilingual("Time", "Temps"))
            ax.set_ylabel("Signal")
            ax.set_title(bilingual("Chromatogram", "Chromatogramme"))
            st.pyplot(fig)

            # let user choose baseline range for USP noise
            st.markdown(bilingual("Choose baseline (USP) noise region (time min/max). If empty, first 10% is used.",
                                 "Choisissez la région de bruit baseline (USP) (temps min/max). Si vide, les 10% premiers sont utilisés."))
            c1, c2 = st.columns(2)
            with c1:
                tmin = st.number_input(bilingual("Baseline time min", "Basline temps min"), value=float(df["time"].min()), key="sn_tmin")
            with c2:
                tmax = st.number_input(bilingual("Baseline time max", "Baseline temps max"), value=float(df["time"].min() + 0.1*(df["time"].max()-df["time"].min())), key="sn_tmax")
            noise_region = (tmin, tmax)

            sn_results = calculate_sn_from_df(df, noise_region=noise_region)
            st.success(bilingual(f"Signal/Noise = {sn_results['sn_classic']:.2f}", f"Rapport S/N = {sn_results['sn_classic']:.2f}"))
            st.info(bilingual(f"USP S/N = {sn_results['sn_usp']:.2f} (baseline noise = {sn_results['noise_usp']:.6f})",
                              f"USP S/N = {sn_results['sn_usp']:.2f} (bruit baseline = {sn_results['noise_usp']:.6f})"))
            st.info(bilingual(f"LOD (signal units) = {sn_results['lod_signal']:.6f}, LOQ = {sn_results['loq_signal']:.6f}",
                              f"LOD (unités signal) = {sn_results['lod_signal']:.6f}, LOQ = {sn_results['loq_signal']:.6f}"))

            # convert to concentration using slope (if available)
            if st.session_state.linearity["slope"] and st.session_state.linearity["slope"] != 0:
                slope = st.session_state.linearity["slope"]
                unit = st.session_state.linearity["unit"]
                lod_conc = sn_results["lod_signal"] / slope
                loq_conc = sn_results["loq_signal"] / slope
                st.info(bilingual(f"LOD = {lod_conc:.6f} {unit}, LOQ = {loq_conc:.6f} {unit}",
                                  f"LOD = {lod_conc:.6f} {unit}, LOQ = {loq_conc:.6f} {unit}"))
            else:
                st.warning(bilingual("No linearity slope available to convert LOD/LOQ to concentration. Compute linearity first.",
                                     "Aucune pente de linéarité disponible pour convertir LOD/LOQ en concentration. Calculer la linéarité d'abord."))

            # Export PDF for S/N
            if st.button(bilingual("Export S/N PDF report", "Exporter le rapport S/N")):
                if not company_name.strip():
                    st.warning(bilingual("Please enter company name before exporting.", "Veuillez saisir le nom de la compagnie avant d'exporter."))
                else:
                    # save chromatogram figure to buffer
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches="tight")
                    buf.seek(0)
                    img_path = f"sn_{st.session_state.username}.png"
                    with open(img_path, "wb") as f:
                        f.write(buf.getvalue())
                    # pdf
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, "LabT - S/N Report", ln=True, align="C")
                    pdf.set_font("Arial", "", 12)
                    pdf.cell(0, 8, f"Company: {company_name}", ln=True)
                    pdf.cell(0, 8, f"User: {st.session_state.username}", ln=True)
                    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
                    pdf.cell(0, 8, f"App: LabT", ln=True)
                    pdf.ln(6)
                    pdf.multi_cell(0, 8, f"Signal max: {sn_results['peak']:.6f}")
                    pdf.multi_cell(0, 8, f"Noise (std): {sn_results['noise_std']:.6f}")
                    pdf.multi_cell(0, 8, f"S/N ratio: {sn_results['sn_classic']:.2f}")
                    pdf.multi_cell(0, 8, f"USP S/N ratio: {sn_results['sn_usp']:.2f}")
                    pdf.multi_cell(0, 8, f"LOD (signal units): {sn_results['lod_signal']:.6f}, LOQ: {sn_results['loq_signal']:.6f}")
                    if st.session_state.linearity["slope"] and st.session_state.linearity["slope"] != 0:
                        pdf.multi_cell(0, 8, f"LOD in concentration ({st.session_state.linearity['unit']}): {sn_results['lod_signal']/st.session_state.linearity['slope']:.6f}")
                        pdf.multi_cell(0, 8, f"LOQ in concentration ({st.session_state.linearity['unit']}): {sn_results['loq_signal']/st.session_state.linearity['slope']:.6f}")
                    pdf.image(img_path, x=15, w=180)
                    pdf_file = f"SN_Report_{st.session_state.username}.pdf"
                    pdf.output(pdf_file)
                    st.success(bilingual("PDF exported", "PDF exporté"))
                    st.markdown(make_download_link(pdf_file, bilingual("⬇️ Download PDF", "⬇️ Télécharger le PDF")), unsafe_allow_html=True)

        except Exception as e:
            st.error(bilingual("Error reading CSV", f"Erreur de lecture CSV: {e}"))

    if st.button(bilingual("⬅️ Back to menu", "⬅️ Retour au menu"), key="sn_back"):
        st.experimental_rerun()

# ------------------------------
# User menu + change password
# ------------------------------
def user_menu():
    st.title(bilingual("🧪 LabT - Main menu", "🧪 LabT - Menu principal"))
    st.write(bilingual(f"You are logged in as **{st.session_state.username}**", f"Vous êtes connecté en tant que **{st.session_state.username}**"))

    choice = st.selectbox(bilingual("Choose an option", "Choisir une option"), [bilingual("Linearity", "Courbe de linéarité"), bilingual("Signal/Noise (S/N)", "Calcul S/N")], key="user_choice")
    if choice == bilingual("Linearity", "Courbe de linéarité"):
        linearity_page()
    else:
        sn_page()

    st.markdown("---")
    st.header(bilingual("Account", "Compte"))
    if st.button(bilingual("Change my password", "Changer mon mot de passe")):
        # show form
        with st.form("change_pass_form", clear_on_submit=False):
            cur = st.text_input(bilingual("Current password", "Mot de passe actuel"), type="password", key="cp_cur")
            new = st.text_input(bilingual("New password", "Nouveau mot de passe"), type="password", key="cp_new")
            confirm = st.text_input(bilingual("Confirm new password", "Confirmer le mot de passe"), type="password", key="cp_confirm")
            sub = st.form_submit_button(bilingual("Apply", "Appliquer"))
            if sub:
                users = load_users()
                uname = st.session_state.username
                if users[uname]["password"] != cur:
                    st.error(bilingual("Current password is incorrect.", "Le mot de passe actuel est incorrect."))
                elif new != confirm:
                    st.error(bilingual("New passwords do not match.", "Les nouveaux mots de passe ne correspondent pas."))
                elif not new:
                    st.warning(bilingual("New password cannot be empty.", "Le nouveau mot de passe ne peut être vide."))
                else:
                    users[uname]["password"] = new
                    save_users(users)
                    st.success(bilingual("Password changed ✅", "Mot de passe modifié ✅"))

    if st.button(bilingual("⬅️ Logout", "⬅️ Déconnexion"), key="user_logout"):
        logout()

# ------------------------------
# Main
# ------------------------------
def main():
    st.set_page_config(page_title="LabT", layout="centered")
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.role == "admin":
            admin_page()
        else:
            user_menu()

if __name__ == "__main__":
    main()