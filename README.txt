# LabT – Chromatogram Analyzer

LabT est une application Streamlit pour :

- Calcul USP S/N, LOD et LOQ à partir de fichiers CSV, PNG ou PDF
- Tracer et analyser des chromatogrammes
- Calculer la linéarité (entrée manuelle ou CSV)
- Calcul automatique de concentration inconnue ou signal inconnu
- Export PDF des rapports avec logo, date et utilisateur
- Gestion simple des utilisateurs (admin uniquement)

## Connexion

- Utilisateurs par défaut : 
  - admin / bb
  - BB / bb
  - user / user
- Admin peut seulement ajouter, supprimer ou modifier les utilisateurs

## Installation

1. Créez un environnement Python 3.13
2. Installez les dépendances : 
   ```bash
   pip install -r requirements.txt