# ================== app.py ==================
import streamlit as st
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from pdf2image import convert_from_bytes
from skimage.color import rgb2gray
from skimage.filters import threshold_otsu

# ------------------- SESSION INIT -------------------
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'linearity_slope' not in st.session_state:
    st.session_state['linearity_slope'] = None
if 'feedbacks' not in st.session_state:
    st.session_state['feedbacks'] = []

# ------------------- USERS JSON -------------------
users_json = {
    "admin": {"password": "admin", "role": "admin"},
    "user": {"password": "user", "role": "user"}
}

# ------------------- LOGIN PAGE -------------------
def login_page():
    st.title("Connexion / Login")
    st.write("Powered by: BnB")
    username = st.text_input("Nom d'utilisateur / Username")
    password = st.text_input("Mot de passe / Password", type="password")
    if st.button("Se connecter / Login"):
        uname = username.lower()
        if uname in users_json and users_json[uname]['password'] == password:
            st.session_state['user_role'] = users_json[uname]['role']
            st.session_state['username'] = uname
            st.success("Connexion réussie / Login success")
            st.experimental_rerun()
        else:
            st.error("Identifiants invalides / Invalid credentials")

# ------------------- MENU -------------------
def main_menu():
    st.title("Menu Principal / Main Menu")
    if st.session_state['user_role'] == "admin":
        st.subheader("Gestion des utilisateurs / User management")
        admin_panel()
    elif st.session_state['user_role'] == "user":
        st.subheader("Calculs / Calculations")
        menu_choice = st.radio("Sélectionnez le module / Select module", ["Linéarité / Linearity", "S/N / Signal to Noise", "Changer mot de passe / Change password", "Feed-back / Feedback"])
        if menu_choice.startswith("Linéarité"):
            linearity_panel()
        elif menu_choice.startswith("S/N"):
            sn_panel_robust()
        elif menu_choice.startswith("Changer"):
            change_password()
        elif menu_choice.startswith("Feed"):
            feedback_panel()

# ------------------- ADMIN PANEL -------------------
def admin_panel():
    st.write("Admin: accès gestion utilisateurs / Admin: only user management")
    new_user = st.text_input("Nom utilisateur / New username")
    new_pass = st.text_input("Mot de passe / Password", type="password")
    new_role = st.selectbox("Rôle", ["admin","user"])
    if st.button("Ajouter / Add user"):
        users_json[new_user.lower()] = {"password": new_pass, "role": new_role}
        st.success("Utilisateur ajouté / User added")
    st.write("Liste des utilisateurs / Users list")
    st.json(users_json)

# ------------------- CHANGE PASSWORD -------------------
def change_password():
    st.subheader("Changer mot de passe / Change password")
    old = st.text_input("Ancien mot de passe / Old password", type="password")
    new = st.text_input("Nouveau mot de passe / New password", type="password")
    if st.button("Valider / Save"):
        uname = st.session_state['username']
        if users_json[uname]['password'] == old:
            users_json[uname]['password'] = new
            st.success("Mot de passe changé / Password changed")
        else:
            st.error("Ancien mot de passe incorrect / Wrong old password")

# ------------------- LINEARITY PANEL -------------------
def linearity_panel():
    st.subheader("Linéarité / Linearity")
    # Entrée manuelle ou CSV
    manual = st.checkbox("Saisie manuelle / Manual input")
    if manual:
        conc_str = st.text_input("Concentrations séparées par ',' / Concentrations comma-separated")
        signal_str = st.text_input("Signaux séparés par ',' / Signals comma-separated")
        try:
            conc = np.array([float(x) for x in conc_str.split(",")])
            sig = np.array([float(x) for x in signal_str.split(",")])
        except:
            st.error("Entrée invalide / Invalid input")
            return
    else:
        uploaded = st.file_uploader("Importer CSV / Upload CSV", type="csv")
        if uploaded:
            df = pd.read_csv(uploaded)
            conc = df.iloc[:,0].values
            sig = df.iloc[:,1].values
        else:
            return
    
    # Choix unité
    unit = st.selectbox("Unité concentration / Concentration unit", ["µg/mL","mg/mL","ng/mL"])
    
    # Fit linéaire
    slope, intercept = np.polyfit(conc, sig,1)
    st.session_state['linearity_slope'] = slope
    
    # Tracé
    fig, ax = plt.subplots()
    ax.plot(conc, sig, 'bo', label='Données / Data')
    ax.plot(conc, slope*conc + intercept, 'k-', label='Fit')
    ax.set_xlabel(f"Concentration ({unit})")
    ax.set_ylabel("Signal")
    ax.set_title("Courbe de linéarité / Linearity curve")
    ax.legend()
    st.pyplot(fig)
    
    # Calcul concentration inconnue
    sig_unknown = st.number_input("Signal inconnu / Unknown signal", min_value=0.0)
    conc_calc = (sig_unknown - intercept)/slope
    st.write(f"Concentration inconnue: {conc_calc:.4f} {unit}")
    
    conc_unknown = st.number_input("Concentration inconnue / Unknown concentration", min_value=0.0)
    sig_calc = slope*conc_unknown + intercept
    st.write(f"Signal correspondant: {sig_calc:.4f}")

# ------------------- S/N PANEL -------------------
def sn_panel_robust():
    st.subheader("S/N / Signal to Noise")
    uploaded_file = st.file_uploader("Charger PDF ou image / Upload PDF or image", type=["pdf","png","jpg","jpeg"])
    if not uploaded_file:
        return
    
    # PDF → PNG
    if uploaded_file.type == "application/pdf":
        try:
            images = convert_from_bytes(uploaded_file.read())
            img = images[0]
        except Exception as e:
            st.error(f"Erreur conversion PDF / PDF conversion error: {e}")
            return
    else:
        img = Image.open(uploaded_file)

    st.image(img, caption="Image originale / Original Image", use_column_width=True)
    
    img_gray = rgb2gray(np.array(img))
    
    st.write("Sélection de la zone de bruit / Select noise region")
    min_val, max_val = st.slider("Zone du bruit / Noise region", 0, img_gray.shape[1]-1, (0, img_gray.shape[1]//5))
    noise_region = img_gray[:, min_val:max_val]

    thresh_val = threshold_otsu(noise_region)
    threshold = st.slider("Threshold / Sensitivity", float(noise_region.min()), float(noise_region.max()), float(thresh_val))
    
    H = img_gray.max()
    h = noise_region.max()
    st.write(f"Hauteur pic H: {H:.3f}, Bruit h: {h:.3f}")

    S_N_classic = H/h
    st.write(f"S/N classique: {S_N_classic:.2f}")

    slope = st.session_state.get('linearity_slope', None)
    unit = st.selectbox("Unité concentration / Concentration unit", ["µg/mL","mg/mL","ng/mL"])
    if slope:
        LOQ = (10 * h)/slope
        LOD = (3.3 * h)/slope
        st.write(f"LOD: {LOD:.4f} {unit}, LOQ: {LOQ:.4f} {unit}")
    else:
        st.info("Importer d'abord la linéarité pour LOQ/LOD / Import linearity first for LOQ/LOD")

    with st.expander("Formules de calcul / Calculation formulas"):
        st.markdown("""
        - S/N classique = H / h  
        - LOD = 3.3 × h / pente  
        - LOQ = 10 × h / pente  
        """)

    # Pic principal
    fig, ax = plt.subplots()
    ax.imshow(img)
    peak_y, peak_x = np.unravel_index(np.argmax(img_gray), img_gray.shape)
    ax.plot(peak_x, peak_y, 'ro')
    ax.set_title("Pic principal marqué / Main peak marked")
    st.pyplot(fig)

# ------------------- FEEDBACK -------------------
def feedback_panel():
    st.subheader("Feed-back / Feedback")
    feedback_text = st.text_area("Envoyer un commentaire / Send feedback")
    if st.button("Envoyer / Send"):
        st.session_state['feedbacks'].append(feedback_text)
        st.success("Feedback envoyé / Feedback sent")
    
    if st.session_state.get('user_role') == "admin":
        st.subheader("Réponses aux feed-back / Feedback responses")
        for fb in st.session_state.get('feedbacks', []):
            st.write(fb)

# ------------------- RUN -------------------
def run():
    if st.session_state['user_role'] is None:
        login_page()
    else:
        main_menu()
        if st.button("Déconnexion / Logout"):
            st.session_state['user_role'] = None
            st.session_state['username'] = None
            st.experimental_rerun()

if __name__ == "__main__":
    run()