import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from PIL import Image
import pytesseract
import pdfplumber
import io

def calculate_sn(df, start, end):
    df_zone = df[(df["Time"] >= start) & (df["Time"] <= end)]
    y = df_zone["Signal"].values
    peak_height = np.max(y)
    noise = np.std(y)
    sn = peak_height / noise
    lod = 3 * noise
    loq = 10 * noise
    return sn, lod, loq, df_zone

def linear_regression(df):
    x = np.array(df["Concentration"]).reshape(-1,1)
    y = np.array(df["Response"])
    model = LinearRegression().fit(x,y)
    slope = model.coef_[0]
    intercept = model.intercept_
    r2 = model.score(x,y)
    return slope, intercept, r2

def load_chromatogram_pdf_png(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        df.columns = ["Time","Signal"]
        return df
    elif uploaded_file.name.endswith(".png"):
        img = Image.open(uploaded_file).convert("RGB")
        text = pytesseract.image_to_string(img)
        lines = text.splitlines()
        data = [line.split() for line in lines if len(line.split())==2]
        if len(data)==0:
            return None
        df = pd.DataFrame(data, columns=["Time","Signal"])
        df = df.astype(float)
        return df
    elif uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            page = pdf.pages[0]
            text = page.extract_text()
            lines = text.splitlines()
            data = [line.split() for line in lines if len(line.split())==2]
            if len(data)==0:
                return None
            df = pd.DataFrame(data, columns=["Time","Signal"])
            df = df.astype(float)
            return df
    else:
        return None