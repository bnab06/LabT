# LabT - Chromatography and Linearity App

**Description:**
LabT is a Streamlit-based application for chromatogram analysis, including:
- Signal-to-noise (S/N) calculation
- LOD & LOQ determination
- Linearity plot and calculation
- Concentration or signal prediction
- Admin user management

**Features:**
- Login with role-based access (admin/user)
- S/N, LOD, LOQ from CSV chromatograms
- Manual or CSV input for linearity
- Automatic R² calculation
- PDF export of reports (with logo, date, and username)
- Simple, modern UI (no sidebar)
- All buttons work with a single click

**Default Users:**
- admin / admin123
- bb / bb123
- user / user123

**Usage:**
1. Install requirements:
```bash
pip install -r requirements.txt