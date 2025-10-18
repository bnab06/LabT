# LabT - Application de Laboratoire

LabT est une application Streamlit pour la gestion des utilisateurs, le calcul de la linéarité et du signal/bruit (S/N) à partir de chromatogrammes.

## Fonctionnalités
- Connexion sécurisée avec mot de passe
- Gestion des utilisateurs pour l’admin (ajout/suppression)
- Calcul de la linéarité avec saisie manuelle des concentrations et réponses
- Tracé automatique de la courbe de linéarité avec équation et R²
- Calcul automatique de concentration inconnue ou signal inconnu
- Upload de chromatogrammes CSV pour le calcul S/N, LOD, LOQ
- PDF report de linéarité avec logo, date et utilisateur
- Interface compacte et esthétique (plateforme bleu moderne)
- Boutons activables au simple clic

## Installation
1. Créez un environnement virtuel Python 3.13 :
```bash
python3 -m venv venv
source venv/bin/activate