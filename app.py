# app.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
from datetime import datetime
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import matplotlib.pyplot as plt
from fpdf import FPDF
from scipy import stats

# -------------------------------------------------------
# Simple bilingual helper (EN default). Use st.selectbox to toggle.
# -------------------------------------------------------
LANG = {
    "en": {
        "app_title": "LabT — Linearity & S/N",
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "login_btn": "Sign in",
        "logout": "Logout",
        "invalid": "Invalid username or password",
        "linearity": "Linearity",
        "s_n": "S/N",
        "admin": "Admin",
        "upload_csv": "Upload CSV (two columns: x,y)",
        "manual_input": "Manual input (comma separated x and y)",
        "calculate": "Calculate (automatic)",
        "export_pdf": "Export report (PDF)",
        "company_name": "Company name (will be asked at export)",
        "unit": "Concentration unit",
        "unit_default": "µg/mL",
        "unknown_choice": "Unknown to compute",
        "unknown_conc": "Concentration (unknown)",
        "unknown_sig": "Signal (unknown)",
        "r2": "R²",
        "slope": "Slope",
        "intercept": "Intercept",
        "upload_image": "Upload image (png/jpg) or CSV for chromatogram",
        "select_region": "Select region for baseline/noise (via sliders)",
        "sn_classic": "Classic S/N",
        "sn_usp": "USP S/N (peak height / std noise)",
        "download_pdf": "Download PDF",
        "change_pwd": "Change password (user)",
        "add_user": "Add user",
        "delete_user": "Delete user",
        "modify_user": "Modify user",
        "admin_only": "Admin menu (manage users)",
        "preview_not_impl": "Preview PDF not implemented — exported file will be downloaded",
        "csv_error_cols": "CSV must have at least two columns (x,y).",
        "select_language": "Select language",
        "english": "English",
        "french": "Français",
        "company_missing_warn": "Provide company name when exporting PDF.",
        "choose_unit": "Choose unit (default µg/mL)",
        "baseline_region": "Baseline (noise) region"
    },
    "fr": {
        "app_title": "LabT — Linéarité & S/N",
        "login": "Connexion",
        "username": "Utilisateur",
        "password": "Mot de passe",
        "login_btn": "Se connecter",
        "logout": "Déconnexion",
        "invalid": "Utilisateur ou mot de passe invalide",
        "linearity": "Linéarité",
        "s_n": "S/N",
        "admin": "Admin",
        "upload_csv": "Importer CSV (2 colonnes : x,y)",
        "manual_input": "Saisie manuelle (x et y séparés par des virgules)",
        "calculate": "Calcul (automatique)",
        "export_pdf": "Exporter rapport (PDF)",
        "company_name": "Nom de la société (saisi lors de l'export)",
        "unit": "Unité de concentration",
        "unit_default": "µg/mL",
        "unknown_choice": "Inconnue à calculer",
        "unknown_conc": "Concentration (inconnue)",
        "unknown_sig": "Signal (inconnu)",
        "r2": "R²",
        "slope": "Pente",
        "intercept": "Ordonnée à l'origine",
        "upload_image": "Importer image (png/jpg) ou CSV pour chromatogramme",
        "select_region": "Sélectionner la zone pour le bruit (sliders)",
        "sn_classic": "S/N classique",
        "sn_usp": "S/N USP (hauteur du pic / écart-type du bruit)",
        "download_pdf": "Télécharger PDF",
        "change_pwd": "Changer mot de passe (user)",
        "add_user": "Ajouter utilisateur",
        "delete_user": "Supprimer utilisateur",
        "modify_user": "Modifier utilisateur",
        "admin_only": "Menu Admin (gestion des users)",
        "preview_not_impl": "Aperçu PDF non implémenté — le fichier sera téléchargé",
        "csv_error_cols": "Le CSV doit contenir au moins deux colonnes (x,y).",
        "select_language": "Choisir la langue",
        "english": "English",
        "french": "Français",
        "company_missing_warn": "Entrez le nom de la société pour exporter le PDF.",
        "choose_unit": "Choisir unité (par défaut µg/mL)",
        "baseline_region": "Région de baseline (bruit)"
    }
}

# ---------------------------
# USERS file utility (simple JSON)
# ---------------------------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        # default sample users
        default = {"admin": {"password": "admin"}, "user": {"password": "user"}}
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        return default
    except json.JSONDecodeError:
        # if file corrupted, reset minimal
        default = {"admin": {"password": "admin"}, "user": {"password": "user"}}
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        return default

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# ---------------------------
# Auth management (no sidebar)
# ---------------------------
def login_ui(t):
    st.title(t["app_title"])
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(t["username"])
    with col2:
        password = st.text_input(t["password"], type="password")
    if st.button(t["login_btn"]):
        users = load_users()
        u = username.strip()
        if u and u in users and users[u]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = u
            # admin flag
            st.session_state.is_admin = (u == "admin")
            st.experimental_set_query_params()  # small no-op to cause state to persist
            st.success(f"{t['login_btn']} ✅")
            # immediately show next page (no extra click)
        else:
            st.error(t["invalid"])

def logout_ui(t):
    if st.button(t["logout"]):
        st.session_state.clear()
        st.experimental_set_query_params()
        st.experimental_rerun_wrapper = True  # placeholder to avoid attribute errors
        st.success("Logged out")

# streamlit versions differ: avoid st.experimental_rerun call; instead ask user to refresh after logout
def do_logout():
    st.session_state.clear()
    st.info("You were logged out. Refresh the page.")

# ---------------------------
# Linearity functions
# ---------------------------
def compute_linearity(x, y):
    # require at least 2 points
    if len(x) < 2:
        return None
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return {"slope": slope, "intercept": intercept, "r2": r_value**2, "std_err": std_err}

def predict_from_signal(slope, intercept, signal):
    # conc = (signal - intercept) / slope
    return (signal - intercept) / slope

def predict_from_conc(slope, intercept, conc):
    return slope * conc + intercept

# ---------------------------
# PDF export (simple)
# ---------------------------
def create_pdf_report(company, user, title, fig, results, unit):
    # fig: matplotlib figure
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, company if company else "Company", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"User: {user}    Date: {datetime.now().isoformat(sep=' ', timespec='seconds')}", ln=True)
    pdf.ln(6)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, title, ln=True)
    pdf.ln(6)

    # insert figure image
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    pdf.image(buf, x=15, w=180)
    pdf.ln(6)

    # results
    pdf.set_font("Arial", "", 12)
    for k, v in results.items():
        pdf.cell(0, 7, f"{k}: {v}", ln=True)
    # unit mention
    pdf.ln(4)
    pdf.cell(0, 6, f"Concentration unit: {unit}", ln=True)

    out = BytesIO()
    pdf.output(out)
    out.seek(0)
    return out

# ---------------------------
# S/N functions (basic)
# ---------------------------
def compute_sn_from_signal_array(x, y, left_idx, right_idx, method="classic"):
    # compute peak height: max in region - baseline
    region_x = x[left_idx:right_idx+1]
    region_y = y[left_idx:right_idx+1]
    if len(region_y) == 0:
        return None
    peak = np.max(region_y)
    baseline_region = np.concatenate([y[max(0,left_idx-50):left_idx], y[right_idx:right_idx+50]])
    if len(baseline_region) < 2:
        # fallback use region edges std
        baseline_region = region_y[:max(1, len(region_y)//4)]
    noise_std = np.std(baseline_region) if len(baseline_region)>0 else 1e-9
    sn_classic = peak / (noise_std if noise_std>0 else 1e-9)
    # USP typical: height/noise_std as well
    sn_usp = (peak - np.mean(baseline_region)) / (noise_std if noise_std>0 else 1e-9)
    return {"sn_classic": sn_classic, "sn_usp": sn_usp, "peak": peak, "noise_std": noise_std}

# ---------------------------
# UI building blocks
# ---------------------------
def linearity_panel(t):
    st.header(t["linearity"])
    unit = st.selectbox(t["unit"], [t["unit_default"], "mg/mL", "ng/mL"], index=0 if t["unit_default"] == "µg/mL" else 1)
    mode = st.radio("Input mode", ["CSV", "Manual"], index=0)
    df = None
    x = y = None
    if mode == "CSV":
        uploaded = st.file_uploader(t["upload_csv"], type=["csv"], key="lin_csv")
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                if df.shape[1] < 2:
                    st.error(t["csv_error_cols"])
                else:
                    x = df.iloc[:,0].astype(float).values
                    y = df.iloc[:,1].astype(float).values
                    st.write("Preview:", df.head())
            except Exception as e:
                st.error("Error reading CSV: " + str(e))
    else:
        s_x = st.text_area("x values (comma separated)", placeholder="1,2,3")
        s_y = st.text_area("y values (comma separated)", placeholder="10,20,30")
        if s_x and s_y:
            try:
                x = np.array([float(v.strip()) for v in s_x.split(",") if v.strip()!=''])
                y = np.array([float(v.strip()) for v in s_y.split(",") if v.strip()!=''])
            except Exception as e:
                st.error("Parsing error: " + str(e))
    # compute if possible (automatic)
    if x is not None and y is not None and len(x) >= 2:
        res = compute_linearity(x, y)
        if res is None:
            st.warning("Not enough data points")
            return None
        slope = res["slope"]
        intercept = res["intercept"]
        r2 = res["r2"]
        st.metric(t["slope"], f"{slope:.6g}")
        st.metric(t["intercept"], f"{intercept:.6g}")
        st.metric(t["r2"], f"{r2:.6g}")

        # plot
        fig, ax = plt.subplots()
        ax.scatter(x, y, label="data")
        xs = np.linspace(min(x), max(x), 200)
        ax.plot(xs, slope*xs + intercept, label=f"fit (R2={r2:.4f})")
        ax.set_xlabel("Concentration")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)

        # compute unknown automatically if user provides value
        unknown_mode = st.selectbox(t["unknown_choice"], [t["unknown_conc"], t["unknown_sig"]])
        if unknown_mode == t["unknown_conc"]:
            s_val = st.number_input("Signal value", value=0.0, format="%.6f")
            if s_val is not None:
                try:
                    conc = predict_from_signal(slope, intercept, s_val)
                    st.write(f"Estimated concentration: {conc:.6g} {unit}")
                except Exception as e:
                    st.error("Cannot compute concentration: " + str(e))
        else:
            c_val = st.number_input("Concentration value", value=0.0, format="%.6f")
            if c_val is not None:
                sig = predict_from_conc(slope, intercept, c_val)
                st.write(f"Estimated signal: {sig:.6g}")

        # export slope to session for S/N usage
        if st.button("Use slope in S/N panel (export)"):
            st.session_state.get("line_slope", slope)
            st.session_state.get("line_intercept", intercept)
            st.success("Slope exported to S/N panel")

        # export PDF
        if st.button(t["export_pdf"]):
            company = st.text_input(t["company_name"], key="company_lin")
            if not company:
                st.warning(t["company_missing_warn"])
            fig_pdf = fig
            results = {
                t["slope"]: f"{slope:.6g}",
                t["intercept"]: f"{intercept:.6g}",
                t["r2"]: f"{r2:.6g}"
            }
            pdf_bytes = create_pdf_report(company, st.session_state.get("username", "unknown"), t["linearity"], fig_pdf, results, unit)
            st.download_button(t["download_pdf"], data=pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")
    else:
        st.info("Provide at least two points to compute linearity.")

def sn_panel(t):
    st.header(t["s_n"])
    uploaded = st.file_uploader(t["upload_image"], type=["png","jpg","jpeg","csv"], key="sn_file")
    x = y = None
    if uploaded is None:
        st.info("Upload an image (png/jpg) or a csv with two columns x,y")
        return
    # CSV case: expect two columns x,y
    if uploaded.name.lower().endswith(".csv"):
        try:
            df = pd.read_csv(uploaded)
            if df.shape[1] < 2:
                st.error(t["csv_error_cols"])
                return
            x = df.iloc[:,0].astype(float).values
            y = df.iloc[:,1].astype(float).values
            st.write("Preview:", df.head())
        except Exception as e:
            st.error("CSV read error: " + str(e))
            return
    else:
        # image -> extract a simple chromatogram by summing vertical pixel intensities
        try:
            img = Image.open(uploaded).convert("L")
            arr = np.array(img)
            # invert so higher pixel value is peak
            arr_inverted = 255 - arr
            # sum rows to get a 1D signal
            y = arr_inverted.sum(axis=0).astype(float)
            x = np.arange(len(y))
            st.image(img, caption="Uploaded image (preview)")
        except UnidentifiedImageError:
            st.error("Cannot identify image file.")
            return
        except Exception as e:
            st.error("Image processing error: " + str(e))
            return

    # show simple interactive sliders to select region
    n = len(x)
    st.write(f"Signal length: {n}")
    left = st.slider("Left index", min_value=0, max_value=max(0, n-1), value=0, key="left")
    right = st.slider("Right index", min_value=0, max_value=max(0, n-1), value=max(0, n-1), key="right")
    if left >= right:
        st.warning("Choose left < right")
        return

    res = compute_sn_from_signal_array(x, y, left, right)
    if res is None:
        st.error("S/N computation failed")
        return
    st.metric(t["sn_classic"], f"{res['sn_classic']:.4g}")
    st.metric(t["sn_usp"], f"{res['sn_usp']:.4g}")
    st.write(f"Peak: {res['peak']:.4g}, Noise std: {res['noise_std']:.4g}")

    # plot
    fig, ax = plt.subplots()
    ax.plot(x, y, label="signal")
    ax.axvspan(left, right, color='orange', alpha=0.2, label="selected region")
    ax.set_xlabel("index")
    ax.set_ylabel("intensity")
    ax.legend()
    st.pyplot(fig)

    # Option: use slope from linearity if present to compute LOD/LOQ in concentration
    slope = st.session_state.get("line_slope", None)
    if slope:
        # classic LOD ~ 3*noise/slope ; LOQ ~ 10*noise/slope
        lod = 3 * res["noise_std"] / slope
        loq = 10 * res["noise_std"] / slope
        st.write(f"LOD (conc) ≈ {lod:.6g}")
        st.write(f"LOQ (conc) ≈ {loq:.6g}")

    # export PDF
    if st.button("Export S/N report (PDF)"):
        company = st.text_input(t["company_name"], key="company_sn")
        if not company:
            st.warning(t["company_missing_warn"])
        results = {
            t["sn_classic"]: f"{res['sn_classic']:.6g}",
            t["sn_usp"]: f"{res['sn_usp']:.6g}",
            "peak": f"{res['peak']:.6g}",
            "noise_std": f"{res['noise_std']:.6g}"
        }
        if slope:
            results["LOD_conc"] = f"{lod:.6g}"
            results["LOQ_conc"] = f"{loq:.6g}"
        pdf_bytes = create_pdf_report(company, st.session_state.get("username","unknown"), t["s_n"], fig, results, st.selectbox(t["choose_unit"], ["µg/mL","mg/mL","ng/mL"]))
        st.download_button(t["download_pdf"], data=pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")

# ---------------------------
# Admin user management
# ---------------------------
def admin_panel(t):
    st.header(t["admin_only"])
    users = load_users()
    st.write("Users (usernames only):", list(users.keys()))
    col1, col2 = st.columns(2)
    with col1:
        add_name = st.text_input(t["add_user"], key="add_name")
        add_pwd = st.text_input("Password for new user", type="password", key="add_pwd")
        if st.button(t["add_user"] + " ▶"):
            if add_name:
                users[add_name] = {"password": add_pwd if add_pwd else "changeme"}
                save_users(users)
                st.success("User added")
    with col2:
        del_name = st.text_input(t["delete_user"], key="del_name")
        if st.button(t["delete_user"] + " ▶"):
            if del_name in users:
                del users[del_name]
                save_users(users)
                st.success("User deleted")
            else:
                st.error("User not found")
    # modify
    mod_name = st.text_input(t["modify_user"] + " (username)", key="mod_name")
    mod_pwd = st.text_input("New password", type="password", key="mod_pwd")
    if st.button(t["modify_user"] + " ▶"):
        if mod_name in users:
            users[mod_name]["password"] = mod_pwd
            save_users(users)
            st.success("Password updated")
        else:
            st.error("User not found")

# ---------------------------
# Small change-password UI for logged users (discrete)
# ---------------------------
def change_password_ui(t):
    st.write("---")
    st.subheader(t["change_pwd"])
    new = st.text_input("New password", type="password", key="ch_new")
    if st.button("Set new password"):
        users = load_users()
        u = st.session_state.get("username")
        if u and u in users:
            users[u]["password"] = new
            save_users(users)
            st.success("Password changed (you must re-login)")
            do_logout()
        else:
            st.error("User not found")

# ---------------------------
# Main
# ---------------------------
def main():
    # language selection
    lang_choice = st.selectbox("Language / Langue", [LANG["en"]["english"], LANG["en"]["french"]], index=0)
    lang_key = "en" if lang_choice == LANG["en"]["english"] else "fr"
    t = LANG[lang_key]

    # login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_ui(t)
        return

    # logged in UI
    st.sidebar.empty()  # ensure no sidebar elements are used (user requested no sidebar)
    st.write(f"{t['app_title']} — {st.session_state.get('username')}")
    if st.button(t["logout"]):
        do_logout()
        return

    # small button to change password, separate and discrete (not in main menu)
    if st.checkbox(t["change_pwd"]):
        change_password_ui(t)

    # main tabs (two separate panels)
    choice = st.radio("Choose panel / Choisir volet", [t["linearity"], t["s_n"]])
    if choice == t["linearity"]:
        linearity_panel(t)
    else:
        sn_panel(t)

    # admin panel (only admin)
    if st.session_state.get("is_admin"):
        st.write("---")
        admin_panel(t)

if __name__ == "__main__":
    main()