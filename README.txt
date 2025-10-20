# LabT — Signal / Bruit, LOD, LOQ

LabT est une application Streamlit bilingue (FR/EN) pour analyser des signaux, calculer le rapport signal sur bruit (S/N), le LOD et le LOQ, et générer des rapports PDF.

---

## 🧩 Fonctionnalités

- Authentification multi-utilisateur :
  - **admin** : gestion des utilisateurs.
  - **user1 / user2** : accès aux fonctionnalités d'analyse.
- Import de fichiers CSV avec colonnes **Time** et **Signal**.
- Sélection interactive des zones de pic et de bruit pour le calcul S/N.
- Calcul automatique de **LOD** et **LOQ**.
- Visualisation des signaux avec zones de pic et bruit sur graphique Plotly.
- Génération et téléchargement de rapports PDF.
- Interface bilingue **Français / English**.

---

## ⚙️ Installation

1. Crée un environnement Python 3.13 :
```bash
python3.13 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows