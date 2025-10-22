# LabT — Linéarité & S/N

## But
Application Streamlit pour :
- calculer la linéarité (régression linéaire), exporter le rapport PDF,
- calculer le rapport Signal / Bruit (classique et méthode USP approximative),
- gérer des utilisateurs (Admin / User).

## Installation (serveur / Streamlit Cloud)
1. Copier les fichiers `app.py`, `utils.py`, `requirements.txt`, `users.json`, `README.md` dans le dépôt.
2. S'assurer que `requirements.txt` est utilisé (Streamlit Cloud lira ce fichier).
3. Lancer l'application.

**Conseil** : sur Streamlit Cloud, choisir Python 3.11 si des conflits apparaissent.

## Pages
- **Linéarité**
  - Import CSV (x,y) ou saisie manuelle (valeurs séparées par des virgules).
  - Affiche la courbe, la pente, l'intercept, R².
  - Calculs : concentration ←→ signal.
  - Export PDF : nom de la compagnie, unité personnalisable (par défaut µg/mL).
  - Option : exporter la pente vers le volet S/N.

- **S/N**
  - Import CSV (x,y) ou image (png/jpg/pdf).
  - Pour CSV : sélectionner la zone X (xmin,xmax) utilisée pour estimer le bruit; sélectionner position du pic.
  - Pour image : indiquer coordonnées (en pixels) xmin/xmax et position du pic.
  - Calculs : S/N classique = (peak - mean(noise)) / std(noise).
    - S/N USP (approx) : convertit signal -> concentration avec la pente stockée depuis la page Linéarité et calcule S/N en concentration.

- **Admin**
  - Ajouter / Modifier / Supprimer des utilisateurs (accessible aux admins uniquement).

## Remarques
- Les utilisateurs peuvent changer leur mot de passe via la page Admin (ou tu peux ajouter une page dédiée).
- Les boutons utilisent `st.button`/`st.form` pour éviter double-exécution intempestive.
- Pour des graphiques image->CSV auto (OCR de chromatogramme), il faut ajouter une extraction plus avancée (non incluse dans cette version).

## Limitations & améliorations possibles
- Extraction automatique du signal à partir d'images (pixel->axe X réel) n'est pas implémentée : il faut fournir un CSV ou indiquer manuellement la zone en pixels.
- Le calcul S/N USP est une approximation. Si tu veux la méthode USP officielle, donne la formule précise et on l'implémente.