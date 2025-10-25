import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import json
from io import BytesIO
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import os

# ---------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------

def load_users():
    with open("users.json", "r") as f:
        return json.load(f)["users"]

def save_users(users):
    with open("users.json", "w") as f:
        json.dump({"users": users}, f, indent=4)

def check_login(username, password):
    users = load_users()
    for user in users:
        if user["username"] == username and user["password"] == password:
            return user["role"]
    return None

def linear_regression(x, y):
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    intercept = coeffs[1]
    y_pred = np.polyval(coeffs, x)
    r2 = np.corrcoef(y, y_pred)[0,1]**2
    return slope, intercept, r2

def generate_pdf_report(title, company_name, slope, intercept, r2, username):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Company: {company_name}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"User: {username}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Slope: {slope:.6g}", ln=True)
    pdf.cell(0, 10, f"Intercept: {intercept:.6g}", ln=True)
    pdf.cell(0, 10, f"R²: {r2:.6g}", ln=True)
    return pdf.output(dest="S").encode("latin1")
# ---------------------------------------------------
# Paramètres de l'application
# ---------------------------------------------------

LANGUAGES = {
    "English": {
        "username": "Username",
        "password": "Password",
        "login": "Login",
        "logout": "Logout",
        "invalid": "Invalid username or password",
        "choose_lang": "Choose language",
        "company": "Company Name",
    },
    "Français": {
        "username": "Nom d'utilisateur",
        "password": "Mot de passe",
        "login": "Connexion",
        "logout": "Déconnexion",
        "invalid": "Nom d'utilisateur ou mot de passe incorrect",
        "choose_lang": "Choisir la langue",
        "company": "Nom de la compagnie",
    }
}

# ---------------------------------------------------
# Choix de la langue
# ---------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "English"

lang = st.selectbox("🌐 " + LANGUAGES[st.session_state.lang]["choose_lang"],
                    options=list(LANGUAGES.keys()))
st.session_state.lang = lang
L = LANGUAGES[lang]

# ---------------------------------------------------
# Connexion
# ---------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.title("LabT")
    st.caption("Powered by BnB")
    
    username = st.text_input(L["username"])
    password = st.text_input(L["password"], type="password")
    
    if st.button(L["login"]):
        role = check_login(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.experimental_rerun()
        else:
            st.error(L["invalid"])
else:
    st.sidebar.button(L["logout"], on_click=lambda: logout())

# ---------------------------------------------------
# Fonction logout
# ---------------------------------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.experimental_rerun()
# ---------------------------------------------------
# Menu principal
# ---------------------------------------------------
def main_menu():
    st.sidebar.title(f"👋 {st.session_state.username}")
    
    if st.session_state.role == "admin":
        st.sidebar.subheader("Admin Menu")
        if st.sidebar.button("Manage Users"):
            admin_panel()
    else:
        st.sidebar.subheader("User Menu")
        menu = st.sidebar.radio("Choose Section", ["Linearity", "Signal/Noise"])
        if menu == "Linearity":
            linear_panel()
        elif menu == "Signal/Noise":
            sn_panel()

# ---------------------------------------------------
# Admin panel (gestion des users)
# ---------------------------------------------------
def admin_panel():
    st.header("User Management")
    st.info("Admin can only add, delete or modify users")
    
    if st.button("Add User"):
        add_user()
    if st.button("Delete User"):
        delete_user()
    if st.button("Modify User"):
        modify_user()

# ---------------------------------------------------
# Fonctions fictives pour gérer users
# ---------------------------------------------------
def add_user():
    st.success("Add user functionality here")

def delete_user():
    st.success("Delete user functionality here")

def modify_user():
    st.success("Modify user functionality here")

# ---------------------------------------------------
# Appel du menu principal
# ---------------------------------------------------
if st.session_state.logged_in:
    main_menu()
# ---------------------------------------------------
# Linear Regression Helper
# ---------------------------------------------------
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import io
from fpdf import FPDF

def linear_regression(x, y):
    x = np.array(x).reshape(-1, 1)
    y = np.array(y)
    model = LinearRegression().fit(x, y)
    slope = model.coef_[0]
    intercept = model.intercept_
    r2 = model.score(x, y)
    return slope, intercept, r2

# ---------------------------------------------------
# Linear Panel
# ---------------------------------------------------
def linear_panel():
    st.header("📈 Linearity Curve")
    
    # Nom de la compagnie
    company = st.text_input("Company Name:")
    if company.strip() == "":
        st.warning("Please enter the company name to generate the report.")
        return

    # Choix de saisie
    input_type = st.radio("Data Input", ["CSV Upload", "Manual Entry"])
    
    if input_type == "CSV Upload":
        uploaded_file = st.file_uploader("Upload CSV with X,Y columns", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
    else:
        x_vals = st.text_area("Enter X values (comma separated)").split(",")
        y_vals = st.text_area("Enter Y values (comma separated)").split(",")
        if x_vals and y_vals:
            try:
                df = pd.DataFrame({
                    "X": [float(i) for i in x_vals],
                    "Y": [float(i) for i in y_vals]
                })
            except:
                st.error("Invalid manual input. Please enter numbers separated by commas.")
                return
        else:
            return
    
    # Calcul linéaire
    slope, intercept, r2 = linear_regression(df["X"], df["Y"])
    st.write(f"Equation: Y = {slope:.4f} X + {intercept:.4f}")
    st.write(f"R² = {r2:.4f}")
    
    # Trace courbe
    fig, ax = plt.subplots()
    ax.scatter(df["X"], df["Y"], label="Data")
    ax.plot(df["X"], slope*df["X"]+intercept, color="red", label="Fit")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    st.pyplot(fig)
    
    # Calcul concentration inconnue
    calc_type = st.selectbox("Calculate", ["Unknown Y -> X", "Unknown X -> Y"])
    conc_unit = st.selectbox("Unit", ["µg/mL", "mg/mL", "ng/mL"])
    
    if calc_type == "Unknown Y -> X":
        unknown_y = st.number_input("Enter unknown signal Y")
        if st.button("Calculate X"):
            calc_x = (unknown_y - intercept) / slope
            st.success(f"Calculated X = {calc_x:.4f} {conc_unit}")
    else:
        unknown_x = st.number_input("Enter unknown X")
        if st.button("Calculate Y"):
            calc_y = slope*unknown_x + intercept
            st.success(f"Calculated Y = {calc_y:.4f}")

    # Bouton générer PDF
    if st.button("Generate PDF Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"Linearity Report - {company}", ln=1)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Equation: Y = {slope:.4f} X + {intercept:.4f}", ln=1)
        pdf.cell(0, 10, f"R² = {r2:.4f}", ln=1)
        pdf.cell(0, 10, f"Generated by {st.session_state.username} on {pd.Timestamp.now()}", ln=1)
        
        # Courbe en image
        buf = io.BytesIO()
        fig.savefig(buf, format="PNG")
        buf.seek(0)
        pdf.image(buf, x=10, y=60, w=180)
        
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        st.download_button("Download PDF", pdf_output, file_name="linearity_report.pdf")
# ---------------------------------------------------
# Signal/Noise Panel
# ---------------------------------------------------
import pytesseract
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image

def sn_panel():
    st.header("🔬 Signal / Noise Analysis")
    
    uploaded_file = st.file_uploader("Upload chromatogram (CSV, PNG, PDF)", type=["csv", "png", "pdf"])
    if not uploaded_file:
        return

    # Lire CSV
    if uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
        x = df.iloc[:,0]
        y = df.iloc[:,1]
        st.line_chart(df)
    
    # Lire PNG
    elif uploaded_file.type == "image/png":
        image = Image.open(uploaded_file)
        st.image(image, caption="Chromatogram")
        st.info("Digitizing feature not implemented for PNG yet.")  # placeholder
    
    # Lire PDF et digitize
    elif uploaded_file.type == "application/pdf":
        try:
            images = convert_from_path(uploaded_file)
            st.image(images[0], caption="Chromatogram (PDF)")
            st.info("Digitizing feature: Click on points manually or via OCR (to implement).")
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            return

    # Sliders pour choisir zone de calcul S/N
    st.subheader("Select region for S/N calculation")
    start = st.slider("Start index", 0, len(y)-1 if uploaded_file.type=="text/csv" else 100, 0)
    end = st.slider("End index", 0, len(y)-1 if uploaded_file.type=="text/csv" else 100, 50)
    
    if uploaded_file.type == "text/csv":
        region_y = y[start:end]
        signal = region_y.max()
        noise = region_y.std()
        sn_classic = signal / noise
        st.write(f"Signal = {signal:.4f}")
        st.write(f"Noise = {noise:.4f}")
        st.write(f"S/N (Classic) = {sn_classic:.4f}")
        
        # LOQ & LOD using S/N 10 and 3
        lod = 3 * noise
        loq = 10 * noise
        st.write(f"LOD = {lod:.4f}")
        st.write(f"LOQ = {loq:.4f}")
    
    # Affichage formules
    if st.button("Show S/N Formulas"):
        st.markdown("""
        **Classic S/N:** S/N = Signal / Noise  
        **USP S/N:** S/N = (H - B) / σ  
        **LOD:** LOD = 3 * σ  
        **LOQ:** LOQ = 10 * σ  
        """)

    st.info("Digitizing for PDF/PNG is planned to extract data points automatically for S/N calculation.")
# ---------------------------------------------------
# Login, Logout, Admin/User Panel & Bilingual Menu
# ---------------------------------------------------

# Dummy users database
users_db = {
    "admin": {"password": "admin123", "role": "admin"},
    "user1": {"password": "user123", "role": "user"},
}

def login():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("role", "")
    st.session_state.setdefault("lang", "EN")

    if not st.session_state.logged_in:
        st.title("🔒 LabT Login")
        lang_choice = st.selectbox("Choose language / Choisir la langue", ["EN", "FR"])
        st.session_state.lang = lang_choice

        username = st.text_input("Username / Nom d'utilisateur")
        password = st.text_input("Password / Mot de passe", type="password")

        if st.button("Login / Connexion"):
            user = users_db.get(username)
            if user and user["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = user["role"]
                st.experimental_rerun()
            else:
                st.error("Invalid credentials / Identifiants invalides")

def logout():
    if st.session_state.logged_in:
        if st.button("Logout / Déconnexion"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.experimental_rerun()

def admin_panel():
    st.header("Admin Panel")
    st.write("Manage users (add / delete / modify).")
    st.write("⚠️ Admin cannot access analysis features.")
    
    if st.button("Add User"):
        st.info("Add User functionality placeholder")
    if st.button("Delete User"):
        st.info("Delete User functionality placeholder")
    if st.button("Modify User"):
        st.info("Modify User functionality placeholder")

def user_panel():
    st.header(f"Welcome {st.session_state.username}!")
    
    # Menu déroulant pour navigation
    menu = st.selectbox("Select Analysis / Sélectionnez l'analyse", ["Linearity / Linéarité", "S/N Analysis / S/N"])
    
    # Retour au menu précédent
    if st.button("Back to Menu / Retour"):
        st.experimental_rerun()
    
    if menu.startswith("Linearity"):
        linear_panel()  # fonction déjà définie
    elif menu.startswith("S/N"):
        sn_panel()  # fonction déjà définie

def main():
    login()
    if st.session_state.logged_in:
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        logout()
        
        if st.session_state.role == "admin":
            admin_panel()
        else:
            user_panel()

if __name__ == "__main__":
    main()
# ----------------------------------------
# PDF Report Generation for Linearity & S/N
# ----------------------------------------
from fpdf import FPDF
from datetime import datetime

def generate_pdf_report(report_type, username, company_name, params):
    """
    report_type: "Linearity" or "S/N"
    username: str
    company_name: str
    params: dict containing relevant calculated values
    """
    if not company_name:
        st.error("Please enter company name / Veuillez saisir le nom de la compagnie")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    # Title
    pdf.cell(0, 10, f"LabT Report - {report_type}", 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    
    # Info
    pdf.cell(0, 10, f"User: {username}", 0, 1)
    pdf.cell(0, 10, f"Company: {company_name}", 0, 1)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.ln(5)

    # Parameters
    pdf.set_font("Arial", '', 11)
    for key, value in params.items():
        pdf.cell(0, 8, f"{key}: {value}", 0, 1)
    
    # Optionally include a chart (saved as image previously)
    if 'chart_path' in params:
        pdf.image(params['chart_path'], x=30, w=150)

    # Save PDF
    filename = f"{report_type}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    st.success(f"Report generated: {filename}")
    st.download_button("Download PDF / Télécharger PDF", filename, file_name=filename)
# ----------------------------------------
# Digitizing Chromatograms & S/N Calculation
# ----------------------------------------
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

def load_chromatogram(file):
    """
    Load chromatogram from CSV, PDF, or PNG
    """
    ext = file.name.split('.')[-1].lower()
    if ext == 'csv':
        df = pd.read_csv(file)
        return df['Time'], df['Signal']
    elif ext == 'png':
        img = Image.open(file)
        return img
    elif ext == 'pdf':
        pages = convert_from_path(file)
        return pages[0]  # take first page for simplicity
    else:
        st.error("Unsupported file format / Format de fichier non supporté")
        return None

def sn_panel():
    st.header("Signal-to-Noise / Rapport Signal sur Bruit")
    
    file = st.file_uploader("Upload chromatogram / Importer chromatogramme", type=['csv', 'png', 'pdf'])
    if file:
        result = load_chromatogram(file)
        if isinstance(result, tuple):
            time, signal = result
            st.line_chart(pd.DataFrame({'Signal': signal}, index=time))
            
            # Sliders to select zone
            st.subheader("Select noise region / Sélectionner zone de bruit")
            t_min, t_max = st.slider("Time range / Plage de temps", float(time.min()), float(time.max()), (float(time.min()), float(time.max())))
            
            # Extract selected zone
            mask = (time >= t_min) & (time <= t_max)
            noise_signal = signal[mask]
            
            # S/N calculation
            sn_classic = signal.max() / noise_signal.std()
            st.write(f"S/N Classic: {sn_classic:.2f}")
            
            # USP S/N if slope available
            if 'slope' in st.session_state:
                sn_usp = (signal.max() - signal.min()) / (noise_signal.std() * st.session_state.slope)
                st.write(f"S/N USP: {sn_usp:.2f}")
        else:
            st.image(result, caption="Chromatogram / Chromatogramme")
# ----------------------------------------
# LOQ / LOD calculations & Formulas display
# ----------------------------------------
def display_sn_formulas():
    """
    Display S/N formulas in a collapsible section
    """
    with st.expander("Show S/N formulas / Afficher formules S/N"):
        st.markdown("""
        **Classic S/N / Classique :**  
        S/N = Maximum signal / Standard deviation of noise  

        **USP S/N :**  
        S/N = (Maximum signal - Minimum signal) / (σ_noise * slope of linearity)  
        """)

def calculate_loq_lod(signal_max, noise_std, slope=None):
    """
    Calculate LOQ and LOD from S/N, optionally using slope
    """
    sn_classic = signal_max / noise_std
    lod_classic = 3.3 * noise_std / slope if slope else None
    loq_classic = 10 * noise_std / slope if slope else None

    results = {
        "S/N Classic": sn_classic,
        "LOD Classic": lod_classic,
        "LOQ Classic": loq_classic
    }

    if slope:
        sn_usp = (signal_max) / (noise_std * slope)
        lod_usp = 3.3 * noise_std / slope
        loq_usp = 10 * noise_std / slope
        results.update({
            "S/N USP": sn_usp,
            "LOD USP": lod_usp,
            "LOQ USP": loq_usp
        })
    return results

def sn_panel_extended():
    st.header("Signal-to-Noise / Rapport Signal sur Bruit")
    display_sn_formulas()

    file = st.file_uploader("Upload chromatogram / Importer chromatogramme", type=['csv', 'png', 'pdf'])
    if file:
        result = load_chromatogram(file)
        if isinstance(result, tuple):
            time, signal = result
            st.line_chart(pd.DataFrame({'Signal': signal}, index=time))

            st.subheader("Select noise region / Sélectionner zone de bruit")
            t_min, t_max = st.slider("Time range / Plage de temps", float(time.min()), float(time.max()), (float(time.min()), float(time.max())))
            mask = (time >= t_min) & (time <= t_max)
            noise_signal = signal[mask]

            # Retrieve slope from linearity if available
            slope = st.session_state.get('slope', None)
            results = calculate_loq_lod(signal.max(), noise_signal.std(), slope)
            for k, v in results.items():
                if v is not None:
                    st.write(f"{k}: {v:.2f}")
        else:
            st.image(result, caption="Chromatogram / Chromatogramme")
# ----------------------------------------
# Linear regression panel & PDF report
# ----------------------------------------
def linear_panel():
    st.header("Linearity / Linéarité")

    # Choix CSV ou saisie manuelle
    input_method = st.radio("Input method / Méthode de saisie", ["CSV", "Manual / Manuel"])
    
    if input_method == "CSV":
        file = st.file_uploader("Upload CSV / Importer CSV", type=['csv'])
        if file:
            df = pd.read_csv(file)
    else:
        # Saisie manuelle
        x_input = st.text_area("Enter X values separated by comma / Entrez X séparés par des virgules")
        y_input = st.text_area("Enter Y values separated by comma / Entrez Y séparés par des virgules")
        try:
            x_vals = [float(i.strip()) for i in x_input.split(",")]
            y_vals = [float(i.strip()) for i in y_input.split(",")]
            df = pd.DataFrame({'X': x_vals, 'Y': y_vals})
        except:
            st.warning("Check your inputs / Vérifiez vos saisies")
            return

    if 'X' in df.columns and 'Y' in df.columns:
        slope, intercept, r2 = linear_regression(df["X"], df["Y"])
        st.session_state['slope'] = slope  # Export slope to S/N panel
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode='markers', name='Data'))
        fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"] + intercept, mode='lines', name='Fit'))
        st.plotly_chart(fig)
        st.write(f"Equation / Équation: Y = {slope:.4f}X + {intercept:.4f}")
        st.write(f"R²: {r2:.4f}")

        # Calculate unknown concentration from signal
        mode = st.selectbox("Calculate / Calculer", ["Concentration from Signal / Conc. à partir du Signal", 
                                                      "Signal from Concentration / Signal à partir de la Conc."])
        value = st.number_input("Enter value / Entrez la valeur")
        if mode.startswith("Concentration"):
            conc = (value - intercept) / slope
            st.write(f"Concentration: {conc:.4f}")
        else:
            signal_pred = slope*value + intercept
            st.write(f"Predicted signal / Signal prédit: {signal_pred:.4f}")

        # Export PDF report
        company_name = st.text_input("Company name / Nom de la compagnie")
        if st.button("Generate PDF report / Générer rapport PDF"):
            if not company_name.strip():
                st.warning("Please enter company name / Entrez le nom de la compagnie")
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, "Linearity Report / Rapport Linéarité", ln=True, align='C')
                pdf.set_font("Arial", '', 12)
                pdf.ln(10)
                pdf.cell(0, 10, f"Company / Compagnie: {company_name}", ln=True)
                pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
                pdf.cell(0, 10, f"Equation / Équation: Y = {slope:.4f}X + {intercept:.4f}", ln=True)
                pdf.cell(0, 10, f"R²: {r2:.4f}", ln=True)
                pdf.output("linearity_report.pdf")
                st.success("PDF report generated! / Rapport PDF généré !")
# ----------------------------------------
# Login & Main menu
# ----------------------------------------
def login():
    st.title("LabT")  # Logo banner
    st.text("Powered by BnB")  # Only on login page
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    language = st.selectbox("Language / Langue", ["English", "Français"])
    
    if st.button("Login / Connexion"):
        if username in st.session_state['users'] and st.session_state['users'][username]['password'] == password:
            st.session_state['logged_in'] = username
            st.session_state['language'] = language
            st.experimental_rerun()
        else:
            st.warning("Invalid credentials / Identifiants invalides")

def logout():
    st.session_state['logged_in'] = None
    st.experimental_rerun()

def main_menu():
    st.sidebar.title("Menu")
    st.sidebar.button("Logout / Déconnexion", on_click=logout)
    
    user = st.session_state.get('logged_in', None)
    if user:
        role = st.session_state['users'][user]['role']
        if role == "admin":
            st.sidebar.subheader("Admin Panel / Panneau Admin")
            if st.sidebar.button("Manage Users / Gestion des utilisateurs"):
                manage_users_panel()
        else:
            st.sidebar.subheader("User Panel / Panneau Utilisateur")
            if st.sidebar.button("Linearity / Linéarité"):
                linear_panel()
            if st.sidebar.button("S/N Panel"):
                sn_panel()
# ----------------------------------------
# Signal-to-Noise Panel
# ----------------------------------------
from pdf2image import convert_from_path
import pytesseract
import cv2
from PIL import Image

def sn_panel():
    st.header("Signal-to-Noise Panel / Panneau S/N")
    
    st.subheader("Upload chromatogram / Importer chromatogramme")
    file = st.file_uploader("Choose CSV, PDF or PNG", type=["csv", "pdf", "png"])
    
    if file:
        # CSV
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            st.line_chart(df['Signal'])
        
        # PDF
        elif file.name.endswith(".pdf"):
            images = convert_from_path(file)
            st.image(images[0])
            img_cv = cv2.cvtColor(np.array(images[0]), cv2.COLOR_RGB2BGR)
            # Digitizing example using pytesseract if needed
            extracted_text = pytesseract.image_to_string(img_cv)
            st.text_area("Digitized data / Données extraites", value=extracted_text, height=200)
        
        # PNG
        elif file.name.endswith(".png"):
            img = Image.open(file)
            st.image(img)
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            extracted_text = pytesseract.image_to_string(img_cv)
            st.text_area("Digitized data / Données extraites", value=extracted_text, height=200)
        
        # Zone selection for S/N
        st.subheader("Select zone for S/N calculation / Sélectionner zone pour S/N")
        start = st.slider("Start / Début", 0, 100, 0)
        end = st.slider("End / Fin", 0, 100, 100)
        
        # Display formulas
        if st.button("Show S/N formulas / Voir les formules S/N"):
            st.markdown("""
            **Classical S/N:** S/N = (Signal_max - Signal_blank) / Noise  
            **USP S/N:** S/N = Height / StdDev(noise)  
            LOQ = 10 * σ / slope  
            LOD = 3.3 * σ / slope
            """)
        
        st.subheader("Slope from Linearity / Pente de linéarité")
        slope = st.number_input("Enter slope / Entrer pente", value=1.0)
        st.write(f"Slope exported for calculations / Pente exportée : {slope}")
# ----------------------------------------
# Linearity Panel / Panneau Linéarité
# ----------------------------------------
from io import StringIO
from datetime import datetime
from fpdf import FPDF
import plotly.graph_objects as go

def linear_panel():
    st.header("Linearity Panel / Panneau Linéarité")
    
    company_name = st.text_input("Company name / Nom de la compagnie")
    if not company_name:
        st.warning("Please enter company name / Veuillez entrer le nom de la compagnie")
        return
    
    # Input mode
    mode = st.radio("Input data / Mode de saisie", ["CSV", "Manual / Manuel"])
    
    df = None
    if mode == "CSV":
        file = st.file_uploader("Upload CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        st.write("Enter X and Y separated by commas / Entrer X et Y séparés par des virgules")
        x_raw = st.text_area("X values")
        y_raw = st.text_area("Y values")
        try:
            x = [float(i.strip()) for i in x_raw.split(",") if i.strip() != ""]
            y = [float(i.strip()) for i in y_raw.split(",") if i.strip() != ""]
            df = pd.DataFrame({"X": x, "Y": y})
        except:
            st.error("Invalid input / Entrée invalide")
            return
    
    if df is not None and not df.empty:
        # Linear regression
        slope, intercept, r2 = linear_regression(df["X"], df["Y"])
        
        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode='markers', name='Data'))
        fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode='lines', name='Fit'))
        st.plotly_chart(fig)
        
        st.write(f"Equation / Équation: y = {slope:.4f} x + {intercept:.4f}")
        st.write(f"R²: {r2:.4f}")
        
        # Calculate unknown concentration
        st.subheader("Calculate unknown concentration / Calculer concentration inconnue")
        unknown_mode = st.selectbox("Mode / Mode", ["Signal → Concentration", "Concentration → Signal"])
        if unknown_mode == "Signal → Concentration":
            sig = st.number_input("Signal value / Valeur du signal")
            conc = (sig - intercept)/slope
            st.write(f"Calculated concentration / Concentration calculée: {conc:.4f}")
        else:
            conc = st.number_input("Concentration value / Valeur de la concentration")
            sig = slope*conc + intercept
            st.write(f"Predicted signal / Signal prédit: {sig:.4f}")
        
        # Units
        unit = st.selectbox("Unit / Unité", ["µg/mL", "mg/mL", "ng/mL"])
        
        # Generate PDF report
        if st.button("Generate PDF report / Générer rapport PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Linearity Report / Rapport de linéarité", ln=1)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Company: {company_name}", ln=1)
            pdf.cell(0, 10, f"Generated by: {st.session_state.get('username', 'User')}", ln=1)
            pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1)
            pdf.cell(0, 10, f"Equation: y = {slope:.4f} x + {intercept:.4f}", ln=1)
            pdf.cell(0, 10, f"R² = {r2:.4f}", ln=1)
            pdf.output("linearity_report.pdf")
            st.success("PDF report generated / Rapport PDF généré : linearity_report.pdf")
# ----------------------------------------
# Login & User Panel / Connexion et panneau utilisateur
# ----------------------------------------
def login():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("role", "user")
    st.session_state.setdefault("language", "English")
    
    st.title("LabT Login / Connexion")
    
    # Language selection
    lang = st.selectbox("Select language / Choisir langue", ["English", "Français"])
    st.session_state.language = lang
    
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    
    if st.button("Login / Connexion"):
        # Check credentials (simple example, replace with proper DB)
        if username == "admin" and password == "admin":
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = "admin"
            st.experimental_rerun()
        elif username == "user" and password == "user":
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = "user"
            st.experimental_rerun()
        else:
            st.error("Invalid credentials / Identifiants invalides")

def logout():
    if st.session_state.get("logged_in"):
        if st.button("Logout / Déconnexion"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = "user"
            st.experimental_rerun()

def user_panel():
    st.sidebar.title(f"Welcome / Bienvenue: {st.session_state.username}")
    logout()
    
    if st.session_state.role == "admin":
        st.header("Admin Panel / Panneau Admin")
        st.write("Manage users only / Gérer uniquement les utilisateurs")
        if st.button("Add User / Ajouter un utilisateur"):
            st.info("Functionality to add user goes here")
        if st.button("Delete User / Supprimer un utilisateur"):
            st.info("Functionality to delete user goes here")
        if st.button("Modify User / Modifier un utilisateur"):
            st.info("Functionality to modify user goes here")
    else:
        st.header("User Panel / Panneau Utilisateur")
        menu = st.sidebar.selectbox("Menu", ["Linearity / Linéarité", "S/N"])
        if menu == "Linearity / Linéarité":
            linear_panel()
        elif menu == "S/N":
            sn_panel()  # à définir dans la partie S/N.

# ----------------------------------------
# Signal-to-Noise Panel / Volet S/N
# ----------------------------------------
import pytesseract
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image

def sn_panel():
    st.header("Signal-to-Noise / Rapport Signal sur Bruit")
    
    # Import chromatogram
    file = st.file_uploader("Upload chromatogram (CSV, PDF, PNG) / Importer chromatogramme (CSV, PDF, PNG)",
                            type=["csv","pdf","png"])
    if file is not None:
        data = None
        if file.name.endswith(".csv"):
            data = pd.read_csv(file)
            st.success("CSV loaded successfully / CSV chargé avec succès")
        elif file.name.endswith(".png"):
            img = Image.open(file)
            st.image(img, caption="Chromatogram / Chromatogramme")
            # Digitizing PNG
            st.info("Digitizing functionality for PNG (manual extraction) goes here")
        elif file.name.endswith(".pdf"):
            try:
                pages = convert_from_path(file)
                st.image(pages[0], caption="First page PDF / Première page PDF")
                # Digitizing PDF
                st.info("Digitizing functionality for PDF (manual extraction) goes here")
            except Exception as e:
                st.error(f"Error loading PDF / Erreur PDF: {e}")
        
        if data is not None:
            # Sliders to select zone for S/N calculation
            st.subheader("Select zone / Choisir la zone pour S/N")
            start = st.slider("Start index / Début", 0, len(data)-1, 0)
            end = st.slider("End index / Fin", 0, len(data)-1, len(data)-1)
            
            signal_zone = data.iloc[start:end]["Signal"]
            noise_zone = data.iloc[start:end]["Signal"]  # à remplacer par zone de bruit si différente
            
            # Calculate S/N
            sn_classic = signal_zone.mean() / noise_zone.std()
            sn_usp = (signal_zone.max() - signal_zone.min()) / (2 * noise_zone.std())
            
            st.subheader("S/N Results / Résultats S/N")
            st.write(f"Classical / Classique: {sn_classic:.2f}")
            st.write(f"USP: {sn_usp:.2f}")
            
            # Display formulas
            if st.button("Show formulas / Afficher formules"):
                st.markdown("""
                **Classical / Classique:** S/N = Mean(signal) / Std(noise)  
                **USP:** S/N = (Max(signal) - Min(signal)) / (2 * Std(noise))
                """)
            
            # Use linearity slope if available
            if "slope" in st.session_state:
                slope = st.session_state.slope
                st.write(f"Using slope from linearity / Utilisation pente linéarité: {slope:.4f}")
                lod = 3.3 * noise_zone.std() / slope
                loq = 10 * noise_zone.std() / slope
                st.write(f"LOD: {lod:.4f}, LOQ: {loq:.4f}")
            
            # Export S/N report as PDF
            if st.button("Generate PDF report / Générer rapport PDF"):
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(0, 10, f"User: {st.session_state.username}", ln=True)
                pdf.cell(0, 10, f"Date: {pd.Timestamp.now()}", ln=True)
                pdf.cell(0, 10, f"S/N Classical: {sn_classic:.2f}", ln=True)
                pdf.cell(0, 10, f"S/N USP: {sn_usp:.2f}", ln=True)
                if "slope" in st.session_state:
                    pdf.cell(0, 10, f"Linearity slope: {slope:.4f}", ln=True)
                    pdf.cell(0, 10, f"LOD: {lod:.4f}, LOQ: {loq:.4f}", ln=True)
                pdf_file = "/tmp/sn_report.pdf"
                pdf.output(pdf_file)
                st.success("PDF report generated / Rapport PDF généré")
                st.download_button("Download PDF / Télécharger PDF", pdf_file, "sn_report.pdf")
# ----------------------------------------
# Linearity Panel / Volet Linéarité
# ----------------------------------------
def linear_panel():
    st.header("Linearity / Linéarité")
    
    # Nom de la compagnie
    company = st.text_input("Company Name / Nom de la compagnie")
    if not company:
        st.warning("Please enter company name / Veuillez saisir le nom de la compagnie")
    
    # Input: CSV or manual
    input_type = st.radio("Input type / Type de saisie", ["CSV", "Manual / Manuel"])
    
    df = None
    if input_type == "CSV":
        file = st.file_uploader("Upload CSV (X,Y) / Importer CSV (X,Y)", type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        x_str = st.text_area("X values separated by commas / Valeurs X séparées par des virgules")
        y_str = st.text_area("Y values separated by commas / Valeurs Y séparées par des virgules")
        try:
            x = [float(i) for i in x_str.split(",")]
            y = [float(i) for i in y_str.split(",")]
            df = pd.DataFrame({"X": x, "Y": y})
        except:
            st.warning("Invalid input / Entrée invalide")
    
    if df is not None and len(df) > 1:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        
        X = df["X"].values.reshape(-1,1)
        Y = df["Y"].values
        model = LinearRegression()
        model.fit(X,Y)
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = model.score(X,Y)
        
        st.session_state.slope = slope  # export slope to S/N panel
        
        # Plot
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.scatter(df["X"], df["Y"], label="Data points")
        ax.plot(df["X"], model.predict(X), color="red", label="Fit line")
        ax.set_xlabel(f"Concentration ({st.selectbox('Unit / Unité',['µg/mL','mg/mL','ng/mL'])})")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)
        
        st.write(f"Equation: Y = {slope:.4f} X + {intercept:.4f}")
        st.write(f"R²: {r2:.4f}")
        
        # Calculate unknown concentration ↔ signal
        mode = st.selectbox("Calculate / Calculer", ["Concentration from Signal / Concentration à partir du signal",
                                                      "Signal from Concentration / Signal à partir de la concentration"])
        if mode.startswith("Concentration"):
            s = st.number_input("Enter Signal / Entrer le signal")
            conc = (s - intercept)/slope
            st.write(f"Concentration: {conc:.4f}")
        else:
            c = st.number_input("Enter Concentration / Entrer la concentration")
            sig = slope * c + intercept
            st.write(f"Signal: {sig:.4f}")
        
        # Generate PDF report
        if st.button("Generate PDF report / Générer rapport PDF"):
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"Company: {company}", ln=True)
            pdf.cell(0, 10, f"User: {st.session_state.username}", ln=True)
            pdf.cell(0, 10, f"Date: {pd.Timestamp.now()}", ln=True)
            pdf.cell(0, 10, f"Equation: Y = {slope:.4f} X + {intercept:.4f}", ln=True)
            pdf.cell(0, 10, f"R²: {r2:.4f}", ln=True)
            pdf_file = "/tmp/linearity_report.pdf"
            pdf.output(pdf_file)
            st.success("PDF report generated / Rapport PDF généré")
            st.download_button("Download PDF / Télécharger PDF", pdf_file, "linearity_report.pdf")
# ----------------------------------------
# Login and User/Admin Menu
# ----------------------------------------
def login():
    st.title("LabT")
    st.markdown("<small>Powered by BnB</small>", unsafe_allow_html=True)
    
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    
    if "users" not in st.session_state:
        st.session_state.users = {"admin": {"password":"admin", "role":"admin"},
                                  "user1": {"password":"user1", "role":"user"}}
    
    if st.button("Login / Connexion"):
        if username in st.session_state.users and st.session_state.users[username]["password"]==password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = st.session_state.users[username]["role"]
            st.experimental_rerun()
        else:
            st.error("Invalid username or password / Nom d'utilisateur ou mot de passe invalide")

def logout():
    for key in ["logged_in","username","role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()

def user_panel():
    st.sidebar.button("Logout / Déconnexion", on_click=logout)
    lang = st.sidebar.selectbox("Language / Langue", ["English", "Français"])
    st.session_state.lang = lang
    
    menu = st.sidebar.radio("Menu", ["Linearity / Linéarité", "Signal-to-Noise / S/N"])
    
    if menu.startswith("Linearity"):
        linear_panel()
    else:
        sn_panel()  # Partie S/N à inclure séparément

def admin_panel():
    st.sidebar.button("Logout / Déconnexion", on_click=logout)
    st.sidebar.selectbox("Language / Langue", ["English", "Français"])
    st.header("Admin: User Management / Gestion des utilisateurs")
    
    if st.button("Add User / Ajouter utilisateur"):
        new_user = st.text_input("New Username / Nom d'utilisateur")
        new_pass = st.text_input("Password / Mot de passe", type="password")
        role = st.selectbox("Role", ["user","admin"])
        if new_user and new_pass:
            st.session_state.users[new_user] = {"password":new_pass,"role":role}
            st.success(f"User {new_user} added / ajouté")
    
    if st.button("Remove User / Supprimer utilisateur"):
        del_user = st.selectbox("Select user / Choisir utilisateur", list(st.session_state.users.keys()))
        if del_user:
            st.session_state.users.pop(del_user)
            st.success(f"User {del_user} removed / supprimé")

def main():
    if "logged_in" not in st.session_state:
        login()
    else:
        if st.session_state.role == "admin":
            admin_panel()
        else:
            user_panel()

if __name__=="__main__":
    main()
# ----------------------------------------
# Signal-to-Noise Panel / Volet S/N
# ----------------------------------------
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

def sn_panel():
    st.header("Signal-to-Noise / S/N")
    
    # --- Import file ---
    file = st.file_uploader("Upload chromatogram CSV, PDF or PNG / Importer chromatogramme CSV, PDF ou PNG", type=["csv","pdf","png"])
    
    if file:
        df = None
        if file.type == "text/csv":
            try:
                df = pd.read_csv(file)
            except Exception as e:
                st.error(f"CSV parsing error: {e}")
        elif file.type == "application/pdf":
            images = convert_from_path(file)
            text = ""
            for img in images:
                text += pytesseract.image_to_string(img)
            # Transformation text -> dataframe selon format CSV (à adapter selon PDF)
            df = pd.read_csv(pd.compat.StringIO(text))
        elif file.type.startswith("image"):
            img = Image.open(file)
            text = pytesseract.image_to_string(img)
            df = pd.read_csv(pd.compat.StringIO(text))
        
        if df is not None:
            st.subheader("Chromatogram preview / Aperçu chromatogramme")
            st.line_chart(df["Signal"])
            
            # --- Select zone for S/N ---
            min_index = int(df.index.min())
            max_index = int(df.index.max())
            start = st.slider("Start index / Début", min_value=min_index, max_value=max_index, value=min_index)
            end = st.slider("End index / Fin", min_value=min_index, max_value=max_index, value=max_index)
            
            signal_zone = df["Signal"].iloc[start:end]
            noise_zone = df["Signal"].iloc[min_index:max_index].drop(signal_zone.index)
            
            # --- S/N calculations ---
            sn_classic = signal_zone.max()/noise_zone.std()
            sn_usp = (signal_zone.max() - noise_zone.mean())/noise_zone.std()
            
            st.write(f"Classic S/N: {sn_classic:.2f}")
            st.write(f"USP S/N: {sn_usp:.2f}")
            
            # --- LOQ / LOD ---
            slope = st.session_state.get("linear_slope", None)
            if slope:
                lod = 3.3 * (noise_zone.std()) / slope
                loq = 10 * (noise_zone.std()) / slope
                st.write(f"LOD (from slope): {lod:.2f}")
                st.write(f"LOQ (from slope): {loq:.2f}")
            
            # --- Show formulas ---
            if st.button("Show S/N formulas / Voir formules S/N"):
                st.markdown("""
                **Classic S/N:** Signal_max / Noise_std  
                **USP S/N:** (Signal_max - Noise_mean) / Noise_std  
                **LOD:** 3.3 * (σ / slope)  
                **LOQ:** 10 * (σ / slope)
                """)
# ----------------------------------------
# Linearity Panel / Volet Linéarité
# ----------------------------------------
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime

def linear_panel():
    st.header("Linearity / Linéarité")
    
    # --- Nom de la compagnie ---
    company = st.text_input("Company name / Nom de la compagnie")
    if not company:
        st.warning("Please enter the company name / Veuillez saisir le nom de la compagnie")
    
    # --- Import CSV or manual input ---
    input_method = st.radio("Input method / Méthode de saisie", ["CSV", "Manual / Manuel"])
    
    df = None
    if input_method == "CSV":
        file = st.file_uploader("Upload CSV / Importer CSV", type="csv")
        if file:
            df = pd.read_csv(file)
    else:
        x_input = st.text_area("Enter X values separated by commas / Saisir valeurs X séparées par des virgules")
        y_input = st.text_area("Enter Y values separated by commas / Saisir valeurs Y séparées par des virgules")
        if x_input and y_input:
            try:
                X = [float(i.strip()) for i in x_input.split(",")]
                Y = [float(i.strip()) for i in y_input.split(",")]
                df = pd.DataFrame({"X": X, "Y": Y})
            except:
                st.error("Invalid input. Check your numbers / Entrée invalide. Vérifiez vos nombres")
    
    if df is not None and company:
        # --- Linear regression ---
        slope, intercept = np.polyfit(df["X"], df["Y"], 1)
        r2 = np.corrcoef(df["X"], df["Y"])[0,1]**2
        
        st.session_state["linear_slope"] = slope  # export slope to S/N panel
        
        # --- Plot ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode='markers', name='Data'))
        fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode='lines', name='Fit'))
        st.plotly_chart(fig)
        
        # --- Display equation and R² ---
        st.write(f"Equation: Y = {slope:.4f}*X + {intercept:.4f}")
        st.write(f"R² = {r2:.4f}")
        
        # --- Unknown calculation ---
        calc_type = st.selectbox("Calculate / Calculer", ["Concentration from signal / Concentration à partir du signal",
                                                          "Signal from concentration / Signal à partir de la concentration"])
        input_value = st.number_input("Enter value / Entrer valeur", min_value=0.0)
        if st.button("Compute / Calculer"):
            if calc_type.startswith("Concentration"):
                conc = (input_value - intercept)/slope
                st.write(f"Calculated concentration: {conc:.4f}")
            else:
                signal = slope*input_value + intercept
                st.write(f"Calculated signal: {signal:.4f}")
        
        # --- Unit selection ---
        unit = st.selectbox("Unit / Unité", ["µg/mL", "mg/mL", "ng/mL"])
        
        # --- Generate PDF report ---
        if st.button("Generate PDF / Générer PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Linearity Report / Rapport de Linéarité", ln=1, align='C')
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Company / Société: {company}", ln=1)
            pdf.cell(0, 10, f"User: {st.session_state.get('username','Unknown')}", ln=1)
            pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1)
            pdf.cell(0, 10, f"Equation: Y = {slope:.4f}*X + {intercept:.4f}", ln=1)
            pdf.cell(0, 10, f"R² = {r2:.4f}", ln=1)
            pdf.output("/mnt/data/Linearity_Report.pdf")
            st.success("PDF generated / PDF généré. [Download here](./mnt/data/Linearity_Report.pdf)")
# ----------------------------------------
# Login / Connexion
# ----------------------------------------
def login():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("role", "")
    
    # --- Logo et banner ---
    st.image("LabT_logo.png", width=200)
    st.caption("Powered by BnB")
    
    # --- Language selection / Sélection langue ---
    language = st.selectbox("Language / Langue", ["English", "Français"])
    
    if not st.session_state["logged_in"]:
        st.subheader("Login / Connexion")
        username = st.text_input("Username / Nom d'utilisateur")
        password = st.text_input("Password / Mot de passe", type="password")
        if st.button("Login / Se connecter"):
            users_db = {
                "admin": {"password": "adminpass", "role": "admin"},
                "user1": {"password": "userpass", "role": "user"}
            }
            if username in users_db and password == users_db[username]["password"]:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = users_db[username]["role"]
                st.success("Logged in successfully / Connecté")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials / Identifiants incorrects")
    else:
        # --- Menu principal ---
        st.sidebar.title(f"Menu - {st.session_state['username']}")
        if st.session_state["role"] == "admin":
            st.sidebar.subheader("Admin Panel")
            if st.sidebar.button("Add User / Ajouter user"):
                st.info("Add user functionality here")
            if st.sidebar.button("Delete User / Supprimer user"):
                st.info("Delete user functionality here")
            if st.sidebar.button("Modify User / Modifier user"):
                st.info("Modify user functionality here")
        else:
            st.sidebar.subheader("User Panel")
            if st.sidebar.button("Linearity / Linéarité"):
                linear_panel()
            if st.sidebar.button("S/N"):
                sn_panel()
        
        if st.sidebar.button("Logout / Déconnexion"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["role"] = ""
            st.experimental_rerun()
        
        if st.sidebar.button("Back / Retour"):
            st.experimental_rerun()
# =========================
# Partie 21 : Panel S/N
# =========================

import streamlit as st
import pandas as pd
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io
import plotly.graph_objects as go

def sn_panel(slope=None):
    st.header("S/N Calculation / Calcul S/N")
    
    # Importation du chromatogramme
    file = st.file_uploader("Upload chromatogram (CSV, PDF, PNG)", type=["csv", "pdf", "png"])
    
    df = None
    if file:
        if file.name.endswith(".csv"):
            try:
                df = pd.read_csv(file)
            except Exception as e:
                st.error(f"Erreur CSV: {e}")
        elif file.name.endswith(".pdf"):
            try:
                images = convert_from_path(file)
                st.info(f"{len(images)} page(s) détectée(s)")
                image = images[0]  # Utilisation de la première page
                df = extract_signal_from_image(image)
            except Exception as e:
                st.error(f"Erreur PDF: {e}")
        elif file.name.endswith(".png"):
            try:
                image = Image.open(file)
                df = extract_signal_from_image(image)
            except Exception as e:
                st.error(f"Erreur PNG: {e}")

    if df is not None:
        st.success("Chromatogram loaded successfully!")

        # Affichage graphique interactif avec Plotly
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Signal"], mode='lines', name='Chromatogram'))
        st.plotly_chart(fig, use_container_width=True)

        # Sliders pour sélectionner la zone de bruit et de pic
        start_noise, end_noise = st.slider("Select Noise Zone", float(df["Time"].min()), float(df["Time"].max()), (float(df["Time"].min()), float(df["Time"].min()+1)))
        start_peak, end_peak = st.slider("Select Peak Zone", float(df["Time"].min()), float(df["Time"].max()), (float(df["Time"].min()), float(df["Time"].min()+1)))

        # Extraction des zones
        noise_zone = df[(df["Time"] >= start_noise) & (df["Time"] <= end_noise)]["Signal"]
        peak_zone = df[(df["Time"] >= start_peak) & (df["Time"] <= end_peak)]["Signal"]

        noise = noise_zone.std()
        peak_height = peak_zone.max() - noise_zone.mean()  # approx hauteur du pic

        # Calcul S/N classique et USP
        sn_classic = peak_height / noise
        sn_usp = sn_classic * (1 if slope is None else slope)  # Si slope fournie, utilisée pour conversion en concentration

        st.write(f"**S/N classique :** {sn_classic:.2f}")
        st.write(f"**S/N USP :** {sn_usp:.2f}")
        
        # Affichage des formules
        if st.checkbox("Show formulas / Afficher les formules"):
            st.markdown("""
            **S/N classique :** \( \frac{Hauteur\ du\ pic}{Écart-type\ du\ bruit} \)  
            **S/N USP :** \( S/N_{classique} \times pente\ (de\ la\ linéarité) \)
            """)

        # Bouton pour exporter PDF avec S/N
        if st.button("Generate PDF report / Générer rapport PDF"):
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "S/N Report", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"S/N classique: {sn_classic:.2f}", ln=True)
            pdf.cell(0, 10, f"S/N USP: {sn_usp:.2f}", ln=True)
            pdf.output("/tmp/sn_report.pdf")
            st.success("PDF generated! Download link:")
            st.download_button("Download PDF", "/tmp/sn_report.pdf", file_name="sn_report.pdf")

# Fonction utilitaire pour extraire signal d'une image (digitizing)
def extract_signal_from_image(image):
    gray = image.convert('L')
    text = pytesseract.image_to_string(gray)
    # Simplifié: rechercher des paires Time-Signal dans le texte OCR
    data = []
    for line in text.split("\n"):
        if line.strip() == "":
            continue
        parts = line.replace(",", ".").split()
        if len(parts) >= 2:
            try:
                t = float(parts[0])
                s = float(parts[1])
                data.append((t, s))
            except:
                continue
    df = pd.DataFrame(data, columns=["Time", "Signal"])
    return df
# =========================
# Partie 22 : Intégration Linéarité + S/N
# =========================

def main_panel():
    st.title("LabT Application")
    # Menu déroulant bilingue
    language = st.selectbox("Language / Langue", ["English", "Français"])
    
    menu = st.radio("Select Module / Sélectionner le module", ["Linearity / Linéarité", "S/N Calculation / Calcul S/N"])
    
    slope = None  # pour passer à S/N

    if menu.startswith("Linearity"):
        # Panel linéarité
        slope = linear_panel()
    else:
        # Panel S/N
        sn_panel(slope=slope)

# Exemple de linear_panel simplifié
def linear_panel():
    st.header("Linearity / Linéarité")
    
    input_method = st.radio("Input data / Saisie des données", ["CSV Upload", "Manual Entry / Saisie manuelle"])
    
    df = None
    if input_method == "CSV Upload":
        file = st.file_uploader("Upload CSV", type="csv")
        if file:
            try:
                df = pd.read_csv(file)
            except Exception as e:
                st.error(f"Erreur CSV: {e}")
    else:
        manual_input = st.text_area("Enter X,Y values separated by commas / Entrez X,Y séparés par des virgules")
        if manual_input:
            data = []
            for line in manual_input.split("\n"):
                parts = line.replace(",", ".").split(",")
                if len(parts) >= 2:
                    try:
                        x = float(parts[0])
                        y = float(parts[1])
                        data.append((x, y))
                    except:
                        continue
            df = pd.DataFrame(data, columns=["X", "Y"])
    
    if df is not None and len(df) > 1:
        # Calcul régression linéaire
        slope, intercept, r2 = linear_regression(df["X"], df["Y"])
        
        # Affichage graphique
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode="markers", name="Data"))
        fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode="lines", name="Fit"))
        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"Equation: Y = {slope:.4f} X + {intercept:.4f}")
        st.write(f"R² = {r2:.4f}")
        
        # Export PDF
        if st.button("Generate Linearity PDF / Générer PDF Linéarité"):
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Linearity Report", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Equation: Y = {slope:.4f} X + {intercept:.4f}", ln=True)
            pdf.cell(0, 10, f"R² = {r2:.4f}", ln=True)
            pdf.output("/tmp/linearity_report.pdf")
            st.success("PDF generated!")
            st.download_button("Download PDF", "/tmp/linearity_report.pdf", file_name="linearity_report.pdf")
        
        return slope  # retour de la pente pour S/N
    else:
        st.warning("Please enter at least 2 points / Entrez au moins 2 points")
        return None

# Fonction de régression linéaire
def linear_regression(x, y):
    import numpy as np
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    y_pred = m*x + c
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res/ss_tot
    return m, c, r2
# =========================
# Partie 23 : Authentification & Gestion Users/Admin
# =========================

import streamlit as st
import json
import hashlib
from datetime import datetime

# ---------- Helpers ----------
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {"admin": {"password": hashlib.sha256("admin".encode()).hexdigest(), "role": "admin"}}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def check_password(username, password):
    users = load_users()
    if username in users:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        return hashed == users[username]["password"]
    return False

def get_role(username):
    users = load_users()
    return users.get(username, {}).get("role", None)

# ---------- Login ----------
def login_page():
    st.title("LabT Login / Connexion")
    st.write("Powered by BnB")
    
    username = st.text_input("Username / Nom d'utilisateur")
    password = st.text_input("Password / Mot de passe", type="password")
    
    if st.button("Login / Connexion"):
        if check_password(username, password):
            st.session_state["user"] = username
            st.session_state["role"] = get_role(username)
            st.experimental_rerun()
        else:
            st.error("Invalid credentials / Identifiants invalides")

# ---------- Logout ----------
def logout():
    if st.button("Logout / Déconnexion"):
        st.session_state.pop("user", None)
        st.session_state.pop("role", None)
        st.experimental_rerun()

# ---------- Admin Panel ----------
def admin_panel():
    st.header("Admin Panel / Gestion des utilisateurs")
    users = load_users()
    
    for user, data in users.items():
        st.write(f"User: {user} - Role: {data['role']}")
        if user != "admin":
            if st.button(f"Delete {user}"):
                del users[user]
                save_users(users)
                st.experimental_rerun()
    
    new_user = st.text_input("New Username / Nouvel utilisateur")
    new_password = st.text_input("Password / Mot de passe", type="password")
    new_role = st.selectbox("Role / Rôle", ["user", "admin"])
    if st.button("Add User / Ajouter utilisateur"):
        if new_user and new_password:
            users[new_user] = {"password": hashlib.sha256(new_password.encode()).hexdigest(), "role": new_role}
            save_users(users)
            st.experimental_rerun()

# ---------- Main App ----------
def main():
    st.set_page_config(page_title="LabT", layout="wide")
    
    if "user" not in st.session_state:
        login_page()
    else:
        st.sidebar.write(f"Logged in as: {st.session_state['user']}")
        logout()
        
        if st.session_state.get("role") == "admin":
            admin_panel()
        else:
            main_panel()  # Partie 22 : Linéarité + S/N

if __name__ == "__main__":
    main()
# =========================
# Partie 24 : Digitizing et S/N
# =========================

import streamlit as st
import pandas as pd
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io

# ---------- Helpers ----------
def read_csv(file):
    try:
        df = pd.read_csv(file)
        return df
    except Exception as e:
        st.error(f"CSV Error: {e}")
        return None

def extract_from_image(image):
    text = pytesseract.image_to_string(image)
    data = []
    for line in text.splitlines():
        if "," in line or "\t" in line:
            parts = line.replace("\t", ",").split(",")
            try:
                x, y = float(parts[0]), float(parts[1])
                data.append([x, y])
            except:
                pass
    return pd.DataFrame(data, columns=["X","Y"])

def extract_from_pdf(file):
    images = convert_from_path(file)
    all_data = pd.DataFrame(columns=["X","Y"])
    for img in images:
        df = extract_from_image(img)
        all_data = pd.concat([all_data, df])
    return all_data.reset_index(drop=True)

# ---------- S/N Calculations ----------
def sn_classic(signal_peak, signal_noise):
    return signal_peak / signal_noise

def sn_usp(signal_peak, std_noise):
    return signal_peak / std_noise

# ---------- Panel S/N ----------
def sn_panel():
    st.header("Signal-to-Noise / Rapport signal sur bruit")
    
    file_type = st.selectbox("Select file type / Choisir type de fichier", ["CSV","PDF","PNG"])
    file = st.file_uploader("Upload file / Charger fichier", type=["csv","pdf","png"])
    
    if file is not None:
        if file_type == "CSV":
            df = read_csv(file)
        elif file_type == "PDF":
            df = extract_from_pdf(file)
        elif file_type == "PNG":
            image = Image.open(file)
            df = extract_from_image(image)
        else:
            df = None
        
        if df is not None and not df.empty:
            st.line_chart(df.set_index("X")["Y"])
            
            x_min, x_max = st.slider("Select zone X / Sélectionner zone X", float(df["X"].min()), float(df["X"].max()), (float(df["X"].min()), float(df["X"].max())))
            selected = df[(df["X"]>=x_min) & (df["X"]<=x_max)]
            
            signal_peak = selected["Y"].max()
            signal_noise = selected["Y"].min()
            std_noise = selected["Y"].std()
            
            st.write("Signal Peak:", signal_peak)
            st.write("Signal Noise:", signal_noise)
            st.write("Std Noise:", std_noise)
            
            classic = sn_classic(signal_peak, signal_noise)
            usp = sn_usp(signal_peak, std_noise)
            
            st.subheader("S/N Values / Valeurs S/N")
            st.write(f"Classical / Classique: {classic:.2f}")
            st.write(f"USP: {usp:.2f}")
            
            if st.button("Show formulas / Afficher formules"):
                st.info("S/N Classic = Signal Peak / Noise\nS/N USP = Signal Peak / Std(Noise)")
            
            if st.button("Export report PDF / Exporter rapport"):
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="LabT - S/N Report", ln=True, align="C")
                pdf.cell(200, 10, txt=f"User: {st.session_state.get('user','')}", ln=True)
                pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
                pdf.cell(200, 10, txt=f"S/N Classic: {classic:.2f}", ln=True)
                pdf.cell(200, 10, txt=f"S/N USP: {usp:.2f}", ln=True)
                
                pdf_output = io.BytesIO()
                pdf.output(pdf_output)
                pdf_output.seek(0)
                st.download_button("Download PDF / Télécharger PDF", pdf_output, file_name="sn_report.pdf", mime="application/pdf")
# =========================
# Partie 25 : App.py final intégrée
# =========================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from fpdf import FPDF
import io
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import plotly.graph_objects as go

# ---------- Session et langue ----------
if "lang" not in st.session_state:
    st.session_state.lang = "FR"
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

# ---------- Traduction simple ----------
texts = {
    "FR": {
        "login": "Connexion",
        "user": "Utilisateur",
        "password": "Mot de passe",
        "logout": "Se déconnecter",
        "linear": "Linéarité",
        "sn": "S/N",
        "choose_file": "Charger fichier",
        "file_type": "Type de fichier",
        "upload": "Importer",
        "classic": "Classique",
        "usp": "USP",
        "show_formulas": "Afficher formules",
        "export_pdf": "Exporter PDF",
    },
    "EN": {
        "login": "Login",
        "user": "User",
        "password": "Password",
        "logout": "Logout",
        "linear": "Linearity",
        "sn": "S/N",
        "choose_file": "Upload file",
        "file_type": "File type",
        "upload": "Upload",
        "classic": "Classic",
        "usp": "USP",
        "show_formulas": "Show formulas",
        "export_pdf": "Export PDF",
    }
}

def t(key):
    return texts[st.session_state.lang].get(key,key)

# ---------- Authentification ----------
USERS = {"admin":"admin123", "user":"user123"}

def login_panel():
    st.title("LabT")
    st.selectbox("Langue / Language", ["FR","EN"], key="lang")
    
    if st.session_state.user is None:
        username = st.text_input(t("user"))
        password = st.text_input(t("password"), type="password")
        if st.button(t("login")):
            if username in USERS and USERS[username]==password:
                st.session_state.user = username
                st.session_state.role = "admin" if username=="admin" else "user"
                st.experimental_rerun()
            else:
                st.error("Invalid login / Identifiants invalides")
    else:
        st.write(f"{t('user')}: {st.session_state.user} ({st.session_state.role})")
        if st.button(t("logout")):
            st.session_state.user = None
            st.session_state.role = None
            st.experimental_rerun()

# ---------- Linéarité ----------
def linear_panel():
    st.header(t("linear"))
    
    # Upload CSV or manual input
    input_type = st.radio("Input type / Type de saisie", ["CSV", "Manual"])
    
    if input_type=="CSV":
        file = st.file_uploader(t("choose_file"), type=["csv"])
        if file:
            try:
                df = pd.read_csv(file)
                if "X" not in df.columns or "Y" not in df.columns:
                    st.error("CSV must contain X and Y columns")
                    return
            except:
                st.error("Error reading CSV")
                return
    else:
        x_values = st.text_area("X values (comma separated)")
        y_values = st.text_area("Y values (comma separated)")
        try:
            x = [float(i) for i in x_values.split(",")]
            y = [float(i) for i in y_values.split(",")]
            df = pd.DataFrame({"X":x,"Y":y})
        except:
            st.error("Invalid manual input")
            return
    
    # Regression
    slope, intercept = np.polyfit(df["X"], df["Y"], 1)
    r2 = np.corrcoef(df["X"], df["Y"])[0,1]**2
    
    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode="markers", name="Data"))
    fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode="lines", name="Fit"))
    st.plotly_chart(fig)
    
    st.write(f"Slope / Pente: {slope:.4f}")
    st.write(f"Intercept / Ordonnée: {intercept:.4f}")
    st.write(f"R²: {r2:.4f}")
    
    # Concentration unknown
    calc_choice = st.selectbox("Calculate / Calculer", ["Y from X", "X from Y"])
    if calc_choice=="Y from X":
        val = st.number_input("X value")
        st.write("Y:", slope*val+intercept)
    else:
        val = st.number_input("Y value")
        st.write("X:", (val-intercept)/slope)
    
    # Export PDF
    if st.button(t("export_pdf")):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200,10,txt="LabT - Linearity Report",ln=True,align="C")
        pdf.cell(200,10,txt=f"User: {st.session_state.user}",ln=True)
        pdf.cell(200,10,txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
        pdf.cell(200,10,txt=f"Slope: {slope:.4f}",ln=True)
        pdf.cell(200,10,txt=f"Intercept: {intercept:.4f}",ln=True)
        pdf.cell(200,10,txt=f"R²: {r2:.4f}",ln=True)
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        st.download_button("Download PDF", pdf_output, file_name="linearity_report.pdf", mime="application/pdf")

# ---------- S/N Panel (from Partie 24) ----------
def read_csv(file):
    try:
        df = pd.read_csv(file)
        return df
    except:
        st.error("CSV read error")
        return None

def extract_from_image(image):
    text = pytesseract.image_to_string(image)
    data=[]
    for line in text.splitlines():
        if "," in line or "\t" in line:
            parts=line.replace("\t",",").split(",")
            try:
                x,y=float(parts[0]),float(parts[1])
                data.append([x,y])
            except:
                pass
    return pd.DataFrame(data, columns=["X","Y"])

def extract_from_pdf(file):
    images = convert_from_path(file)
    all_data=pd.DataFrame(columns=["X","Y"])
    for img in images:
        df = extract_from_image(img)
        all_data = pd.concat([all_data,df])
    return all_data.reset_index(drop=True)

def sn_classic(signal_peak, signal_noise):
    return signal_peak / signal_noise

def sn_usp(signal_peak, std_noise):
    return signal_peak / std_noise

def sn_panel():
    st.header(t("sn"))
    
    file_type = st.selectbox(t("file_type"), ["CSV","PDF","PNG"])
    file = st.file_uploader(t("choose_file"), type=["csv","pdf","png"])
    
    if file:
        if file_type=="CSV":
            df = read_csv(file)
        elif file_type=="PDF":
            df = extract_from_pdf(file)
        elif file_type=="PNG":
            img = Image.open(file)
            df = extract_from_image(img)
        else:
            df = None
        
        if df is not None and not df.empty:
            st.line_chart(df.set_index("X")["Y"])
            
            x_min,x_max = st.slider("Select zone / Zone de calcul", float(df["X"].min()), float(df["X"].max()), (float(df["X"].min()), float(df["X"].max())))
            selected = df[(df["X"]>=x_min)&(df["X"]<=x_max)]
            
            signal_peak = selected["Y"].max()
            signal_noise = selected["Y"].min()
            std_noise = selected["Y"].std()
            
            classic = sn_classic(signal_peak, signal_noise)
            usp = sn_usp(signal_peak, std_noise)
            
            st.subheader("S/N Values")
            st.write(f"Classical / Classique: {classic:.2f}")
            st.write(f"USP: {usp:.2f}")
            
            if st.button(t("show_formulas")):
                st.info("S/N Classic = Signal Peak / Noise\nS/N USP = Signal Peak / Std(Noise)")
            
            if st.button(t("export_pdf")):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200,10,txt="LabT - S/N Report",ln=True,align="C")
                pdf.cell(200,10,txt=f"User: {st.session_state.user}",ln=True)
                pdf.cell(200,10,txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
                pdf.cell(200,10,txt=f"S/N Classic: {classic:.2f}",ln=True)
                pdf.cell(200,10,txt=f"S/N USP: {usp:.2f}",ln=True)
                pdf_output = io.BytesIO()
                pdf.output(pdf_output)
                pdf_output.seek(0)
                st.download_button("Download PDF", pdf_output, file_name="sn_report.pdf", mime="application/pdf")

# ---------- Main ----------
def main():
    login_panel()
    if st.session_state.user:
        st.sidebar.title("Menu")
        choice = st.sidebar.radio("Navigation", [t("linear"), t("sn")])
        st.sidebar.button(t("logout"), on_click=lambda: st.session_state.update({"user":None,"role":None}), key="logout_btn")
        
        if choice==t("linear"):
            linear_panel()
        else:
            sn_panel()

if __name__=="__main__":
    main()
