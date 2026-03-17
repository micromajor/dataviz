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
│   └── style.css           # Styles CSS (thème light OUDS v1.1)
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

## Branding Orange — Design System OUDS Web (thème light)
Ce projet applique le **branding Orange OUDS Web v1.1** (Unified Design System), thème **light mode** :
- Source CSS de référence : `https://cdn.jsdelivr.net/npm/@ouds/web-orange@1.1.0/dist/css/ouds-web.min.css`
- Documentation : https://web.unified-design-system.orange.com/orange/docs/1.1/foundation/color-modes/

### Tokens de couleur du thème light — valeurs exactes OUDS v1.1
Variables CSS custom (`:root`) utilisées dans `static/style.css` :

| Token CSS (var)        | Valeur OUDS exacte        | Token OUDS source                                  | Usage |
|------------------------|---------------------------|----------------------------------------------------|-------|
| `--bg`                 | `#ffffff`                 | `--bs-color-bg-primary`                            | Fond principal de page |
| `--surface`            | `#f4f4f4`                 | `--bs-color-bg-secondary`                          | Fond des cartes / panneaux |
| `--surface-hover`      | `rgba(0, 0, 0, 0.08)`     | `--bs-color-action-support-hover`                  | Survol des surfaces |
| `--border`             | `rgba(0, 0, 0, 0.2)`      | `--bs-color-border-default`                        | Bordures |
| `--text`               | `#000000`                 | `--bs-color-content-default`                       | Texte principal |
| `--text-muted`         | `rgba(0, 0, 0, 0.68)`     | `--bs-color-content-muted`                         | Texte secondaire / sous-titres |
| `--primary`            | `#ff7900`                 | `--bs-color-surface-brand-primary`                 | Orange brand — action principale |
| `--primary-hover`      | `#f15e00`                 | `--bs-color-action-pressed`                        | Survol / pressed bouton primaire |
| `--primary-text`       | `#000000`                 | `--bs-color-content-on-brand-primary`              | Texte sur fond orange primaire |
| `--success`            | `#138126`                 | `--bs-color-surface-status-positive-emphasized`    | Statut positif (fond ET texte) |
| `--warning`            | `#ffd000`                 | `--bs-color-surface-status-warning-emphasized`     | Statut attention (fond / bordure) |
| `--warning-text`       | `#856a00`                 | `--bs-color-content-status-warning`                | Texte warning sur fond clair |
| `--danger`             | `#db0002`                 | `--bs-color-action-negative-enabled`               | Statut erreur / critique |
| `--radius`             | `4px`                     | `--bs-border-radius` (OUDS peu arrondi)            | Border-radius composants |

### Autres tokens OUDS light utilisés directement (sans variable CSS) :
| Valeur hex              | Token OUDS source                              | Où utilisé dans le code |
|-------------------------|------------------------------------------------|-------------------------|
| `#0073b2`               | `--bs-color-content-status-info`               | Zones cosmétiques (badge, hit, bordure) |
| `#272727`               | `--bs-color-overlay-tooltip`                   | Fond des tooltips flottants |
| `rgba(0, 115, 178, 0.08)` | `--bs-color-surface-status-info-muted`       | Fond info-banner, zone cosmétique |
| `#000000`               | `--bs-color-border-focus`                      | Focus ring sur éléments interactifs |

### Règles de style OUDS à respecter :
1. **Couleur primaire** : toujours `#ff7900` pour les actions (boutons, liens actifs, focus ring) — jamais de bleu substitut
2. **Boutons primaires** : fond `#ff7900`, texte `#000000` (noir — contraste ~7:1, WCAG AA) ; hover fond `#f15e00`
3. **Focus visible** : `outline: 2px solid #ff7900; outline-offset: 2px` sur tous les éléments interactifs
4. **Typographie** : stack `"Helvetica Neue", Helvetica, Arial, sans-serif`
5. **Arrondis** : 4px pour les composants, 2px pour les badges/tags (OUDS est peu arrondi)
6. **Couleurs de statut** : utiliser les valeurs ci-dessus — ne pas inventer d'autres couleurs sémantiques
7. **Texte warning** : utiliser `#856a00` (`--warning-text`) pour le texte sur fond clair — jamais `#ffd000` en texte (contraste insuffisant)

## Accessibilité numérique — Guidelines Orange
Ce projet applique les **recommandations d'accessibilité Orange** (WCAG 2.2 niveau AA) :
- Référence : https://a11y-guidelines.orange.com/fr/
- Critères web incontournables : https://a11y-guidelines.orange.com/fr/web/checklist-incontournables/
- Guide développeur : https://a11y-guidelines.orange.com/fr/web/developper/

### Règles à respecter dans tous les templates HTML :
1. **Contenu textuel** : titre de page `<title>` unique, hiérarchie de titres cohérente (`h1` > `h2` > `h3`), `lang="fr"` sur `<html>`
2. **Emojis** : toujours `aria-hidden="true"` sur les `<span>` d'emoji ; si l'emoji porte une information, ajouter un texte visible ou un `aria-label`
3. **Images** : `alt` descriptif sur toutes les `<img>` ; `alt=""` pour les images purement décoratives
4. **Navigation** : `<nav>` doit avoir `aria-label` ; page courante signalée par `aria-current="page"`
5. **Formulaires** : chaque champ doit avoir un `<label>` explicite associé via `for`/`id` ; les erreurs doivent être annoncées
6. **Couleurs** : l'information ne doit jamais être transmise uniquement par la couleur — toujours doubler avec un texte ou une icône
7. **Contraste** : ratio minimum 4.5:1 pour le texte normal, 3:1 pour le grand texte (>18pt ou 14pt gras)
8. **Clavier** : tout élément interactif doit être focusable et utilisable au clavier ; `focus-visible` CSS explicite
9. **ARIA** : utiliser `role="status"` ou `role="alert"` pour les zones mises à jour dynamiquement ; `aria-busy` pendant les chargements ; `aria-describedby` pour les tooltips et descriptions
10. **Slider** : `<input type="range">` doit avoir `aria-valuetext` pour exposer une valeur lisible aux lecteurs d'écran
11. **Tooltips** : implémenter via `role="tooltip"` + `aria-describedby`, accessibles au focus clavier ET au survol souris
12. **Taille des cibles tactiles** : minimum 44×44px pour tous les éléments interactifs

## Notes pour Copilot
- Quand tu génères du code, respecte le style existant (FastAPI + Jinja2)
- Privilégie la simplicité — pas de classes inutiles, pas d'abstraction prématurée
- Les nouvelles routes doivent suivre le pattern existant dans app.py
- Les templates HTML doivent utiliser le même système de design (CSS variables)
- Toute nouvelle fonctionnalité doit fonctionner offline
- **Tout nouveau composant HTML doit respecter les guidelines Orange ci-dessus**
