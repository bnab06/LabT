# LabT

## Description
LabT est une application Streamlit bilingue (EN/FR) pour :
- l'analyse de linéarité (import CSV ou saisie manuelle), calcul de pente, R², export PDF
- le calcul S/N (import CSV / image / PDF), choix d'une fenêtre temporelle, calcul S/N (classique et USP-style), LOD/LOQ (signal et en concentration si pente fournie)
- gestion des utilisateurs (admin: ajout/modification/suppression des users)
- export PDF des rapports (company name demandé au moment de l'export)

## Fonctionnalités clés
- Bilingue (EN par défaut, FR disponible)
- Authentification basique via `users.json` (le fichier est créé automatiquement s'il n'existe pas)
- Admin : gestion complète des utilisateurs (username/password/role). Admin **ne voit pas** le contenu du JSON ni n'accède aux calculs.
- Users : accès aux modules Linearity et S/N
- Linearity : import CSV (2 colonnes minimum) **ou** saisie manuelle (valeurs séparées par des virgules). Calcul automatique de concentration/signal inconnus.
- S/N : import CSV (Time,Signal) ou image/pdf (digitize automatique en sommant verticalement l'image). Choix de la fenêtre via sliders.
- LOD/LOQ calculés au niveau signal et convertis en concentration si pente disponible.
- Export PDF des rapports (company name demandé à l'export).

## Installation (Streamlit Cloud)
1. Déposer les fichiers `app.py`, `requirements.txt`, `README.md` dans le repo.
2. Dans le dashboard Streamlit Cloud, créer une nouvelle app pointant sur ce repo.
3. S'assurer que l'environnement Python est **3.11**.
4. Déployer.

## Remarques
- Si l'import PDF ne fonctionne pas, installer `pymupdf` et/ou `pdf2image` localement.
- Les algorithmes de digitalisation utilisés sont volontairement simples (extraction par sommation verticale). Pour une digitalisation interactive avancée, il faut intégrer un widget JS/JSPlot ou un service externe.