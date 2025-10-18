# LabT

LabT est une application Streamlit pour les calculs de linéarité et S/N (USP) pour chromatogrammes.

## Fonctionnalités
- Connexion utilisateur avec menu déroulant.
- Gestion des utilisateurs par l'admin (ajout de nouveaux utilisateurs).
- Calcul S/N, LOD, LOQ à partir de fichiers CSV.
- Courbe de linéarité avec R² affiché automatiquement.
- Calcul automatique de concentration inconnue à partir du signal.
- Choix d'unités de concentration (µg/mL ou mg/mL) et type de réponse (aire ou absorbance).
- Boutons à **un seul clic** et retour au menu principal.
- Tutoriel pour convertir PDF/PNG en CSV pour le calcul S/N.

## Instructions
1. Installer les dépendances :
```bash
pip install -r requirements.txt