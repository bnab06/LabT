---

### 4️⃣ `app.py` (version rapide)
```python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json

USERS_FILE = "users.json"

# --- Load users ---
with open(USERS_FILE, "r") as f:
    users = json.load(f)

# --- Session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- Login page ---
def login():
    st.title("LabT Login")
    username = st.selectbox("Select user", list(users.keys()))
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("Incorrect password")

# --- Main menu ---
def main_menu():
    st.title("LabT - Home")
    st.write(f"Connected as: **{st.session_state.username}**")
    choice = st.selectbox("Select function", ["S/N", "Linearity"])
    if choice == "S/N":
        sn_page()
    elif choice == "Linearity":
        linearity_page()
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

# --- S/N page ---
def sn_page():
    st.header("Signal-to-Noise Calculation")
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write(df.head())
        y = df.iloc[:,1].values
        sn = np.max(y)/np.std(y)
        st.write(f"Signal/Noise: {sn:.2f}")

# --- Linearity page ---
def linearity_page():
    st.header("Linearity")
    conc = st.text_input("Enter concentrations separated by commas", "1,2,3")
    resp = st.text_input("Enter responses separated by commas", "10,20,30")
    if st.button("Calculate"):
        try:
            c = np.array([float(x) for x in conc.split(",")])
            r = np.array([float(x) for x in resp.split(",")])
            fig = go.Figure(data=go.Scatter(x=c, y=r, mode='markers+lines'))
            st.plotly_chart(fig)
            m, b = np.polyfit(c,r,1)
            r2 = np.corrcoef(c,r)[0,1]**2
            st.write(f"Slope: {m:.2f}, Intercept: {b:.2f}, R²: {r2:.3f}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- App logic ---
if st.session_state.logged_in:
    main_menu()
else:
    login()