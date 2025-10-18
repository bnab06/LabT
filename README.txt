# LabT – Application de Calcul de Linéarité et S/N USP

LabT est une application Streamlit pour le calcul de la linéarité, du signal/bruit (S/N), du LOD et du LOQ à partir de chromatogrammes. Elle permet également de générer des rapports PDF personnalisés.

## Fonctionnalités

- **Connexion utilisateur** avec gestion des utilisateurs par l’administrateur.
- **Linéarité** : 
  - Saisie manuelle des concentrations et réponses (séparées par virgule).  
  - Calcul automatique de R², équation de la droite, et concentration inconnue à partir d’un signal.  
  - Possibilité de choisir l’unité de concentration (`µg/mL` par défaut).  
  - Génération d’un rapport PDF avec logo, date et utilisateur.
- **S/N, LOD, LOQ** : 
  - Chargement et visualisation de chromatogrammes en CSV (PDF et PNG à venir avec OCR rapide).  
  - Sélection de zones pour calculer le bruit.  
  - Calcul automatique de S/N, LOD et LOQ.

## Installation

1. Cloner le dépôt ou télécharger les fichiers :  
   - `app.py`  
   - `requirements.txt`  
   - `users.json`  
   - `logo.png` (optionnel)

2. Installer les dépendances :  
```bash
pip install -r requirements.txt