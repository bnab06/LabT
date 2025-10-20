# LabT - Streamlit Analytical App

## Overview
LabT is a bilingual analytical app for linearity, signal-to-noise (S/N) calculations, and PDF report generation.

Features:
- User roles: Admin and User
- Admin can manage users only
- Users can calculate linearity, unknown concentrations/signals, S/N (classic & USP)
- Upload CSV for data
- Choose noise region for S/N
- Generate PDF reports with graphs, username, company, and date
- Change password
- Bilingual interface (English/French)

## Installation
1. Install Python 3.11+
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows