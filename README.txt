# LabT - Chromatogram Analyzer

## Description
LabT est une application Streamlit pour l'analyse de chromatogrammes selon la méthode USP. 
Elle permet :
- Calcul du signal/bruit (S/N), LOD, LOQ
- Courbe de linéarité avec saisie manuelle ou CSV
- Calcul d'une concentration inconnue
- Export PDF des rapports
- Gestion des utilisateurs pour l'admin

## Utilisation
1. Installer les dépendances : `pip install -r requirements.txt`
2. Lancer l'application : `streamlit run app.py`
3. Se connecter avec l'un des utilisateurs par défaut :
   - admin / admin123
   - bb / bb123
   - user / user123
4. Choisir l'action : Linéarité ou S/N

## Admin
- L'administrateur peut ajouter, supprimer ou modifier les utilisateurs.