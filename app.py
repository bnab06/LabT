# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
import io
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import base64
from sklearn.linear_model import LinearRegression

# ---------------------------
# Utilities
# ---------------------------

# Load users
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        # Default users
        return {
            "admin": {"password": "admin123", "role": "admin"},
            "user": {"password": "user123", "role": "user"}
        }

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# Translation
LANGUAGES = {"EN":"English","FR":"Français"}
def T(label, lang_dict):
    # lang_dict = {"EN":"text","FR":"texte"}
    lang = st.session_state.get("lang","EN")
    return lang_dict.get(lang,label)

# Linear regression
def linear_regression(x, y):
    x = np.array(x).reshape(-1,1)
    y = np.array(y)
    model = LinearRegression().fit(x, y)
    slope = model.coef_[0]
    intercept = model.intercept_
    r2 = model.score(x, y)
    return slope, intercept, r2

# PDF report
def create_pdf_report(company_name, slope, intercept, r2, df, username):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,f"Linearity Report - {company_name}", ln=True)
    pdf.set_font("Arial","",12)
    pdf.cell(0,10,f"Username: {username}", ln=True)
    pdf.cell(0,10,f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)
    pdf.cell(0,10,f"Slope: {slope:.4f}", ln=True)
    pdf.cell(0,10,f"Intercept: {intercept:.4f}", ln=True)
    pdf.cell(0,10,f"R²: {r2:.4f}", ln=True)
    pdf.ln(10)
    # Plot
    fig, ax = plt.subplots()
    ax.scatter(df["X"], df["Y"], label="Data")
    ax.plot(df["X"], slope*np.array(df["X"]) + intercept, color="red", label="Fit")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    plt.tight_layout()
    # Save figure to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_bytes = buf.read()
    pdf.image(io.BytesIO(img_bytes), x=10, y=None, w=180)
    return pdf.output(dest='S').encode('latin1')

# ---------------------------
# User Interface
# ---------------------------

def login():
    users = load_users()
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]
            st.experimental_rerun()
        else:
            st.sidebar.error("Invalid credentials")

def change_password():
    users = load_users()
    st.sidebar.subheader("Change Password")
    old = st.sidebar.text_input("Old password", type="password")
    new = st.sidebar.text_input("New password", type="password")
    if st.sidebar.button("Update Password"):
        username = st.session_state["username"]
        if old == users[username]["password"]:
            users[username]["password"] = new
            save_users(users)
            st.sidebar.success("Password updated")
        else:
            st.sidebar.error("Old password incorrect")

# ---------------------------
# Linearity Panel
# ---------------------------
def linear_panel():
    st.header("Linearity")
    method = st.radio("Data input method", ["CSV Upload","Manual input"])
    if method=="CSV Upload":
        file = st.file_uploader("Upload CSV", type=["csv"])
        if file is not None:
            df = pd.read_csv(file)
    else:
        text = st.text_area("Enter X,Y separated by comma", "1,10\n2,20\n3,30")
        data = [list(map(float,line.split(","))) for line in text.strip().split("\n")]
        df = pd.DataFrame(data, columns=["X","Y"])
    if 'df' in locals():
        slope, intercept, r2 = linear_regression(df["X"], df["Y"])
        st.write(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}, R²: {r2:.4f}")
        # Plot
        fig, ax = plt.subplots()
        ax.scatter(df["X"], df["Y"], label="Data")
        ax.plot(df["X"], slope*np.array(df["X"]) + intercept, color="red", label="Fit")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.legend()
        st.pyplot(fig)
        # Calculate unknown
        st.subheader("Calculate Unknown")
        mode = st.selectbox("Calculate:", ["Signal -> Conc","Conc -> Signal"])
        unit = st.selectbox("Unit", ["µg/mL","mg/mL","ng/mL"])
        val = st.number_input("Value")
        if st.button("Calculate"):
            if mode=="Signal -> Conc":
                conc = (val - intercept)/slope
                st.success(f"Concentration: {conc:.4f} {unit}")
            else:
                sig = slope*val + intercept
                st.success(f"Signal: {sig:.4f}")

        # Export PDF
        st.subheader("Export Report PDF")
        company = st.text_input("Company Name")
        if st.button("Generate PDF"):
            username = st.session_state.get("username","unknown")
            pdf_bytes = create_pdf_report(company, slope, intercept, r2, df, username)
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="linearity_report.pdf">Download PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

# ---------------------------
# Main App
# ---------------------------
def user_panel():
    linear_panel()
    st.subheader("Signal/Noise (S/N) placeholder")

def admin_panel():
    st.header("Admin Panel")
    st.write("Manage Users")
    users = load_users()
    for u in users:
        st.write(f"{u} - Role: {users[u]['role']}")
    st.subheader("Add new user")
    newuser = st.text_input("Username")
    newpass = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["admin","user"])
    if st.button("Add User"):
        users[newuser] = {"password": newpass, "role": role}
        save_users(users)
        st.success("User added")

def main():
    st.title("LabT Application")
    if "lang" not in st.session_state:
        st.session_state["lang"]="EN"
    st.sidebar.selectbox("Language", list(LANGUAGES.keys()), key="lang")
    if "username" not in st.session_state:
        login()
    else:
        st.sidebar.write(f"Logged in as {st.session_state['username']}")
        change_password()
        if st.session_state.get("role")=="admin":
            admin_panel()
        else:
            user_panel()

if __name__=="__main__":
    main()