# LabT — Linéarité & S/N (Streamlit)

## Résumé
Application Streamlit pour:
- Calcul de la linéarité (import CSV ou saisie manuelle), affichage pente/intercept/R², prédictions concentration ↔ signal, export PDF avec graphique.
- Calcul S/N depuis un chromatogramme (image PNG/JPG ou CSV), possibilité de sélectionner la zone pour le calcul du bruit, calcul S/N classique et "USP".
- Gestion des utilisateurs (admin peut ajouter/supprimer/modifier). Les users peuvent changer leur mot de passe via une option discrète.
- Bilingue: anglais par défaut, français disponible via le menu.

## Installation (local / container)
1. Utiliser Python **3.11**.
2. Créer un environnement:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt