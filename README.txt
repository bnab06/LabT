# LABT — Application d'analyse (Linearity & S/N)

## Description
Application Streamlit pour:
- Calcul de linéarité (import CSV ou saisie manuelle), affichage de la courbe et R².
- Calcul automatique de concentration ou signal inconnu (sans bouton).
- Export PDF des rapports (nom société demandé à la génération).
- Calcul S/N (import CSV pour chromatogramme), sélection d'une zone de bruit.
- Import d'images (PNG/JPG) pour aperçu; pour calcul S/N privilégier CSV.
- Gestion utilisateurs (admin: ajouter/supprimer/modifier; user: accès aux outils + changer mot de passe via paramètres discrets).

Langue par défaut: Français (FR), option EN (anglais).

## Fichiers
- `app.py` — code principal
- `requirements.txt` — dépendances
- `users.json` — fichier d'utilisateurs (exemple)

## Exécution locale
1. Créer un environnement Python 3.11.
2. `pip install -r requirements.txt`
3. `streamlit run app.py`
4. Se connecter avec `admin/admin123` (admin) ou `user/user123` (user).

## Remarques importantes
- `users.json` contient les comptes (démo). Pour production, utiliser un stockage plus sûr et hacher les mots de passe.
- Aperçu PDF non implémenté: on accepte les PDF en upload mais on recommande conversion en CSV/PNG pour le traitement.