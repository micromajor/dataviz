# Roadmap — DataViz TNR

Vision : un comparateur TNR visuel **crédible, offline, utilisable sans formation** par une équipe IT.

Légende : ✅ Livré · 🚧 En cours · 📋 Planifié · 💡 Idée

---

## MVP — Sprint actuel

Les éléments suivants conditionnent la crédibilité de l'outil comme outil de travail réel.

| # | Fonctionnalité | Statut | Impact |
|---|---|---|---|
| MVP-1 | **Historique local des comparaisons** (JSON + page liste navigable) | ✅ Livré | ⭐⭐⭐ |
| MVP-2 | **Nommage du rapport** (libellé libre ex. "Sprint 42 – Homepage") | ✅ Livré | ⭐⭐⭐ |
| MVP-3 | **Seuils verdict configurables** (SSIM et % pixels ajustables par l'utilisateur) | ✅ Livré | ⭐⭐ |
| MVP-4 | **Voir la référence avant capture URL** (nom fichier + date de la capture précédente) | ✅ Livré | ⭐⭐ |
| MVP-5 | **Export du rapport** (HTML standalone ou PDF imprimable) | 📋 Planifié | ⭐⭐⭐ |

---

## Fonctionnalités livrées ✅

| Version | Fonctionnalité |
|---|---|
| 0.8 | Historique local des comparaisons (JSON + page liste + réouverture) |
| 0.8 | Nommage libre des rapports (champ label dans les formulaires) |
| 0.8 | Seuils verdict configurables par comparaison (SSIM + % pixels) |
| 0.8 | Référence URL visible avant capture (date + aperçu via API) |
| 0.6 | Split-view layout (liste gauche / image droite sticky) |
| 0.6 | OUDS Web v1.1 light mode appliqué à la lettre (tokens CDN) |
| 0.5 | Overlay SVG interactif avec zones numérotées et colorées par sévérité |
| 0.5 | Cross-highlight image ↔ résumé textuel |
| 0.5 | Tooltip flottant avec détails de zone |
| 0.5 | Fix double annotation (image affichée propre vs téléchargeable annoté) |
| 0.4 | Détection bas contraste (`max canal` + fusion Canny) |
| 0.3 | Accessibilité WCAG 2.2 AA (guidelines Orange) |
| 0.2 | Drag & drop upload, slider avant/après, redesign interface |
| 0.1 | Comparaison SSIM + heatmap + contours, mode URL + Playwright, IA Ollama |

---

## Post-MVP — Court terme

| Fonctionnalité | Impact | Notes |
|---|---|---|
| Comparaison par lots (dossier ou liste d'URLs) | ⭐⭐⭐ | Clé pour l'intégration en livraison |
| Zones d'exclusion configurables | ⭐⭐⭐ | Masquer dates, compteurs, publicités dynamiques |
| API REST pour CI/CD | ⭐⭐ | `POST /api/compare` → JSON avec score + verdict |
| Réinitialiser la référence URL manuellement | ⭐⭐ | Ne pas attendre une nouvelle livraison |

---

## Post-MVP — Moyen terme

| Fonctionnalité | Impact | Notes |
|---|---|---|
| Dashboard récapitulatif (suivi des régressions dans le temps) | ⭐⭐⭐ | Nécessite l'historique |
| Multi-résolutions et multi-navigateurs | ⭐⭐ | Mobile vs desktop, Chrome vs Firefox |
| Apprentissage des faux positifs | ⭐⭐ | Zones marquées "acceptées" mémorisées |

---

## Long terme / Innovation

| Fonctionnalité | Notes |
|---|---|
| Segmentation composants UI (SAM) | Comparaison par composant individuel |
| Plugin navigateur | Capture directe depuis Chrome / Firefox sans passer par l'interface |
| Rapport multi-pages (comparaison de flux) | Pour tester un parcours utilisateur complet |
