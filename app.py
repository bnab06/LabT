# -----------------------
# PART 1: Authentification, users, session init, textes, utilitaires
# -----------------------
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression
from fpdf import FPDF

# Users file (we'll use the users.json you provided)
USER_FILE = "users.json"
if not os.path.exists(USER_FILE):
    # create a safe default to avoid crashes
    with open(USER_FILE, "w") as f:
        json.dump({
            "admin": {"password": "admin", "role": "admin"},
            "user": {"password": "user", "role": "user"},
            "guest": {"password": "guest", "role": "user"}
        }, f, indent=2)

with open(USER_FILE, "r") as f:
    users = json.load(f)

def save_users(u):
    with open(USER_FILE, "w") as f:
        json.dump(u, f, indent=2)

# session defaults
_defaults = {
    "logged_in": False,
    "user": "",
    "role": None,
    "access": None,
    "lin_slope": None,
    "lin_intercept": None,
    "sn_result": {},
    "sn_img_annot": None,
    "lang": "FR",
    "show_pass_change": False,
    # admin helper
    "admin_change_pw_for": None
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# bilingual texts
TEXTS = {
    "FR": {
        "app_title": "🔬 LabT — Connexion",
        "username": "Nom d'utilisateur",
        "password": "Mot de passe",
        "login_btn": "Connexion",
        "login_error": "Nom d'utilisateur ou mot de passe incorrect.",
        "powered_by": "Powered by : BnB",
        "linear_title": "📈 Linéarité",
        "sn_title": "📊 Rapport Signal/Bruit (S/N)",
        "download_pdf": "📄 Télécharger le PDF complet",
        "change_pass": "Changer le mot de passe",
        "new_pass": "Nouveau mot de passe",
        "save_pass": "Enregistrer",
        "admin_users": "Admin — Gestion des utilisateurs",
        "select_user": "Sélectionner un utilisateur",
        "add_user": "Ajouter utilisateur",
        "del_user": "Supprimer utilisateur",
        "update_priv": "Mettre à jour privilèges",
        "manual_lin_btn": "Calculer Linéarité",
        "manual_sn_btn": "Calculer S/N manuel",
        "unit_label": "Unité de concentration",
        "enter_slope_manual": "Saisir pente manuelle (optionnel)",
        "logout": "Déconnexion / Logout"
    },
    "EN": {
        "app_title": "🔬 LabT — Login",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "login_error": "Incorrect username or password.",
        "powered_by": "Powered by : BnB",
        "linear_title": "📈 Linearity",
        "sn_title": "📊 Signal-to-Noise (S/N)",
        "download_pdf": "📄 Download full PDF",
        "change_pass": "Change Password",
        "new_pass": "New Password",
        "save_pass": "Save",
        "admin_users": "Admin — User management",
        "select_user": "Select a user",
        "add_user": "Add user",
        "del_user": "Delete user",
        "update_priv": "Update privileges",
        "manual_lin_btn": "Compute Linearity",
        "manual_sn_btn": "Compute manual S/N",
        "unit_label": "Concentration unit",
        "enter_slope_manual": "Enter manual slope (optional)",
        "logout": "Logout"
    }
}

# helpers
def user_access_from_record(rec):
    """Return access list given a user record (compatibility for role or explicit access)."""
    if not isinstance(rec, dict):
        return []
    if rec.get("role") == "admin":
        return ["admin"]
    if "access" in rec:
        return rec.get("access", [])
    return ["linearity", "sn"]

def calculate_lod_loq_from_noise(slope, noise):
    lod_signal = 3.3 * noise
    loq_signal = 10.0 * noise
    if slope and slope != 0:
        lod_conc = lod_signal / slope
        loq_conc = loq_signal / slope
    else:
        lod_conc = None
        loq_conc = None
    return lod_signal, loq_signal, lod_conc, loq_conc

def annotate_peak_on_image(img_pil, x_pixel, y_pixel, text):
    draw = ImageDraw.Draw(img_pil)
    r = 6
    draw.ellipse((x_pixel-r, y_pixel-r, x_pixel+r, y_pixel+r), fill="red")
    try:
        font = ImageFont.load_default()
        draw.text((x_pixel+8, max(0, y_pixel-12)), text, fill="red", font=font)
    except Exception:
        draw.text((x_pixel+8, max(0, y_pixel-12)), text, fill="red")
    return img_pil

# login page
def login_page():
    texts = TEXTS[st.session_state.lang]
    st.title(texts["app_title"])
    chosen = st.selectbox("Lang / Language", ["FR", "EN"], index=0 if st.session_state.lang=="FR" else 1)
    st.session_state.lang = chosen
    texts = TEXTS[st.session_state.lang]

    username = st.text_input(texts["username"])
    password = st.text_input(texts["password"], type="password")
    if st.button(texts["login_btn"]):
        u = username.strip()
        if u in users and users[u].get("password") == password:
            st.session_state.logged_in = True
            st.session_state.user = u
            rec = users[u]
            st.session_state.role = rec.get("role", "user")
            st.session_state.access = user_access_from_record(rec)
            st.rerun()
        else:
            st.error(texts["login_error"])

    st.markdown(f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;'>{texts['powered_by']}</div>", unsafe_allow_html=True)
# -----------------------
# PART 2: Linéarité (CSV or manual inputs)
# -----------------------
def linearity_module():
    texts = TEXTS[st.session_state.lang]
    st.subheader(texts["linear_title"])

    mode = st.selectbox("Mode Linéarité", ["CSV", "Saisie manuelle"], key="lin_mode")
    if mode == "CSV":
        uploaded = st.file_uploader("Upload CSV (concentration, signal)", type=["csv"], key="lin_csv")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                if df.shape[1] < 2:
                    st.error("Le CSV doit contenir au moins deux colonnes (concentration, signal).")
                else:
                    x = df.iloc[:,0].astype(float).values.reshape(-1,1)
                    y = df.iloc[:,1].astype(float).values
                    reg = LinearRegression().fit(x,y)
                    slope = float(reg.coef_[0])
                    intercept = float(reg.intercept_)
                    st.session_state.lin_slope = slope
                    st.session_state.lin_intercept = intercept
                    st.success(f"Slope: {slope:.6g}  Intercept: {intercept:.6g}")
                    st.dataframe(df)
            except Exception as e:
                st.error(f"Erreur CSV: {e}")
    else:
        conc_input = st.text_input("Concentrations (séparées par des virgules)", key="lin_manual_conc")
        sig_input = st.text_input("Signal (séparés par des virgules)", key="lin_manual_sig")
        if st.button(TEXTS[st.session_state.lang]["manual_lin_btn"], key="lin_manual_btn"):
            try:
                concs = [float(v.strip()) for v in conc_input.split(",") if v.strip()]
                sigs = [float(v.strip()) for v in sig_input.split(",") if v.strip()]
                if len(concs) != len(sigs) or len(concs) < 2:
                    st.error("Nombres invalides ou insuffisants")
                else:
                    x = np.array(concs).reshape(-1,1)
                    y = np.array(sigs)
                    reg = LinearRegression().fit(x,y)
                    slope = float(reg.coef_[0])
                    intercept = float(reg.intercept_)
                    st.session_state.lin_slope = slope
                    st.session_state.lin_intercept = intercept
                    st.success(f"Slope: {slope:.6g}  Intercept: {intercept:.6g}")
                    st.dataframe(pd.DataFrame({"concentration": concs, "signal": sigs}))
            except Exception as e:
                st.error("Erreur saisie manuelle")
# -----------------------
# PART 3: S/N module (image analysis + manual S/N)
# -----------------------
def sn_module():
    texts = TEXTS[st.session_state.lang]
    st.subheader(texts["sn_title"])

    unit = st.selectbox(TEXTS[st.session_state.lang]["unit_label"], ["µg/mL","mg/mL","ng/mL"], index=0, key="sn_unit")
    manual_slope = st.text_input(TEXTS[st.session_state.lang]["enter_slope_manual"], placeholder="laisser vide si non", key="manual_slope")

    st.markdown("**S/N depuis image**")
    uploaded_img = st.file_uploader("Upload chromatogram image (png/jpg/tif)", type=["png","jpg","jpeg","tif"], key="sn_img")
    if uploaded_img:
        try:
            img = Image.open(uploaded_img).convert("RGB")
            img_gray = img.convert("L")
            arr = np.array(img_gray)
            trace = arr.max(axis=0).astype(float)
            width = trace.shape[0]

            col1, col2 = st.columns(2)
            with col1:
                start = st.number_input("Start pixel", 0, width-1, 0, key="sn_start")
            with col2:
                end = st.number_input("End pixel", 0, width-1, width-1, key="sn_end")
            if start >= end:
                st.warning("Start doit être < End")
            else:
                zone = trace[start:end+1]
                peaks, _ = find_peaks(zone)
                if len(peaks) == 0:
                    st.info("Aucun pic détecté dans la zone. Ajuster la zone.")
                else:
                    idx_rel = peaks[np.argmax(zone[peaks])]
                    idx_global = start + int(idx_rel)
                    H = float(zone[int(idx_rel)])
                    left = max(0, int(idx_rel) - 3)
                    right = min(len(zone) - 1, int(idx_rel) + 3)
                    baseline = np.concatenate([zone[:left], zone[right+1:]]) if (left > 0 or right < len(zone)-1) else np.array([])
                    noise = float(np.std(baseline)) if baseline.size > 0 else float(np.std(zone))
                    sn_value = H / noise if noise > 0 else None

                    # optional time mapping
                    st.markdown("**Échelle temporelle (optionnel)**")
                    t0 = st.number_input("Image start time (minutes)", value=0.0, format="%.6f", key="sn_t0")
                    t1 = st.number_input("Image end time (minutes)", value=0.0, format="%.6f", key="sn_t1")
                    if (t1 > t0) and (width > 1):
                        rt_minutes = t0 + (idx_global / (width - 1)) * (t1 - t0)
                        rt_text = f"{rt_minutes:.3f} min"
                    else:
                        rt_text = f"{idx_global} px"

                    # annotate and show
                    img_annot = img.copy()
                    annotate_peak_on_image(img_annot, idx_global, 10, rt_text)
                    st.image(img_annot, caption="Image annotée (pic en rouge)")
                    st.session_state.sn_img_annot = img_annot

                    # choose slope (manual override or stored)
                    try:
                        slope_use = float(manual_slope) if (manual_slope is not None and manual_slope.strip() != "") else st.session_state.lin_slope
                    except:
                        slope_use = None

                    lod_s = loq_s = lod_c = loq_c = None
                    if noise is not None:
                        if slope_use is not None:
                            lod_s, loq_s, lod_c, loq_c = calculate_lod_loq_from_noise(slope_use, noise)
                        else:
                            lod_s, loq_s = 3.3*noise, 10*noise
                            lod_c, loq_c = None, None

                    st.session_state.sn_result = {
                        "signal": H,
                        "noise": noise,
                        "sn": sn_value,
                        "lod_s": lod_s,
                        "loq_s": loq_s,
                        "lod_c": lod_c,
                        "loq_c": loq_c,
                        "rt_text": rt_text,
                        "unit": unit
                    }

                    st.write(f"H (signal) = {H:.6g}")
                    st.write(f"h (noise) = {noise:.6g}")
                    if sn_value is not None:
                        st.write(f"S/N = {sn_value:.3f}")
                    else:
                        st.write("S/N indéterminé (bruit nul)")
                    if lod_s is not None:
                        st.write(f"LOD signal = {lod_s:.6g} ; LOQ signal = {loq_s:.6g}")
                    if lod_c is not None:
                        st.write(f"LOD concentration = {lod_c:.6g} {unit} ; LOQ concentration = {loq_c:.6g} {unit}")
        except Exception as e:
            st.error(f"Erreur lors du traitement de l'image: {e}")

    # --- Manual S/N (button-driven) ---
    st.markdown("---")
    st.subheader("Calcul manuel S/N")
    H_in = st.number_input("Entrer H (hauteur pic)", value=0.0, format="%.6f", key="manual_H")
    h_in = st.number_input("Entrer h (bruit)", value=0.0, format="%.6f", key="manual_h")
    if st.button(TEXTS[st.session_state.lang]["manual_sn_btn"], key="manual_sn_compute"):
        if h_in > 0:
            sn_manual = float(H_in) / float(h_in)
            try:
                slope_use2 = float(manual_slope) if (manual_slope is not None and manual_slope.strip() != "") else st.session_state.lin_slope
            except:
                slope_use2 = None
            lod_s_man = 3.3 * h_in
            loq_s_man = 10.0 * h_in
            lod_c_man = lod_s_man / slope_use2 if slope_use2 else None
            loq_c_man = loq_s_man / slope_use2 if slope_use2 else None
            st.success(f"S/N manuel = {sn_manual:.3f}")
            st.write(f"LOD_signal = {lod_s_man:.6g}; LOQ_signal = {loq_s_man:.6g}")
            if lod_c_man is not None:
                st.write(f"LOD_conc = {lod_c_man:.6g} {unit}; LOQ_conc = {loq_c_man:.6g} {unit}")
        else:
            st.error("h doit être > 0 pour calculer S/N")
# -----------------------
# PART 4: PDF generation, admin panel, main_app, run
# -----------------------
def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "LabT Report", ln=True, align="C")

    # Linearity section
    pdf.set_font("Arial", "", 12)
    slope = st.session_state.lin_slope
    intercept = st.session_state.lin_intercept
    if slope is not None:
        pdf.cell(0, 8, f"Slope: {slope:.6g}   Intercept: {intercept:.6g}", ln=True)
    else:
        pdf.cell(0, 8, "Slope: N/A", ln=True)

    # S/N results
    snr = st.session_state.sn_result
    if snr:
        pdf.cell(0, 8, f"S/N: {snr.get('sn','N/A')}", ln=True)
        pdf.cell(0, 8, f"Signal H: {snr.get('signal','N/A')}", ln=True)
        pdf.cell(0, 8, f"Noise h: {snr.get('noise','N/A')}", ln=True)
        if snr.get("lod_s") is not None:
            pdf.cell(0, 8, f"LOD signal: {snr.get('lod_s'):.6g}", ln=True)
            pdf.cell(0, 8, f"LOQ signal: {snr.get('loq_s'):.6g}", ln=True)
        if snr.get("lod_c") is not None:
            pdf.cell(0, 8, f"LOD conc: {snr.get('lod_c'):.6g} {snr.get('unit')}", ln=True)
            pdf.cell(0, 8, f"LOQ conc: {snr.get('loq_c'):.6g} {snr.get('unit')}", ln=True)
        if snr.get("rt_text"):
            pdf.cell(0, 8, f"Retention: {snr.get('rt_text')}", ln=True)

    # annotated image
    if st.session_state.sn_img_annot is not None:
        buf = io.BytesIO()
        try:
            st.session_state.sn_img_annot.save(buf, format="PNG")
            buf.seek(0)
            try:
                pdf.image(buf, x=10, w=180)
            except Exception:
                tmpname = f"tmp_img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                with open(tmpname, "wb") as f:
                    f.write(buf.getbuffer())
                pdf.image(tmpname, x=10, w=180)
                os.remove(tmpname)
        except Exception:
            pass

    out_bytes = pdf.output(dest="S").encode("latin1")
    st.download_button(TEXTS[st.session_state.lang]["download_pdf"], data=out_bytes,
                       file_name=f"LabT_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                       mime="application/pdf")

# Admin panel (no JSON table shown)
def admin_panel():
    texts = TEXTS[st.session_state.lang]
    st.subheader(texts["admin_users"])

    user_list = sorted(list(users.keys()))
    selected_user = st.selectbox(texts["select_user"], user_list, key="admin_selected_user")

    # show role derived from record
    rec = users.get(selected_user, {})
    current_role = rec.get("role", "user")
    st.write("Rôle actuel:", current_role)

    # change password for selected (discreet)
    if st.button("Modifier mot de passe sélectionné", key="admin_show_pw"):
        st.session_state.admin_change_pw_for = selected_user
    if st.session_state.get("admin_change_pw_for") == selected_user:
        newpw = st.text_input(f"Nouveau mot de passe pour {selected_user}", type="password", key="admin_newpw")
        if st.button("Enregistrer mot de passe", key="admin_savepw"):
            if newpw:
                users[selected_user]["password"] = newpw
                save_users(users)
                st.success(f"Mot de passe de {selected_user} mis à jour.")
                del st.session_state["admin_change_pw_for"]
            else:
                st.error("Mot de passe vide.")

    # Add user
    with st.expander("Ajouter un nouvel utilisateur"):
        new_user = st.text_input("Nom nouvel utilisateur", key="admin_add_user")
        new_pass = st.text_input("Mot de passe", type="password", key="admin_add_pass")
        if st.button("Ajouter", key="admin_add_btn"):
            if not new_user:
                st.error("Nom utilisateur requis.")
            elif new_user in users:
                st.error("Utilisateur existe déjà.")
            else:
                users[new_user] = {"password": new_pass, "access": []}
                save_users(users)
                st.success(f"Utilisateur {new_user} ajouté.")
                st.experimental_rerun()

    # Privileges multiselect (safe default values)
    all_privs = ["linearity", "sn"]
    raw_current = users[selected_user].get("access", [])
    current_privs = [p for p in raw_current if p in all_privs]
    new_privs = st.multiselect("Modifier privilèges (cocher pour donner accès)", options=all_privs, default=current_privs, key="admin_privs_safe")
    if st.button("Mettre à jour privilèges", key="admin_update_priv"):
        users[selected_user]["access"] = new_privs
        save_users(users)
        st.success(f"Privilèges de {selected_user} mis à jour.")
        st.experimental_rerun()

    # delete (except admin)
    if selected_user != "admin":
        if st.button(f"Supprimer {selected_user}", key="admin_del"):
            del users[selected_user]
            save_users(users)
            st.success(f"Utilisateur {selected_user} supprimé.")
            st.experimental_rerun()

# Change own password (discreet deploy) for normal users
def change_password_widget():
    texts = TEXTS[st.session_state.lang]
    if st.button(texts["change_pass"], key="show_change_pass_btn"):
        st.session_state.show_pass_change = True
    if st.session_state.show_pass_change:
        newpw = st.text_input(texts["new_pass"], type="password", key="user_newpw")
        if st.button(texts["save_pass"], key="save_user_pw"):
            if newpw:
                users[st.session_state.user]["password"] = newpw
                save_users(users)
                st.success("Mot de passe mis à jour." if st.session_state.lang == "FR" else "Password updated.")
                st.session_state.show_pass_change = False
            else:
                st.error("Entrer un mot de passe valide.")

# Main app
def main_app():
    texts = TEXTS[st.session_state.lang]

    # determine role (explicit 'role' field preferred)
    rec = users.get(st.session_state.user, {})
    role = rec.get("role", None)
    if role is None:
        role = "admin" if "admin" in rec.get("access", []) else "user"

    if role == "admin":
        admin_panel()
        if st.button(texts["logout"]):
            lang_keep = st.session_state.lang
            for k in list(st.session_state.keys()):
                if k not in ["lang"]:
                    del st.session_state[k]
            st.session_state.lang = lang_keep
            st.rerun()
        return

    # normal user
    change_password_widget()

    access_list = users.get(st.session_state.user, {}).get("access", st.session_state.get("access", [])) or []
    if isinstance(access_list, str):
        access_list = [access_list]

    if "linearity" in access_list:
        linearity_module()

    if "sn" in access_list:
        sn_module()

    if st.button(texts["download_pdf"]):
        generate_pdf()

    if st.button(texts["logout"]):
        lang_keep = st.session_state.lang
        for k in list(st.session_state.keys()):
            if k not in ["lang"]:
                del st.session_state[k]
        st.session_state.lang = lang_keep
        st.rerun()

def run():
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    run()