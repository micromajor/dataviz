# DataViz — Comparateur Visuel TNR

Outil de comparaison visuelle d'images pour les tests de non-régression (TNR) entre deux livraisons applicatives. Fonctionne **100% offline**, sans connexion internet.

## Fonctionnalités

- **Upload** de deux images (référence vs nouvelle version)
- **Comparaison pixel-à-pixel** avec heatmap des différences
- **Score SSIM** (Structural Similarity Index) — mesure de similarité perceptuelle
- **Détection automatique des zones modifiées** avec contours
- **Slider interactif** pour comparer visuellement les deux versions
- **Seuil configurable** pour ignorer les différences mineures

## Installation

```bash
# Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate   # Windows

# Installer les dépendances
pip install -r requirements.txt
```

## Lancement

```bash
python app.py
```

Puis ouvrir **http://localhost:8000** dans un navigateur.

## Roadmap

- [ ] Comparaison par lots (dossiers entiers)
- [ ] Historique des comparaisons
- [ ] Export PDF des rapports de différences
- [ ] Intégration CI/CD
- [ ] Comparaison intelligente (ignorer les données dynamiques : dates, compteurs…)
