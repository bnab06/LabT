# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fpdf import FPDF
import json
from datetime import datetime
import pytesseract
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import cv2
from io import BytesIO

# -----------------------------
# Utils
# -----------------------------
def load_users():
    with open("users.json", "r") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def linear_regression(x, y):
    slope, intercept = np.polyfit(x, y, 1)
    r2 = np.corrcoef(x, y)[0,1]**2
    return slope, intercept, r2

def calculate_loq_lod(sn, slope):
    lod = 3.3 / slope * sn if slope!=0 else 0
    loq = 10 / slope * sn if slope!=0 else 0
    return lod, loq

# -----------------------------
# PDF export
# -----------------------------
def export_pdf(username, company, slope, intercept, r2, lod, loq):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{company} - Linear Report", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"User: {username}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Slope: {slope:.4f}", ln=True)
    pdf.cell(0, 10, f"Intercept: {intercept:.4f}", ln=True)
    pdf.cell(0, 10, f"R2: {r2:.4f}", ln=True)
    pdf.cell(0, 10, f"LOD: {lod:.4g}", ln=True)
    pdf.cell(0, 10, f"LOQ: {loq:.4g}", ln=True)
    pdf.output("linear_report.pdf")
    st.success("PDF exported as linear_report.pdf")

# -----------------------------
# Login
# -----------------------------
def login(users):
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state['username'] = username
            st.session_state['role'] = users[username]["role"]
            st.experimental_rerun()
        else:
            st.sidebar.error("Invalid credentials")
    if 'username' in st.session_state:
        st.sidebar.success(f"Logged in as {st.session_state['username']}")

# -----------------------------
# Admin panel
# -----------------------------
def admin_panel(users):
    st.header("Admin Panel")
    st.subheader("Manage Users")
    for u, info in users.items():
        st.write(f"{u} - role: {info['role']}")
    new_user = st.text_input("New username")
    new_pass = st.text_input("New password")
    role = st.selectbox("Role", ["user", "admin"])
    if st.button("Add user"):
        if new_user not in users:
            users[new_user] = {"password": new_pass, "role": role}
            save_users(users)
            st.success(f"User {new_user} added")
        else:
            st.error("User exists")

# -----------------------------
# Linear panel
# -----------------------------
def linear_panel():
    st.header("Linearity")
    method = st.radio("Input Method", ["CSV", "Manual"])
    if method == "CSV":
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded:
            df = pd.read_csv(uploaded)
            if 'X' not in df.columns or 'Y' not in df.columns:
                st.error("CSV must have 'X' and 'Y' columns")
                return
    else:
        x = st.text_area("X values (comma-separated)")
        y = st.text_area("Y values (comma-separated)")
        try:
            x = list(map(float, x.split(",")))
            y = list(map(float, y.split(",")))
            df = pd.DataFrame({"X": x, "Y": y})
        except:
            st.error("Invalid input")
            return
    slope, intercept, r2 = linear_regression(df["X"], df["Y"])
    st.write(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}, R2: {r2:.4f}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["X"], y=df["Y"], mode="markers", name="Data"))
    fig.add_trace(go.Scatter(x=df["X"], y=slope*df["X"]+intercept, mode="lines", name="Fit"))
    st.plotly_chart(fig)
    # Concentration unknown
    mode = st.selectbox("Calculate", ["Signal -> Concentration", "Concentration -> Signal"])
    val = st.number_input("Enter value")
    conc_unit = st.selectbox("Unit", ["ug/mL", "mg/mL", "ng/mL"])
    if mode=="Signal -> Concentration":
        conc = (val - intercept)/slope
        st.write(f"Concentration: {conc:.4g} {conc_unit}")
    else:
        sig = slope*val + intercept
        st.write(f"Signal: {sig:.4g}")
    sn = st.number_input("Enter S/N", value=10.0)
    lod, loq = calculate_loq_lod(sn, slope)
    st.write(f"LOD: {lod:.4g}, LOQ: {loq:.4g}")
    company = st.text_input("Company name")
    if st.button("Export PDF"):
        export_pdf(st.session_state['username'], company, slope, intercept, r2, lod, loq)

# -----------------------------
# S/N panel
# -----------------------------
def sn_panel():
    st.header("S/N Calculation")
    uploaded = st.file_uploader("Upload chromatogram", type=["csv", "pdf", "png"])
    if uploaded:
        ext = uploaded.name.split(".")[-1].lower()
        if ext=="csv":
            df = pd.read_csv(uploaded)
            st.write(df.head())
            # Here implement S/N calculation logic using df
        elif ext=="pdf":
            images = convert_from_path(uploaded)
            st.image(images)
        else:
            image = uploaded.read()
            st.image(image)
    st.write("Formulas:")
    st.write("Classical S/N: S/N = Signal / Noise")
    st.write("USP S/N: S/N = Height / Standard Deviation of Noise")
    st.write("Use sliders below to select region for S/N calculation (if CSV)")

# -----------------------------
# User panel
# -----------------------------
def user_panel():
    menu = ["Linearity", "S/N"]
    choice = st.selectbox("Select Menu", menu)
    if choice=="Linearity":
        linear_panel()
    elif choice=="S/N":
        sn_panel()

# -----------------------------
# Main
# -----------------------------
def main():
    st.set_page_config(page_title="LabT App")
    users = load_users()
    if 'username' not in st.session_state:
        login(users)
        return
    if st.session_state['role']=="admin":
        admin_panel(users)
    else:
        user_panel()
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

if __name__=="__main__":
    main()