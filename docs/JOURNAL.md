# Journal de bord — DataViz TNR

Historique chronologique des évolutions significatives du projet.
Mis à jour à chaque avancée notable.

---

## [0.8] — 17 mars 2026 — MVP : Historique, nommage, seuils configurables, référence URL

### Fonctionnalités ajoutées

#### MVP-1 : Historique local
- Chaque comparaison est sauvegardée dans `history/{uid}.json` (métadonnées complètes + résumé, pas les images)
- Nouvelle page `/history` : liste décroissante, filtre recherche temps réel, vignettes, métriques colorées, verdict PASSÉ/ÉCHOUÉ
- Nouvelle route `/history/{uid}` : réouvre un rapport archivé depuis result.html (bannière "🗃️ Rapport archivé")
- Lien "Historique" ajouté dans la nav des 3 pages
- Nouveau template `templates/history.html`
- Nouveau dossier `history/` créé au démarrage

#### MVP-2 : Nommage du rapport
- Champ "Nom du rapport" (optionnel) dans les formulaires de comparaison fichier et capture URL
- Le label est affiché dans result.html + sauvegardé dans le JSON d'historique
- Affiché dans la liste historique (« Sans titre » si vide)

#### MVP-3 : Seuils verdict configurables
- Section "⚙️ Seuils du verdict TNR" masquable (`<details>`) dans les deux formulaires
- Champs SSIM minimum (%) et pixels différents max (%)
- Le verdict est calculé dynamiquement et les seuils utilisés sont affichés dans la bandière de verdict
- Valeurs par défaut : SSIM ≥ 95%, pixels ≤ 2%

#### MVP-4 : Référence visible avant capture URL
- Nouvelle route `GET /capture/reference?url=...` : indique si une référence existe, sa date et son nombre de captures
- En mode URL : l'interface affiche une bannière informative dès que l'URL est saisie (appel API asynchrone)
  - Vert si une référence existe (date, nombre de captures)
  - Bleu si première capture (avertissement)
- La date de la référence utilisée est aussi affichée dans result.html

### Fichiers modifiés
- **`app.py`** : `HISTORY_DIR`, `save_report()`, routes `POST /compare` et `POST /capture/screenshot` (label, seuils, sauvegarde), nouvelles routes `GET /history`, `GET /history/{uid}`, `GET /capture/reference`
- **`templates/history.html`** : nouveau template
- **`templates/index.html`** : lien nav + champ label + section seuils
- **`templates/capture.html`** : lien nav + champ label + section seuils + JS vérification référence
- **`templates/result.html`** : lien nav + bannière historique + label display + verdict dynamique + date référence URL
- **`static/style.css`** : styles pour `.report-meta`, `.advanced-options`, `.history-*`, `.ref-info-banner`, `.verdict-thresholds`
- **`docs/ROADMAP.md`** : MVP-1 à 4 marqués livrés

---



### Problème résolu
Les zones clairement visibles à l'œil nu étaient systématiquement classées "mineur" car `avg_intensity` (moyenne sur tout le bounding box) était diluée par les pixels inchangés autour du contenu modifié.

### Changements
- **`app.py`** : ajout de `max_intensity` (pic d'écart) comme critère indépendant de classification
- Seuils recalibrés pour correspondre à la visibilité humaine :

| Sévérité | Avant | Après |
|---|---|---|
| Critique | avg > 150 ou surface > 10% | avg > 100 **ou max > 230** ou surface > 8% |
| Majeur | avg > 80 ou surface > 5% | avg > 40 **ou max > 150** ou surface > 3% |
| Mineur | avg > 40 ou surface > 1% | avg > 10 **ou max > 50** ou surface > 0,3% |
| Cosmétique | reste | Nettement moins fréquent |

- **`templates/result.html`** : table "Comment les niveaux de sévérité sont-ils calculés ?" mise à jour

---

## [0.6] — 17 mars 2026 — Split-view layout + OUDS light mode exact

### Problème résolu
- Impossible de voir simultanément la liste des différences et l'image annotée
- Charte graphique OUDS interprétée au lieu d'être appliquée à la lettre

### Changements
- **`static/style.css`** : tokens OUDS Web v1.1 extraits directement depuis le CDN officiel (`https://cdn.jsdelivr.net/npm/@ouds/web-orange@1.1.0/dist/css/ouds-web.min.css`)
- Layout split-view : grille `minmax(420px, 1fr) / minmax(0, 1.8fr)`, liste à gauche, image sticky à droite
- `max-width: 1440px` sur `<main>` ; image pleine largeur + `max-height: 75vh`
- Tableau sévérité scrollable (`overflow-x: auto` + `min-width: 480px`)
- **`.github/copilot-instructions.md`** : table complète des tokens OUDS light documentée

---

## [0.5] — Mars 2026 — Identification des zones et interactivité

### Changements
- **Overlay SVG interactif** sur l'image annotée : hit areas transparentes par zone
- **Badges numérotés** colorés par sévérité (triés critique → cosmétique)
- **Cross-highlight** : survol d'une zone dans l'image ↔ mise en valeur dans la liste (et vice-versa)
- **Tooltip flottant** : détails de la zone au survol (sévérité, position, taille, intensité, critère)
- **Fix double annotation** : l'image affichée utilise `img2` propre, les rectangles OpenCV restent uniquement dans le fichier téléchargeable
- **Fix badges noirs** (zones "cosmétique") : bug d'accent `é` → `e` dans les classes CSS Jinja
- Section "Zones modifiées" remontée sous le résumé textuel pour meilleure visibilité

---

## [0.4] — Mars 2026 — Détection robuste bas contraste

### Problème résolu
Les éléments peu contrastés (rectangle blanc sur fond pâle) n'étaient pas détectés.

### Changements
- **`app.py`** : diff calculé sur `np.max(canal_R, canal_G, canal_B)` au lieu de la luminance pondérée — plus sensible aux changements de couleur nets
- Fusion `threshold + Canny` : les contours fins sont capturés même sous le seuil de seuillage simple
- Paramètres Canny adaptatifs proportionnels au seuil utilisateur

---

## [0.3] — Mars 2026 — Accessibilité WCAG 2.2 AA

### Changements
- Tous les templates HTML auditées et corrigées selon les guidelines Orange (a11y-guidelines.orange.com)
- `aria-hidden` sur tous les emojis informatifs ; texte alternatif ajouté
- `role="status"` / `role="alert"` sur les zones dynamiques
- `aria-describedby` sur les tooltips
- Focus visible explicite (`outline: 2px solid #ff7900`) sur tous les éléments interactifs
- Cibles tactiles ≥ 44×44px

---

## [0.2] — Mars 2026 — UX upload et redesign interface

### Changements
- Drag & drop sur les zones d'upload (index.html)
- Redesign du sélecteur de seuil (slider + affichage valeur temps réel)
- Réorganisation de la page résultats (métriques en premier, puis zones, puis images)
- Slider interactif avant/après sur la page résultats

---

## [0.1] — Mars 2026 — Version initiale

### Fonctionnalités initiales
- Mode fichier : upload de 2 images, comparaison SSIM + heatmap + contours
- Mode URL : capture Playwright, comparaison automatique avec la capture précédente
- Analyse IA optionnelle via Ollama (Pixtral)
- Verdict TNR PASSÉ / ÉCHOUÉ
- Thème Orange OUDS, 100% offline
