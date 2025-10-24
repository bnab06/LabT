import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
from fpdf import FPDF
import json
from datetime import datetime
import pytesseract
from PIL import Image

USERS_FILE = "users.json"
DEFAULT_UNIT = "ug/ml"

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def linear_regression(x, y):
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return slope, intercept, r_value**2

def login():
    users = load_users()
    st.title("LabT - Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

def admin_panel():
    st.title("Admin - User Management")
    users = load_users()
    
    action = st.selectbox("Action", ["Add User", "Delete User", "Modify User"])
    
    if action == "Add User":
        new_user = st.text_input("New username")
        new_password = st.text_input("New password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        if st.button("Add"):
            if new_user in users:
                st.error("User already exists")
            else:
                users[new_user] = {"password": new_password, "role": role}
                save_users(users)
                st.success(f"User {new_user} added")
    elif action == "Delete User":
        del_user = st.selectbox("Select user", list(users.keys()))
        if st.button("Delete"):
            if del_user in users:
                del users[del_user]
                save_users(users)
                st.success(f"User {del_user} deleted")
    elif action == "Modify User":
        mod_user = st.selectbox("Select user", list(users.keys()))
        new_password = st.text_input("New password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        if st.button("Modify"):
            users[mod_user]["password"] = new_password
            users[mod_user]["role"] = role
            save_users(users)
            st.success(f"User {mod_user} modified")

def user_panel():
    st.title("LabT - User Panel")
    menu = st.selectbox("Menu", ["Linearity", "S/N, LOD, LOQ", "Change Password"])
    
    if menu == "Change Password":
        change_password()
    elif menu == "Linearity":
        linear_panel()
    elif menu == "S/N, LOD, LOQ":
        sn_panel()

def change_password():
    users = load_users()
    username = st.session_state["username"]
    new_password = st.text_input("Enter new password", type="password")
    if st.button("Change"):
        users[username]["password"] = new_password
        save_users(users)
        st.success("Password changed successfully")

def linear_panel():
    st.subheader("Linearity")
    input_mode = st.radio("Input mode", ["CSV Upload", "Manual Entry"])
    
    if input_mode == "CSV Upload":
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
    else:
        x_str = st.text_area("Enter X values separated by commas")
        y_str = st.text_area("Enter Y values separated by commas")
        if x_str and y_str:
            x = list(map(float, x_str.split(",")))
            y = list(map(float, y_str.split(",")))
            df = pd.DataFrame({"X": x, "Y": y})
            st.dataframe(df)
    
    if 'df' in locals():
        slope, intercept, r2 = linear_regression(df["X"], df["Y"])
        st.write(f"Equation: Y = {slope:.4f}X + {intercept:.4f}")
        st.write(f"R² = {r2:.4f}")
        st.session_state["linear_slope"] = slope
        st.session_state["linear_intercept"] = intercept

        calc_choice = st.selectbox("Calculate", ["Signal from Concentration", "Concentration from Signal"])
        unit = st.text_input("Concentration Unit", value=DEFAULT_UNIT)
        if calc_choice == "Signal from Concentration":
            conc = st.number_input("Enter concentration", value=0.0)
            signal = slope * conc + intercept
            st.write(f"Signal = {signal:.4f}")
        else:
            signal = st.number_input("Enter signal", value=0.0)
            conc = (signal - intercept)/slope
            st.write(f"Concentration = {conc:.4f} {unit}")
        
        company = st.text_input("Company Name")
        if st.button("Export PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"Company: {company}", ln=True)
            pdf.cell(0, 10, f"User: {st.session_state['username']}", ln=True)
            pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
            pdf.cell(0, 10, f"Equation: Y = {slope:.4f}X + {intercept:.4f}", ln=True)
            pdf.cell(0, 10, f"R²: {r2:.4f}", ln=True)
            pdf.output("Linearity_Report.pdf")
            st.success("PDF exported as Linearity_Report.pdf")

def sn_panel():
    st.subheader("Signal-to-Noise, LOD, LOQ")
    slope = st.session_state.get("linear_slope", None)
    if slope is None:
        st.warning("Please calculate linearity first")
        return
    signal = st.number_input("Enter Signal", value=0.0)
    noise = st.number_input("Enter Noise", value=0.0)
    sn = signal/noise if noise else 0
    lod = 3*noise/slope if slope else 0
    loq = 10*noise/slope if slope else 0
    st.write(f"S/N = {sn:.4f}")
    st.write(f"LOD = {lod:.4f}")
    st.write(f"LOQ = {loq:.4f}")

def main():
    st.session_state.setdefault("username", None)
    
    lang = st.selectbox("Language", ["EN", "FR"], index=0)
    
    if st.session_state["username"] is None:
        login()
    else:
        role = st.session_state["role"]
        st.sidebar.write(f"Logged in as: {st.session_state['username']} ({role})")
        st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"username": None, "role": None}))
        
        if role == "admin":
            admin_panel()
        else:
            user_panel()

if __name__ == "__main__":
    main()