# LABT — Linearity & Signal-to-Noise (S/N) Streamlit app

## But
Application pour:
- calculer la linéarité (slope, intercept, R²),
- prédire concentration ↔ signal,
- calculer S/N (classique & USP-like), LOD/LOQ (si pente disponible),
- exporter rapports PDF,
- gérer utilisateurs (admin).

L'application est bilingue (FR/EN). Interface principale sans sidebar.

## Fichiers fournis
- `app.py` — application Streamlit
- `requirements.txt` — dépendances recommandées
- `users.json` — exemple d'utilisateurs (admin/user) — **ne pas** exposer publiquement
  - admin: `admin / admin123`
  - user: `user / user123`

## Installation (local)
1. Créer un environnement Python 3.11:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt