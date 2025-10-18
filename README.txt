# LabT

LabT est une application Streamlit pour le calcul USP S/N, LOD, LOQ et pour tracer des courbes de linéarité.

## Fonctionnalités

- Connexion utilisateur avec mot de passe.
- Gestion des utilisateurs par l'admin uniquement.
- Calcul de S/N sur chromatogrammes (CSV pour l'instant, PDF/PNG à ajouter).
- Courbe de linéarité avec calcul automatique de la concentration ou du signal inconnu.
- Export possible de rapports PDF (avec logo, date et utilisateur).
- Interface moderne, compacte et intuitive.
- Boutons activés au **simple clic**.

## Installation

1. Installer Python 3.11 ou supérieur.
2. Créer un environnement virtuel:
   ```bash
   python -m venv env
   source env/bin/activate   # Linux/macOS
   env\Scripts\activate      # Windows