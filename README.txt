# LabT - Chromatogram Analysis

LabT est une application Streamlit pour analyser des chromatogrammes, calculer le signal/bruit, LOD, LOQ et tracer des courbes de calibration (linéarité).

## Fonctionnalités

- Login sécurisé avec `admin`, `bb` et `user`.
- Import CSV, PNG, PDF pour calculs S/N.
- Calcul automatique de Signal / Bruit, LOD, LOQ.
- Courbes de linéarité avec calcul R².
- Export graphique et rapport PDF (à implémenter).
- Choix des unités : µg/mL ou mg/mL, aire ou absorbance.

## Déploiement

```bash
pip install -r requirements.txt
streamlit run app.py