# LabT - Application de traitement de chromatogrammes et calculs analytiques

LabT est une application **bilingue (FR/EN)** pour l’analyse chromatographique, la gestion des utilisateurs et le calcul de concentrations inconnues, S/N, LOQ, LOD et linéarité.  

---

## Fonctionnalités principales

1. **Gestion des utilisateurs**
   - Administration simple : l’admin peut gérer uniquement les utilisateurs.
   - Chaque utilisateur peut changer son mot de passe.
   - Nom d’utilisateur **non sensible à la casse**.

2. **Linéarité**
   - Calcul de la concentration inconnue à partir du signal et vice versa.
   - Possibilité d’**importer un fichier CSV** ou de saisir les données manuellement.
   - Génération de la pente de linéarité utilisée pour les calculs S/N, LOQ et LOD.

3. **S/N (Signal-to-Noise)**
   - S/N classique ou selon USP.
   - Possibilité de sélectionner la zone où calculer S/N.
   - Calculs LOQ et LOD basés sur la linéarité.

4. **Visualisation**
   - Affichage des chromatogrammes avec tracé des pics et du bruit.
   - Graphiques interactifs pour S/N et linéarité.

5. **Export des rapports**
   - Export PDF incluant :
     - Nom de l’entreprise
     - Nom de l’utilisateur
     - Date et heure
   - Export CSV des résultats.

---

## Installation

1. **Cloner le dépôt :**
```bash
git clone https://github.com/ton-repo/labt.git
cd labt