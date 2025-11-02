import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
from pdf2image import convert_from_bytes

# ---------------------------
# User Management
# ---------------------------
import json
USER_FILE = "users.json"

def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

def login_page():
    st.title("LabT Login / Connexion")
    st.markdown("Powered by BnB")
    users = load_users()
    
    username = st.text_input("Username / Nom d'utilisateur").lower()
    password = st.text_input("Password / Mot de passe", type="password")
    
    if st.button("Login / Se connecter"):
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = users[username]["role"]
            st.success(f"Welcome {username}!")
        else:
            st.error("Invalid credentials / Identifiants invalides")

def change_password():
    st.subheader("Change Password / Modifier mot de passe")
    users = load_users()
    new_pass = st.text_input("New password / Nouveau mot de passe", type="password")
    if st.button("Update / Mettre à jour"):
        users[st.session_state["user"]]["password"] = new_pass
        save_users(users)
        st.success("Password updated / Mot de passe modifié")
# ---------------------------
# Linéarité Panel
# ---------------------------

def linearity_panel():
    st.header("Linearity / Linéarité")
    
    # Upload CSV or manual input
    csv_file = st.file_uploader("Upload CSV / Charger CSV", type=["csv"])
    concentrations = st.text_input("Concentrations (comma-separated) / Concentrations (séparées par des virgules)")
    signals = st.text_input("Signals (comma-separated) / Signaux (séparés par des virgules)")
    
    if csv_file:
        df = pd.read_csv(csv_file)
        x = df["Concentration"].values
        y = df["Signal"].values
    elif concentrations and signals:
        x = np.array([float(c) for c in concentrations.split(",")])
        y = np.array([float(s) for s in signals.split(",")])
    else:
        st.info("Provide CSV or manual input / Fournir CSV ou saisie manuelle")
        return
    
    # Fit linear
    slope, intercept = np.polyfit(x, y, 1)
    st.write(f"Slope / Pente: {slope:.4f}, Intercept / Ordonnée à l'origine: {intercept:.4f}")
    
    # Plot
    plt.figure(figsize=(6,4))
    plt.plot(x, y, 'o', label="Data / Données")
    plt.plot(x, slope*x + intercept, '-', label="Fit / Ajustement")
    plt.xlabel("Concentration")
    plt.ylabel("Signal")
    plt.legend()
    st.pyplot(plt)

    # Unknown calculations
    st.subheader("Unknown / Inconnu")
    signal_unknown = st.number_input("Signal unknown / Signal inconnu")
    conc_calc = (signal_unknown - intercept) / slope
    st.write(f"Calculated concentration / Concentration calculée: {conc_calc:.4f}")

    conc_unknown = st.number_input("Concentration unknown / Concentration inconnue")
    signal_calc = slope * conc_unknown + intercept
    st.write(f"Calculated signal / Signal calculé: {signal_calc:.4f}")

# ---------------------------
# Image inversion utility
# ---------------------------

def invert_image(img):
    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    return inverted.convert("RGB")

# ---------------------------
# S/N Panel
# ---------------------------

def sn_panel(slope_from_linearity=None):
    st.header("Signal-to-Noise / Rapport Signal sur Bruit")

    # PDF/PNG upload
    pdf_file = st.file_uploader("Upload PDF chromatogram / Charger PDF", type=["pdf"])
    img_file = st.file_uploader("Upload image / Charger image", type=["png", "jpg", "jpeg"])
    
    img = None
    if pdf_file:
        try:
            pages = convert_from_bytes(pdf_file.read())
            img = pages[0].convert("RGB")
        except Exception as e:
            st.error(f"PDF conversion failed. Install poppler and check PATH. Error: {e}")
    
    elif img_file:
        img = Image.open(img_file).convert("RGB")
    
    if img is None:
        st.info("Upload PDF or Image to proceed / Charger PDF ou image pour continuer")
        return
    
    # Inversion: baseline at bottom
    img_proc = invert_image(img)
    st.image(img_proc, caption="Processed Image / Image traitée", use_column_width=True)
    
    # Further calculations will follow...
# ---------------------------
# S/N Panel Suite
# ---------------------------

def sn_panel_continued(slope_from_linearity=None):
    st.subheader("Calcul manuel / Manual calculation")
    
    # User input for S/N classical and USP
    H = st.number_input("Peak height H / Hauteur du pic", min_value=0.0, value=1.0)
    h = st.number_input("Noise height h / Hauteur bruit", min_value=0.0, value=0.1)
    
    sn_classical = H / h if h != 0 else None
    st.write(f"S/N classical: {sn_classical:.2f}" if sn_classical else "Cannot compute / Impossible")
    
    if slope_from_linearity:
        conc_unknown = st.number_input("Concentration unknown / Concentration inconnue")
        signal_calc = slope_from_linearity * conc_unknown
        st.write(f"Signal predicted from linearity / Signal prédit: {signal_calc:.4f}")
    
    # LOQ/LOD calculation
    unit = st.selectbox("Unit / Unité", ["µg/mL", "mg/L"])
    lod = 3 * h
    loq = 10 * h
    st.write(f"LOD ({unit}): {lod:.4f}, LOQ ({unit}): {loq:.4f}")
    
    # Mark peak on image
    img_array = np.array(invert_image(img_proc))
    fig, ax = plt.subplots(figsize=(6,4))
    ax.imshow(img_array)
    
    # Assuming x_peak, y_peak from image processing
    x_peak, y_peak = img_array.shape[1]//2, img_array.shape[0]//2  # placeholder
    ax.plot(x_peak, y_peak, "ro", label="Main peak / Pic principal")
    ax.legend()
    st.pyplot(fig)

# ---------------------------
# Feedback system
# ---------------------------

FEEDBACK_FILE = "feedback.json"

def load_feedback():
    try:
        with open(FEEDBACK_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_feedback(fb_list):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(fb_list, f, indent=4)

def feedback_button():
    if st.button("Feedback / Retour d'expérience"):
        feedback_text = st.text_area("Enter your feedback / Saisir votre feedback")
        if st.button("Submit / Envoyer"):
            fb_list = load_feedback()
            fb_list.append({
                "user": st.session_state["user"],
                "text": feedback_text,
                "response": ""
            })
            save_feedback(fb_list)
            st.success("Feedback submitted / Feedback envoyé")

def view_feedback():
    if st.session_state["role"] == "admin":
        fb_list = load_feedback()
        for i, fb in enumerate(fb_list):
            st.write(f"User: {fb['user']}")
            st.write(f"Feedback: {fb['text']}")
            resp = st.text_input(f"Response / Réponse #{i}", value=fb['response'])
            if st.button(f"Save response / Sauvegarder #{i}"):
                fb_list[i]['response'] = resp
                save_feedback(fb_list)
                st.success("Response saved / Réponse sauvegardée")
    else:
        fb_list = load_feedback()
        for fb in fb_list:
            st.write(f"User: {fb['user']}")
            st.write(f"Feedback: {fb['text']}")
            st.write(f"Response / Réponse: {fb['response']}")

# ---------------------------
# Main App
# ---------------------------

def main_app():
    if "user" not in st.session_state:
        login_page()
        return
    
    st.title("LabT Application")
    
    # Change password
    if st.session_state["role"] == "user":
        if st.button("Change password / Modifier mot de passe"):
            change_password()
    
    # Select Panel
    panel_choice = st.radio("Select Panel / Choisir le volet", ["Linearity / Linéarité", "S/N"])
    
    if panel_choice.startswith("Linearity"):
        linearity_panel()
    else:
        sn_panel(slope_from_linearity=1.0)  # placeholder slope
        sn_panel_continued(slope_from_linearity=1.0)
    
    # Feedback (discret button)
    feedback_button()
    view_feedback()
