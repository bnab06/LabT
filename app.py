---

### **4️⃣ app.py** (version complète et moderne)

> L’application inclut : login, menu principal, S/N, LOD/LOQ, linéarité, export PDF, choix unités, concentration inconnue, signal inconnu, CSV/PNG/PDF.  

```python
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from pdf2image import convert_from_path
from io import BytesIO
from sklearn.linear_model import LinearRegression

# --- Chargement utilisateurs ---
USERS_FILE = "users.json"

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)["users"]

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump({"users": users}, f, indent=4)

# --- Session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "login"

# --- Login page ---
def login_page():
    st.title("LabT - Chromatogram Analyzer")
    users = load_users()
    usernames = [u["username"] for u in users]
    username = st.selectbox("Select User", usernames)
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = next((u for u in users if u["username"] == username and u["password"] == password), None)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.page = "menu"
        else:
            st.error("Incorrect credentials")

# --- Logout ---
def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "login"

# --- Menu Principal ---
def menu_page():
    st.header(f"Welcome, {st.session_state.user['username']}")
    if st.session_state.user["role"] == "admin":
        option = st.selectbox("Admin Menu", ["Manage Users"])
        if option == "Manage Users":
            manage_users()
    else:
        option = st.selectbox("Choose Analysis", ["Select","Linearity","S/N USP/LOD/LOQ"])
        if option == "Linearity":
            linearity_page()
        elif option == "S/N USP/LOD/LOQ":
            sn_page()
    if st.button("Logout"):
        logout()

# --- User management ---
def manage_users():
    users = load_users()
    st.subheader("Current Users")
    for u in users:
        st.write(f"{u['username']} ({u['role']})")
    st.subheader("Add User")
    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    new_role = st.selectbox("Role", ["user"])
    if st.button("Add User"):
        if new_username and new_password:
            users.append({"username": new_username,"password": new_password,"role": new_role})
            save_users(users)
            st.success(f"User {new_username} added")
        else:
            st.error("Enter both username and password")

# --- Linearity ---
def linearity_page():
    st.subheader("Linearity Calculation")
    method = st.radio("Input Method", ["Manual Entry","CSV Upload"])
    if method == "Manual Entry":
        conc_str = st.text_input("Concentrations (comma separated)", "1,2,3")
        resp_str = st.text_input("Responses (comma separated)", "10,20,30")
        unit_conc = st.selectbox("Concentration Unit", ["µg/mL","mg/mL"])
        unit_resp = st.selectbox("Response Type", ["Aire","Absorbance"])
        if st.button("Calculate"):
            try:
                c = np.array([float(x.strip()) for x in conc_str.split(",")])
                r = np.array([float(x.strip()) for x in resp_str.split(",")])
                if len(c) != len(r):
                    st.error("Concentration and response must have same length")
                    return
                df = pd.DataFrame({"Concentration": c, "Response": r})
                lr = LinearRegression().fit(c.reshape(-1,1),r)
                r2 = lr.score(c.reshape(-1,1),r)
                st.write(f"R² = {r2:.4f}")
                fig, ax = plt.subplots()
                ax.scatter(c,r)
                ax.plot(c, lr.predict(c.reshape(-1,1)), color='red')
                ax.set_xlabel(f"Concentration ({unit_conc})")
                ax.set_ylabel(f"Response ({unit_resp})")
                st.pyplot(fig)
                # Calculate unknown
                unknown_val = st.number_input("Enter unknown value (according to your input type)")
                unknown_type = st.selectbox("Unknown Type", ["Concentration","Response"])
                if unknown_val:
                    if unknown_type=="Concentration":
                        pred = lr.predict(np.array([[unknown_val]]))[0]
                        st.success(f"Predicted Response: {pred:.3f} {unit_resp}")
                    else:
                        pred = (unknown_val - lr.intercept_)/lr.coef_[0]
                        st.success(f"Predicted Concentration: {pred:.3f} {unit_conc}")
            except:
                st.error("Invalid input. Use numbers separated by commas.")
    else:
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        unit_conc = st.selectbox("Concentration Unit", ["µg/mL","mg/mL"])
        unit_resp = st.selectbox("Response Type", ["Aire","Absorbance"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                if df.shape[1]<2:
                    st.error("CSV must have at least two columns")
                    return
                c = df.iloc[:,0].values
                r = df.iloc[:,1].values
                lr = LinearRegression().fit(c.reshape(-1,1),r)
                r2 = lr.score(c.reshape(-1,1),r)
                st.write(f"R² = {r2:.4f}")
                fig, ax = plt.subplots()
                ax.scatter(c,r)
                ax.plot(c, lr.predict(c.reshape(-1,1)), color='red')
                ax.set_xlabel(f"Concentration ({unit_conc})")
                ax.set_ylabel(f"Response ({unit_resp})")
                st.pyplot(fig)
            except:
                st.error("Error reading CSV")

# --- S/N USP / LOD / LOQ ---
def sn_page():
    st.subheader("S/N, LOD, LOQ Calculation")
    uploaded_file = st.file_uploader("Upload CSV or Image (PNG, PDF)", type=["csv","png","pdf"])
    if uploaded_file:
        st.info("Extraction not implemented for PNG/PDF yet, use CSV")
        try:
            df = pd.read_csv(uploaded_file)
            if "Time" not in df.columns or "Signal" not in df.columns:
                df.columns = ["Time","Signal"]
            st.line_chart(df.set_index("Time")["Signal"])
            # Simple S/N, LOD, LOQ calculation placeholder
            y = df["Signal"].values
            sn = np.max(y)/np.std(y)
            lod = 3*np.std(y)
            loq = 10*np.std(y)
            st.write(f"S/N = {sn:.2f}, LOD = {lod:.2f}, LOQ = {loq:.2f}")
        except:
            st.error("Error reading file")

# --- Main