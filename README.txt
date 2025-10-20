# LabT – Application de calculs chromatographiques / Chromatography Calculation App

**LabT** est une application Streamlit pour la gestion de données chromatographiques, calculs de linéarité et de signal sur bruit (S/N), et génération de rapports PDF. L’application est bilingue (FR/EN).

---

## Fonctionnalités principales / Main features

### Connexion / Login
- Nom d’utilisateur insensible à la casse / Case-insensitive username
- Gestion des utilisateurs par l’admin / Admin user management

### Menu Utilisateur / User Panel
- **Linéarité / Linearity**
  - Possibilité d’utiliser **CSV** ou **saisie manuelle / manual input**
  - Calcul de la **pente**, **intercept** et **R²**
  - Graphique interactif des points et de la régression
  - Possibilité de calculer **concentration inconnue à partir du signal** et vice versa

- **S/N classique / Signal-to-noise**
  - Téléversement de chromatogrammes **CSV**
  - Calcul automatique S/N avec choix de la zone
  - Possibilité de télécharger les graphiques **PDF** ou **PNG**

- **S/N USP**
  - Utilisation de la pente de linéarité pour calculer **LOQ** et **LOD** en concentration

- **Rapports PDF**
  - Ajout du logo **LabT**
  - Informations : nom de l’entreprise, utilisateur, date
  - Téléchargement en PDF

- **Changer mot de passe / Change password**
  - Bouton pour modification sécurisée du mot de passe

---

## Installation

1. Créer un environnement Python (3.11 recommandé) :

```bash
python -m venv venv
source venv/bin/activate  # Linux / Mac
venv\Scripts\activate     # Windows