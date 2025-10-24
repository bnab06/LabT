import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from fpdf import FPDF
import json
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from datetime import datetime
import io
import base64

# --- Config ---
st.set_page_config(page_title="LabT", layout="wide")
LANGUAGES = {"English": "en", "Français": "fr"}
DEFAULT_UNIT = "µg/mL"

# --- Load users ---
def load_users():
    with open("users.json", "r") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# --- Linear regression utility ---
def linear_regression(x, y):
    x = np.array(x).reshape(-1, 1)
    y = np.array(y)
    model = LinearRegression()
    model.fit(x, y)
    slope = model.coef_[0]
    intercept = model.intercept_
    r2 = r2_score(y, model.predict(x))
    return slope, intercept, r2

# --- PDF report generation ---
def generate_linear_pdf(username, company, x, y, slope, intercept, r2):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Linearity Report - {company}", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Username: {username}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)
    
    # Plot line
    fig, ax = plt.subplots()
    ax.scatter(x, y, label="Data")
    ax.plot(x, [slope*xi + intercept for xi in x], color='red', label="Fit")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="PNG")
    plt.close(fig)
    img_buffer.seek(0)
    pdf.image(img_buffer, x=10, y=60, w=180)
    
    pdf.ln(100)
    pdf.cell(0, 10, f"Equation: Y = {slope:.4f} * X + {intercept:.4f}", ln=True)
    pdf.cell(0, 10, f"R² = {r2:.4f}", ln=True)
    return pdf
# --- Translation ---
def T(en_text, fr_text, lang="en"):
    return en_text if lang == "en" else fr_text

# --- Login ---
def login():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    users = load_users()
    
    if not st.session_state.logged_in:
        st.title("LabT Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username in users and users[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
    else:
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.experimental_rerun()

# --- Language selection ---
def language_selector():
    lang = st.sidebar.selectbox("Language / Langue", list(LANGUAGES.keys()))
    return LANGUAGES[lang]

# --- User panel ---
def user_panel():
    st.title("LabT Dashboard")
    st.write("Select a function:")
    choice = st.radio("Menu", ["Linearity", "S/N & LOQ/LOD", "Change Password"])
    
    if choice == "Linearity":
        linear_panel()
    elif choice == "S/N & LOQ/LOD":
        sn_panel()
    elif choice == "Change Password":
        change_password_panel()

# --- Admin panel ---
def admin_panel():
    st.title("Admin - User Management")
    users = load_users()
    st.write("Existing users:")
    st.json(users)
    
    st.write("Add new user:")
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["admin", "user"])
    if st.button("Add User"):
        if new_user not in users:
            users[new_user] = {"password": new_pass, "role": role}
            save_users(users)
            st.success("User added!")
        else:
            st.error("User already exists")
# --- Linear regression and plotting ---
def linear_regression(x, y):
    from sklearn.linear_model import LinearRegression
    import numpy as np
    x = np.array(x).reshape(-1,1)
    y = np.array(y)
    model = LinearRegression().fit(x, y)
    slope = model.coef_[0]
    intercept = model.intercept_
    r2 = model.score(x, y)
    return slope, intercept, r2

def linear_panel():
    st.subheader("Linearity")
    input_method = st.radio("Input method", ["CSV upload", "Manual entry"])
    
    if input_method == "CSV upload":
        file = st.file_uploader("Upload CSV", type=["csv"])
        if file:
            df = pd.read_csv(file)
    else:
        x_str = st.text_area("Enter X values (comma separated)")
        y_str = st.text_area("Enter Y values (comma separated)")
        try:
            df = pd.DataFrame({
                "X": [float(v) for v in x_str.split(",")],
                "Y": [float(v) for v in y_str.split(",")]
            })
        except:
            st.error("Invalid input")
            return
    
    if "X" in df.columns and "Y" in df.columns:
        slope, intercept, r2 = linear_regression(df["X"], df["Y"])
        st.write(f"Slope: {slope:.4g}, Intercept: {intercept:.4g}, R²: {r2:.4g}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode='markers', name="Data"))
        fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode='lines', name="Fit"))
        st.plotly_chart(fig)

        # Calculate unknown
        calc_choice = st.selectbox("Calculate", ["Unknown conc from signal", "Signal from conc"])
        val = st.number_input("Enter value")
        if calc_choice == "Unknown conc from signal":
            conc = (val - intercept)/slope
            st.success(f"Concentration: {conc:.4g}")
        else:
            signal = slope*val + intercept
            st.success(f"Signal: {signal:.4g}")

        # PDF report
        company = st.text_input("Company name")
        if st.button("Export PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Linearity Report - {company}", ln=True)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Username: {st.session_state.username}", ln=True)
            pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
            pdf.cell(0, 10, f"Slope: {slope:.4g}, Intercept: {intercept:.4g}, R²: {r2:.4g}", ln=True)
            pdf.output("linearity_report.pdf")
            st.success("PDF exported as linearity_report.pdf")

# --- Signal-to-noise and LOQ/LOD calculations ---
def sn_panel():
    st.subheader("Signal-to-Noise (S/N) & LOQ/LOD")
    st.write("Upload chromatogram (CSV, PDF, PNG)")
    file = st.file_uploader("File", type=["csv","pdf","png"])
    
    if file:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            st.write(df.head())
        else:
            st.warning("PDF/PNG import to be processed via OCR or image processing")

    # S/N formula display
    if st.checkbox("Show S/N formulas"):
        st.markdown("""
        **USP method:** S/N = H / (2*σ)
        **Classical method:** S/N = H / σ
        H = peak height, σ = noise standard deviation
        """)

    st.number_input("Enter slope from linearity (if available) to calculate LOQ/LOD", key="slope_sn")
    st.button("Calculate LOQ/LOD (2 methods)")
    # Calculations would go here using S/N and slope

# --- Change password panel ---
def change_password_panel():
    st.subheader("Change Password")
    users = load_users()
    old = st.text_input("Old password", type="password")
    new = st.text_input("New password", type="password")
    if st.button("Change"):
        if users[st.session_state.username]["password"] == old:
            users[st.session_state.username]["password"] = new
            save_users(users)
            st.success("Password changed!")
        else:
            st.error("Old password incorrect")

# --- Main ---
def main():
    if "username" not in st.session_state:
        st.session_state.username = ""
    login()
    if st.session_state.logged_in:
        users = load_users()
        role = users[st.session_state.username]["role"]
        if role == "admin":
            admin_panel()
        else:
            user_panel()

if __name__ == "__main__":
    main()