# LabT Application

## Description
LabT is a bilingual (English/French) Streamlit application for laboratory calculations including unknown concentration, S/N ratio (classic & USP), LOD, LOQ, and linearity. It allows admin management of users and normal users can update their password.

## Features
- Bilingual interface: English & French
- Admin panel: add, modify, delete users
- User panel: change password
- Unknown concentration calculations
- Signal-to-noise (classic & USP)
- LOD/LOQ calculation using linearity
- PDF report generation including units
- Validation to ensure company name is entered before PDF generation
- Return to previous menu functionality

## Requirements
Use the provided `requirements.txt` for a consistent environment.

```txt
streamlit==1.39.0
pandas==2.2.3
numpy==2.1.3
plotly==5.24.1
matplotlib==3.7.2
scipy==1.11.2
fpdf2==2.8.1
pygments==2.19.2
rich==14.2.0
markdown-it-py==4.0.0
mdurl==0.1.2