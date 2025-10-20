# LabT Application

## Description
LabT est une application pour la gestion de linéarité, calcul S/N classique et USP, LOD/LOQ en concentration, et export PDF/PNG/CSV.

## Features
- Login admin / user (username non case-sensitive)
- User peut changer son mot de passe
- Linéarité : CSV ou saisie manuelle, R² affiché
- S/N : choix de zone, export PDF/PNG/CSV
- Graphiques interactifs
- Application bilingue (FR/EN)
- Export rapport PDF avec logo, nom entreprise, utilisateur, date

## Requirements
- Python 3.11
- Voir `requirements.txt`

## Deployment
```bash
pip install -r requirements.txt
streamlit run app.py