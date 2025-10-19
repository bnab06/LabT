# LabT - Signal to Noise & Linearity Analysis

**LabT** is a Streamlit application for managing users and performing chromatographic analyses including linearity curves and signal-to-noise calculations, with PDF reporting.

---

## Features

1. **User Management (Admin only)**
   - Add, edit, or delete users.
   - Bilingual interface (English/French).
   - Role-based access: `admin` and `user`.
   - Display logged-in user.

2. **Linearity Curve**
   - Input known concentrations and responses.
   - Compute slope, intercept, and R².
   - Calculate unknown concentration or signal.
   - Export report to PDF (includes user, date, unit, company).

3. **Signal-to-Noise (S/N)**
   - Upload CSV chromatograms with `Time` and `Signal` columns.
   - Calculate classical S/N and USP S/N.
   - Calculate LOD and LOQ.
   - Convert S/N to concentration using linearity slope.
   - Export report to PDF.

4. **PDF Reports**
   - Include username, date, company, units, and App: LabT.
   - Downloadable and shareable.

---

## Installation

1. Clone the repository or copy the files:

```bash
git clone <your-repo-url>
cd <repo-folder>