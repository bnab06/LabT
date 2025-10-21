# LabT - Streamlit App

Petit outil LabT pour :
- Courbe de linéarité (saisie manuelle ou CSV)
- Calcul Signal-to-Noise (CSV) avec choix de la région de bruit
- Export de rapports PDF (avec le nom de la compagnie)
- Authentification simple (admin + users), admin gère uniquement les utilisateurs
- Bilingue (English default / Français)

## Fichiers principaux
- `app.py` : application Streamlit complète
- `users.json` : utilisateurs initiaux (admin, user1, user2)
- `requirements.txt` : dépendances recommandées

## Installation (local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py