# LabT Application

## Description

LabT est une application Streamlit pour les calculs de **linéarité** et de **Signal/Niveau de bruit (S/N)**.  
Elle permet :

- L'import de données CSV ou saisie manuelle pour la linéarité.
- Le calcul automatique de **concentration ou signal inconnu**.
- L'import de CSV, PNG, ou PDF pour le calcul S/N.
- La sélection de zone pour le calcul S/N.
- L'export de rapports PDF, avec possibilité d'entrer le **nom de la compagnie** au moment de l'export.
- Une interface **bilingue FR/EN**.
- Une gestion des utilisateurs avec **admin** et **users**.
- Les utilisateurs peuvent changer leur mot de passe via un bouton discret.

---

## Installation

1. Cloner le dépôt ou télécharger les fichiers.
2. Installer les dépendances :

```bash
pip install -r requirements.txt