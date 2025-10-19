# LabT - Analytical Tool

LabT is a Streamlit-based application for laboratory data analysis. It allows users to perform linearity analysis, calculate signal-to-noise ratios (S/N), and generate PDF reports.

---

## Features

- **User Management** (Admin only)
  - Add, modify, delete users
  - Roles: `admin` or `user`
- **Linearity Analysis**
  - Input known concentrations and corresponding responses
  - Calculate linear regression, display equation and R²
  - Solve for unknown concentration or unknown signal
  - Export report to PDF with company name, username, and timestamp
- **Signal-to-Noise (S/N) Analysis**
  - Upload chromatogram CSV files
  - Calculate standard S/N and USP S/N
  - Compute LOD (Limit of Detection) and LOQ (Limit of Quantitation)
  - Convert S/N into concentration using linearity data
  - Export PDF report
- **PDF Reports**
  - Include company name, user, date, and LabT log
  - Downloadable via browser
- **Bilingual support**
  - English is default, but can be adapted for other languages

---

## Requirements

Python 3.10+ and the following packages: