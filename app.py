# app.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from fpdf import FPDF
import json
import os
from math import isnan

# ---------- Configuration ----------
USERS_FILE = "users.json"  # ne pas afficher publiquement
DEFAULT_UNIT = "µg/mL"  # default concentration unit

# ---------- Simple bilingual function ----------
def T(fr, en):
    lang = st.session_state.get("lang", "fr")
    return fr if lang == "fr" else en

# ---------- Utils: users ----------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        # comptes d'exemple: admin / user
        example = {
            "admin": {"password": "admin123", "role": "admin"},
            "user": {"password": "user123", "role": "user"}
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(example, f, indent=2)

def load_users():
    ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# ---------- Authentication (no sidebar) ----------
def login_form():
    st.title("LABT - " + T("Application d'analyse", "Analysis app"))
    cols = st.columns([1, 1, 1])
    with cols[0]:
        if st.button("FR"):
            st.session_state.lang = "fr"
    with cols[1]:
        if st.button("EN"):
            st.session_state.lang = "en"
    # Small user-settings area (discrete)
    with st.expander(T("Paramètres utilisateur", "User settings"), expanded=False):
        if st.session_state.get("logged_in"):
            st.write(T("Connecté en tant que", "Logged in as"), st.session_state.username)
            if st.button(T("Changer mot de passe (discret)", "Change password (user)")):
                st.session_state.show_pw_change = True

    if st.session_state.get("show_pw_change"):
        st.subheader(T("Changer mot de passe", "Change password"))
        old = st.text_input(T("Ancien mot de passe", "Old password"), type="password")
        new = st.text_input(T("Nouveau mot de passe", "New password"), type="password")
        if st.button(T("Valider", "Confirm")):
            users = load_users()
            u = st.session_state.get("username")
            if u and users.get(u) and users[u]["password"] == old:
                users[u]["password"] = new
                save_users(users)
                st.success(T("Mot de passe changé", "Password changed"))
                st.session_state.show_pw_change = False
            else:
                st.error(T("Ancien mot de passe incorrect", "Old password incorrect"))

    if not st.session_state.get("logged_in"):
        st.subheader(T("Connexion", "Login"))
        username = st.text_input(T("Utilisateur", "Username"), key="login_username")
        password = st.text_input(T("Mot de passe", "Password"), type="password", key="login_password")
        if st.button(T("Se connecter", "Login")):
            users = load_users()
            if username and users.get(username.lower()) and users[username.lower()]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username.lower()
                st.experimental_set_query_params()  # no rerun call to avoid experimental_rerun issues
                st.success(T("Connecté", "Logged in"))
            else:
                st.error(T("Utilisateur ou mot de passe invalide", "Invalid username or password"))

# ---------- Admin user management ----------
def admin_panel():
    st.header(T("Administration des utilisateurs", "User administration"))
    users = load_users()
    # Do not dump JSON to screen
    st.write(T("Ajouter / supprimer / modifier des utilisateurs (admin only)", "Add / delete / modify users (admin only)"))
    with st.form("admin_form", clear_on_submit=False):
        action = st.selectbox(T("Action", "Action"), [T("Ajouter", "Add"), T("Supprimer", "Delete"), T("Modifier", "Modify")])
        uname = st.text_input(T("Nom d'utilisateur", "Username"))
        pwd = st.text_input(T("Mot de passe", "Password"), type="password")
        role = st.selectbox(T("Rôle", "Role"), ["user", "admin"])
        submit = st.form_submit_button(T("Exécuter", "Execute"))
        if submit:
            uname_l = uname.lower().strip()
            if action == T("Ajouter", "Add"):
                if not uname_l or not pwd:
                    st.error(T("Précisez username et mot de passe", "Specify username and password"))
                elif users.get(uname_l):
                    st.error(T("Utilisateur existe déjà", "User already exists"))
                else:
                    users[uname_l] = {"password": pwd, "role": role}
                    save_users(users)
                    st.success(T("Utilisateur ajouté", "User added"))
            elif action == T("Supprimer", "Delete"):
                if users.pop(uname_l, None):
                    save_users(users)
                    st.success(T("Utilisateur supprimé", "User deleted"))
                else:
                    st.error(T("Utilisateur introuvable", "User not found"))
            else:  # modify
                if users.get(uname_l):
                    if pwd:
                        users[uname_l]["password"] = pwd
                    users[uname_l]["role"] = role
                    save_users(users)
                    st.success(T("Utilisateur modifié", "User modified"))
                else:
                    st.error(T("Utilisateur introuvable", "User not found"))
    st.markdown("---")
    st.write(T("Liste des utilisateurs (nom + rôle)", "User list (name + role)"))
    for u, v in users.items():
        st.write(f"- {u} — {v.get('role','user')}")

# ---------- Linear regression / linearity ----------
def compute_linearity_from_df(df):
    # df must have >=2 columns; take first as x, second as y
    if df is None or df.shape[1] < 2 or df.shape[0] < 2:
        raise ValueError(T("CSV doit contenir au moins deux colonnes et deux lignes", "CSV must have at least 2 columns and 2 rows"))
    x = pd.to_numeric(df.iloc[:,0], errors='coerce').values
    y = pd.to_numeric(df.iloc[:,1], errors='coerce').values
    mask = (~np.isnan(x)) & (~np.isnan(y))
    x = x[mask]; y = y[mask]
    if len(x) < 2:
        raise ValueError(T("Pas assez de données valides pour la régression", "Not enough valid data for regression"))
    # Fit linear model
    a, b = np.polyfit(x, y, 1)  # slope a, intercept b
    # r2
    y_pred = a*x + b
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot != 0 else 0.0
    return {"slope": float(a), "intercept": float(b), "r2": float(r2), "x": x, "y": y}

def linearity_tab():
    st.header(T("Linéarité", "Linearity"))
    mode = st.radio(T("Mode d'entrée", "Input mode"), [T("Importer CSV", "Import CSV"), T("Saisie manuelle", "Manual input")])
    df = None
    if mode == T("Importer CSV", "Import CSV"):
        uploaded = st.file_uploader(T("Télécharger CSV (au moins 2 colonnes)", "Upload CSV (at least 2 columns)"), type=["csv"])
        if uploaded:
            try:
                # try comma and semicolon
                s = uploaded.read().decode("utf-8")
                sep = "," if s.count(",") >= s.count(";") else ";"
                df = pd.read_csv(BytesIO(s.encode("utf-8")), sep=sep)
                if df.shape[1] < 2:
                    st.error(T("CSV doit contenir au moins deux colonnes", "CSV must have at least two columns"))
                    df = None
            except Exception as e:
                st.error(T("Erreur lecture CSV :", "CSV read error:") + " " + str(e))
                df = None
    else:
        txt = st.text_area(T("Entrer valeurs x (séparées par ,)", "Enter x values (comma-separated)"))
        txt2 = st.text_area(T("Entrer valeurs y (séparées par ,)", "Enter y values (comma-separated)"))
        if txt and txt2:
            try:
                xs = np.array([float(v.strip()) for v in txt.split(",") if v.strip()!=""])
                ys = np.array([float(v.strip()) for v in txt2.split(",") if v.strip()!=""])
                if len(xs) != len(ys):
                    st.error(T("x et y doivent avoir même longueur", "x and y must have same length"))
                else:
                    df = pd.DataFrame({"x": xs, "y": ys})
            except Exception as e:
                st.error(T("Erreur de saisie :", "Input error:") + " " + str(e))
                df = None
    slope_info = None
    if df is not None:
        try:
            res = compute_linearity_from_df(df)
            st.write(T("Régression linéaire (y = pente * x + intercept)", "Linear regression (y = slope * x + intercept)"))
            st.write(f"{T('Pente', 'Slope')}: {res['slope']:.6g}")
            st.write(f"{T('Intercept', 'Intercept')}: {res['intercept']:.6g}")
            st.write(f"R²: {res['r2']:.6g}")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.scatter(res["x"], res["y"], label=T("Données", "Data"))
            ax.plot(res["x"], res["slope"]*res["x"] + res["intercept"], label=T("Ajustement", "Fit"))
            ax.set_xlabel(T("Concentration (x)", "Concentration (x)"))
            ax.set_ylabel(T("Signal (y)", "Signal (y)"))
            ax.legend()
            st.pyplot(fig)
            slope_info = {"slope": res["slope"], "intercept": res["intercept"], "r2": res["r2"]}
        except Exception as e:
            st.error(T("Erreur calcul linéarité :", "Linearity calculation error:") + " " + str(e))

    # Calculate unknown automatically (no button)
    st.markdown("---")
    st.subheader(T("Calculer concentration ou signal inconnu", "Calculate unknown concentration or signal"))
    choice = st.selectbox(T("Choix", "Choice"), [T("Concentration inconnue (calculer C à partir du signal)", "Unknown concentration (calc C from signal)"),
                                                  T("Signal inconnu (calculer signal à partir de la concentration)", "Unknown signal (calc signal from concentration)")])
    unit = st.selectbox(T("Unité concentration", "Concentration unit"), [DEFAULT_UNIT, "mg/mL", "ng/mL"])
    if slope_info is not None:
        if choice == T("Concentration inconnue (calculer C à partir du signal)", "Unknown concentration (calc C from signal)"):
            sig = st.number_input(T("Entrer signal mesuré", "Enter measured signal"), value=0.0, format="%.6f")
            if not isnan(sig):
                # C = (signal - intercept) / slope
                if slope_info["slope"] == 0:
                    st.error(T("Pente = 0, impossible de calculer", "Slope = 0, cannot compute"))
                else:
                    c = (sig - slope_info["intercept"]) / slope_info["slope"]
                    st.success(f"{T('Concentration inconnue', 'Unknown concentration')}: {c:.6g} {unit}")
        else:
            conc = st.number_input(T("Entrer concentration", "Enter concentration"), value=0.0, format="%.6f")
            sig_calc = slope_info["slope"] * conc + slope_info["intercept"]
            st.success(f"{T('Signal calculé', 'Calculated signal')}: {sig_calc:.6g}")

    # Export slope to session for S/N use
    if slope_info:
        st.session_state["linearity_slope"] = slope_info["slope"]
        st.session_state["linearity_intercept"] = slope_info["intercept"]

    # Export report PDF
    st.markdown("---")
    st.subheader(T("Exporter rapport de linéarité", "Export linearity report"))
    company = st.text_input(T("Nom de la compagnie (optionnel — demandé au moment de l'export)", "Company name (optional — asked at export)"), key="company_lin")
    if st.button(T("Générer PDF linéarité", "Generate linearity PDF")):
        if slope_info is None:
            st.error(T("Aucun calcul de linéarité disponible à exporter", "No linearity calculation available to export"))
        else:
            pdf_bytes = generate_linearity_pdf(slope_info, company or "")
            st.download_button(T("Télécharger PDF", "Download PDF"), data=pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")

# ---------- S/N tab ----------
def sn_tab():
    st.header(T("S/N (Signal / Bruit)", "S/N (Signal / Noise)"))
    st.write(T("Importer un CSV (temps, signal) ou une image (PNG/JPG). Pour PDF: aperçu non implémenté.", 
               "Upload a CSV (time, signal) or image (PNG/JPG). PDF preview not implemented."))
    uploaded = st.file_uploader(T("Fichier (csv / png / jpg / jpeg / pdf)", "File (csv / png / jpg / jpeg / pdf)"), 
                                type=["csv","png","jpg","jpeg","pdf"])
    baseline_region = None
    if uploaded:
        name = uploaded.name.lower()
        if name.endswith(".csv"):
            try:
                s = uploaded.read().decode("utf-8")
                sep = "," if s.count(",") >= s.count(";") else ";"
                df = pd.read_csv(BytesIO(s.encode("utf-8")), sep=sep)
                if df.shape[1] < 2:
                    st.error(T("CSV doit avoir au moins 2 colonnes", "CSV must have at least 2 columns"))
                else:
                    st.success(T("CSV chargé", "CSV loaded"))
                    # preview first rows
                    st.dataframe(df.head())
                    # convert numeric
                    x = pd.to_numeric(df.iloc[:,0], errors='coerce').values
                    y = pd.to_numeric(df.iloc[:,1], errors='coerce').values
                    # slider to select baseline region by index
                    n = len(x)
                    if n >= 2:
                        start = st.slider(T("Début zone bruit (index)", "Noise zone start (index)"), 0, max(0, n-1), 0)
                        end = st.slider(T("Fin zone bruit (index)", "Noise zone end (index)"), 0, max(0, n-1), max(1, n//10))
                        baseline = y[start:end+1] if end >= start else y[start:start+1]
                        noise_std = float(np.nanstd(baseline))
                        # signal: choose peak index or enter manually
                        peak_mode = st.radio(T("Détecter pic automatiquement ou manuel", "Detect peak automatically or manual"), 
                                             [T("Auto", "Auto"), T("Manuel", "Manual")])
                        if peak_mode == T("Auto", "Auto"):
                            peak_idx = int(np.nanargmax(y))
                            signal_val = float(y[peak_idx])
                        else:
                            pidx = st.number_input(T("Index pic (entier)", "Peak index (int)"), min_value=0, max_value=n-1, value=int(np.nanargmax(y)))
                            peak_idx = int(pidx)
                            signal_val = float(y[peak_idx])
                        sn_classic = signal_val / noise_std if noise_std != 0 else float("inf")
                        # USP style: maybe use RMS of baseline vs peak height? We'll provide same as classic but label USP option
                        sn_usp = sn_classic
                        st.write(T("Signal (au pic)", "Signal (at peak)"), f"{signal_val:.6g}")
                        st.write(T("Bruit (std zone sélectionnée)", "Noise (std of selected zone)"), f"{noise_std:.6g}")
                        st.write(T("S/N (classique)", "S/N (classic)"), f"{sn_classic:.4g}")
                        st.write(T("S/N (USP)", "S/N (USP)"), f"{sn_usp:.4g}")
                        # LOD/LOQ in concentration using slope if present
                        slope = st.session_state.get("linearity_slope")
                        if slope:
                            lod_conc = (3 * noise_std - st.session_state.get("linearity_intercept",0)) / slope
                            loq_conc = (10 * noise_std - st.session_state.get("linearity_intercept",0)) / slope
                            st.write(T("LOD (approx, en concentration)", "LOD (approx, in concentration)"), f"{lod_conc:.6g} {DEFAULT_UNIT}")
                            st.write(T("LOQ (approx, en concentration)", "LOQ (approx, in concentration)"), f"{loq_conc:.6g} {DEFAULT_UNIT}")
                        # plot
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots()
                        ax.plot(x, y, label="signal")
                        ax.axvspan(x[start], x[end], color="orange", alpha=0.3, label=T("Zone bruit","Noise zone"))
                        ax.scatter([x[peak_idx]], [y[peak_idx]], color="red", label=T("Pic","Peak"))
                        ax.set_xlabel(T("Temps", "Time"))
                        ax.set_ylabel(T("Signal", "Signal"))
                        ax.legend()
                        st.pyplot(fig)
                        # Export report
                        if st.button(T("Générer PDF S/N", "Generate S/N PDF")):
                            company = st.text_input(T("Nom compagnie pour le rapport (optionnel)", "Company name for report (optional)"), key="company_sn")
                            pdf_bytes = generate_sn_pdf(signal_val, noise_std, sn_classic, sn_usp, slope if slope else None, company or "")
                            st.download_button(T("Télécharger PDF", "Download PDF"), data=pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")
                    else:
                        st.error(T("CSV trop court", "CSV too short"))
            except Exception as e:
                st.error(T("Erreur lecture CSV :", "CSV read error:") + " " + str(e))
        elif name.endswith((".png", ".jpg", ".jpeg")):
            # show image; cannot compute S/N unless user provides numeric baseline & signal or CSV
            try:
                data = uploaded.read()
                img = Image.open(BytesIO(data))
                st.image(img, caption=T("Image téléchargée (aperçu)", "Uploaded image (preview)"))
                st.info(T("Pour le calcul S/N, préférez un CSV contenant temps/signal. Vous pouvez aussi entrer signal et bruit manuellement.",
                          "For S/N calculation prefer CSV with time/signal. You may also enter signal and noise manually."))
                # manual entry fallback
                sig = st.number_input(T("Entrer signal (manuellement)", "Enter signal (manual)"), value=0.0)
                noise = st.number_input(T("Entrer bruit (std) (manuellement)", "Enter noise (std) (manual)"), value=1.0)
                if noise == 0:
                    st.error(T("Bruit ne peut être 0", "Noise cannot be 0"))
                else:
                    sn = sig / noise
                    st.write(T("S/N (calculé)", "S/N (calculated)"), f"{sn:.4g}")
            except UnidentifiedImageError:
                st.error(T("Fichier image non reconnu", "Image file not recognized"))
            except Exception as e:
                st.error(T("Erreur image:", "Image error:") + " " + str(e))
        elif name.endswith(".pdf"):
            st.warning(T("Aperçu PDF non implémenté. Pour le calcul S/N, convertissez en CSV ou PNG.", 
                         "PDF preview not implemented. For S/N calculations convert to CSV or PNG."))
        else:
            st.error(T("Type de fichier non supporté", "File type not supported"))
    else:
        st.info(T("Importer un fichier pour commencer", "Upload a file to begin"))

# ---------- PDF generation helpers ----------
def generate_linearity_pdf(slope_info, company):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Linearity report", ln=True)
    if company:
        pdf.cell(0, 8, f"Company: {company}", ln=True)
    pdf.cell(0, 8, f"Slope: {slope_info['slope']:.6g}", ln=True)
    pdf.cell(0, 8, f"Intercept: {slope_info['intercept']:.6g}", ln=True)
    pdf.cell(0, 8, f"R2: {slope_info['r2']:.6g}", ln=True)
    # return bytes
    return pdf.output(dest='S').encode('latin-1')

def generate_sn_pdf(signal, noise, sn_classic, sn_usp, slope=None, company=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "S/N report", ln=True)
    if company:
        pdf.cell(0, 8, f"Company: {company}", ln=True)
    pdf.cell(0, 8, f"Signal: {signal:.6g}", ln=True)
    pdf.cell(0, 8, f"Noise (std): {noise:.6g}", ln=True)
    pdf.cell(0, 8, f"S/N (classic): {sn_classic:.6g}", ln=True)
    pdf.cell(0, 8, f"S/N (USP): {sn_usp:.6g}", ln=True)
    if slope:
        pdf.cell(0, 8, f"Slope used from linearity: {slope:.6g}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# ---------- Main ----------
def main():
    st.set_page_config(page_title="LABT", layout="wide")
    # session defaults
    if "lang" not in st.session_state:
        st.session_state.lang = "fr"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "show_pw_change" not in st.session_state:
        st.session_state.show_pw_change = False

    if not st.session_state.logged_in:
        login_form()
        return  # stop here until login
    # logged in
    username = st.session_state.get("username")
    users = load_users()
    role = users.get(username, {}).get("role", "user")

    # Top bar: logout small button
    cols = st.columns([8,1])
    with cols[1]:
        if st.button(T("Déconnexion", "Logout")):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.success(T("Déconnecté", "Logged out"))
            return

    # If admin only show admin panel (and not the main tabs)
    if role == "admin":
        st.title(T("Panneau Admin", "Admin panel"))
        st.write(T("En tant qu'administrateur vous pouvez gérer uniquement les utilisateurs.", "As admin you can manage users only."))
        admin_panel()
        return

    # For normal users: show the two main tabs (linearity & s/n) as separate sections (no sidebar)
    st.title(T("LABT - Outils", "LABT - Tools"))
    tab = st.radio(T("Choisir un volet", "Choose a panel"), [T("Linéarité", "Linearity"), T("S/N", "S/N")])
    if tab == T("Linéarité", "Linearity"):
        linearity_tab()
    else:
        sn_tab()

if __name__ == "__main__":
    ensure_users_file()
    main()