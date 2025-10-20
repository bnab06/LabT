# App: LabT

## Description
LabT est une application Streamlit pour le traitement de données de laboratoire, calcul du rapport inconnu, S/N, LOD et LOQ. L'application est **bilingue** (anglais/français) et offre une gestion utilisateurs sécurisée.

## Fonctionnalités

### Connexion
- Connexion avec utilisateur et mot de passe.
- Gestion de la casse ignorée pour les noms d'utilisateur.

### Rôles
- **Admin** :
  - Ajouter, supprimer ou modifier des utilisateurs.
  - Accès uniquement à la gestion utilisateurs.
- **User** :
  - Modifier son mot de passe.

### Calculs
- Calcul inconnu (concentration et signal avec unités).
- Calcul S/N classique et USP.
- Possibilité de générer LOD et LOQ à partir de la courbe de linéarité.
- Export des résultats et graphiques en PDF.
- Choix de la langue pour les menus et messages.

### Dépendances
- `streamlit`, `pandas`, `numpy`, `plotly`, `fpdf2`, `matplotlib`.

## Installation

1. Créer un environnement Python 3.13 :
```bash
python -m venv venv
source venv/bin/activate  # Linux / Mac
venv\Scripts\activate     # Windows