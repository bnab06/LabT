# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io
from pdf2image import convert_from_bytes
import pytesseract

# ==========================================================
#            OUTILS GÉNÉRAUX + BILINGUE SIMPLE
# ==========================================================
def t(txt):
    return txt

# --- Conversion PDF → image ---
def pdf_to_png_bytes(uploaded_file):
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1, dpi=300)
        if pages:
            return pages[0].convert("RGB"), None
    except Exception as e:
        return None, f"Erreur conversion PDF : {e}"
    return None, "Erreur inconnue PDF"

# ==========================================================
#               MODULE LINÉARITÉ
# ==========================================================
def linearity_module():
    st.title("📊 Linéarité")

    mode = st.radio("Méthode de saisie :", ["Importer un fichier CSV", "Saisie manuelle"])

    slope = None
    unit = st.selectbox("Unité de concentration :", ["µg/mL", "mg/mL", "ng/mL"], index=0)

    if mode == "Importer un fichier CSV":
        uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
            if "Concentration" in df.columns and "Réponse" in df.columns:
                x, y = df["Concentration"], df["Réponse"]
                try:
                    coeffs = np.polyfit(x, y, 1)
                    slope, intercept = coeffs
                    r = np.corrcoef(x, y)[0, 1]
                    st.markdown(f"**Équation :** y = {slope:.4f}x + {intercept:.4f}")
                    st.markdown(f"**R² = {r**2:.4f}**")
                    st.session_state["slope_lin"] = slope
                except np.linalg.LinAlgError:
                    st.error("Erreur : impossible de calculer la droite de régression (SVD non convergente).")
            else:
                st.warning("Le fichier doit contenir les colonnes 'Concentration' et 'Réponse'.")

    else:
        concs = st.text_input("Concentrations (séparées par des virgules)")
        signals = st.text_input("Réponses / Signaux (séparées par des virgules)")
        if concs and signals:
            try:
                x = np.array([float(i) for i in concs.split(",")])
                y = np.array([float(i) for i in signals.split(",")])
                if len(x) == len(y) and len(x) > 1:
                    coeffs = np.polyfit(x, y, 1)
                    slope, intercept = coeffs
                    r = np.corrcoef(x, y)[0, 1]
                    st.markdown(f"**Équation :** y = {slope:.4f}x + {intercept:.4f}")
                    st.markdown(f"**R² = {r**2:.4f}**")
                    st.session_state["slope_lin"] = slope
                else:
                    st.warning("Nombre de valeurs incohérent.")
            except Exception as e:
                st.error(f"Erreur de saisie : {e}")

    return slope, unit

# ==========================================================
#               ANALYSE S/N AUTOMATIQUE
# ==========================================================
def analyze_sn(image):
    try:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    except Exception:
        return None, "Erreur: image invalide."

    profile = np.mean(gray, axis=0)
    x = np.arange(len(profile))
    y = profile

    if len(np.unique(x)) <= 1:
        return None, "Signal plat ou OCR invalide : axe X artificiel utilisé."

    # --- Détection du pic principal ---
    peak_idx = np.argmax(y)
    peak_height = y[peak_idx]
    retention_time_px = x[peak_idx]

    # Conversion (fictive) en minutes
    retention_time_min = retention_time_px / 100.0
    tr_label = f"{retention_time_min:.2f} min"

    # --- Marquage sur l’image ---
    img_marked = np.array(image).copy()
    y_center = gray.shape[0] // 2
    cv2.circle(img_marked, (peak_idx, y_center), 10, (255, 0, 0), -1)
    cv2.putText(img_marked, tr_label, (peak_idx + 10, y_center - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    baseline = np.median(y)
    noise = np.std(y[:len(y)//10]) if len(y) > 10 else 1
    sn_classic = (peak_height - baseline) / (noise if noise != 0 else 1)
    sn_usp = sn_classic / np.sqrt(2)

    return {
        "S/N Classique": sn_classic,
        "S/N USP": sn_usp,
        "tR (px)": retention_time_px,
        "tR (min)": retention_time_min,
        "image_marked": img_marked
    }, None

# ==========================================================
#               MODULE S/N
# ==========================================================
def sn_module():
    st.title("📈 Rapport Signal / Bruit (S/N)")
    slope_lin = st.session_state.get("slope_lin", None)
    unit = st.session_state.get("unit", "µg/mL")

    uploaded_file = st.file_uploader("Importer une image ou un PDF", type=["png", "jpg", "jpeg", "pdf"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            img, err = pdf_to_png_bytes(uploaded_file)
            if err:
                st.error(err)
                return
        else:
            img = Image.open(uploaded_file).convert("RGB")

        res, err = analyze_sn(img)
        if err:
            st.warning(err)
        elif res:
            st.image(res["image_marked"], caption="Pic détecté", use_container_width=True)
            st.markdown(f"**S/N Classique :** {res['S/N Classique']:.4f}")
            st.markdown(f"**S/N USP :** {res['S/N USP']:.4f}")
            st.markdown(f"**tR :** {res['tR (min)']:.2f} min")

    # --- Calcul manuel indépendant ---
    with st.expander("🧮 Calcul manuel (S/N Classique & USP)"):
        H = st.number_input("Hauteur du pic (H)", min_value=0.0, format="%.4f")
        h = st.number_input("Hauteur du bruit (h)", min_value=0.0, format="%.4f")
        if H > 0 and h > 0:
            sn_manual = H / h
            sn_manual_usp = sn_manual / np.sqrt(2)
            st.markdown(f"**S/N (Classique)** = {sn_manual:.2f}")
            st.markdown(f"**S/N (USP)** = {sn_manual_usp:.2f}")

            # LOD & LOQ (Signal et Concentration)
            if slope_lin:
                lod_signal = 3.3 * h
                loq_signal = 10 * h
                lod_conc = lod_signal / slope_lin
                loq_conc = loq_signal / slope_lin
                st.markdown("---")
                st.markdown(f"**LOD (signal)** = {lod_signal:.2f}")
                st.markdown(f"**LOQ (signal)** = {loq_signal:.2f}")
                st.markdown(f"**LOD (concentration)** = {lod_conc:.4f} {unit}")
                st.markdown(f"**LOQ (concentration)** = {loq_conc:.4f} {unit}")
            else:
                st.info("Aucune pente de linéarité disponible. Vous pouvez la saisir manuellement.")
                slope_manual = st.number_input("Saisir pente de la droite de linéarité", min_value=0.0001, format="%.6f")
                if slope_manual > 0:
                    lod_signal = 3.3 * h
                    loq_signal = 10 * h
                    lod_conc = lod_signal / slope_manual
                    loq_conc = loq_signal / slope_manual
                    st.markdown("---")
                    st.markdown(f"**LOD (signal)** = {lod_signal:.2f}")
                    st.markdown(f"**LOQ (signal)** = {loq_signal:.2f}")
                    st.markdown(f"**LOD (concentration)** = {lod_conc:.4f} {unit}")
                    st.markdown(f"**LOQ (concentration)** = {loq_conc:.4f} {unit}")

# ==========================================================
#               INTERFACE PRINCIPALE
# ==========================================================
def main_app():
    st.set_page_config(page_title="LabT", layout="wide")

    st.markdown(\"\"\"
        <h2 style='text-align:center;'>🔬 LabT — Analyse Chromatographique</h2>
        <hr>
    \"\"\", unsafe_allow_html=True)

    page = st.selectbox("Sélectionner un module :", ["Accueil", "Linéarité", "S/N"], index=0)

    if page == "Accueil":
        st.info("Bienvenue dans LabT — choisissez un module ci-dessus.")

    elif page == "Linéarité":
        slope, unit = linearity_module()
        if slope:
            st.success(f"Pente enregistrée : {slope:.4f} ({unit})")
            st.session_state["slope_lin"] = slope
            st.session_state["unit"] = unit

    elif page == "S/N":
        sn_module()

# ==========================================================
#               LANCEMENT
# ==========================================================
if __name__ == "__main__":
    main_app()
