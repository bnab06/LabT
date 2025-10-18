# LabT - Analytical Lab Tool

**Description :**  
LabT est une application Streamlit pour le calcul de S/N, LOD, LOQ et linéarité.  
Elle supporte l’extraction de données depuis CSV, PNG, JPG et PDF via OCR.

**Fonctionnalités :**  
- Login utilisateur avec menu déroulant.  
- Admin gère uniquement les utilisateurs.  
- Calcul S/N USP avec sélection de zone.  
- Calcul linéarité automatique, R² affiché, concentration inconnue calculée à partir de la courbe.  
- Export rapport PDF avec logo, date et utilisateur.  
- Interface moderne bleu, simple clic, boutons retour au menu principal.  

**Installation :**
```bash
pip install -r requirements.txt
streamlit run app.py