import streamlit as st

# --- Initialisation des variables de session ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = ""
if 'unit' not in st.session_state:
    st.session_state.unit = ""
if 'language' not in st.session_state:
    st.session_state.language = 'English'  # langue par défaut

# --- Liste des utilisateurs ---
# Les utilisateurs peuvent être en majuscules ou minuscules sans effet
USERS = {
    "admin": "admin123",
    "user1": "pass1"
}

def login_action(username, password):
    """Vérifie le login sans rerun automatique"""
    username_lower = username.lower()
    if username_lower in USERS and password == USERS[username_lower]:
        st.session_state.logged_in = True
        st.session_state.user = username_lower
        st.success(f"Connexion réussie ✅ / You are logged in as {username_lower}")
    else:
        st.error("Nom d'utilisateur ou mot de passe incorrect / Wrong username or password")

# --- Affichage du formulaire de login ---
if not st.session_state.logged_in:
    st.title("App: LabT")
    st.subheader("Connexion / Login")
    
    selected_user = st.selectbox(
        "Choisir un utilisateur / Choose user:",
        list(USERS.keys())
    )
    password = st.text_input("Mot de passe / Password:", type="password")
    
    if st.button("Se connecter / Login"):
        login_action(selected_user, password)
else:
    st.write(f"Bienvenue / Welcome, {st.session_state.user} !")
    st.write("Vous êtes connecté en tant que admin / You are logged in as admin")
    # Ici, on pourra afficher le menu principal de l'app
# --- Partie 2 : Menu principal et options ---
if st.session_state.logged_in:

    st.title("App: LabT")

    # --- Choix de la langue ---
    language = st.selectbox(
        "Language / Langue:",
        ["English", "Français"],
        index=0 if st.session_state.language == "English" else 1,
        key="lang_select"
    )
    st.session_state.language = language

    # --- Menu principal bilingue ---
    menu_options = {
        "English": ["Unknown calculation", "S/N Analysis", "Linearity", "Admin", "Logout"],
        "Français": ["Calcul inconnu", "Analyse S/N", "Linéarité", "Admin", "Déconnexion"]
    }

    selected_option = st.radio(
        "Menu:",
        menu_options[st.session_state.language]
    )

    # --- Admin panel options bilingual ---
    if selected_option in ["Admin", "Déconnexion"]:
        if selected_option in ["Admin"]:
            st.subheader("Admin Panel / Panneau Admin")
            st.write("You can add or remove users / Vous pouvez ajouter ou supprimer des utilisateurs")
            # Ajout d'un utilisateur
            new_user = st.text_input("Add user / Ajouter un utilisateur:")
            new_password = st.text_input("Password / Mot de passe:", type="password")
            if st.button("Add / Ajouter"):
                if new_user and new_password:
                    USERS[new_user.lower()] = new_password
                    st.success(f"User {new_user} added ✅")
                else:
                    st.error("Please enter username and password / Veuillez entrer nom et mot de passe")
            
            # Suppression d'un utilisateur
            del_user = st.text_input("Delete user / Supprimer un utilisateur:")
            if st.button("Delete / Supprimer"):
                if del_user.lower() in USERS:
                    del USERS[del_user.lower()]
                    st.success(f"User {del_user} deleted ✅")
                else:
                    st.error("User not found / Utilisateur non trouvé")

        # --- Déconnexion ---
        if selected_option in ["Déconnexion", "Logout"]:
            if st.button("Confirm / Confirmer"):
                st.session_state.logged_in = False
                st.session_state.user = ""
                st.experimental_rerun()

    # --- Options pour calculs / analyses ---
    if selected_option in ["Unknown calculation", "Calcul inconnu"]:
        st.subheader("Unknown calculation / Calcul inconnu")
        # Ici on affichera les champs pour entrer les données
        conc_unit = st.selectbox("Unit / Unité:", ["mg/mL", "µg/mL", "ppm"], key="unit")
        st.session_state.unit = conc_unit

    if selected_option in ["S/N Analysis", "Analyse S/N"]:
        st.subheader("Signal-to-Noise Analysis / Analyse S/N")
        sn_method = st.radio(
            "Select method / Sélectionner méthode:",
            ["Classical", "USP"],
            index=0
        )
        st.write(f"Selected method: {sn_method}")

    if selected_option in ["Linearity", "Linéarité"]:
        st.subheader("Linearity Curve / Courbe de linéarité")
        use_linearity = st.checkbox("Use linearity for S/N calculation / Utiliser la linéarité pour S/N")
# --- Partie 3 : Calculs et génération PDF ---
import io
from fpdf import FPDF
import numpy as np

def calculate_unknown(concentration_values, signal_values):
    """Calcul inconnu"""
    if not concentration_values or not signal_values:
        st.error("Please enter data / Veuillez entrer des données")
        return None
    conc_array = np.array(concentration_values)
    sig_array = np.array(signal_values)
    unknown_conc = np.mean(sig_array) / np.mean(conc_array)  # simplifié
    return unknown_conc

def calculate_sn(signal, noise, slope=None, use_linearity=False):
    """Calcul S/N classique ou USP"""
    if use_linearity and slope:
        sn_conc = (signal / noise) / slope
        return sn_conc
    else:
        return signal / noise

def export_pdf(
    unknown_conc, conc_unit, sn_value, sn_unit, company_name="LabT"
):
    if not company_name:
        st.error("Please enter company name before generating PDF / Veuillez entrer le nom de l'entreprise")
        return
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"App: {company_name}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Unknown concentration: {unknown_conc:.4f} {conc_unit}", ln=True)
    pdf.cell(0, 10, f"S/N value: {sn_value:.4f} {sn_unit}", ln=True)

    # Save PDF to buffer
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    st.download_button("Download PDF / Télécharger PDF", pdf_buffer, file_name="LabT_Report.pdf")

# --- Exemple d'utilisation ---
if selected_option in ["Unknown calculation", "Calcul inconnu"]:
    conc_input = st.text_area("Enter known concentrations / Entrer concentrations connues (comma-separated):")
    sig_input = st.text_area("Enter signals / Entrer signaux (comma-separated):")
    conc_list = [float(x) for x in conc_input.split(",") if x.strip()]
    sig_list = [float(x) for x in sig_input.split(",") if x.strip()]
    
    if st.button("Calculate / Calculer"):
        unknown_conc = calculate_unknown(conc_list, sig_list)
        st.session_state.unknown_conc = unknown_conc
        st.success(f"Unknown concentration: {unknown_conc:.4f} {st.session_state.unit}")

if selected_option in ["S/N Analysis", "Analyse S/N"]:
    signal_val = st.number_input("Signal / Signal:", value=0.0)
    noise_val = st.number_input("Noise / Bruit:", value=0.0)
    use_linearity = st.checkbox("Use linearity / Utiliser linéarité")
    slope_val = st.number_input("Slope / Pente:", value=1.0)
    
    if st.button("Calculate S/N"):
        sn_result = calculate_sn(signal_val, noise_val, slope_val, use_linearity)
        st.session_state.sn_value = sn_result
        st.success(f"S/N: {sn_result:.4f} {st.session_state.unit if 'unit' in st.session_state else ''}")

if st.button("Generate PDF / Générer PDF"):
    export_pdf(
        st.session_state.get("unknown_conc", 0),
        st.session_state.get("unit", ""),
        st.session_state.get("sn_value", 0),
        st.session_state.get("unit", ""),
        company_name=st.text_input("Company name / Nom de l'entreprise:")
    )
# --- Partie 4 : Navigation et menu bilingue ---
import streamlit as st

def main_menu():
    st.title("LabT App / Application LabT")
    
    menu_options = {
        "en": ["Unknown calculation", "S/N Analysis", "Admin", "Exit"],
        "fr": ["Calcul inconnu", "Analyse S/N", "Admin", "Quitter"]
    }
    
    lang = st.session_state.get("lang", "en")
    selected = st.selectbox(
        "Select option / Sélectionner une option:",
        menu_options[lang]
    )
    
    st.session_state.current_page = selected
    return selected

def previous_menu_button():
    if st.session_state.get("current_page") not in [None, "Admin", "Quitter", "Exit"]:
        if st.button("Back / Retour"):
            st.session_state.current_page = None
            st.experimental_rerun()

def admin_menu():
    st.subheader("Admin Panel / Panneau Admin")
    lang = st.session_state.get("lang", "en")
    actions = {
        "en": ["Add user", "Delete user", "Logout"],
        "fr": ["Ajouter utilisateur", "Supprimer utilisateur", "Se déconnecter"]
    }
    
    choice = st.selectbox("Choose action / Choisir action:", actions[lang])
    
    if st.button("Execute / Exécuter"):
        if choice in ["Add user", "Ajouter utilisateur"]:
            st.info("Add user functionality / Ajouter utilisateur")
        elif choice in ["Delete user", "Supprimer utilisateur"]:
            st.info("Delete user functionality / Supprimer utilisateur")
        elif choice in ["Logout", "Se déconnecter"]:
            st.session_state.logged_in = False
            st.session_state.current_page = None
            st.experimental_rerun()

# --- Main loop ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "lang" not in st.session_state:
    st.session_state.lang = "en"

if not st.session_state.logged_in:
    st.header("Login / Connexion")
    username = st.text_input("Username / Nom d'utilisateur:").lower()
    password = st.text_input("Password / Mot de passe:", type="password")
    
    if st.button("Login / Se connecter"):
        # Vérification simple pour l'exemple
        if username == "admin" and password == "admin":
            st.session_state.logged_in = True
            st.success("Login successful ✅ / Connexion réussie ✅")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials / Identifiants invalides")
else:
    selected_option = main_menu()
    
    previous_menu_button()  # Bouton pour revenir au menu précédent
    
    if selected_option in ["Admin", "Panneau Admin"]:
        admin_menu()
    elif selected_option in ["Unknown calculation", "Calcul inconnu"]:
        st.info("Go to Part 3 / Aller à Partie 3 pour calcul inconnu")
    elif selected_option in ["S/N Analysis", "Analyse S/N"]:
        st.info("Go to Part 3 / Aller à Partie 3 pour S/N analysis")