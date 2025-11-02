# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
import tempfile, io, fitz  # PyMuPDF for PDF
import json
from datetime import datetime

# -------------------------
# User data (demo)
# -------------------------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"admin": {"password": "admin", "role": "admin"}}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

USERS = load_users()

def find_user_key(username):
    for k in USERS.keys():
        if k.lower() == username.lower():
            return k
    return None


# -------------------------
# Language helper
# -------------------------
def t(key):
    text = {
        "FR": {
            "username": "Nom d'utilisateur",
            "password": "Mot de passe",
            "login": "Connexion",
            "invalid": "Nom d'utilisateur ou mot de passe invalide",
            "change_pwd": "Changer le mot de passe",
            "powered": "Propulsé par BnB",
            "admin": "Panneau administrateur",
            "add_user": "Ajouter un utilisateur",
            "enter_username": "Nom d'utilisateur",
            "enter_password": "Mot de passe",
            "Upload file": "Téléverser un fichier",
            "Upload your chromatogram (CSV, image, or PDF)": "Téléversez votre chromatogramme (CSV, image ou PDF)",
            "Please upload a chromatogram.": "Veuillez téléverser un chromatogramme.",
            "Invert chromatogram (flip vertically)": "Inverser le chromatogramme (ligne de base en bas)",
            "Select noise region manually": "Sélectionner manuellement la zone de bruit",
            "Start of noise region": "Début de la zone de bruit",
            "End of noise region": "Fin de la zone de bruit",
            "Noise region": "Zone de bruit",
            "Peak position": "Position du pic",
            "Download processed chromatogram": "Télécharger le chromatogramme traité",
        },
        "EN": {
            "username": "Username",
            "password": "Password",
            "login": "Login",
            "invalid": "Invalid username or password",
            "change_pwd": "Change password",
            "powered": "Powered by BnB",
            "admin": "Admin panel",
            "add_user": "Add user",
            "enter_username": "Enter username",
            "enter_password": "Enter password",
            "Upload file": "Upload file",
            "Upload your chromatogram (CSV, image, or PDF)": "Upload your chromatogram (CSV, image, or PDF)",
            "Please upload a chromatogram.": "Please upload a chromatogram.",
            "Invert chromatogram (flip vertically)": "Invert chromatogram (flip vertically)",
            "Select noise region manually": "Select noise region manually",
            "Start of noise region": "Start of noise region",
            "End of noise region": "End of noise region",
            "Noise region": "Noise region",
            "Peak position": "Peak position",
            "Download processed chromatogram": "Download processed chromatogram",
        },
    }
    lang = st.session_state.get("lang", "FR")
    return text.get(lang, text["EN"]).get(key, key)


# -------------------------
# Login screen
# -------------------------
def login_screen():
    st.markdown("<h2 style='text-align:center;'>LabT - Login</h2>", unsafe_allow_html=True)

    lang = st.selectbox("Language / Langue", ["FR", "EN"], key="lang_select")
    st.session_state.lang = lang

    username = st.text_input(t("username"))
    password = st.text_input(t("password"), type="password")
    if st.button(t("login")):
        uname = username.strip()
        matched = find_user_key(uname)
        if matched and USERS[matched]["password"] == password:
            st.session_state.user = matched
            st.session_state.role = USERS[matched].get("role", "user")
            st.rerun()
        else:
            st.error(t("invalid"))

    st.markdown(
        f"<div style='text-align:center;color:gray;font-size:12px;margin-top:2em'>{t('powered')}</div>",
        unsafe_allow_html=True,
    )


# -------------------------
# Logout button
# -------------------------
def logout_button():
    if st.button("🚪 Déconnexion / Logout"):
        for key in ["user", "role"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


# -------------------------
# Admin panel
# -------------------------
def admin_panel():
    st.header(t("admin"))
    col_left, col_right = st.columns([2, 1])

    with col_left:
        users_list = list(USERS.keys())
        sel = st.selectbox("Select user", users_list, key="admin_sel_user")
        if sel:
            info = USERS.get(sel, {})
            st.write(f"**Username:** {sel}")
            st.write(f"**Role:** {info.get('role', 'user')}")
            new_pwd = st.text_input(f"New password for {sel}", type="password", key=f"newpwd_{sel}")
            new_role = st.selectbox("Role", ["user", "admin"], index=0 if info.get("role") == "user" else 1, key=f"role_{sel}")
            if st.button("Save changes", key=f"save_{sel}"):
                if new_pwd:
                    USERS[sel]["password"] = new_pwd
                USERS[sel]["role"] = new_role
                save_users(USERS)
                st.success("Updated!")
                st.rerun()
            if sel.lower() != "admin" and st.button("Delete user", key=f"del_{sel}"):
                USERS.pop(sel)
                save_users(USERS)
                st.success("Deleted!")
                st.rerun()

    with col_right:
        st.subheader(t("add_user"))
        new_user = st.text_input(t("enter_username"), key="add_user")
        new_pass = st.text_input(t("enter_password"), type="password", key="add_pass")
        role = st.selectbox("Role", ["user", "admin"], key="add_role")
        if st.button("Add user"):
            if not new_user.strip() or not new_pass.strip():
                st.warning("Missing info.")
            elif find_user_key(new_user):
                st.warning("User exists.")
            else:
                USERS[new_user.strip()] = {"password": new_pass.strip(), "role": role}
                save_users(USERS)
                st.success(f"{new_user.strip()} added!")
                st.rerun()


# -------------------------
# Linearity (placeholder)
# -------------------------
def linearity_panel():
    st.header("📈 Linéarité")
    st.info("Section à venir — collez ici le code complet de la linéarité existant.")


# -------------------------
# Signal/Noise panel
# -------------------------
def sn_panel():
    st.header("📊 S/N (Signal / Bruit)")

    file = st.file_uploader(
        t("Upload your chromatogram (CSV, image, or PDF)"),
        type=["csv", "png", "jpg", "jpeg", "pdf"]
    )

    if not file:
        st.info(t("Please upload a chromatogram."))
        return

    invert = st.checkbox(t("Invert chromatogram (flip vertically)"), value=True)
    use_sliders = st.checkbox(t("Select noise region manually"), value=True)

    img = None
    x = None
    y = None

    # --- CSV file ---
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file, sep=None, engine="python")
        df.columns = [c.strip().lower() for c in df.columns]
        time_col = next((c for c in df.columns if "time" in c), None)
        signal_col = next((c for c in df.columns if "signal" in c or "intensity" in c), None)
        if time_col and signal_col:
            x = df[time_col].values
            y = df[signal_col].values
        else:
            st.error("Missing columns.")
            return

    # --- PDF ---
    elif file.name.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(file.read())
            tmp_pdf_path = tmp_pdf.name
        pdf_doc = fitz.open(tmp_pdf_path)
        page = pdf_doc[0]
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        pdf_doc.close()

    # --- Image ---
    else:
        img = Image.open(file)

    if img is not None:
        if invert:
            img = ImageOps.flip(img)
        st.image(img, caption="Chromatogram (processed)", use_container_width=True)
        img_array = np.array(img.convert("L"))
        y = np.mean(img_array, axis=1)
        x = np.arange(len(y))

    st.subheader("Noise region")
    if use_sliders:
        start_noise = st.slider("Start", 0, len(y)-2, int(len(y)*0.1))
        end_noise = st.slider("End", start_noise+1, len(y)-1, int(len(y)*0.2))
    else:
        start_noise, end_noise = 0, int(len(y)*0.2)

    noise_region = y[start_noise:end_noise]
    noise_std = np.std(noise_region)

    peak_index = np.argmax(y)
    H = np.max(y)
    baseline = np.min(y)
    h = H - baseline

    half_max = baseline + h/2
    indices_above_half = np.where(y >= half_max)[0]
    w_half = indices_above_half[-1] - indices_above_half[0] if len(indices_above_half)>1 else 0
    sn_ratio = h / (noise_std * 2) if noise_std>0 else np.nan

    fig, ax = plt.subplots()
    ax.plot(x, y, label="Chromatogram")
    ax.axvspan(start_noise, end_noise, color="gray", alpha=0.3, label=t("Noise region"))
    ax.axhline(half_max, color="orange", linestyle="--", label="½ Height")
    ax.axvline(peak_index, color="red", linestyle="--", label=t("Peak position"))
    ax.text(peak_index, H, f"H={H:.1f}\nh={h:.1f}\nw½={w_half:.1f}", color="red", fontsize=8)
    ax.legend()
    st.pyplot(fig)

    st.markdown(f"**H:** {H:.2f} **h:** {h:.2f} **w½:** {w_half:.2f} **σ(noise):** {noise_std:.4f} **S/N:** {sn_ratio:.2f}")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button(t("Download processed chromatogram"), buf.getvalue(), file_name="chromato_processed.png", mime="image/png")


# -------------------------
# Main app
# -------------------------
def main_app():
    logout_button()

    page = st.radio("Choisir la section / Choose section", ["Linéarité", "S/N", "Admin"])
    if page == "Linéarité":
        linearity_panel()
    elif page == "S/N":
        sn_panel()
    elif page == "Admin" and st.session_state.role == "admin":
        admin_panel()
    else:
        st.warning("Vous n'avez pas les droits d'accès.")


# -------------------------
# Run
# -------------------------
def run():
    if "user" not in st.session_state:
        login_screen()
    else:
        main_app()


if __name__ == "__main__":
    run()