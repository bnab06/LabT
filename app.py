import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import os
from fpdf import FPDF
from datetime import datetime
import base64

USERS_FILE = "users.json"

# -------------------------------
# Gestion des utilisateurs
# -------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": {"password": "admin", "role": "admin"},
            "bb": {"password": "bb", "role": "user"},
            "user": {"password": "user", "role": "user"},
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------------
# Connexion et session
# -------------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.current_page = None
    st.experimental_rerun()

def login_action(selected_user, password):
    users = load_users()
    if selected_user in users and users[selected_user]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = selected_user
        st.session_state.role = users[selected_user]["role"]
        st.session_state.current_page = "manage_users" if st.session_state.role == "admin" else "linearity"
        st.success(f"✅ You are logged in as {selected_user}")
        st.experimental_rerun()
    else:
        st.error("❌ Incorrect username or password")

def login():
    st.title("🔬 LabT - Login")
    selected_user = st.selectbox("Select user:", list(load_users().keys()))
    password = st.text_input("Password:", type="password")
    st.button("Login", on_click=login_action, args=(selected_user, password))

# -------------------------------
# Gestion utilisateurs (Admin)
# -------------------------------
def validate_user_action(action, username, password, role):
    if not username or (action != "Supprimer" and not password):
        st.warning("⚠️ All fields must be filled!")
        return
    users = load_users()
    if action == "Ajouter":
        if username in users:
            st.warning("User already exists.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("✅ User added")
    elif action == "Modifier":
        if username not in users:
            st.warning("User not found.")
        else:
            if password:
                users[username]["password"] = password
            users[username]["role"] = role
            save_users(users)
            st.success("✅ User modified")
    elif action == "Supprimer":
        if username not in users:
            st.warning("User not found.")
        else:
            del users[username]
            save_users(users)
            st.success("✅ User deleted")

def manage_users():
    st.header("👥 User Management")
    st.write(f"You are logged in as **{st.session_state.username}**")

    action = st.selectbox("Action:", ["Ajouter", "Modifier", "Supprimer"], key="action_admin")
    username = st.text_input("Username:", key="username_admin")
    password = st.text_input("Password:", key="password_admin")
    role = st.selectbox("Role:", ["user", "admin"], key="role_admin")
    st.button("Validate", on_click=validate_user_action, args=(action, username, password, role))
    st.button("⬅️ Logout", on_click=logout)

# -------------------------------
# PDF simple
# -------------------------------
def generate_pdf(title, content_text, company=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LabT Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Company: {company}", ln=True)
    pdf.cell(0, 10, f"User: {st.session_state.username}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"Log: LabT", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 8, content_text)

    pdf_file = f"{title}_{st.session_state.username}.pdf"
    pdf.output(pdf_file)
    return pdf_file

def offer_pdf_actions(pdf_file):
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_file}">⬇️ Download PDF</a>', unsafe_allow_html=True)

# -------------------------------
# Linéarité
# -------------------------------
def linearity_page():
    st.header("📈 Linearity Curve")
    st.write(f"You are logged in as **{st.session_state.username}**")

    conc_input = st.text_input("Known concentrations (comma-separated)", key="conc_input")
    resp_input = st.text_input("Responses (comma-separated)", key="resp_input")
    unknown_type = st.selectbox("Unknown type:", ["Concentration", "Signal"], key="unknown_type")
    unknown_value = st.number_input("Unknown value:", value=0.0, step=0.1, key="unknown_value")
    unit = st.selectbox("Unit:", ["µg/mL", "mg/L", "g/L"], index=0, key="unit")
    company_name = st.text_input("Company name for PDF report:", value="", key="company_name")

    if conc_input and resp_input:
        try:
            conc = np.array([float(x.strip()) for x in conc_input.split(",") if x.strip()])
            resp = np.array([float(x.strip()) for x in resp_input.split(",") if x.strip()])
            if len(conc) != len(resp) or len(conc) == 0:
                st.warning("⚠️ Lists must be the same length and non-empty.")
                return

            slope, intercept = np.polyfit(conc, resp, 1)
            r2 = np.corrcoef(conc, resp)[0,1]**2
            eq = f"y = {slope:.4f}x + {intercept:.4f} (R² = {r2:.4f})"

            st.session_state.slope = slope
            st.session_state.unit = unit

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=conc, y=resp, mode="markers", name="Points"))
            fig.add_trace(go.Scatter(x=conc, y=slope * conc + intercept, mode="lines", name=f"Line ({eq})"))
            fig.update_layout(xaxis_title=f"Concentration ({unit})", yaxis_title="Signal", title="Linearity Curve")
            st.plotly_chart(fig)
            st.success(f"Equation: {eq}")

            if slope != 0:
                if unknown_type == "Concentration":
                    result = (unknown_value - intercept) / slope
                    st.info(f"🔹 Unknown concentration = {result:.4f} {unit}")
                else:
                    result = slope * unknown_value + intercept
                    st.info(f"🔹 Unknown signal = {result:.4f}")

            def export_pdf_linearity():
                content_text = f"Linearity Curve:\nEquation: {eq}\nUnknown type: {unknown_type}\nUnknown value: {unknown_value}\nResult: {result:.4f} {unit if unknown_type=='Concentration' else ''}"
                pdf_file = generate_pdf("Linearity_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF Report", on_click=export_pdf_linearity)

        except Exception as e:
            st.error(f"Error in calculation: {e}")

    st.button("⬅️ Logout", on_click=logout)

# -------------------------------
# S/N
# -------------------------------
def calculate_sn(df):
    signal_peak = df["signal"].max()
    noise = df["signal"].std()
    sn_ratio = signal_peak / noise

    baseline = df.iloc[:max(1, int(0.1*len(df)))]
    noise_usp = baseline["signal"].std()
    sn_usp = signal_peak / noise_usp

    lod = 3 * noise
    loq = 10 * noise

    return sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp

def sn_page():
    st.header("📊 Signal-to-Noise (S/N)")
    st.write(f"You are logged in as **{st.session_state.username}**")
    company_name = st.text_input("Company name for PDF report:", value="", key="company_name_sn")

    uploaded_file = st.file_uploader("Upload chromatogram (CSV)", type=["csv"], key="sn_upload")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]

            if "time" not in df.columns or "signal" not in df.columns:
                st.error("CSV must contain columns: Time and Signal")
                return

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["signal"], mode="lines", name="Signal"))
            fig.update_layout(xaxis_title="Time", yaxis_title="Signal", title="Chromatogram")
            st.plotly_chart(fig)

            sn_ratio, sn_usp, lod, loq, signal_peak, noise, noise_usp = calculate_sn(df)
            st.success(f"S/N = {sn_ratio:.2f}")
            st.info(f"USP S/N = {sn_usp:.2f} (baseline noise = {noise_usp:.4f})")
            st.info(f"LOD = {lod:.4f}, LOQ = {loq:.4f}")

            if 'slope' in st.session_state and st.session_state.slope != 0:
                sn_conc = sn_ratio / st.session_state.slope
                sn_usp_conc = sn_usp / st.session_state.slope
                st.info(f"S/N in concentration: {sn_conc:.4f} {st.session_state.unit}")
                st.info(f"USP S/N in concentration: {sn_usp_conc:.4f} {st.session_state.unit}")

            def export_pdf_sn():
                content_text = f"""USP Signal to Noise Analysis:
Signal max: {signal_peak}
Noise: {noise:.4f}
S/N ratio: {sn_ratio:.2f}
USP S/N: {sn_usp:.2f}
LOD: {lod:.4f}, LOQ: {loq:.4f}
S/N in concentration: {sn_conc:.4f if 'sn_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}
USP S/N in concentration: {sn_usp_conc:.4f if 'sn_usp_conc' in locals() else 'N/A'} {st.session_state.unit if 'unit' in st.session_state else ''}"""
                pdf_file = generate_pdf("SN_Report", content_text, company_name)
                offer_pdf_actions(pdf_file)

            st.button("Export PDF Report", on_click=export_pdf_sn)

        except Exception as e:
            st.error(f"Error reading CSV: {e}")

    st.button("⬅️ Logout", on_click=logout)

# -------------------------------
# Menu principal
# -------------------------------
def main_menu():
    role = st.session_state.role
    if role == "admin":
        manage_users()
    elif role == "user":
        choice = st.selectbox("Choose an option:", ["Linearity Curve", "S/N Calculation"])
        if choice == "Linearity Curve":
            linearity_page()
        else:
            sn_page()
    else:
        st.error("Unknown role.")

# -------------------------------
# Lancement
# -------------------------------
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login()
    else:
        main_menu()