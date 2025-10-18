import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
import io
import pytesseract
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import datetime
import json
import os

# ---------- Constants ----------
USERS_FILE = "users.json"

# ---------- Helper Functions ----------
def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": "bb",
            "user1": "user1",
            "user2": "user2"
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def login_page():
    st.title("LabT - Login")
    users = load_users()
    user_selected = st.selectbox("Select user", list(users.keys()))
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")
    if login_btn:
        if password == users[user_selected]:
            st.session_state['username'] = user_selected
            st.session_state['logged_in'] = True
            st.experimental_rerun()
        else:
            st.error("Incorrect password")

def logout():
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.experimental_rerun()

# ---------- S/N Calculations ----------
def calculate_sn(df, start, end):
    df_zone = df[(df["Time"] >= start) & (df["Time"] <= end)]
    y = df_zone["Signal"].values
    noise = np.std(y)
    signal = np.max(y)
    sn = signal / noise if noise != 0 else np.nan
    lod = 3 * noise
    loq = 10 * noise
    return sn, lod, loq, df_zone

# ---------- Linearity ----------
def linearity_page():
    st.header("Linearity")
    # Choose unit
    conc_unit = st.selectbox("Concentration Unit", ["µg/mL", "mg/mL"])
    resp_unit = st.selectbox("Response Unit", ["Area", "Absorbance"])
    input_type = st.radio("Input type", ["Manual Entry", "Upload CSV"])
    
    if input_type == "Manual Entry":
        conc_text = st.text_area("Enter concentrations separated by commas")
        resp_text = st.text_area("Enter responses separated by commas")
        if st.button("Calculate"):
            try:
                c = np.array([float(i.strip()) for i in conc_text.split(",")])
                r = np.array([float(i.strip()) for i in resp_text.split(",")])
                df = pd.DataFrame({"Concentration": c, "Response": r})
                slope, intercept = np.polyfit(c, r, 1)
                y_fit = slope * c + intercept
                r2 = np.corrcoef(c, r)[0,1]**2
                st.write(f"R² = {r2:.4f}")
                
                # Plot
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=c, y=r, mode='markers', name='Data'))
                fig.add_trace(go.Scatter(x=c, y=y_fit, mode='lines', name='Fit'))
                fig.update_layout(
                    xaxis_title=f"Concentration ({conc_unit})",
                    yaxis_title=f"Response ({resp_unit})"
                )
                st.plotly_chart(fig)
                
                # Unknown calculation
                unknown = st.number_input("Enter unknown value")
                unknown_type = st.radio("Unknown type", ["Concentration", "Response"])
                if unknown_type == "Concentration":
                    predicted_response = slope * unknown + intercept
                    st.success(f"Predicted Response = {predicted_response:.3f} {resp_unit}")
                else:
                    predicted_conc = (unknown - intercept)/slope
                    st.success(f"Predicted Concentration = {predicted_conc:.3f} {conc_unit}")
            except Exception as e:
                st.error(f"Error: {e}")
    
    else:
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            if "Concentration" in df.columns and "Response" in df.columns:
                slope, intercept = np.polyfit(df["Concentration"], df["Response"],1)
                y_fit = slope * df["Concentration"] + intercept
                r2 = np.corrcoef(df["Concentration"], df["Response"])[0,1]**2
                st.write(f"R² = {r2:.4f}")
                
                # Plot
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["Concentration"], y=df["Response"], mode='markers', name='Data'))
                fig.add_trace(go.Scatter(x=df["Concentration"], y=y_fit, mode='lines', name='Fit'))
                fig.update_layout(
                    xaxis_title=f"Concentration ({conc_unit})",
                    yaxis_title=f"Response ({resp_unit})"
                )
                st.plotly_chart(fig)

# ---------- Main ----------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
    
    if not st.session_state['logged_in']:
        login_page()
    else:
        st.write(f"Connected as: {st.session_state['username']}")
        logout()
        option = st.selectbox("Select Operation", ["Linearity", "S/N Calculation"])
        if option == "Linearity":
            linearity_page()
        else:
            st.info("S/N Calculation page not implemented yet")

if __name__ == "__main__":
    main()