# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import json
import io
from PIL import Image

# ---------------------- Utils ----------------------
USERS_FILE = "users.json"
LOGO_FILE = "logo.png"

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_pdf(df, user, report_type, filename="report.pdf"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    # Logo
    try:
        logo = Image.open(LOGO_FILE)
        logo_io = io.BytesIO()
        logo.save(logo_io, format='PNG')
        c.drawImage(Image.open(LOGO_FILE), 50, height-100, width=80, height=50)
    except:
        pass
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(150, height-50, f"LabT Report - {report_type}")
    c.setFont("Helvetica", 12)
    c.drawString(50, height-130, f"User: {user}")
    c.drawString(50, height-150, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # Data
    text = c.beginText(50, height-180)
    for i, row in df.iterrows():
        text.textLine(str(row.to_dict()))
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ---------------------- Authentication ----------------------
def login_page():
    st.title("LabT - Login")
    users = load_users()
    usernames = list(users.keys())
    selected_user = st.selectbox("Select User", usernames)
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")
    if login_btn:
        if password == users[selected_user]["password"]:
            st.session_state["user"] = selected_user
            st.session_state["role"] = users[selected_user]["role"]
            st.session_state["page"] = "main"
        else:
            st.error("Incorrect password")

def logout():
    st.session_state.clear()
    st.experimental_rerun()

# ---------------------- Main Menu ----------------------
def main_menu():
    st.title("LabT")
    st.write(f"Connected as: **{st.session_state['user']}**")
    st.button("Logout", on_click=logout)
    menu_options = ["Linéarité", "S/N, LOD, LOQ", "Admin (User Management)"]
    choice = st.selectbox("Select Action", menu_options)
    if choice == "Linéarité":
        st.session_state["page"] = "linearite"
    elif choice == "S/N, LOD, LOQ":
        st.session_state["page"] = "sn"
    elif choice == "Admin (User Management)" and st.session_state.get("role") == "admin":
        st.session_state["page"] = "admin"

# ---------------------- Linéarité ----------------------
def linearite_page():
    st.header("Linéarité")
    back_btn = st.button("Back to Main Menu")
    if back_btn:
        st.session_state["page"] = "main"
        st.experimental_rerun()
    
    # Input type
    input_type = st.radio("Input Type", ["Manual", "CSV"])
    conc_unit = st.selectbox("Concentration Unit", ["µg/mL", "mg/mL"])
    if input_type == "Manual":
        c_str = st.text_area("Enter concentrations (comma-separated)")
        r_str = st.text_area("Enter responses (comma-separated)")
        if st.button("Calculate"):
            try:
                c = np.array([float(x.strip()) for x in c_str.split(",")])
                r = np.array([float(x.strip()) for x in r_str.split(",")])
                df = pd.DataFrame({"Concentration": c, "Response": r})
                # Linear regression
                coeffs = np.polyfit(c, r, 1)
                slope, intercept = coeffs
                r2 = np.corrcoef(c, r)[0,1]**2
                st.write(f"R² = {r2:.4f}")
                fig = px.scatter(df, x="Concentration", y="Response", title="Linéarité")
                fig.add_traces(px.line(x=c, y=slope*c+intercept).data)
                st.plotly_chart(fig)
                # Unknown calculation
                unknown = st.number_input("Enter unknown concentration or response")
                unknown_type = st.radio("Calculate", ["From concentration", "From response"])
                if st.button("Compute Unknown"):
                    if unknown_type=="From concentration":
                        calc = slope*unknown + intercept
                        st.success(f"Predicted Response: {calc:.4f}")
                    else:
                        calc = (unknown - intercept)/slope
                        st.success(f"Predicted Concentration: {calc:.4f} {conc_unit}")
                # Export PDF
                pdf_buffer = generate_pdf(df, st.session_state["user"], "Linéarité")
                st.download_button("Download PDF", data=pdf_buffer, file_name="linearite_report.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write(df)

# ---------------------- S/N, LOD, LOQ ----------------------
def sn_page():
    st.header("S/N, LOD, LOQ")
    back_btn = st.button("Back to Main Menu")
    if back_btn:
        st.session_state["page"] = "main"
        st.experimental_rerun()
    
    uploaded_file = st.file_uploader("Upload CSV chromatogram", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            x = df.iloc[:,0].values
            y = df.iloc[:,1].values
            st.line_chart(df)
            start = st.number_input("Start Time", value=float(np.min(x)))
            end = st.number_input("End Time", value=float(np.max(x)))
            if st.button("Calculate S/N"):
                # Simple S/N calculation
                zone = (x>=start)&(x<=end)
                signal_peak = np.max(y[zone])
                noise_std = np.std(y[zone])
                sn = signal_peak / noise_std
                lod = 3*noise_std
                loq = 10*noise_std
                st.write(f"S/N = {sn:.4f}, LOD = {lod:.4f}, LOQ = {loq:.4f}")
        except Exception as e:
            st.error(f"Error: {e}")

# ---------------------- Admin ----------------------
def admin_page():
    st.header("Admin - User Management")
    back_btn = st.button("Back to Main Menu")
    if back_btn:
        st.session_state["page"] = "main"
        st.experimental_rerun()
    users = load_users()
    st.subheader("Existing Users")
    selected_user = st.selectbox("Select User", list(users.keys()))
    new_user = st.text_input("New Username")
    new_pass = st.text_input("Password", type="password")
    add_btn = st.button("Add User")
    if add_btn:
        if new_user and new_pass:
            users[new_user] = {"password": new_pass, "role": "user"}
            save_users(users)
            st.success("User added")
        else:
            st.error("Enter username and password")
    if st.button("Delete User"):
        if selected_user in users:
            del users[selected_user]
            save_users(users)
            st.success("User deleted")

# ---------------------- App Router ----------------------
if "page" not in st.session_state:
    st.session_state["page"] = "login"

if st.session_state["page"]=="login":
    login_page()
elif st.session_state["page"]=="main":
    main_menu()
elif st.session_state["page"]=="linearite":
    linearite_page()
elif st.session_state["page"]=="sn":
    sn_page()
elif st.session_state["page"]=="admin":
    admin_page()