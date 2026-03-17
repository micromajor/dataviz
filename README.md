# DataViz — Comparateur Visuel TNR

Outil de comparaison visuelle d'images pour les tests de non-régression (TNR) entre deux livraisons applicatives. Fonctionne **100% offline**, sans connexion internet.

## Démarrage rapide

Double-cliquez sur **`start.bat`** — le script prend en charge tout le reste.

Il installe automatiquement (à la première exécution) :
- Python venv + dépendances
- Chromium headless (capture par URL)
- Ollama (moteur IA local) + modèle `llava`

L'application s'ouvre dans le navigateur pendant que le modèle IA se télécharge en arrière-plan.
L'indicateur IA dans l'interface se met à jour automatiquement une fois le modèle disponible.

**Démarrages suivants (plus rapides) :**
```
start.bat -SkipDeps
```

## Fonctionnalités

- **Deux modes de comparaison** : upload de fichiers image ou capture par URL
- **Comparaison pixel-à-pixel** avec heatmap des différences
- **Score SSIM** (Structural Similarity Index) — mesure de similarité perceptuelle
- **Détection des zones modifiées** avec contours, badges numérotés et classification de sévérité
- **Slider interactif** avant/après avec overlay SVG des zones
- **Seuil configurable** (4 niveaux) pour filtrer les différences mineures
- **Analyse IA en langage naturel** via Ollama local (optionnelle, dégradation gracieuse)
- **Verdict automatique** TNR PASSÉ / ÉCHOUÉ
- **Historique** des comparaisons avec nom de rapport personnalisable
- **Indicateur de statut IA** en temps réel dans la navigation

## Prérequis

- **Windows 10/11** avec PowerShell 5.1+
- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- Connexion internet uniquement pour la première installation

## Installation manuelle (alternative)

```bash
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python -m playwright install chromium --with-deps
```

Puis lancer avec :
```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

Ouvrir **http://localhost:8000** dans un navigateur.

## Analyse IA (Ollama)

L'analyse IA est **optionnelle** — l'outil fonctionne pleinement sans elle.

- Moteur : [Ollama](https://ollama.com) — 100% local, aucune donnée envoyée sur internet
- Modèle par défaut : `llava` (~4 Go, téléchargé automatiquement par `start.bat`)
- Modèles alternatifs compatibles : `moondream` (~1.5 Go), `minicpm-v`, `llava:13b`

Pour changer de modèle, modifier la ligne dans `app.py` :
```python
OLLAMA_MODEL = "llava"
```

## Architecture

```
dataviz/
├── app.py              # Serveur FastAPI — point d'entrée
├── requirements.txt    # Dépendances Python
├── start.bat           # Lanceur Windows clé en main (double-clic)
├── start.ps1           # Script PowerShell de démarrage automatisé
├── build_zip.bat       # Génération d'un ZIP de distribution
├── templates/
│   ├── index.html      # Page d'accueil — upload de 2 images
│   ├── capture.html    # Capture par URL
│   └── result.html     # Résultats de comparaison
├── static/
│   └── style.css       # Thème Orange OUDS Web v1.1 (light mode)
└── docs/
    └── PRODUCT.md      # Documentation produit détaillée
```

## Roadmap

- [ ] Comparaison par lots (dossiers entiers d'images ou liste d'URLs)
- [ ] Export PDF des rapports
- [ ] Intégration CI/CD (API REST)
- [ ] Zones d'exclusion configurables (ignorer dates, compteurs dynamiques)
- [ ] Comparaison multi-résolutions / multi-navigateurs
