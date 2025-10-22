# LabT - Streamlit App

Petit outil analytique LabT pour :
- 📈 **Courbe de linéarité** (saisie manuelle ou CSV)
- 📊 **Calcul du rapport Signal / Bruit (S/N)** :
  - Traditionnel et USP
  - Import possible de chromatogrammes (CSV, PDF, PNG)
  - Sélection de zone de bruit
- 📄 **Export PDF** avec le nom de la compagnie
- 👤 **Authentification** :
  - Admin = gère uniquement les utilisateurs
  - User = utilise les outils analytiques et peut changer son mot de passe
- 🌐 **Bilingue** : anglais par défaut / français en option

---

## ⚙️ Installation locale

```bash
# Créer l'environnement
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sous Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py