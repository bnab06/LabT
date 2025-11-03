import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image, ImageOps
from pdf2image import convert_from_bytes
import json
import io

# =========================
# 🔐 Connexion
# =========================
def login_page():
    st.title("LabT - Connexion / Login")
    st.markdown("Powered by BnB")
    username = st.text_input("Nom d'utilisateur / Username")
    password = st.text_input("Mot de passe / Password", type="password")
    
    if st.button("Connexion / Login"):
        try:
            with open("users.json", "r") as f:
                users = json.load(f)
        except:
            users = {}
        
        user = username.lower()
        if user in users and users[user]["password"] == password:
            st.session_state["user"] = user
            st.session_state["role"] = users[user]["role"]
            st.success(f"Connecté en tant que {user}")
        else:
            st.error("Identifiants invalides / Invalid credentials")

# =========================
# 👤 Gestion utilisateurs (admin only)
# =========================
def admin_panel():
    st.subheader("Gestion des utilisateurs")
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except:
        users = {}
    
    new_user = st.text_input("Ajouter un nouvel utilisateur / New user")
    new_pass = st.text_input("Mot de passe / Password")
    new_role = st.selectbox("Rôle", ["admin","user"], key="role_select")
    
    if st.button("Ajouter / Add"):
        if new_user in users:
            st.warning("Utilisateur existe déjà / User exists")
        else:
            users[new_user] = {"password": new_pass, "role": new_role}
            with open("users.json", "w") as f:
                json.dump(users, f, indent=4)
            st.success("Utilisateur ajouté / User added")

    st.markdown("### Liste des utilisateurs / Users list")
    for u, v in users.items():
        st.write(f"{u} - {v['role']}")
        if st.button(f"Supprimer {u}", key=f"del_{u}"):
            users.pop(u)
            with open("users.json", "w") as f:
                json.dump(users, f, indent=4)
            st.success(f"Utilisateur {u} supprimé")
            st.experimental_rerun()
# =========================
# 📈 Linéarité
# =========================
def linearite_panel():
    st.subheader("Linéarité / Linearity")
    
    # Upload CSV ou saisie manuelle
    uploaded_file = st.file_uploader("Téléverser CSV: concentration, signal", type=["csv"])
    conc_manual = st.text_input("Concentrations séparées par des virgules / Concentrations (manual)")
    signal_manual = st.text_input("Signaux séparés par des virgules / Signals (manual)")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        concentrations = df['concentration'].values
        signals = df['signal'].values
    else:
        try:
            concentrations = np.array([float(c.strip()) for c in conc_manual.split(",")])
            signals = np.array([float(s.strip()) for s in signal_manual.split(",")])
        except:
            concentrations = np.array([])
            signals = np.array([])

    if len(concentrations) > 1 and len(signals) > 1:
        # Ajustement linéaire
        slope, intercept = np.polyfit(concentrations, signals, 1)
        st.session_state["lin_slope"] = slope

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=concentrations, y=signals, mode="markers", name="Données"))
        x_fit = np.linspace(min(concentrations), max(concentrations), 100)
        y_fit = slope*x_fit + intercept
        fig.add_trace(go.Scatter(x=x_fit, y=y_fit, mode="lines", name="Fit linéaire"))
        fig.update_layout(title="Courbe de linéarité", xaxis_title="Concentration", yaxis_title="Signal", template="simple_white")
        st.plotly_chart(fig, use_container_width=True)
        
        # Calculs concentrations inconnues
        unknown_signal = st.number_input("Signal inconnu / Unknown signal")
        conc_unknown = (unknown_signal - intercept)/slope
        st.markdown(f"Concentration inconnue: {conc_unknown:.4f}")
        
        unknown_conc = st.number_input("Concentration inconnue / Unknown concentration")
        signal_unknown = slope*unknown_conc + intercept
        st.markdown(f"Signal inconnu: {signal_unknown:.4f}")
        
        return slope
    return None

# =========================
# 📷 S/N Panel
# =========================
def sn_panel(lin_slope=None):
    st.subheader("Signal / Noise Calculation (S/N)")
    
    uploaded_file = st.file_uploader("Téléverser le chromatogramme (PDF ou PNG)", type=["pdf", "png"])
    img = None
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            try:
                images = convert_from_bytes(uploaded_file.read())
                img = images[0].convert("RGB")
            except Exception as e:
                st.error(f"PDF conversion failed: {e}")
                return
        else:
            img = Image.open(uploaded_file)
        st.image(img, caption="Chromatogramme original", use_column_width=True)
        
        # Inversion image
        img_inv = ImageOps.flip(img)
        img_gray = img_inv.convert("L")
        st.image(img_gray, caption="Chromatogramme inversé pour calcul S/N", use_column_width=True)

        # Slider bruit
        st.markdown("Sélectionner la zone de bruit")
        start_x, end_x = st.slider("Zone bruit (start - end)", 0, img_gray.width, (0, img_gray.width))
        if start_x >= end_x:
            st.warning("Le début doit être inférieur à la fin")
            return

        arr = np.array(img_gray)
        signal = arr.mean(axis=0)
        noise_std = np.std(signal[start_x:end_x])
        H = np.max(signal)
        peak_idx = np.argmax(signal)

        st.markdown(f"Hauteur maximale (H): {H:.2f}, Temps de rétention approx: {peak_idx}")
        
        # Tracé
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=signal, mode="lines", line=dict(color="black"), name="Signal"))
        fig.add_trace(go.Scatter(x=[peak_idx], y=[H], mode="markers", marker=dict(color="red", size=10), name="Pic principal"))
        fig.update_layout(title="Chromatogramme pour S/N", xaxis_title="Temps / Time", yaxis_title="Signal", template="simple_white")
        st.plotly_chart(fig, use_container_width=True)

        # Calcul S/N
        st.markdown(f"S/N classique: {H/noise_std:.2f}")
        st.markdown(f"S/N USP: {H/(3*noise_std):.2f}")
        
        # LOD / LOQ
        if lin_slope:
            lod = 3*noise_std/lin_slope
            loq = 10*noise_std/lin_slope
            st.markdown(f"LOD: {lod:.4f}")
            st.markdown(f"LOQ: {loq:.4f}")
        
        # Télécharger image
        buf = io.BytesIO()
        img_gray.save(buf, format="PNG")
        st.download_button("Télécharger image inversée", data=buf.getvalue(), file_name="chromatogram.png")
# =========================
# 💬 Feed-back
# =========================
def feedback_panel():
    st.subheader("Feedback / Suggestions")
    
    exp = st.expander("Envoyer feedback / Send feedback")
    with exp:
        fb = st.text_area("Votre feedback / Your feedback")
        if st.button("Envoyer / Submit"):
            try:
                with open("feedback.json", "r") as f:
                    fb_data = json.load(f)
            except:
                fb_data = []
            fb_data.append({"user": st.session_state.get("user"), "feedback": fb, "response": ""})
            with open("feedback.json", "w") as f:
                json.dump(fb_data, f, indent=4)
            st.success("Feedback envoyé!")

    # Lecture admin
    if st.session_state.get("role") == "admin":
        st.subheader("Lecture feed-back")
        try:
            with open("feedback.json", "r") as f:
                fb_data = json.load(f)
        except:
            fb_data = []

        for i, fb in enumerate(fb_data):
            st.markdown(f"**Utilisateur:** {fb['user']}")
            st.markdown(f"**Feedback:** {fb['feedback']}")
            resp = st.text_input(f"Réponse à {fb['user']}", value=fb.get("response", ""), key=f"resp_{i}")
            if st.button("Envoyer réponse", key=f"btn_{i}"):
                fb_data[i]["response"] = resp
                with open("feedback.json", "w") as f:
                    json.dump(fb_data, f, indent=4)
                st.success("Réponse envoyée!")

# =========================
# 🔄 Main
# =========================
def main_app():
    if "user" not in st.session_state:
        login_page()
    else:
        st.title(f"Bienvenue {st.session_state['user']}")
        role = st.session_state.get("role")
        if role == "admin":
            admin_panel()
        else:
            tab = st.radio("Choisir module / Select module", ["Linéarité / Linearity", "S/N", "Feedback"], horizontal=True)
            slope = None
            if tab.startswith("Linéarité"):
                slope = linearite_panel()
            elif tab.startswith("S/N"):
                sn_panel(lin_slope=slope)
            elif tab.startswith("Feedback"):
                feedback_panel()

if __name__ == "__main__":
    main_app()