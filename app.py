import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import calculate_sn, linear_regression, load_chromatogram_pdf_png
from datetime import datetime
import json
import io

# -----------------------
# Constants
# -----------------------
USERS_FILE = "users.json"
APP_NAME = "LabT"

# -----------------------
# Load users
# -----------------------
with open(USERS_FILE, "r") as f:
    USERS = json.load(f)

# -----------------------
# Session State
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# -----------------------
# Login Function
# -----------------------
def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Connect"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.session_state.page = "home"
        else:
            st.sidebar.error("Incorrect credentials")

# -----------------------
# Logout Function
# -----------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "login"

# -----------------------
# Home Page
# -----------------------
def home_page():
    st.markdown(f"<h1 style='color:blue'>{APP_NAME}</h1>", unsafe_allow_html=True)
    st.write(f"Connected as **{st.session_state.user}**")
    st.button("Logout", on_click=logout)

    st.markdown("---")
    option = st.selectbox("Select Function:", ["Signal / Noise", "Linéarité"])
    
    if option == "Signal / Noise":
        st.session_state.page = "sn_page"
    elif option == "Linéarité":
        st.session_state.page = "linear_page"

# -----------------------
# S/N Page
# -----------------------
def sn_page():
    st.header("Signal / Noise Calculation")
    uploaded_file = st.file_uploader("Upload CSV, PNG, PDF", type=["csv", "png", "pdf"])
    if uploaded_file:
        df = load_chromatogram_pdf_png(uploaded_file)
        if df is not None:
            start = st.number_input("Start Time", value=float(df["Time"].min()))
            end = st.number_input("End Time", value=float(df["Time"].max()))
            sn, lod, loq, df_zone = calculate_sn(df, start, end)
            st.write(f"S/N: {sn:.2f}, LOD: {lod:.2f}, LOQ: {loq:.2f}")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Time"], y=df["Signal"], mode="lines", name="Chromatogram"))
            st.plotly_chart(fig)
    if st.button("Back to Home"):
        st.session_state.page = "home"

# -----------------------
# Linéarité Page
# -----------------------
def linear_page():
    st.header("Linéarité / Calibration Curve")
    unit = st.selectbox("Select concentration unit", ["µg/mL", "mg/mL"])
    response_type = st.selectbox("Select response type", ["Aire", "Absorbance"])

    input_method = st.radio("Input method:", ["Manual entry", "Upload CSV"])
    concentrations = []
    responses = []
    if input_method == "Manual entry":
        n_points = st.number_input("Number of points", min_value=2, step=1)
        for i in range(n_points):
            c = st.number_input(f"Concentration {i+1} ({unit})")
            r = st.number_input(f"Response {i+1} ({response_type})")
            concentrations.append(c)
            responses.append(r)
    else:
        file = st.file_uploader("Upload CSV", type="csv")
        if file:
            df_csv = pd.read_csv(file)
            concentrations = df_csv["Concentration"].tolist()
            responses = df_csv["Response"].tolist()

    if st.button("Calculate Calibration"):
        df_lin = pd.DataFrame({"Concentration": concentrations, "Response": responses})
        slope, intercept, r2 = linear_regression(df_lin)
        st.write(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}, R²: {r2:.4f}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_lin["Concentration"], y=df_lin["Response"], mode="markers", name="Points"))
        fig.add_trace(go.Scatter(x=df_lin["Concentration"], y=slope*df_lin["Concentration"] + intercept, mode="lines", name="Fit"))
        st.plotly_chart(fig)
    if st.button("Back to Home"):
        st.session_state.page = "home"

# -----------------------
# Main Logic
# -----------------------
if st.session_state.logged_in:
    if st.session_state.page == "home":
        home_page()
    elif st.session_state.page == "sn_page":
        sn_page()
    elif st.session_state.page == "linear_page":
        linear_page()
else:
    login()