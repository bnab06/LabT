# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime
from PIL import Image
from pdf2image import convert_from_bytes
import cv2
import matplotlib.pyplot as plt
import os
import re

# ===============================
#        TRADUCTIONS BILINGUE
# ===============================
TRANSLATIONS = {
    "FR": {
        "Language / Langue": "Langue",
        "Connexion": "Connexion",
        "Utilisateur": "Utilisateur",
        "Mot de passe": "Mot de passe",
        "Connexion réussie !": "Connexion réussie !",
        "Identifiants invalides.": "Identifiants invalides.",
        "Bienvenue dans LabT": "Bienvenue dans LabT",
        "Choisissez un module ci-dessus.": "Choisissez un module ci-dessus.",
        "Déconnecté": "Déconnecté",
        "Signal plat ou OCR invalide": "Signal plat ou OCR invalide",
        "Importer une image ou un PDF du chromatogramme": "Importer une image ou un PDF du chromatogramme",
        "Temps de rétention": "Temps de rétention",
        "S/N Classique": "S/N Classique",
        "S/N USP": "S/N USP",
        "Importer un fichier CSV": "Importer un fichier CSV",
        "Message ou commentaire": "Message ou commentaire",
        "Entrer signal inconnu": "Entrer signal inconnu",
        "Entrer concentration inconnue": "Entrer concentration inconnue",
        "LOD": "LOD",
        "LOQ": "LOQ",
        "Saisir pente manuellement si non disponible": "Saisir pente manuellement si non disponible",
        "Unités concentration": "Unités de concentration",
        "Changer mot de passe": "Changer mot de passe",
        "Ancien mot de passe": "Ancien mot de passe",
        "Nouveau mot de passe": "Nouveau mot de passe",
        "Confirmer mot de passe": "Confirmer le mot de passe",
        "Mot de passe modifié": "Mot de passe modifié avec succès",
        "Erreur mot de passe": "Ancien mot de passe incorrect ou confirmation différente",
        "Afficher les formules": "Afficher les formules",
        "Formules SN": "Formules S/N :\nS/N classique = H / h\nS/N (USP) = 2 H / h\noù H = hauteur du pic, h = bruit (écart-type).",
        "Formules LOD LOQ": "Formules LOD/LOQ :\nLOD(signal) = 3 * h\nLOQ(signal) = 10 * h\nLOD(conc) = LOD(signal) / slope\nLOQ(conc) = LOQ(signal) / slope"
    },
    "EN": {
        "Language / Langue": "Language",
        "Connexion": "Login",
        "Utilisateur": "User",
        "Mot de passe": "Password",
        "Connexion réussie !": "Login successful!",
        "Identifiants invalides.": "Invalid credentials.",
        "Bienvenue dans LabT": "Welcome to LabT",
        "Choisissez un module ci-dessus.": "Choose a module above.",
        "Déconnecté": "Logged out",
        "Signal plat ou OCR invalide": "Flat signal or invalid OCR",
        "Importer une image ou un PDF du chromatogramme": "Upload image or PDF of chromatogram",
        "Temps de rétention": "Retention time",
        "S/N Classique": "Classic S/N",
        "S/N USP": "USP S/N",
        "Importer un fichier CSV": "Upload CSV file",
        "Message ou commentaire": "Message or comment",
        "Entrer signal inconnu": "Enter unknown signal",
        "Entrer concentration inconnue": "Enter unknown concentration",
        "LOD": "LOD",
        "LOQ": "LOQ",
        "Saisir pente manuellement si non disponible": "Enter slope manually if not available",
        "Unités concentration": "Concentration units",
        "Changer mot de passe": "Change password",
        "Ancien mot de passe": "Old password",
        "Nouveau mot de passe": "New password",
        "Confirmer mot de passe": "Confirm password",
        "Mot de passe modifié": "Password changed successfully",
        "Erreur mot de passe": "Old password incorrect or confirmation mismatch",
        "Afficher les formules": "Show formulas",
        "Formules SN": "S/N formulas:\nClassic S/N = H / h\nUSP S/N = 2 H / h\nwhere H = peak height, h = noise (std).",
        "Formules LOD LOQ": "LOD/LOQ formulas:\nLOD(signal) = 3 * h\nLOQ(signal) = 10 * h\nLOD(conc) = LOD(signal) / slope\nLOQ(conc) = LOQ(signal) / slope"
    }
}

# ===============================
# LANGUE PAR DÉFAUT (définie avant t())
# ===============================
LANG = "FR"
def t(txt, lang=None):
    if lang is None:
        lang = LANG
    return TRANSLATIONS.get(lang, {}).get(txt, txt)

# ===============================
# USERS FILE (création auto si absent)
# ===============================
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    users = {
        "admin":{"password":"admin","role":"admin","access":["linearity","sn"]},
        "user":{"password":"user","role":"user","access":["linearity","sn"]}
    }
    with open(USERS_FILE,"w") as f:
        json.dump(users,f,indent=4)

def load_users():
    with open(USERS_FILE,"r") as f: return json.load(f)
def save_users(users):
    with open(USERS_FILE,"w") as f: json.dump(users,f,indent=4)

# ===============================
# PDF → IMAGE util
# ===============================
def pdf_to_png_bytes(uploaded_file):
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1, dpi=300)
        if pages: return pages[0].convert("RGB"), None
    except Exception:
        try:
            import fitz
            uploaded_file.seek(0)
            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if doc.page_count < 1:
                return None, "PDF vide."
            page = doc.load_page(0)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            return img, None
        except Exception as e_fitz:
            return None, f"Erreur conversion PDF : {e_fitz}"

# ===============================
# LOGIN / AUTH
# ===============================
def login_page():
    st.title(t("Connexion"))
    users = load_users()
    username = st.selectbox(t("Utilisateur"), list(users.keys()))
    password = st.text_input(t("Mot de passe"), type="password")
    if st.button(t("Connexion")):
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = users[username].get("role", "user")
            st.session_state["access"] = users[username].get("access", [])
            st.session_state.setdefault("slope", None)
            st.success(t("Connexion réussie !"))
            st.session_state["page"] = "menu"
            st.rerun()
        else:
            st.error(t("Identifiants invalides."))

# ===============================
# Change password (accessible to all logged users)
# ===============================
def change_password_panel():
    st.subheader(t("Changer mot de passe"))
    users = load_users()
    user = st.session_state.get("user")
    if not user:
        st.warning("Not logged in")
        return
    old = st.text_input(t("Ancien mot de passe"), type="password")
    new = st.text_input(t("Nouveau mot de passe"), type="password")
    confirm = st.text_input(t("Confirmer mot de passe"), type="password")
    if st.button(t("Changer mot de passe")):
        if users.get(user) and users[user]["password"] == old and new and new == confirm:
            users[user]["password"] = new
            save_users(users)
            st.success(t("Mot de passe modifié"))
        else:
            st.error(t("Erreur mot de passe"))

# ===============================
# ADMIN panel (intact except safe gets)
# ===============================
def admin_panel():
    st.subheader("👤 Gestion des utilisateurs")
    users = load_users()
    action = st.selectbox("Action", ["Ajouter utilisateur", "Modifier privilèges", "Supprimer utilisateur"])
    if action == "Ajouter utilisateur":
        new_user = st.text_input("Nom d'utilisateur")
        new_pass = st.text_input("Mot de passe")
        privileges = st.multiselect("Modules", ["linearity", "sn"])
        if st.button("Créer"):
            if new_user and new_pass:
                users[new_user] = {"password": new_pass, "role": "user", "access": privileges}
                save_users(users)
                st.success(f"Utilisateur '{new_user}' ajouté.")
            else:
                st.error("Remplir tous les champs.")
    elif action == "Modifier privilèges":
        user_to_edit = st.selectbox("Utilisateur", [u for u in users if users[u].get("role") != "admin"])
        if user_to_edit:
            new_priv = st.multiselect("Modules", ["linearity", "sn"], default=users.get(user_to_edit, {}).get("access", []))
            if st.button("Sauvegarder"):
                users[user_to_edit]["access"] = new_priv
                save_users(users)
                st.success("Modifications enregistrées.")
    elif action == "Supprimer utilisateur":
        user_to_del = st.selectbox("Utilisateur à supprimer", [u for u in users if users[u].get("role") != "admin"])
        if st.button("Supprimer"):
            users.pop(user_to_del, None)
            save_users(users)
            st.warning(f"Utilisateur {user_to_del} supprimé.")
    if st.button("⬅️ Retour au menu principal"):
        st.session_state["page"] = "menu"
        st.rerun()

# ===============================
# S/N helpers: analyze image profile (keeps last result in session)
# ===============================
def analyze_sn_from_image(image, start=None, end=None):
    """Compute profile, return metrics and arrays for plotting."""
    try:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    except Exception:
        return None, t("Signal plat ou OCR invalide")
    profile = np.mean(gray, axis=0)
    x = np.arange(len(profile))
    if start is None: start = 0
    if end is None or end > len(profile): end = len(profile)
    if start >= end:
        return None, "Zone invalide"
    y_zone = profile[start:end]
    x_zone = x[start:end]
    peak_idx_rel = int(np.argmax(y_zone))
    peak_height = float(y_zone[peak_idx_rel])
    baseline = float(np.median(y_zone))
    noise = float(np.std(y_zone[:max(1, len(y_zone)//10)]))
    sn_classic = (peak_height - baseline) / (noise if noise != 0 else 1)
    sn_usp = sn_classic / np.sqrt(2)
    peak_retention_pixel = x_zone[peak_idx_rel]
    return {
        "profile": profile,
        "x_zone": x_zone,
        "y_zone": y_zone,
        "S/N Classique": sn_classic,
        "S/N USP": sn_usp,
        "noise": noise,
        "peak_height": peak_height,
        "peak_retention_pixel": peak_retention_pixel
    }, None

# ===============================
# compute LOD/LOQ given h (uses user formula LOD=3*h; LOQ=10*h)
# returns signal and conc if slope provided
# ===============================
def compute_lod_loq_from_h(h, slope=None):
    lod_signal = 3.0 * h
    loq_signal = 10.0 * h
    lod_conc = None
    loq_conc = None
    if slope and slope != 0:
        lod_conc = lod_signal / slope
        loq_conc = loq_signal / slope
    return lod_signal, loq_signal, lod_conc, loq_conc

# ===============================
# LINEARITY MODULE (manual comma-separated + CSV, exports slope)
# ===============================
CONCENTRATION_UNITS = ["mg/mL", "µg/mL", "ng/mL", "ppm", "mol/L"]

def linearity_module():
    st.title(t("Analyse de linéarité"))
    col_csv, col_manual = st.columns(2)
    slope_export = None

    # Option: CSV
    with col_csv:
        st.subheader("CSV")
        uploaded_file = st.file_uploader(t("Importer un fichier CSV"), type=["csv"], key="lin_csv")
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df)
                if "Concentration" in df.columns and "Réponse" in df.columns:
                    x = df["Concentration"].to_numpy(dtype=float)
                    y = df["Réponse"].to_numpy(dtype=float)
                else:
                    st.error("CSV must contain 'Concentration' and 'Réponse' columns.")
                    x = np.array([])
                    y = np.array([])
            except Exception as e:
                st.error(f"Erreur lecture CSV: {e}")
                x = np.array([])
                y = np.array([])
        else:
            x = np.array([])
            y = np.array([])

    # Manual comma-separated input
    with col_manual:
        st.subheader("Saisie manuelle (virgules)")
        conc_text = st.text_area("Concentrations (séparées par des virgules)", value="", key="lin_conc_text")
        sig_text = st.text_area("Signaux (séparés par des virgules)", value="", key="lin_sig_text")
        unit = st.selectbox(t("Unités concentration"), CONCENTRATION_UNITS, key="lin_unit")
        conc_list = []
        sig_list = []
        if conc_text.strip() and sig_text.strip():
            try:
                conc_list = [float(s.strip()) for s in re.split(r'[,;]+', conc_text.strip()) if s.strip() != ""]
                sig_list = [float(s.strip()) for s in re.split(r'[,;]+', sig_text.strip()) if s.strip() != ""]
            except Exception as e:
                st.error(f"Erreur parsing: {e}")
        if len(conc_list) >= 2 and len(sig_list) == len(conc_list):
            x = np.array(conc_list, dtype=float)
            y = np.array(sig_list, dtype=float)

    # regression if valid
    if x.size >= 2 and y.size >= 2 and x.size == y.size:
        try:
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = float(coeffs[0]), float(coeffs[1])
            r = np.corrcoef(x, y)[0, 1]
            r2 = r ** 2
            slope_export = slope
            # plot (matplotlib)
            fig, ax = plt.subplots()
            ax.scatter(x, y, label=t("Points"))
            xs = np.linspace(min(x), max(x), 100)
            ax.plot(xs, slope * xs + intercept, color='red', label=t("Régression linéaire"))
            ax.set_xlabel(f"Concentration ({unit})")
            ax.set_ylabel("Signal")
            ax.legend()
            st.pyplot(fig)
            st.markdown(f"**y = {slope:.6f} x + {intercept:.6f}**")
            st.markdown(f"**R² = {r2:.6f}**")
            # unknown computations
            unknown_signal = st.number_input(t("Entrer signal inconnu"), value=0.0, key="lin_unknown_signal")
            if unknown_signal and slope != 0:
                conc_unknown = (unknown_signal - intercept) / slope
                st.markdown(f"**Concentration estimée :** {conc_unknown:.6f} {unit}")
            unknown_conc = st.number_input(t("Entrer concentration inconnue"), value=0.0, key="lin_unknown_conc")
            if unknown_conc:
                signal_pred = slope * unknown_conc + intercept
                st.markdown(f"**Signal estimé :** {signal_pred:.6f}")
            # export slope
            st.session_state["slope"] = slope
            st.markdown(f"Slope exported to S/N module: **{slope:.6f}** ({unit})")
        except np.linalg.LinAlgError:
            st.error("Erreur linéaire : SVD did not converge (données inadaptées). Vérifie tes points.")
            st.session_state["slope"] = None
        except Exception as e:
            st.error(f"Erreur calcul linéarité : {e}")
            st.session_state["slope"] = None
    else:
        st.info("Fournis au moins 2 points valides (via CSV ou saisie manuelle).")
        st.session_state.setdefault("slope", None)

    return st.session_state.get("slope", None)

# ===============================
# S/N MODULE (auto image + manual H/h in expander + LOD/LOQ expander)
# ===============================
def sn_module():
    st.title(t("Calcul du rapport Signal / Bruit (S/N)"))
    uploaded_file = st.file_uploader(t("Importer une image ou un PDF du chromatogramme"), type=["png", "jpg", "jpeg", "pdf"], key="sn_file")
    unit = st.selectbox(t("Unités concentration"), CONCENTRATION_UNITS, key="sn_unit")

    # formulas expander (unchanged)
    with st.expander(t("Afficher les formules")):
        st.text(t("Formules SN"))
        st.text(t("Formules LOD LOQ"))

    # MANUAL S/N expander (user requested: show only when user clicks)
    if st.button("Calcul manuel du S/N"):
        st.session_state.setdefault("show_manual_sn", True)
    if st.session_state.get("show_manual_sn"):
        with st.expander("Calcul manuel S/N (H, h)", expanded=True):
            H = st.number_input("H (hauteur du pic)", value=0.0, step=0.1, format="%.6f", key="manual_H")
            h = st.number_input("h (bruit, écart-type)", value=0.0, step=0.0001, format="%.6f", key="manual_h")
            # automatic calculation (no extra button)
            if h == 0:
                st.warning("h doit être non nul pour calcul manuel")
            else:
                sn_classic_manual = H / h
                sn_usp_manual = (2 * H) / h
                st.markdown(f"**S/N Classique (manuel)** : {sn_classic_manual:.4f}")
                st.markdown(f"**S/N USP (manuel)** : {sn_usp_manual:.4f}")
            # store manual h for LOD/LOQ calculations
            st.session_state["manual_h"] = h if h > 0 else None
            st.session_state["manual_H"] = H if H > 0 else None

    # IMAGE-BASED computations
    last_result = None
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            img, err = pdf_to_png_bytes(uploaded_file)
            if err:
                st.error(err)
                return
        else:
            img = Image.open(uploaded_file).convert("RGB")

        st.image(img, caption="Chromatogramme original", use_container_width=True)
        max_x = img.width
        col1, col2, col3 = st.columns(3)
        with col1:
            zone = st.slider("Zone d'analyse (pixels)", 0, max_x, (0, max_x), key="zone_slider")
        with col2:
            sensitivity = st.slider("Sensibilité", 0.1, 5.0, 1.0, key="sn_sensitivity")
        with col3:
            slope_manual_input = st.number_input(t("Saisir pente manuellement si non disponible"), min_value=0.0, value=0.0, key="slope_manual_input")

        res, err = analyze_sn_from_image(img, start=zone[0], end=zone[1])
        if err:
            st.warning(err)
        else:
            # adjust by sensitivity
            sn_classic = res["S/N Classique"] * sensitivity
            sn_usp = res["S/N USP"] * sensitivity
            noise = res["noise"]
            peak_height = res["peak_height"]
            peak_pixel = res["peak_retention_pixel"]

            st.markdown(f"**S/N Classique (image)** : {sn_classic:.4f}")
            st.markdown(f"**S/N USP (image)** : {sn_usp:.4f}")
            st.markdown(f"**Temps de rétention (pixel)** : {peak_pixel:.0f}")

            # save last image result in session for LOD/LOQ fallback
            st.session_state["last_sn_result"] = res
            last_result = res

    # LOD/LOQ expander - shown only if user clicks button
    if st.button("Afficher LOD/LOQ"):
        st.session_state.setdefault("show_lod", True)
    if st.session_state.get("show_lod"):
        with st.expander("LOD / LOQ", expanded=True):
            # determine h to use: manual h (if provided) else image noise (if available)
            manual_h = st.session_state.get("manual_h", None)
            image_noise = None
            last = st.session_state.get("last_sn_result", None)
            if last:
                image_noise = last.get("noise", None)
            chosen_h = None

            st.write("Choix du 'h' (bruit) utilisé pour LOD/LOQ :")
            h_choice = st.radio("Utiliser", options=["h manuel (si fourni)", "bruit image (si disponible)"], index=0)
            if h_choice == "h manuel (si fourni)":
                if manual_h:
                    chosen_h = manual_h
                    st.write(f"Utilisation h manuel = {chosen_h:.6f}")
                else:
                    # allow immediate manual entry if none provided earlier
                    h_input_now = st.number_input("Saisir h manuellement", value=0.0, format="%.6f", key="lod_h_input")
                    if h_input_now > 0:
                        chosen_h = h_input_now
                        st.write(f"Utilisation h saisi = {chosen_h:.6f}")
                    else:
                        st.warning("Aucun h manuel disponible — saisis h ou choisis bruit image.")
            else:
                if image_noise:
                    chosen_h = image_noise
                    st.write(f"Utilisation bruit image = {chosen_h:.6f}")
                else:
                    st.warning("Aucun bruit d'image disponible. Fournis h manuel.")

            # slope choice: session slope or manual
            slope_session = st.session_state.get("slope", None)
            st.write("Pente pour conversion signal → concentration :")
            slope_choice_radio = st.radio("Pente à utiliser", options=["Pente exportée (si disponible)", "Saisir pente manuellement"], index=0)
            slope_to_use = None
            if slope_choice_radio == "Pente exportée (si disponible)":
                if slope_session:
                    slope_to_use = slope_session
                    st.write(f"Pente exportée utilisée = {slope_to_use:.6f}")
                else:
                    st.warning("Aucune pente exportée disponible. Saisis la pente manuellement ci-dessous.")
                    slope_manual_now = st.number_input("Saisir pente", value=0.0, key="lod_slope_manual")
                    if slope_manual_now > 0:
                        slope_to_use = slope_manual_now
            else:
                slope_manual_now = st.number_input("Saisir pente", value=0.0, key="lod_slope_manual2")
                if slope_manual_now > 0:
                    slope_to_use = slope_manual_now

            # final compute if h provided
            if chosen_h and chosen_h > 0:
                lod_signal, loq_signal, lod_conc, loq_conc = compute_lod_loq_from_h(chosen_h, slope=slope_to_use)
                st.markdown(f"**LOD (signal)** : {lod_signal:.6f}")
                st.markdown(f"**LOQ (signal)** : {loq_signal:.6f}")
                if lod_conc is not None:
                    st.markdown(f"**LOD (concentration)** : {lod_conc:.6f} {unit}")
                    st.markdown(f"**LOQ (concentration)** : {loq_conc:.6f} {unit}")
                else:
                    st.info("Pente non disponible — saisissez la pente pour obtenir LOD/LOQ en concentration.")
            else:
                st.info("Aucun h disponible pour calculer LOD/LOQ (fournis h manuel ou fais une analyse d'image).")

# ===============================
# FEEDBACK (no email needed)
# ===============================
def feedback_module():
    st.title(t("Feedback utilisateur"))
    msg = st.text_area(t("Message ou commentaire"))
    if st.button(t("Envoyer")):
        if msg:
            st.success("Message enregistré ✅")
        else:
            st.warning(t("Remplir tous les champs"))

# ===============================
# APPLICATION PRINCIPALE
# ===============================
CONCENTRATION_UNITS = ["mg/mL", "µg/mL", "ng/mL", "ppm", "mol/L"]

# language selectbox
LANG = st.selectbox(t("Language / Langue"), ["FR", "EN"], index=0)

def main_app():
    # init session keys
    if "user" not in st.session_state: st.session_state["user"] = None
    if "role" not in st.session_state: st.session_state["role"] = None
    if "access" not in st.session_state: st.session_state["access"] = []
    if "slope" not in st.session_state: st.session_state["slope"] = None
    if "manual_h" not in st.session_state: st.session_state["manual_h"] = None
    if "last_sn_result" not in st.session_state: st.session_state["last_sn_result"] = None

    # change password expander small (available for logged users)
    if st.session_state["user"]:
        with st.expander("🔑 " + t("Changer mot de passe"), expanded=False):
            change_password_panel()

    if st.session_state["user"] is None:
        login_page()
        return

    user = st.session_state["user"]
    role = st.session_state["role"]
    access = st.session_state["access"]

    st.title(f"👋 {user}")
    module = st.selectbox("Module", ["Accueil", "Linéarité", "S/N", "Feedback", "Admin", "Déconnexion"])

    if module == "Accueil":
        st.title(t("Bienvenue dans LabT"))
        st.info(t("Choisissez un module ci-dessus."))
    elif module == "Linéarité" and "linearity" in access:
        linearity_module()
    elif module == "S/N" and "sn" in access:
        sn_module()
    elif module == "Feedback":
        feedback_module()
    elif module == "Admin" and role == "admin":
        admin_panel()
    elif module == "Déconnexion":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.success(t("Déconnecté"))
        st.rerun()

def run():
    st.set_page_config(page_title="LabT", layout="wide")
    main_app()

if __name__=="__main__":
    run()