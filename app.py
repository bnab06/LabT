import streamlit as st
from auth import login_screen, admin_screen, user_screen
from utils import set_language

def main():
    # Choix langue
    lang = st.sidebar.selectbox("Language / Langue", ["English", "Français"])
    _ = set_language(lang)

    st.title(_("LabT Application"))

    # Login
    user_info = login_screen()
    if user_info:
        role = user_info['role']
        if role == 'admin':
            admin_screen()
        else:
            user_screen()

if __name__ == "__main__":
    main()
import streamlit as st
import json
import hashlib

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_screen():
    st.sidebar.subheader("Login")
    username = st.sidebar.text_input("Username").lower()
    password = st.sidebar.text_input("Password", type="password")
    users = load_users()
    if st.sidebar.button("Login"):
        if username in users and users[username]["password"] == hash_password(password):
            st.session_state['user'] = {"username": username, "role": users[username]["role"]}
            return st.session_state['user']
        else:
            st.sidebar.error("Invalid credentials")
    return None

def admin_screen():
    st.header("Admin Dashboard")
    st.write("Manage Users")
    users = load_users()
    for u, info in users.items():
        st.write(f"Username: {u}, Role: {info['role']}")
    st.text("Add/Remove users via JSON file for simplicity.")

def user_screen():
    from linearity import page_linearity
    from sn_chromatogram import page_sn
    st.header("User Dashboard")
    page_linearity()
    page_sn()
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def page_linearity():
    st.subheader("Linearity / Linéarité")
    option = st.radio("Input Method / Méthode de saisie", ["CSV Upload", "Manual Entry"])
    if option == "CSV Upload":
        file = st.file_uploader("Upload CSV")
        if file:
            df = pd.read_csv(file)
            slope, intercept, r2 = linearity_calc(df)
            st.write(f"Slope: {slope}, Intercept: {intercept}, R²: {r2}")
            plot_linearity(df, slope, intercept)
    else:
        n = st.number_input("Number of points", 2, 10)
        conc = [st.number_input(f"Concentration {i+1}") for i in range(n)]
        signal = [st.number_input(f"Signal {i+1}") for i in range(n)]
        df = pd.DataFrame({"Concentration": conc, "Signal": signal})
        slope, intercept, r2 = linearity_calc(df)
        st.write(f"Slope: {slope}, Intercept: {intercept}, R²: {r2}")
        plot_linearity(df, slope, intercept)

def linearity_calc(df):
    x = df['Concentration'].values
    y = df['Signal'].values
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope*x + intercept
    r2 = np.corrcoef(y, y_pred)[0,1]**2
    return slope, intercept, r2

def plot_linearity(df, slope, intercept):
    x = df['Concentration'].values
    y = df['Signal'].values
    plt.figure()
    plt.scatter(x, y, label="Data")
    plt.plot(x, slope*x + intercept, color='red', label="Fit")
    plt.xlabel("Concentration")
    plt.ylabel("Signal")
    plt.legend()
    st.pyplot(plt)
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF

def page_sn():
    st.subheader("Signal / Noise Calculation")
    file = st.file_uploader("Upload chromatogram CSV")
    if file:
        df = pd.read_csv(file)
        x = df['Time'].values
        y = df['Signal'].values
        plt.figure()
        plt.plot(x, y)
        plt.xlabel("Time")
        plt.ylabel("Signal")
        st.pyplot(plt)
        noise_region = st.slider("Select noise region (index)", 0, len(y)-1, (0, 10))
        sn = calc_sn(y, noise_region)
        st.write(f"S/N: {sn}")
        if st.button("Export PDF"):
            export_pdf(x, y, sn)

def calc_sn(y, region):
    noise = y[region[0]:region[1]]
    peak = np.max(y)
    std_noise = np.std(noise)
    return peak / std_noise

def export_pdf(x, y, sn):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"LabT Report - S/N: {sn}", 0, 1)
    pdf.output("report.pdf")
    st.success("PDF exported!")
def set_language(lang):
    # Simple bilingual dictionary
    if lang == "English":
        return lambda x: x
    else:
        translations = {
            "LabT Application": "Application LabT",
            "Login": "Connexion"
        }
        return lambda x: translations.get(x, x)