# 🧪 LabT — Analytical Tools App

### 🌐 Bilingual (Français / English)
**LabT** est une application Streamlit complète pour les laboratoires analytiques.  
Elle permet le calcul de **linéarité**, **S/N (Signal-to-Noise)** classique et USP,  
ainsi que le calcul du **LOD** et **LOQ** en signal ou concentration.  

L’app inclut une **gestion sécurisée des utilisateurs (admin + users)**,  
un mode **bilingue (Fr/En)**, et la possibilité d’**exporter les rapports en PDF**.

---

## 🚀 Fonctionnalités principales

### 🔐 Gestion utilisateurs
- L’**administrateur** peut :
  - Ajouter / supprimer des utilisateurs
  - Réinitialiser leurs mots de passe  
- Les **utilisateurs** peuvent :
  - Se connecter et utiliser l’app
  - **Changer leur mot de passe** via un bouton dédié  

---

### 📊 Linéarité
Deux modes :
1. **Téléchargement d’un fichier CSV** (`Concentration`, `Signal`)
2. **Saisie manuelle** dans un tableau interactif  

Affiche :
- Graphique `Signal` vs `Concentration`
- Équation de la droite de calibration
- Coefficient de corrélation **R²**
- Pente, interception, équation et statistiques
- Possibilité d’utiliser la pente pour **calculer LOD/LOQ** en concentration

---

### 🔬 Calcul S/N (Signal-to-Noise)
Deux méthodes disponibles :
- **Classique** : `Signal max / écart-type du bruit`
- **USP** : selon la norme USP <621>  

Fonctionnalités :
- Import d’un chromatogramme (CSV avec `Time`, `Signal`)
- Sélection de la **zone de bruit**
- Calcul automatique :
  - Signal max
  - Bruit (σ)
  - S/N
  - LOD / LOQ (signal ou concentration si pente connue)
- Visualisation du chromatogramme avec zones de calcul

---

### 📄 Export PDF
- Inclut :
  - Nom de l’entreprise
  - Nom d’utilisateur
  - Date
  - Graphiques linéarité et chromatogramme
  - Résultats complets bilingues  
- Format professionnel et lisible

---

## 🧰 Structure du projet