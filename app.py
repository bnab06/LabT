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

# ---------------------
# Configuration / Init
# ---------------------
USERS_FILE = "users.json"
PDF_LOGO_TEXT = "LabT"

# Ensure session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = None
if "current_page" not in st.session_state:
    st.session_state.current_page = None
if "linearity_data" not in st.session_state:
    st.session_state.linearity_data = {"conc": None, "resp": None, "slope": None, "intercept": None, "r2": None, "unit": "µg/mL"}

# ---------------------
# Utilitaires utilisateurs
# ---------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "user1": {"password": "1234", "role": "user"},
            "user2": {"password": "abcd", "role": "user"},
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def normalize_username(u):
    return u.strip().lower()

# ---------------------
# Auth / session actions
# ---------------------
def do_logout():
    for k in list(st.session_state.keys()):
        # preserve users file etc, but clear session state keys related to UI
        if k not in ("run_id",):
            try:
                del st.session_state[k]
            except Exception:
                pass
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = None
    st.session_state.current_page = None
    st.rerun()

def login_action(selected_user, password, lang):
    users = load_users()
    key = normalize_username(selected_user)
    # usernames in JSON might be lowercase keys - ensure match
    matched = None
    for k in users:
        if k.lower() == key:
            matched = k
            break
    if matched and users[matched]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = matched
        st.session_state.role = users[matched]["role"]
        # default landing page
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        # success message (bilingual)
        if lang == "EN":
            st.success(f"Login successful ✅ / You are logged in as {matched}")
        else:
            st.success(f"Connexion réussie ✅ / Vous êtes connecté en tant que {matched}")
        st.rerun()
    else:
        if lang == "EN":
            st.error("Wrong username or password ❌")
        else:
            st.error("Nom d’utilisateur ou mot de passe incorrect ❌")

# ---------------------
# PDF generation
# ---------------------
def generate_pdf(title, content_lines, img_bytes=None, company="", username=""):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"App: {PDF_LOGO_TEXT}", ln=True)
    pdf.cell(0, 6, f"Company: {company if company else 'N/A'}", ln=True)
    pdf.cell(0, 6, f"User: {username}", ln=True)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(6)
    # content
    pdf.set_font("Arial", "", 11)
    for line in content_lines:
        pdf.multi_cell(0, 6, str(line))
    pdf.ln(6)
    if img_bytes is not None:
        # embed PNG image saved as bytes
        img_path = f"_tmp_plot_{int(datetime.now().timestamp())}.png"
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        # keep image width < page width
        pdf.image(img_path, x=15, w=180)
        try:
            os.remove(img_path)
        except Exception:
            pass
    filename = f"{title}_{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

def offer_download(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{os.path.basename(file_path)}">⬇️ Download PDF</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---------------------
# Pages
# ---------------------
def page_login():
    st.title("🔬 LabT")
    lang = st.selectbox("Language / Langue", ["EN", "FR"], index=0, key="lang_select")
    users = load_users()
    # select usernames shown as original keys
    user_list = list(users.keys())
    selected_user = st.selectbox("Choose user / Choisir un utilisateur:", user_list, key="login_user")
    password = st.text_input("Password / Mot de passe:", type="password", key="login_pass")
    st.button("Login / Se connecter", on_click=login_action, args=(selected_user, password, lang))

def admin_manage_users_page():
    st.header("👥 Manage users / Gestion des utilisateurs")
    st.write(f"You are logged in as **{st.session_state.username}**")
    users = load_users()
    action = st.selectbox("Action / Action:", ["Add / Ajouter", "Modify / Modifier", "Delete / Supprimer"], key="admin_action")
    username = st.text_input("Username / Nom d’utilisateur:", key="admin_username")
    password = st.text_input("Password / Mot de passe:", key="admin_password")
    role = st.selectbox("Role / Rôle:", ["user", "admin"], key="admin_role")
    def on_validate():
        if not username:
            st.warning("Please provide a username / Veuillez fournir un nom d'utilisateur.")
            return
        key = normalize_username(username)
        users_local = load_users()
        # find exact key if exists ignoring case
        existing = None
        for k in users_local:
            if k.lower() == key:
                existing = k
                break
        if action.startswith("Add"):
            if existing:
                st.warning("User already exists / Utilisateur déjà existant.")
            else:
                if not password:
                    st.warning("Password required for add / Mot de passe requis pour ajouter.")
                    return
                users_local[username] = {"password": password, "role": role}
                save_users(users_local)
                st.success("User added ✅ / Utilisateur ajouté ✅")
        elif action.startswith("Modify"):
            if not existing:
                st.warning("User not found / Utilisateur introuvable.")
            else:
                if password:
                    users_local[existing]["password"] = password
                users_local[existing]["role"] = role
                save_users(users_local)
                st.success("User modified ✅ / Utilisateur modifié ✅")
        else:  # Delete
            if not existing:
                st.warning("User not found / Utilisateur introuvable.")
            else:
                del users_local[existing]
                save_users(users_local)
                st.success("User deleted ✅ / Utilisateur supprimé ✅")
    st.button("Validate / Valider", on_click=on_validate)
    st.button("Logout / Déconnexion", on_click=do_logout)
    st.markdown("---")
    st.subheader("Existing users / Utilisateurs existants")
    # show table but hide passwords for security; show usernames original
    users = load_users()
    display = []
    for k, v in users.items():
        display.append({"username": k, "role": v.get("role", "")})
    st.table(pd.DataFrame(display))

def user_change_password_page():
    st.header("🔑 Change password / Modifier mot de passe")
    st.write(f"You are logged in as **{st.session_state.username}**")
    current = st.text_input("Current password / Mot de passe actuel:", type="password", key="cp_current")
    newp = st.text_input("New password / Nouveau mot de passe:", type="password", key="cp_new")
    def do_change():
        users = load_users()
        uname = st.session_state.username
        if not users.get(uname) or users[uname]["password"] != current:
            st.error("Current password incorrect / Mot de passe actuel incorrect")
            return
        if not newp:
            st.warning("New password cannot be empty / Le nouveau mot de passe ne peut être vide")
            return
        users[uname]["password"] = newp
        save_users(users)
        st.success("Password updated ✅ / Mot de passe mis à jour")
    st.button("Change / Modifier", on_click=do_change)
    st.button("Back / Retour", on_click=lambda: st.session_state.update(current_page="linearity") or st.rerun())

# ---------- Linearity ----------
def page_linearity():
    st.header("📈 Linearity / Courbe de linéarité")
    st.write(f"You are logged in as **{st.session_state.username}**")
    mode = st.radio("Input mode / Mode d'entrée:", ["Manual / Saisie", "CSV upload"], index=0, key="lin_mode")
    if mode.startswith("Manual"):
        conc_input = st.text_input("Concentrations (comma separated) / Concentrations (séparées par des virgules):", key="lin_conc")
        resp_input = st.text_input("Responses (comma separated) / Réponses (séparées par des virgules):", key="lin_resp")
        if st.button("Load data / Charger données"):
            try:
                conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()!=""])
                resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()!=""])
                if len(conc)==0 or len(conc)!=len(resp):
                    st.error("Lists must be same length and non-empty / Les listes doivent avoir la même longueur et ne pas être vides.")
                else:
                    st.session_state.linearity_data["conc"] = conc
                    st.session_state.linearity_data["resp"] = resp
                    st.success("Data loaded / Données chargées")
            except Exception as e:
                st.error(f"Parsing error / Erreur: {e}")
    else:
        uploaded = st.file_uploader("Upload CSV with columns 'Concentration' and 'Response' / Téléverser CSV avec colonnes 'Concentration' et 'Response'", type=["csv"], key="lin_csv")
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                # find columns case-insensitively
                cols = {c.lower(): c for c in df.columns}
                if "concentration" not in cols or "response" not in cols:
                    st.error("CSV must contain columns 'Concentration' and 'Response' / CSV doit contenir 'Concentration' et 'Response'")
                else:
                    conc = df[cols["concentration"]].astype(float).values
                    resp = df[cols["response"]].astype(float).values
                    st.session_state.linearity_data["conc"] = conc
                    st.session_state.linearity_data["resp"] = resp
                    st.success("CSV loaded / CSV chargé")
            except Exception as e:
                st.error(f"CSV read error / Erreur lecture CSV: {e}")

    # unit selection
    unit = st.selectbox("Concentration unit / Unité de concentration:", ["µg/mL", "mg/L", "g/L"], index=0, key="lin_unit")
    st.session_state.linearity_data["unit"] = unit

    # perform fit if data present
    if st.session_state.linearity_data["conc"] is not None:
        conc = st.session_state.linearity_data["conc"]
        resp = st.session_state.linearity_data["resp"]
        try:
            slope, intercept = np.polyfit(conc, resp, 1)
            # R2:
            pred = slope*conc + intercept
            ss_res = np.sum((resp - pred)**2)
            ss_tot = np.sum((resp - np.mean(resp))**2)
            r2 = 1 - ss_res/ss_tot if ss_tot != 0 else 0.0
            st.session_state.linearity_data.update({"slope": slope, "intercept": intercept, "r2": r2})
            # plot
            fig, ax = plt.subplots()
            ax.scatter(conc, resp, label="Points")
            xs = np.linspace(min(conc), max(conc), 200)
            ax.plot(xs, slope*xs+intercept, label=f"Fit: y={slope:.4f}x+{intercept:.4f}\nR²={r2:.4f}")
            ax.set_xlabel(f"Concentration ({unit})")
            ax.set_ylabel("Signal")
            ax.legend()
            st.pyplot(fig)
            plt.close(fig)
            st.success(f"Equation: y = {slope:.4f}x + {intercept:.4f}    R² = {r2:.4f}")
            # unknown calculation instantly when user changes unknown inputs:
            unknown_type = st.selectbox("Unknown type / Type d'inconnu:", ["Unknown concentration / Concentration inconnue", "Unknown signal / Signal inconnu"], key="lin_unknown_type")
            unknown_value = st.number_input("Unknown value / Valeur inconnue:", value=0.0, step=0.1, key="lin_unknown_value")
            if slope != 0:
                if unknown_type.startswith("Unknown concentration"):
                    res = (unknown_value - intercept) / slope
                    st.info(f"🔹 Concentration = {res:.4f} {unit}")
                else:
                    res = slope * unknown_value + intercept
                    st.info(f"🔹 Signal = {res:.4f}")
            # export pdf
            company_name = st.text_input("Company name for PDF / Nom de la compagnie pour le PDF:", key="lin_company")
            def export_linearity_pdf():
                if not company_name:
                    st.warning("Please enter company name before exporting / Veuillez saisir le nom de la compagnie avant d'exporter.")
                    return
                # re-create figure to embed
                fig2, ax2 = plt.subplots()
                ax2.scatter(conc, resp)
                ax2.plot(xs, slope*xs+intercept)
                ax2.set_xlabel(f"Concentration ({unit})")
                ax2.set_ylabel("Signal")
                ax2.set_title("Linearity")
                buf = io.BytesIO()
                fig2.savefig(buf, format="png", bbox_inches="tight")
                img_bytes = buf.getvalue()
                buf.close()
                plt.close(fig2)
                # content lines
                lines = [
                    "Linearity report / Rapport de linéarité",
                    f"Equation: y = {slope:.4f}x + {intercept:.4f}",
                    f"R² = {r2:.4f}",
                    f"Unit for concentration: {unit}",
                ]
                filename = generate_pdf("Linearity_Report", lines, img_bytes=img_bytes, company=company_name, username=st.session_state.username)
                st.success("PDF generated")
                offer_download(filename)
            st.button("Export PDF / Exporter PDF", on_click=export_linearity_pdf)
        except Exception as e:
            st.error(f"Error in calculations / Erreur: {e}")
    st.button("Back / Retour", on_click=lambda: st.session_state.update(current_page="menu") or st.rerun())

# ---------- Signal to Noise ----------
def page_sn():
    st.header("📊 Signal / Noise (S/N)")
    st.write(f"You are logged in as **{st.session_state.username}**")
    company_name = st.text_input("Company name for PDF / Nom de la compagnie pour le PDF:", key="sn_company")
    uploaded = st.file_uploader("Upload chromatogram CSV with 'Time' and 'Signal' columns / Téléverser CSV (Time & Signal)", type=["csv"], key="sn_upload")
    slope = st.session_state.linearity_data.get("slope")
    unit = st.session_state.linearity_data.get("unit", "")
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            # normalize columns
            cols_map = {c.lower().strip(): c for c in df.columns}
            if "time" not in cols_map or "signal" not in cols_map:
                st.error("CSV must contain 'Time' and 'Signal' columns / CSV doit contenir 'Time' et 'Signal'")
            else:
                tcol = cols_map["time"]
                scol = cols_map["signal"]
                df = df[[tcol, scol]].rename(columns={tcol: "time", scol: "signal"})
                df["time"] = pd.to_numeric(df["time"], errors="coerce")
                df["signal"] = pd.to_numeric(df["signal"], errors="coerce")
                df = df.dropna()
                st.line_chart(df.rename(columns={"time":"index"}).set_index("time"))
                # Let user select baseline region by slider (indices)
                n = len(df)
                st.write("Select noise baseline region (by index slice) / Sélectionner la région de bruit (par indices):")
                start = st.number_input("Start index", min_value=0, max_value=max(0,n-1), value=0, step=1, key="noise_start")
                end = st.number_input("End index", min_value=0, max_value=max(0,n-1), value=max(0,int(n*0.1)), step=1, key="noise_end")
                start, end = int(start), int(end)
                if start >= end:
                    st.warning("Choose start < end / Choisir start < end")
                else:
                    baseline = df.iloc[start:end]
                    noise_std = baseline["signal"].std()
                    peak = df["signal"].max()
                    if noise_std == 0 or np.isnan(noise_std):
                        st.warning("Noise std is zero or invalid; check baseline selection / Le std du bruit est nul ou invalide")
                    else:
                        sn_classic = peak / noise_std
                        # USP style: use baseline noise (same as above) as USP noise
                        sn_usp = peak / noise_std
                        lod = 3 * noise_std
                        loq = 10 * noise_std
                        st.success(f"S/N (classic) = {sn_classic:.2f}")
                        st.info(f"USP S/N = {sn_usp:.2f} (baseline noise std = {noise_std:.4f})")
                        st.info(f"LOD (signal units) = {lod:.4f}, LOQ (signal units) = {loq:.4f}")
                        # convert to concentration if slope available
                        if slope:
                            try:
                                lod_conc = lod / slope
                                loq_conc = loq / slope
                                st.info(f"LOD in concentration = {lod_conc:.4f} {unit}")
                                st.info(f"LOQ in concentration = {loq_conc:.4f} {unit}")
                            except Exception:
                                st.warning("Cannot convert to concentration (slope invalid). / Impossible de convertir en concentration.")
                        # export PDF with plot
                        def export_sn_pdf():
                            if not company_name:
                                st.warning("Please enter company name before exporting / Veuillez saisir le nom de la compagnie avant d'exporter.")
                                return
                            # build plot image
                            fig, ax = plt.subplots()
                            ax.plot(df["time"], df["signal"], label="Signal")
                            ax.axvspan(df["time"].iloc[start], df["time"].iloc[end-1], color='orange', alpha=0.3, label="Baseline region")
                            ax.set_xlabel("Time")
                            ax.set_ylabel("Signal")
                            ax.legend()
                            buf = io.BytesIO()
                            fig.savefig(buf, format="png", bbox_inches="tight")
                            img_bytes = buf.getvalue()
                            buf.close()
                            plt.close(fig)
                            lines = [
                                "S/N report / Rapport S/N",
                                f"Peak (signal): {peak}",
                                f"Noise std (baseline): {noise_std:.4f}",
                                f"S/N (classic): {sn_classic:.2f}",
                                f"USP S/N: {sn_usp:.2f}",
                                f"LOD (signal units): {lod:.4f}",
                                f"LOQ (signal units): {loq:.4f}",
                            ]
                            if slope:
                                try:
                                    lines.append(f"LOD in concentration: {lod_conc:.4f} {unit}")
                                    lines.append(f"LOQ in concentration: {loq_conc:.4f} {unit}")
                                except Exception:
                                    pass
                            filename = generate_pdf("SN_Report", lines, img_bytes=img_bytes, company=company_name, username=st.session_state.username)
                            st.success("PDF generated")
                            offer_download(filename)
                        st.button("Export PDF / Exporter PDF", on_click=export_sn_pdf)
        except Exception as e:
            st.error(f"CSV read error / Erreur lecture CSV: {e}")
    st.button("Back / Retour", on_click=lambda: st.session_state.update(current_page="menu") or st.rerun())

# ---------- Main menu ----------
def page_menu():
    st.title("🧪 LabT - Main menu / Menu principal")
    st.write(f"Logged in as **{st.session_state.username}**")
    if st.session_state.role == "admin":
        st.button("Manage users / Gérer les utilisateurs", on_click=lambda: st.session_state.update(current_page="manage_users") or st.rerun())
    else:
        st.button("Linearity / Linéarité", on_click=lambda: st.session_state.update(current_page="linearity") or st.rerun())
        st.button("Signal/Noise (S/N)", on_click=lambda: st.session_state.update(current_page="sn") or st.rerun())
        st.button("Change password / Modifier mot de passe", on_click=lambda: st.session_state.update(current_page="change_password") or st.rerun())
    st.button("Logout / Déconnexion", on_click=do_logout)

# ---------------------
# Router
# ---------------------
def main():
    if not st.session_state.logged_in:
        page_login()
    else:
        # show basic top navbar of current user and quick actions
        if st.session_state.current_page is None:
            st.session_state.current_page = "menu"
        pg = st.session_state.current_page
        if pg == "menu":
            page_menu()
        elif pg == "manage_users":
            # admin only
            if st.session_state.role == "admin":
                admin_manage_users_page()
            else:
                st.error("Access denied")
        elif pg == "linearity":
            page_linearity()
        elif pg == "sn":
            page_sn()
        elif pg == "change_password":
            user_change_password_page()
        else:
            page_menu()

if __name__ == "__main__":
    main()