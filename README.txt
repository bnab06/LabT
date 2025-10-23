# LabT - Streamlit App

Petit outil **LabT** pour :
- 📈 Courbe de linéarité (CSV ou saisie manuelle)
- 🔢 Calcul automatique de concentration ou signal inconnu
- 📊 Calcul du rapport S/N (CSV, PNG, PDF)
- 🧾 Export PDF avec le nom de la compagnie
- 🔐 Authentification : admin + utilisateurs
- ⚙️ Admin : gestion utilisateurs (add, delete, modify)
- 👥 Users : peuvent changer leur mot de passe
- 🌐 Application bilingue (FR/EN)
- 🖱️ Interface sans sidebar, boutons à un seul clic

## Installation locale
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py