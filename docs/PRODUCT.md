# DataViz TNR — Documentation Produit

## 1. Vision

**DataViz TNR** est un outil de **tests de non-régression visuelle** (TNR) conçu pour les équipes IT. Il permet de détecter automatiquement les différences visuelles entre deux versions d'une application web, avec une analyse intelligente fournie par une IA embarquée.

### Principes fondateurs

| Principe | Description |
|---|---|
| **100% Offline** | Aucune donnée ne quitte la machine. Pas de cloud, pas d'API externe. |
| **Souveraineté** | IA française/européenne (Mistral Pixtral, Hugging Face SmolVLM) |
| **Pragmatique** | Simple à installer, simple à utiliser. Pas de configuration complexe. |
| **Pour les humains** | L'IA aide les testeurs, elle ne les remplace pas. Analyse en français. |

---

## 2. Fonctionnalités

### 2.1 Mode Fichier (upload d'images)
L'utilisateur importe manuellement deux screenshots :
- **Image de référence** : la version attendue (avant livraison)
- **Nouvelle image** : la version à tester (après livraison)

L'outil génère un rapport de comparaison complet.

### 2.2 Mode Capture URL
L'utilisateur saisit une URL dans l'interface :
1. **Première capture** : le screenshot est stocké comme référence
2. **Captures suivantes** : chaque nouvelle capture est automatiquement comparée à la précédente
3. L'historique des captures est conservé localement

### 2.3 Moteur de comparaison (OpenCV + scikit-image)

| Métrique | Description |
|---|---|
| **SSIM** (Structural Similarity Index) | Score de 0 à 100% mesurant la similarité structurelle perçue par l'œil humain |
| **Diff pixel-à-pixel** | Pourcentage de pixels ayant changé au-delà du seuil |
| **Zones modifiées** | Nombre de régions distinctes où des changements sont détectés |
| **Heatmap** | Carte thermique colorée montrant l'intensité des différences |
| **Contours** | Rectangles rouges encadrant chaque zone modifiée |

### 2.4 Slider interactif
Un curseur glissant permet de superposer les deux versions et de faire apparaître progressivement l'une ou l'autre, pour une comparaison visuelle intuitive.

### 2.5 Analyse IA en langage naturel
Si un modèle IA est disponible via Ollama, l'outil envoie les deux images au modèle qui produit une analyse détaillée en français :
- Description de chaque changement détecté
- Localisation spatiale (haut, bas, centre…)
- Classification de sévérité : 🔴 Critique / 🟠 Majeur / 🟡 Mineur / 🔵 Cosmétique
- Hypothèse régression vs changement intentionnel

**Dégradation gracieuse** : si Ollama n'est pas lancé, l'outil fonctionne normalement sans l'analyse IA.

### 2.6 Verdict automatique
Basé sur les métriques SSIM et pourcentage de pixels différents :
- ✅ **TNR PASSÉ** : SSIM ≥ 95% et pixels différents ≤ 2%
- ⚠️ **TNR ÉCHOUÉ** : en dessous de ces seuils

---

## 3. Architecture technique

```
┌──────────────────────────────────────────────────────────────┐
│                        NAVIGATEUR                             │
│   ┌──────────┐  ┌──────────────┐  ┌───────────────────┐     │
│   │  Upload   │  │  Capture URL │  │  Résultats TNR    │     │
│   │  d'images │  │  (Playwright)│  │  (slider, heatmap)│     │
│   └─────┬────┘  └──────┬───────┘  └─────────┬─────────┘     │
└─────────┼──────────────┼────────────────────┼────────────────┘
          │              │                    │
          ▼              ▼                    ▲
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI (Python)                          │
│                                                              │
│   ┌──────────────┐  ┌────────────────┐  ┌────────────────┐  │
│   │   OpenCV +   │  │   Playwright   │  │  Ollama Client │  │
│   │  scikit-image│  │  (Chromium     │  │  (httpx)       │  │
│   │  (SSIM, diff)│  │   headless)    │  │                │  │
│   └──────────────┘  └────────────────┘  └───────┬────────┘  │
│                                                  │           │
└──────────────────────────────────────────────────┼───────────┘
                                                   │
                                        ┌──────────▼──────────┐
                                        │   Ollama (local)    │
                                        │   Pixtral / SmolVLM │
                                        │   localhost:11434   │
                                        └─────────────────────┘
```

### Composants

| Composant | Technologie | Rôle |
|---|---|---|
| Serveur web | FastAPI + Uvicorn | API REST + rendu HTML |
| Templates | Jinja2 | Pages HTML dynamiques |
| Comparaison | OpenCV + scikit-image | SSIM, diff, heatmap, contours |
| Capture | Playwright (Chromium) | Screenshots de pages web |
| IA | Ollama (API locale) | Analyse en langage naturel |
| Frontend | HTML/CSS/JS vanilla | Interface utilisateur |

### Dépendances Python

| Package | Version | Usage |
|---|---|---|
| fastapi | 0.115.0 | Framework web async |
| uvicorn | 0.30.6 | Serveur ASGI |
| opencv-python-headless | 4.10.0 | Traitement d'image |
| scikit-image | 0.24.0 | Métriques SSIM |
| Pillow | 10.4.0 | Manipulation d'images |
| numpy | 1.26.4 | Calcul matriciel |
| playwright | 1.49.1 | Capture d'écran web |
| httpx | 0.27.2 | Client HTTP async (Ollama) |
| jinja2 | 3.1.4 | Templates HTML |

---

## 4. Installation

### Prérequis
- Python 3.11+
- (Optionnel) Ollama pour l'analyse IA

### Étapes

```bash
# 1. Cloner le projet
cd dataviz

# 2. Environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Dépendances Python
pip install -r requirements.txt

# 4. Navigateur pour les captures d'écran
playwright install chromium

# 5. (Optionnel) IA locale
# Installer Ollama depuis https://ollama.com
# Puis :
ollama pull pixtral
```

### Lancement

```bash
python app.py
# → http://localhost:8000
```

---

## 5. Modèles IA supportés

| Modèle | Origine | Taille | Points forts |
|---|---|---|---|
| **Pixtral 12B** | 🇫🇷 Mistral (Paris) | ~7 Go | Excellent en français, vision + texte |
| **SmolVLM-2** | 🇫🇷 Hugging Face (Paris) | ~1,5 Go | Ultra-léger, conçu pour edge/CPU |
| **Mistral Small** | 🇫🇷 Mistral (Paris) | ~4 Go | Peut analyser les métadonnées de diff |
| **minicpm-v** | Open source | ~3 Go | Bon compromis taille/qualité |
| **llava** | Open source | ~4 Go | Référence historique en vision |

Pour changer de modèle, modifier `OLLAMA_MODEL` dans `app.py`.

---

## 6. Roadmap

### Court terme
- [ ] Comparaison par lots (dossier d'images ou liste d'URLs)
- [ ] Historique navigable des comparaisons
- [ ] Configuration des seuils TNR par projet

### Moyen terme
- [ ] Export PDF des rapports de TNR
- [ ] API REST pour intégration CI/CD
- [ ] Zones d'exclusion (masquer dates, compteurs, données dynamiques)
- [ ] Multi-résolutions et multi-navigateurs

### Long terme
- [ ] Dashboard de suivi des régressions dans le temps
- [ ] Apprentissage des faux positifs (l'IA apprend à ignorer les variations acceptées)
- [ ] Mode comparaison de composants UI individuels (via segmentation SAM)
- [ ] Plugin navigateur pour capturer directement depuis Chrome/Firefox

---

## 7. Licence & Souveraineté

- Code : libre d'utilisation interne
- IA : modèles open-source français (Mistral) / européens (Hugging Face)
- Données : **aucune donnée ne quitte la machine** — tout est traité localement
- Conformité RGPD : pas de collecte, pas de transmission, pas de stockage cloud
