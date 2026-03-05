"""
DataViz — Comparateur Visuel TNR
Serveur FastAPI offline pour la comparaison d'images entre livraisons.
Intègre la capture d'écran par URL (Playwright) et l'analyse IA (Ollama).
"""

import base64
import io
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import httpx
import numpy as np
from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger("dataviz")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_DIR = Path("uploads")
RESULT_DIR = Path("results")
CAPTURE_DIR = Path("captures")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)
CAPTURE_DIR.mkdir(exist_ok=True)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "pixtral"  # ou "smolvlm", "minicpm-v", etc.

app = FastAPI(title="DataViz — Comparateur Visuel TNR")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/results", StaticFiles(directory=str(RESULT_DIR)), name="results")
app.mount("/captures", StaticFiles(directory=str(CAPTURE_DIR)), name="captures")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------------------------------
# Moteur de comparaison
# ---------------------------------------------------------------------------

def load_image(file_bytes: bytes) -> np.ndarray:
    """Charge une image depuis des bytes en array BGR (OpenCV)."""
    img_array = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img


def resize_to_match(img1: np.ndarray, img2: np.ndarray) -> tuple:
    """Redimensionne img2 pour correspondre aux dimensions de img1."""
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    if (h1, w1) != (h2, w2):
        img2 = cv2.resize(img2, (w1, h1), interpolation=cv2.INTER_AREA)
    return img1, img2


def compute_diff(img1: np.ndarray, img2: np.ndarray, threshold: int = 30):
    """
    Compare deux images et retourne :
    - score_ssim : score SSIM (0-1, 1 = identique)
    - diff_image : heatmap des différences
    - contour_image : image avec contours des zones modifiées
    - diff_percent : pourcentage de pixels différents
    - num_regions : nombre de zones modifiées détectées
    """
    img1, img2 = resize_to_match(img1, img2)

    # Conversion en niveaux de gris pour SSIM
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Calcul SSIM
    score_ssim, diff_map = ssim(gray1, gray2, full=True)
    diff_map = (diff_map * 255).astype("uint8")

    # Différence absolue pixel-à-pixel
    abs_diff = cv2.absdiff(img1, img2)
    gray_diff = cv2.cvtColor(abs_diff, cv2.COLOR_BGR2GRAY)

    # Seuillage pour isoler les différences significatives
    _, thresh = cv2.threshold(gray_diff, threshold, 255, cv2.THRESH_BINARY)

    # Pourcentage de pixels différents
    total_pixels = thresh.shape[0] * thresh.shape[1]
    diff_pixels = cv2.countNonZero(thresh)
    diff_percent = round((diff_pixels / total_pixels) * 100, 2)

    # Détection des contours des zones modifiées
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filtrer les contours trop petits (bruit)
    min_area = 50
    significant_contours = [c for c in contours if cv2.contourArea(c) >= min_area]

    # Analyse détaillée de chaque zone modifiée
    img_h, img_w = img1.shape[:2]
    regions = []
    contour_img = img2.copy()
    for contour in significant_contours:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(contour_img, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Intensité moyenne du changement dans la zone
        zone_diff = gray_diff[y:y+h, x:x+w]
        avg_intensity = float(np.mean(zone_diff))
        max_intensity = float(np.max(zone_diff))

        # Position en langage naturel
        cx, cy = x + w // 2, y + h // 2
        pos_v = "en haut" if cy < img_h / 3 else ("au centre" if cy < 2 * img_h / 3 else "en bas")
        pos_h = "à gauche" if cx < img_w / 3 else ("au centre" if cx < 2 * img_w / 3 else "à droite")
        position = f"{pos_v} {pos_h}" if pos_v != pos_h else pos_v

        # Taille relative de la zone
        area_percent = round((w * h) / (img_w * img_h) * 100, 1)

        # Sévérité basée sur l'intensité et la taille
        if avg_intensity > 150 or area_percent > 10:
            severity = "critique"
        elif avg_intensity > 80 or area_percent > 5:
            severity = "majeur"
        elif avg_intensity > 40 or area_percent > 1:
            severity = "mineur"
        else:
            severity = "cosmétique"

        regions.append({
            "x": x, "y": y, "w": w, "h": h,
            "position": position,
            "area_percent": area_percent,
            "avg_intensity": round(avg_intensity, 1),
            "max_intensity": round(max_intensity, 1),
            "severity": severity,
        })

    # Heatmap colorée des différences
    heatmap = cv2.applyColorMap(gray_diff, cv2.COLORMAP_JET)
    mask = gray_diff > threshold
    heatmap_masked = np.zeros_like(heatmap)
    heatmap_masked[mask] = heatmap[mask]

    return {
        "score_ssim": round(score_ssim, 4),
        "diff_percent": diff_percent,
        "num_regions": len(significant_contours),
        "regions": regions,
        "heatmap": heatmap_masked,
        "contour_image": contour_img,
        "threshold_mask": thresh,
    }


def save_cv_image(img: np.ndarray, filename: str) -> str:
    """Sauvegarde une image OpenCV et retourne le chemin relatif."""
    path = RESULT_DIR / filename
    cv2.imwrite(str(path), img)
    return f"/results/{filename}"


def generate_text_summary(score_ssim: float, diff_percent: float, regions: list) -> str:
    """
    Génère un résumé textuel des différences détectées par le moteur de comparaison.
    Toujours disponible, même sans IA.
    """
    severity_icons = {
        "critique": "🔴",
        "majeur": "🟠",
        "mineur": "🟡",
        "cosmétique": "🔵",
    }

    lines = []

    # Résumé global
    ssim_pct = round(score_ssim * 100, 1)
    if ssim_pct >= 99:
        lines.append("Les deux versions sont quasiment identiques.")
    elif ssim_pct >= 95:
        lines.append("Les deux versions sont très proches avec quelques différences mineures.")
    elif ssim_pct >= 85:
        lines.append("Des différences notables ont été détectées entre les deux versions.")
    else:
        lines.append("Les deux versions présentent des différences significatives.")

    lines.append(f"Similarité structurelle : {ssim_pct}% — {diff_percent}% des pixels ont changé.")

    if not regions:
        lines.append("Aucune zone de changement significative n'a été isolée.")
        return "\n".join(lines)

    lines.append(f"")
    lines.append(f"{len(regions)} zone(s) de changement détectée(s) :")

    # Tri par sévérité (critique d'abord)
    severity_order = {"critique": 0, "majeur": 1, "mineur": 2, "cosmétique": 3}
    sorted_regions = sorted(regions, key=lambda r: severity_order.get(r["severity"], 4))

    for i, region in enumerate(sorted_regions, 1):
        icon = severity_icons.get(region["severity"], "⚪")
        lines.append(
            f"{icon} Zone {i} — {region['severity'].upper()} — "
            f"{region['position']}, "
            f"taille {region['w']}×{region['h']}px ({region['area_percent']}% de l'image), "
            f"intensité moyenne du changement : {region['avg_intensity']}/255"
        )

    # Comptage par sévérité
    counts = {}
    for r in regions:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1

    summary_parts = []
    for sev in ["critique", "majeur", "mineur", "cosmétique"]:
        if sev in counts:
            summary_parts.append(f"{counts[sev]} {sev}(s)")

    lines.append(f"")
    lines.append(f"Synthèse : {', '.join(summary_parts)}.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Capture d'écran (Playwright)
# ---------------------------------------------------------------------------

async def capture_screenshot(url: str, full_page: bool = True) -> bytes:
    """Capture une page web complète via Playwright et retourne les bytes PNG."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(url, wait_until="networkidle", timeout=30000)
        screenshot = await page.screenshot(full_page=full_page, type="png")
        await browser.close()
    return screenshot


def get_capture_history(url_hash: str) -> list:
    """Retourne la liste ordonnée des captures précédentes pour une URL."""
    pattern = f"{url_hash}_*.png"
    files = sorted(CAPTURE_DIR.glob(pattern), key=lambda f: f.stat().st_mtime)
    return files


# ---------------------------------------------------------------------------
# Analyse IA via Ollama (offline)
# ---------------------------------------------------------------------------

async def analyze_with_ai(
    ref_bytes: bytes,
    new_bytes: bytes,
    score_ssim: float,
    diff_percent: float,
    num_regions: int,
) -> str | None:
    """
    Envoie les deux images à un modèle vision local (Ollama) pour obtenir
    une description en langage naturel des différences détectées.
    Retourne None si Ollama n'est pas disponible.
    """
    ref_b64 = base64.b64encode(ref_bytes).decode("utf-8")
    new_b64 = base64.b64encode(new_bytes).decode("utf-8")

    prompt = (
        "Tu es un expert en tests de non-régression visuelle (TNR) pour des applications web. "
        "On te fournit deux captures d'écran : la première est la VERSION DE RÉFÉRENCE, "
        "la seconde est la NOUVELLE VERSION après livraison.\n\n"
        f"Données techniques : SSIM={score_ssim}, pixels différents={diff_percent}%, "
        f"zones modifiées détectées={num_regions}.\n\n"
        "Analyse précisément les différences visuelles entre ces deux images. "
        "Pour chaque différence trouvée :\n"
        "1. Décris ce qui a changé (position, couleur, texte, élément ajouté/supprimé)\n"
        "2. Localise la zone concernée (haut, bas, centre, gauche, droite)\n"
        "3. Classe la sévérité : 🔴 Critique / 🟠 Majeur / 🟡 Mineur / 🔵 Cosmétique\n"
        "4. Indique si c'est probablement une régression ou un changement intentionnel\n\n"
        "Réponds en français. Sois précis et concis. "
        "Si les images sont identiques, indique-le clairement."
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "images": [ref_b64, new_b64],
        "stream": False,
        "options": {"temperature": 0.2},
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate", json=payload
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
    except Exception as e:
        logger.warning("Ollama non disponible : %s", e)
        return None

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/capture", response_class=HTMLResponse)
async def capture_page(request: Request):
    """Page de capture d'écran par URL."""
    return templates.TemplateResponse("capture.html", {"request": request})


@app.post("/capture/screenshot")
async def take_screenshot(request: Request, url: str = Form(...)):
    """Capture une URL et compare avec la capture précédente si elle existe."""
    import hashlib

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
    previous_captures = get_capture_history(url_hash)

    # Capture de la nouvelle version
    try:
        screenshot_bytes = await capture_screenshot(url)
    except Exception as e:
        return JSONResponse(
            {"error": f"Échec de la capture : {e}"}, status_code=400
        )

    # Sauvegarder la capture
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{url_hash}_{timestamp}.png"
    capture_path = CAPTURE_DIR / filename
    with open(capture_path, "wb") as f:
        f.write(screenshot_bytes)

    # S'il existe une capture précédente, comparer automatiquement
    if previous_captures:
        ref_path = previous_captures[-1]
        ref_bytes = ref_path.read_bytes()

        img_ref = load_image(ref_bytes)
        img_new = load_image(screenshot_bytes)

        result = compute_diff(img_ref, img_new, threshold=30)

        uid = uuid.uuid4().hex[:8]
        heatmap_url = save_cv_image(result["heatmap"], f"{uid}_heatmap.png")
        contour_url = save_cv_image(result["contour_image"], f"{uid}_contours.png")

        # Résumé textuel automatique (toujours disponible)
        text_summary = generate_text_summary(
            result["score_ssim"], result["diff_percent"], result["regions"],
        )

        # Analyse IA (optionnelle — si Ollama est disponible)
        ai_analysis = await analyze_with_ai(
            ref_bytes, screenshot_bytes,
            result["score_ssim"], result["diff_percent"], result["num_regions"],
        )

        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "ref_url": f"/captures/{ref_path.name}",
                "new_url": f"/captures/{filename}",
                "heatmap_url": heatmap_url,
                "contour_url": contour_url,
                "score_ssim": result["score_ssim"],
                "diff_percent": result["diff_percent"],
                "num_regions": result["num_regions"],
                "threshold": 30,
                "text_summary": text_summary,
                "ai_analysis": ai_analysis,
                "source_url": url,
                "capture_count": len(previous_captures) + 1,
            },
        )

    # Première capture : pas de comparaison possible
    return templates.TemplateResponse(
        "capture.html",
        {
            "request": request,
            "message": f"Première capture enregistrée pour cette URL. "
                       f"Capturez à nouveau après la prochaine livraison pour comparer.",
            "capture_url": f"/captures/{filename}",
            "url": url,
        },
    )


@app.post("/compare")
async def compare(
    request: Request,
    image_ref: UploadFile = File(...),
    image_new: UploadFile = File(...),
    threshold: int = Form(default=30),
):
    # Lecture des images
    ref_bytes = await image_ref.read()
    new_bytes = await image_new.read()

    img_ref = load_image(ref_bytes)
    img_new = load_image(new_bytes)

    if img_ref is None or img_new is None:
        return JSONResponse(
            {"error": "Impossible de lire une des images."}, status_code=400
        )

    # Comparaison
    result = compute_diff(img_ref, img_new, threshold=threshold)

    # Sauvegarde des fichiers résultats
    uid = uuid.uuid4().hex[:8]
    ref_path = UPLOAD_DIR / f"{uid}_ref{Path(image_ref.filename).suffix}"
    new_path = UPLOAD_DIR / f"{uid}_new{Path(image_new.filename).suffix}"

    with open(ref_path, "wb") as f:
        f.write(ref_bytes)
    with open(new_path, "wb") as f:
        f.write(new_bytes)

    heatmap_url = save_cv_image(result["heatmap"], f"{uid}_heatmap.png")
    contour_url = save_cv_image(result["contour_image"], f"{uid}_contours.png")

    # Résumé textuel automatique (toujours disponible)
    text_summary = generate_text_summary(
        result["score_ssim"], result["diff_percent"], result["regions"],
    )

    # Analyse IA (optionnelle — si Ollama est disponible)
    ai_analysis = await analyze_with_ai(
        ref_bytes, new_bytes,
        result["score_ssim"], result["diff_percent"], result["num_regions"],
    )

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "ref_url": f"/uploads/{ref_path.name}",
            "new_url": f"/uploads/{new_path.name}",
            "heatmap_url": heatmap_url,
            "contour_url": contour_url,
            "score_ssim": result["score_ssim"],
            "diff_percent": result["diff_percent"],
            "num_regions": result["num_regions"],
            "threshold": threshold,
            "text_summary": text_summary,
            "ai_analysis": ai_analysis,
        },
    )


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
