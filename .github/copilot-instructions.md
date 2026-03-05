# Copilot Instructions — DataViz TNR

## Contexte du projet
DataViz est un **comparateur visuel de tests de non-régression (TNR)** destiné aux équipes IT.
Il permet de comparer visuellement deux versions d'une application web entre deux livraisons.
L'outil fonctionne **100% offline** — aucune donnée ne transite sur internet.

## Stack technique
- **Backend** : Python 3.11+ / FastAPI
- **Moteur de comparaison** : OpenCV + scikit-image (SSIM)
- **Capture d'écran** : Playwright (headless Chromium)
- **Analyse IA** : Ollama local (Pixtral / SmolVLM / tout modèle vision compatible)
- **Frontend** : HTML/CSS/JS vanilla (Jinja2 templates)
- **Pas de framework JS** — garder le front simple et léger

## Architecture des fichiers
```
dataviz/
├── app.py                  # Serveur FastAPI — point d'entrée principal
├── requirements.txt        # Dépendances Python
├── templates/
│   ├── index.html          # Page d'accueil — upload de 2 images
│   ├── capture.html        # Page de capture d'écran par URL
│   └── result.html         # Page de résultats de comparaison
├── static/
│   └── style.css           # Styles CSS (thème dark)
├── uploads/                # Images uploadées (généré)
├── results/                # Images de résultats : heatmap, contours (généré)
├── captures/               # Screenshots capturés par Playwright (généré)
├── docs/
│   └── PRODUCT.md          # Documentation produit
└── .github/
    └── copilot-instructions.md  # Ce fichier
```

## Conventions de code
- **Langue du code** : variables et fonctions en anglais, commentaires et docstrings en français
- **Langue de l'UI** : français
- **Style Python** : PEP 8, type hints encouragés
- **Templates** : HTML sémantique, pas de framework CSS
- **Pas de dépendance cloud** — tout doit fonctionner sans internet
- **Sécurité** : valider les entrées utilisateur, pas d'exécution de code arbitraire

## Principes de conception
1. **Offline first** — l'outil doit fonctionner sans connexion internet
2. **Simple à installer** — `pip install` + `playwright install` et c'est parti
3. **Pragmatique** — des fonctionnalités utiles, pas de sur-engineering
4. **Lisible** — le code doit être compréhensible par un développeur junior
5. **Évolutif** — architecture modulaire pour faciliter les futures évolutions

## Fonctionnalités actuelles
- Upload et comparaison de 2 images (mode fichier)
- Capture d'écran par URL avec comparaison automatique (mode URL)
- Score SSIM (Structural Similarity Index)
- Heatmap des différences pixel-à-pixel
- Détection et comptage des zones modifiées avec contours
- Slider interactif avant/après
- Analyse IA en langage naturel via Ollama (optionnelle, dégradation gracieuse)
- Verdict automatique TNR PASSÉ / ÉCHOUÉ

## Roadmap (priorité décroissante)
- [ ] Comparaison par lots (dossiers entiers d'images ou liste d'URLs)
- [ ] Historique des comparaisons avec navigation
- [ ] Export PDF des rapports
- [ ] Intégration CI/CD (API REST pour automatisation)
- [ ] Zones d'exclusion configurables (ignorer dates, compteurs dynamiques)
- [ ] Comparaison multi-résolutions / multi-navigateurs
- [ ] Dashboard de suivi des régressions dans le temps

## Intégration IA (Ollama)
- Le modèle par défaut est **Pixtral** (Mistral, français, vision)
- L'IA est **optionnelle** : si Ollama n'est pas lancé, l'outil fonctionne sans
- Le prompt système demande une analyse en français avec classification de sévérité
- Les images sont envoyées en base64 à l'API locale `localhost:11434`
- Modèles alternatifs : SmolVLM (Hugging Face), minicpm-v, llava

## Notes pour Copilot
- Quand tu génères du code, respecte le style existant (FastAPI + Jinja2)
- Privilégie la simplicité — pas de classes inutiles, pas d'abstraction prématurée
- Les nouvelles routes doivent suivre le pattern existant dans app.py
- Les templates HTML doivent utiliser le même système de design (CSS variables)
- Toute nouvelle fonctionnalité doit fonctionner offline
