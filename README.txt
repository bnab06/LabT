# LabT — Streamlit application

Small QC / lab helper:
- Linearity (manual input or CSV) — slope, intercept, R², compute unknown concentration or signal.
- Signal-to-noise (S/N) (CSV, PNG or PDF display). Choose baseline window; compute classic S/N and USP S/N. Convert LOD/LOQ to concentration using linearity slope.
- Admin: user management (add/modify/delete).
- Users can change their password.
- Bilingual: English (default) and French.
- Export simple reports to PDF (logo `labt_logo.png` required).

## Files
- `app.py` — main application
- `requirements.txt`
- `labt_logo.png` — put your logo here (optional)
- `users.json` — created automatically with sample users (`admin`, `bb`, `user`)

## Quick start (local)
1. Create a virtualenv with Python 3.11+.
2. `pip install -r requirements.txt`
3. Place `labt_logo.png` next to `app.py` (optional).
4. `streamlit run app.py`

## Notes
- If running on Streamlit Cloud, adjust `requirements.txt` versions if installation issues appear.
- For PDF preview, `pdf2image` requires `poppler`.
- If you upload PNG/PDF chromatograms and you want automatic numeric extraction, that is out-of-scope here; instead the app displays the image and allows manual numeric entry for S/N computation.