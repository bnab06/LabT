# LabT - Streamlit Application

**LabT** est une application complète pour les analyses de linéarité et de signal/bruit (S/N), avec gestion des utilisateurs et export PDF.

## Fonctionnalités

### Pour tous les utilisateurs
- Connexion (login case-insensitive)
- Langue bilingue (FR / EN)
- Calcul de linéarité
  - Saisie manuelle ou import CSV
  - Calcul automatique de l’équation et R²
  - Estimation d’inconnues (concentration ou signal)
  - Export PDF avec graphique et logo
- Calcul S/N (classique et USP)
  - Upload de chromatogrammes CSV (`Time`, `Signal`)
  - Calcul de LOD / LOQ
  - Conversion en concentration si linéarité disponible
  - Export PDF du rapport et du graphique

### Pour l’administrateur
- Gestion complète des utilisateurs
  - Ajouter / Modifier / Supprimer
- Seul l’admin peut gérer les rôles et mots de passe

### Pour les utilisateurs
- Changement de mot de passe personnel

## Fichiers principaux
- `app.py` : script principal Streamlit
- `users.json` : base utilisateurs
- `requirements.txt` : packages Python nécessaires
- `logo.png` : logo LabT pour les PDF (optionnel)

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py