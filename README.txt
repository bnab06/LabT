# LabT – Application d’Analyse de Linéarité et S/N

**LabT** est une application Streamlit bilingue (Français / English) pour :  

- Calcul de linéarité : courbe, R², concentration inconnue ou signal inconnu.
- Calcul de S/N classique et USP à partir de fichiers CSV, PNG ou PDF.
- Gestion sécurisée des utilisateurs avec rôle `admin` ou `user`.
- Export de rapports PDF avec possibilité de saisir le nom de la compagnie.
- Choix des unités de concentration (par défaut µg/mL).

## Fonctionnalités
- Volet Linéarité : import CSV ou saisie manuelle, affichage de la courbe et R².
- Volet S/N : import PDF, PNG ou CSV, affichage du chromatogramme, sélection de la zone de calcul.
- Gestion des utilisateurs : l’admin peut ajouter, supprimer, modifier les users. Users peuvent changer leur mot de passe.
- Boutons à un seul clic, navigation facile entre les volets.