# LabT - Streamlit App

## Files
- app.py : main Streamlit application
- requirements.txt : required Python packages
- users.json : default users and credentials

## Default users
- admin / admin  (admin, can manage users)
- user1 / 1234   (user)
- user2 / abcd   (user)

## Deploy / Local
1. Create a virtual environment (recommended)
2. Install requirements:
   pip install -r requirements.txt
3. Run:
   streamlit run app.py

## Notes
- The app supports bilingual UI (EN/FR).
- Admin page: add/modify/delete users.
- Users can change their password.
- Linearity: manual input or CSV upload. Shows fit, R², equation.
- S/N: upload chromatogram CSV (Time & Signal), choose baseline region to compute noise, S/N, LOD/LOQ. Option to convert LOD/LOQ to concentration if a slope from a linearity is present.
- Export PDF: includes report text and embedded plot PNG.