# app.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
from utils import (
    linear_regression_from_xy,
    predict_conc_from_signal,
    predict_signal_from_conc,
    export_linearity_pdf,
    compute_sn_classic,
    compute_sn_usp,
    read_csv_bytes,
    load_users,
    save_users,
)
from PIL import Image

# --- Config
st.set_page_config(page_title="LabT - Linéarité & S/N", layout="wide")

USERS_FILE = "users.json"
DEFAULT_UNIT = "µg/mL"

# --- Helpers
def login_area():
    users = load_users(USERS_FILE)
    st.sidebar.title("Connexion")
    username = st.sidebar.text_input("Utilisateur")
    password = st.sidebar.text_input("Mot de passe", type="password")
    if st.sidebar.button("Se connecter"):
        if username in users and users[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = users[username].get("role", "user")
            st.experimental_rerun()
        else:
            st.sidebar.error("Nom d'utilisateur ou mot de passe incorrect")

def logout():
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.experimental_rerun()

def require_login():
    if "user" not in st.session_state:
        login_area()
        st.stop()

# --- Layout / Entrée
if "lang" not in st.session_state:
    st.session_state["lang"] = "fr"

st.sidebar.title("LabT")
st.sidebar.selectbox("Langue / Language", ("fr", "en"), index=0, key="lang")

if "user" not in st.session_state:
    login_area()
else:
    st.sidebar.write(f"Connecté: **{st.session_state['user']}** ({st.session_state.get('role','user')})")
    logout()

require_login()

# --- Menu
menu = ["Linéarité", "S/N", "Admin", "Aide / Readme"]
choice = st.sidebar.radio("Menu", menu)

# --- LINÉARITÉ PAGE
def page_linearity():
    st.title("Linéarité")
    col1, col2 = st.columns(2)

    with col1:
        st.header("Source des données")
        input_mode = st.radio("Choix", ["CSV", "Saisie manuelle"], index=0)
        df = None
        if input_mode == "CSV":
            uploaded = st.file_uploader("Importer un CSV (colonnes x,y ou time,intensity)", type=["csv", "txt"])
            if uploaded is not None:
                try:
                    df = read_csv_bytes(uploaded.read())
                    st.success("CSV lu")
                    st.dataframe(df.head())
                except Exception as e:
                    st.error(f"Erreur lecture CSV : {e}")
        else:
            manual_x = st.text_area("X (séparés par des virgules)", help="ex: 1,2,3,4")
            manual_y = st.text_area("Y (séparés par des virgules)", help="ex: 10,20,30,40")
            if st.button("Charger valeurs manuelles"):
                try:
                    xs = [float(s.strip()) for s in manual_x.split(",") if s.strip()!=""]
                    ys = [float(s.strip()) for s in manual_y.split(",") if s.strip()!=""]
                    if len(xs) != len(ys):
                        st.error("Les listes X et Y doivent avoir la même longueur")
                    else:
                        df = pd.DataFrame({"x": xs, "y": ys})
                        st.success("Données manuelles chargées")
                        st.dataframe(df)
                except Exception as e:
                    st.error(f"Erreur parsing : {e}")

        st.divider()
        st.header("Options d'export / unité")
        company = st.text_input("Nom de la compagnie (pour le rapport PDF)", value="Ma société")
        unit = st.text_input("Unité de concentration", value=DEFAULT_UNIT)

    with col2:
        st.header("Analyse")
        if df is None:
            st.info("Importer des données ou saisir manuellement pour calculer")
            return
        if len(df) < 2:
            st.error("Il faut au moins 2 points pour une régression")
            return

        # run regression
        try:
            slope, intercept, r2 = linear_regression_from_xy(df["x"].values, df["y"].values)
        except Exception as e:
            st.error(f"Erreur calcul linéarité : {e}")
            return

        st.metric("R²", f"{r2:.6f}")
        st.metric("Pente", f"{slope:.6f}")
        st.metric("Intercept", f"{intercept:.6f}")

        # plot
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.scatter(df["x"], df["y"], label="Données")
        xs = np.linspace(min(df["x"]), max(df["x"]), 200)
        ax.plot(xs, slope * xs + intercept, label="Régression", linewidth=2)
        ax.set_xlabel(f"Concentration ({unit})")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)

        st.subheader("Calcul concentration ↔ signal")
        colc1, colc2 = st.columns(2)
        with colc1:
            sig = st.number_input("Entrer signal (pour obtenir concentration)", value=0.0, format="%.6f")
            if st.button("Calculer concentration depuis signal"):
                try:
                    c = predict_conc_from_signal(sig, slope, intercept)
                    st.success(f"Concentration estimée : {c:.6g} {unit}")
                except Exception as e:
                    st.error(f"Erreur: {e}")
        with colc2:
            conc = st.number_input(f"Entrer concentration ({unit}) (pour obtenir signal)", value=0.0, format="%.6f")
            if st.button("Calculer signal depuis concentration"):
                try:
                    s = predict_signal_from_conc(conc, slope, intercept)
                    st.success(f"Signal estimé : {s:.6g}")
                except Exception as e:
                    st.error(f"Erreur: {e}")

        st.divider()
        st.header("Exporter / partager")
        slope_for_sn = st.checkbox("Exporter la pente vers volet S/N (st.session_state['slope'])", value=True)
        if slope_for_sn:
            st.session_state["slope"] = float(slope)

        if st.button("Exporter rapport Linéarité (PDF)"):
            try:
                pdf_bytes = export_linearity_pdf(
                    company_name=company,
                    unit=unit,
                    slope=slope,
                    intercept=intercept,
                    r2=r2,
                    df=df,
                )
                st.download_button("Télécharger le rapport (PDF)", data=pdf_bytes, file_name="linearity_report.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Erreur export PDF : {e}")

# --- S/N PAGE
def page_sn():
    st.title("S/N")
    st.write("Calculs de Signal à Bruit (classique et USP).")
    colA, colB = st.columns(2)
    with colA:
        source = st.radio("Source", ["CSV (x,y)", "Image (png/jpg/pdf)"], index=0)
        uploaded = st.file_uploader("Importer fichier", type=["csv","txt","png","jpg","jpeg","pdf"])
        csv_df = None
        image = None
        if uploaded:
            if uploaded.type.startswith("image") or uploaded.name.lower().endswith(".pdf"):
                try:
                    image = Image.open(uploaded)
                    st.image(image, use_container_width=True)
                except Exception as e:
                    st.error(f"PIL.UnidentifiedImageError: {e}")
            else:
                try:
                    csv_df = read_csv_bytes(uploaded.read())
                    st.dataframe(csv_df.head())
                except Exception as e:
                    st.error(f"Erreur lecture CSV : {e}")

    with colB:
        st.header("Zone / Paramètres")
        if csv_df is not None:
            xcol = st.selectbox("Colonne X", options=list(csv_df.columns), index=0)
            ycol = st.selectbox("Colonne Y", options=list(csv_df.columns), index=1 if len(csv_df.columns)>1 else 0)
            xmin = st.number_input("Début zone X pour bruit (xmin)", value=float(csv_df[xcol].iloc[0]))
            xmax = st.number_input("Fin zone X pour bruit (xmax)", value=float(csv_df[xcol].iloc[min(10,len(csv_df)-1)]))
            peak_x = st.number_input("Position du pic (X) pour signal", value=float(csv_df[xcol].iloc[len(csv_df)//2]))
            if st.button("Calculer S/N depuis CSV"):
                try:
                    mask_noise = (csv_df[xcol] >= xmin) & (csv_df[xcol] <= xmax)
                    noise_vals = csv_df.loc[mask_noise, ycol].values
                    if len(noise_vals) < 2:
                        st.error("Zone bruit trop petite")
                    else:
                        # signal: take max in small window around peak_x
                        window = float((csv_df[xcol].max() - csv_df[xcol].min())*0.01)
                        peak_mask = (csv_df[xcol] >= (peak_x - window)) & (csv_df[xcol] <= (peak_x + window))
                        peak_val = csv_df.loc[peak_mask, ycol].max()
                        sn_classic = compute_sn_classic(peak_val, noise_vals)
                        slope = st.session_state.get("slope", None)
                        sn_usp = None
                        if slope is not None:
                            # if slope known, convert signal to concentration and compute USP S/N using slope
                            sn_usp = compute_sn_usp(peak_val, noise_vals, slope)
                        st.success(f"S/N classique = {sn_classic:.3f}")
                        if sn_usp is not None:
                            st.success(f"S/N USP (approx) = {sn_usp:.3f}")
                except Exception as e:
                    st.error(f"Erreur calcul S/N: {e}")

        elif image is not None:
            st.info("Pour image : indique la zone X (en pixels) à utiliser pour le bruit et la position (en pixels) du pic.")
            x1 = st.number_input("xmin (px)", min_value=0, value=0)
            x2 = st.number_input("xmax (px)", min_value=0, value=image.size[0])
            peak_x = st.number_input("Peak X (px)", min_value=0, value=image.size[0]//2)
            if st.button("Calculer S/N depuis image (basique)"):
                try:
                    # convert to grayscale and take vertical profile (mean across y)
                    gray = image.convert("L")
                    arr = np.array(gray)
                    profile = arr.mean(axis=0)  # mean intensity per column
                    noise_vals = profile[int(x1):int(x2)]
                    if len(noise_vals) < 2:
                        st.error("Zone bruit trop petite.")
                    else:
                        peak_val = profile[int(peak_x)]
                        sn_classic = compute_sn_classic(peak_val, noise_vals)
                        slope = st.session_state.get("slope", None)
                        sn_usp = compute_sn_usp(peak_val, noise_vals, slope) if slope is not None else None
                        st.success(f"S/N classique = {sn_classic:.3f}")
                        if sn_usp is not None:
                            st.success(f"S/N USP (approx) = {sn_usp:.3f}")
                except Exception as e:
                    st.error(f"Erreur traitement image : {e}")
        else:
            st.info("Importer un CSV (x,y) ou une image pour faire les calculs.")

# --- ADMIN PAGE
def page_admin():
    if st.session_state.get("role","user") != "admin":
        st.warning("Accès admin réservé. Contacte un administrateur.")
        return
    st.title("Admin - Gestion des utilisateurs")
    users = load_users(USERS_FILE)
    st.write("Utilisateurs actuels")
    st.json(users)

    st.header("Ajouter un utilisateur")
    newu = st.text_input("Nom d'utilisateur (nouveau)")
    newp = st.text_input("Mot de passe", type="password")
    newrole = st.selectbox("Role", ["user", "admin"])
    if st.button("Ajouter utilisateur"):
        if not newu or not newp:
            st.error("Utilisateur et mot de passe requis")
        else:
            users[newu] = {"password": newp, "role": newrole}
            save_users(USERS_FILE, users)
            st.success("Utilisateur ajouté. Redémarre la page.")
            st.experimental_rerun()

    st.header("Modifier / Supprimer")
    sel = st.selectbox("Choisir utilisateur", options=list(users.keys()))
    if sel:
        st.text_input("Modifier mot de passe", key="mod_pass")
        st.selectbox("Modifier role", ["user","admin"], key="mod_role")
        if st.button("Enregistrer modifications"):
            mp = st.session_state.get("mod_pass")
            mr = st.session_state.get("mod_role")
            if mp:
                users[sel]["password"] = mp
            if mr:
                users[sel]["role"] = mr
            save_users(USERS_FILE, users)
            st.success("Modifications enregistrées")
            st.experimental_rerun()
        if st.button("Supprimer utilisateur"):
            if sel in users:
                del users[sel]
                save_users(USERS_FILE, users)
                st.success("Utilisateur supprimé")
                st.experimental_rerun()

# --- README / Aide
def page_readme():
    st.title("README / Aide")
    readme = open("README.md", "r", encoding="utf-8").read()
    st.markdown(readme)

# --- Router
if choice == "Linéarité":
    page_linearity()
elif choice == "S/N":
    page_sn()
elif choice == "Admin":
    page_admin()
else:
    page_readme()