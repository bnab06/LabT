# LabT - Application de Linéarité et Signal/Noise

## Description
Application Streamlit bilingue (Français/Anglais) pour le calcul de linéarité et S/N.

Fonctionnalités principales :
- **Linéarité**
  - Entrée CSV ou manuelle
  - Calcul automatique de concentration ou signal inconnu
  - Graphique avec régression linéaire
  - Export PDF avec graphique, pente, intercept, R², nom de la compagnie, utilisateur et date
  - Possibilité d’exporter la pente vers S/N pour LOD/LOQ
- **S/N**
  - Import CSV / PNG / PDF
  - Affichage chromatogrammes
  - Choix de la portion du graphique pour le calcul
  - Calcul S/N classique et USP

## Authentification
- Admin : accès uniquement à la gestion des utilisateurs
- User : accès aux calculs
- Mot de passe modifiable via un bouton discret

## Installation
1. Installer Python 3.11
2. Installer les dépendances :  
   ```bash
   pip install -r requirements.txt