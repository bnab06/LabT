# LabT - Application de laboratoire

## Description
LabT est une application Streamlit pour :
- La gestion des utilisateurs (admin uniquement)
- Le tracé de courbes de linéarité
- Le calcul du rapport signal/bruit (S/N) et USP S/N
- Export des rapports en PDF

## Fonctionnalités
- Connexion sécurisée
- Interface bilingue Français / English
- Calcul de LOD et LOQ
- S/N converti en concentration
- Génération de PDF avec nom de l’utilisateur, date et société

## Installation
1. Installer Python >= 3.10
2. Créer un environnement virtuel :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows