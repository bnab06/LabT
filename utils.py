# utils.py
import numpy as np
import pandas as pd
from io import BytesIO
from fpdf import FPDF
import json

def read_csv_bytes(b: bytes) -> pd.DataFrame:
    """Lis un csv depuis bytes et retourne un DataFrame.
    On accepte csv avec 2 colonnes (x,y) ou colonnes nommées."""
    s = BytesIO(b)
    df = pd.read_csv(s)
    # essayer de standardiser colonnes
    if df.shape[1] >= 2:
        df = df.iloc[:, :2]
        df.columns = ["x","y"]
    return df

def linear_regression_from_xy(x, y):
    """Retourne slope, intercept, r2"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        raise ValueError("Pas assez de points")
    A = np.vstack([x, np.ones(len(x))]).T
    # numpy lstsq
    res = np.linalg.lstsq(A, y, rcond=None)
    coef, residuals, rank, svals = res
    slope = coef[0]
    intercept = coef[1]
    # calcul R2
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot != 0 else 0.0
    return float(slope), float(intercept), float(r2)

def predict_conc_from_signal(signal, slope, intercept):
    """Concentration = (signal - intercept) / slope"""
    slope = float(slope)
    intercept = float(intercept)
    if slope == 0:
        raise ValueError("Pente = 0")
    return (signal - intercept) / slope

def predict_signal_from_conc(conc, slope, intercept):
    return slope * conc + intercept

def export_linearity_pdf(company_name, unit, slope, intercept, r2, df):
    """Génère un PDF simple et renvoie bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Rapport Linéarité - {company_name}", ln=True)
    pdf.cell(0, 6, f"Unité: {unit}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 6, f"Pente: {slope:.6f}", ln=True)
    pdf.cell(0, 6, f"Intercept: {intercept:.6f}", ln=True)
    pdf.cell(0, 6, f"R2: {r2:.6f}", ln=True)
    pdf.ln(6)
    pdf.cell(0, 6, "Données (extrait):", ln=True)
    pdf.ln(2)
    # tabulaire: 10 premières lignes
    for i, row in df.head(10).iterrows():
        pdf.cell(0, 5, f"{row['x']:.6g}\t{row['y']:.6g}", ln=True)
    # renvoyer bytes
    return pdf.output(dest="S").encode("latin-1")

def compute_sn_classic(peak_value, noise_array):
    """S/N classique: (peak - mean(noise))/std(noise)"""
    noise = np.asarray(noise_array, dtype=float)
    if noise.size < 2:
        raise ValueError("Bruit insuffisant pour calculer std")
    noise_mean = noise.mean()
    noise_std = noise.std(ddof=1)
    if noise_std == 0:
        raise ValueError("Écart-type du bruit = 0")
    return float((peak_value - noise_mean) / noise_std)

def compute_sn_usp(peak_value, noise_array, slope):
    """
    Approche basique pour 'USP' : convertir signal->concentration avec pente, 
    puis calculer S/N en concentration.
    S/N_USP = (conc_peak - mean(conc_noise)) / std(conc_noise)
    where conc = (signal - intercept)/slope, but if intercept unknown, approximate.
    Here slope is used as conversion factor (signal per conc).
    """
    noise = np.asarray(noise_array, dtype=float)
    if noise.size < 2:
        raise ValueError("Bruit insuffisant")
    if slope == 0:
        raise ValueError("Slope = 0")
    conc_noise = noise / slope
    conc_peak = peak_value / slope
    nm = conc_noise.mean()
    ns = conc_noise.std(ddof=1)
    if ns == 0:
        raise ValueError("std(conc_noise)=0")
    return float((conc_peak - nm) / ns)

# --- Users helpers
def load_users(path="users.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            users = json.load(f)
    except FileNotFoundError:
        # créer un user admin par défaut
        users = {"admin": {"password": "admin", "role":"admin"}}
        save_users(path, users)
    return users

def save_users(path, users):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)