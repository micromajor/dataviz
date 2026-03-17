"""
DataViz — Comparateur Visuel TNR
Serveur FastAPI offline pour la comparaison d'images entre livraisons.
Intègre la capture d'écran par URL (Playwright) et l'analyse IA (Ollama).
"""

import asyncio
import sys

# Sur Windows, forcer ProactorEventLoop pour permettre les sous-processus (Playwright)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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
from fastapi import BackgroundTasks, FastAPI, File, UploadFile, Request, Form
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
HISTORY_DIR = Path("history")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)
CAPTURE_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llava"  # llava:7b ~4 Go — bon compromis qualite/taille pour l'analyse de screenshots

# ---------------------------------------------------------------------------
# Helpers Ollama
# ---------------------------------------------------------------------------
def _find_ollama_exe() -> str | None:
    """Cherche l'exécutable Ollama dans le PATH et les chemins Windows courants."""
    import shutil, os
    if found := shutil.which("ollama"):
        return found
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


async def _ensure_ollama_running() -> None:
    """Démarre ollama serve en arrière-plan si installé mais inactif."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        return  # déjà actif
    except Exception:
        pass
    exe = _find_ollama_exe()
    if not exe:
        return
    logger.info("Ollama installé mais inactif — démarrage automatique : %s serve", exe)
    import subprocess
    _no_window = 0x08000000 if sys.platform == "win32" else 0
    subprocess.Popen(
        [exe, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_no_window,
    )


app = FastAPI(title="DataViz — Comparateur Visuel TNR")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/results", StaticFiles(directory=str(RESULT_DIR)), name="results")
app.mount("/captures", StaticFiles(directory=str(CAPTURE_DIR)), name="captures")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def on_startup():
    """Tente de démarrer Ollama automatiquement au lancement de l'application."""
    asyncio.create_task(_ensure_ollama_running())


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
    # Max sur les 3 canaux : plus sensible que la luminance pondérée (ex. blanc sur fond clair)
    gray_diff = np.max(abs_diff, axis=2).astype(np.uint8)

    # Seuillage brut pour le décompte de pixels (metric affiché à l'utilisateur)
    _, thresh_raw = cv2.threshold(gray_diff, threshold, 255, cv2.THRESH_BINARY)
    total_pixels = thresh_raw.shape[0] * thresh_raw.shape[1]
    diff_pixels = cv2.countNonZero(thresh_raw)
    diff_percent = round((diff_pixels / total_pixels) * 100, 2)

    # Détection de contours fins (Canny) : attrape les bordures de rectangles/lignes peu contrastées
    # qui passent sous le seuil de seuillage simple (ex. rectangle blanc sur fond blanc-brumeux)
    canny_lo = max(5, threshold // 4)
    canny_hi = max(15, threshold // 2)
    edges = cv2.Canny(gray_diff, canny_lo, canny_hi)
    # Combiner seuillage + contours fins pour la détection des zones
    thresh = cv2.bitwise_or(thresh_raw, edges)

    # Dilatation morphologique : fusionner les pixels proches en régions cohérentes
    # Évite que des pixels éparpillés forment chacun un micro-contour invisible dans le rapport
    merge_kernel = np.ones((7, 7), np.uint8)
    thresh_merged = cv2.dilate(thresh, merge_kernel, iterations=2)

    # Détection des contours sur l'image dilatée
    contours, _ = cv2.findContours(thresh_merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Seuil minimal de surface : proportionnel à la taille de l'image pour éviter le bruit résiduel
    img_h, img_w = img1.shape[:2]
    min_area = max(20, int(img_h * img_w * 0.00005))  # ~0.005% de l'image
    significant_contours = [c for c in contours if cv2.contourArea(c) >= min_area]

    # Analyse détaillée de chaque zone modifiée
    regions = []
    contour_img = img2.copy()
    for contour in significant_contours:
        x, y, w, h = cv2.boundingRect(contour)

        # Intensité mesurée sur le diff ORIGINAL (pas dilaté) pour garder des valeurs exactes
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

        # Sévérité basée sur 3 critères indépendants :
        #   avg_intensity : écart moyen sur tout le bounding box (dilué par les pixels inchangés)
        #   max_intensity : pic d'écart (un élément fin mais très contrasté reste visible à l'œil nu)
        #   area_percent  : % de l'image couvert par le bounding box
        # Seuils calibrés pour correspondre à la visibilité humaine.
        if avg_intensity > 100 or max_intensity > 230 or area_percent > 8:
            severity = "critique"
            if avg_intensity > 100:
                criteria = f"intensité moy. {round(avg_intensity,1)} > 100/255"
            elif max_intensity > 230:
                criteria = f"intensité max. {round(max_intensity,1)} > 230/255"
            else:
                criteria = f"surface {area_percent}% > 8%"
        elif avg_intensity > 40 or max_intensity > 150 or area_percent > 3:
            severity = "majeur"
            if avg_intensity > 40:
                criteria = f"intensité moy. {round(avg_intensity,1)} > 40/255"
            elif max_intensity > 150:
                criteria = f"intensité max. {round(max_intensity,1)} > 150/255"
            else:
                criteria = f"surface {area_percent}% > 3%"
        elif avg_intensity > 10 or max_intensity > 50 or area_percent > 0.3:
            severity = "mineur"
            if avg_intensity > 10:
                criteria = f"intensité moy. {round(avg_intensity,1)} > 10/255"
            elif max_intensity > 50:
                criteria = f"intensité max. {round(max_intensity,1)} > 50/255"
            else:
                criteria = f"surface {area_percent}% > 0.3%"
        else:
            severity = "cosmétique"
            criteria = f"intensité moy. {round(avg_intensity,1)} ≤ 10/255 et surface {area_percent}% ≤ 0.3%"

        regions.append({
            "x": x, "y": y, "w": w, "h": h,
            "position": position,
            "area_percent": area_percent,
            "avg_intensity": round(avg_intensity, 1),
            "max_intensity": round(max_intensity, 1),
            "severity": severity,
            "criteria": criteria,
        })

    # Trier par sévérité (même ordre que le résumé textuel) puis numéroter et dessiner
    _sev_order = {"critique": 0, "majeur": 1, "mineur": 2, "cosmétique": 3}
    regions.sort(key=lambda r: _sev_order.get(r["severity"], 4))

    # Couleurs BGR par sévérité (palette OUDS : rouge/orange/jaune/bleu)
    _sev_colors_bgr = {
        "critique":   (20, 60, 205),    # #cd3c14
        "majeur":     (0, 121, 255),    # #ff7900
        "mineur":     (0, 210, 255),    # #ffd200
        "cosmétique": (217, 144, 74),   # #4a90d9
    }
    # contour_img = image téléchargeable avec rectangles + numéros gravés
    for idx, region in enumerate(regions, 1):
        region["zone_index"] = idx
        rx, ry, rw, rh = region["x"], region["y"], region["w"], region["h"]
        color = _sev_colors_bgr.get(region["severity"], (0, 0, 255))
        cv2.rectangle(contour_img, (rx, ry), (rx + rw, ry + rh), color, 2)
        # Badge numéroté : fond coloré + chiffre blanc
        label = str(idx)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale, thickness = 0.45, 1
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
        bx = rx if (rx + tw + 6) <= img_w else max(0, img_w - tw - 6)
        by = (ry - th - 6) if ry >= (th + 10) else (ry + rh + 4)
        cv2.rectangle(contour_img, (bx, by), (bx + tw + 6, by + th + 6), color, -1)
        text_color = (0, 0, 0) if region["severity"] in ("mineur", "majeur") else (255, 255, 255)
        cv2.putText(contour_img, label, (bx + 3, by + th + 2), font, font_scale, text_color, thickness, cv2.LINE_AA)

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
        "img_width": img_w,
        "img_height": img_h,
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
            f"intensité moy. {region['avg_intensity']}/255"
            + (f" [critère : {region['criteria']}]" if region.get('criteria') else "")
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


def save_report(uid: str, label: str, mode: str, data: dict) -> None:
    """Sauvegarde les métadonnées d'une comparaison dans l'historique local (JSON)."""
    record = {
        "uid": uid,
        "label": label.strip() if label else "",
        "mode": mode,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        **data,
    }
    path = HISTORY_DIR / f"{uid}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def update_report_ai(uid: str, ai_analysis: str) -> None:
    """Met à jour uniquement le champ ai_analysis d'un rapport existant."""
    path = HISTORY_DIR / f"{uid}.json"
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        record = json.load(f)
    record["ai_analysis"] = ai_analysis
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


async def _ai_background_task(
    uid: str,
    ref_bytes: bytes,
    new_bytes: bytes,
    score_ssim: float,
    diff_percent: float,
    num_regions: int,
) -> None:
    """Tâche de fond : lance l'analyse IA et met à jour le rapport une fois terminée."""
    result = await analyze_with_ai(ref_bytes, new_bytes, score_ssim, diff_percent, num_regions)
    if result:
        update_report_ai(uid, result)



# ---------------------------------------------------------------------------
# Capture d'écran (Playwright)
# ---------------------------------------------------------------------------

def _capture_screenshot_sync(url: str, full_page: bool = True) -> bytes:
    """Capture synchrone dans un thread (contourne les limitations d'event loop Windows)."""
    from playwright.sync_api import sync_playwright

    # Utilise Chrome installé localement (évite le téléchargement de Chromium)
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME_PATH)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url, wait_until="networkidle", timeout=30000)
        screenshot = page.screenshot(full_page=full_page, type="png")
        browser.close()
    return screenshot


async def capture_screenshot(url: str, full_page: bool = True) -> bytes:
    """Capture une page web complète via Playwright et retourne les bytes PNG.
    Lance la capture dans un thread executor pour éviter les problèmes d'event loop Windows.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _capture_screenshot_sync, url, full_page)


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
        async with httpx.AsyncClient(timeout=300.0) as client:
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
async def take_screenshot(
    request: Request,
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    label: str = Form(default=""),
    threshold_ssim: int = Form(default=95),
    threshold_pixels: float = Form(default=2.0),
):
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

        # Date de la capture de référence (extraite du nom de fichier)
        ref_ts = ref_path.stem.replace(url_hash + "_", "")
        try:
            ref_date = datetime.strptime(ref_ts, "%Y%m%d_%H%M%S").strftime("%d/%m/%Y à %H:%M")
        except ValueError:
            ref_date = ref_ts

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

    # Analyse IA (optionnelle — lancée en arrière-plan, ne bloque pas la réponse)
    ai_analysis = None
    background_tasks.add_task(
        _ai_background_task, uid,
        ref_bytes, screenshot_bytes,
        result["score_ssim"], result["diff_percent"], result["num_regions"],
    )

    verdict = "pass" if result["score_ssim"] >= threshold_ssim / 100 and result["diff_percent"] <= threshold_pixels else "fail"
        save_report(uid, label, "url", {
            "score_ssim": result["score_ssim"],
            "diff_percent": result["diff_percent"],
            "num_regions": result["num_regions"],
            "threshold": 30,
            "threshold_ssim": threshold_ssim,
            "threshold_pixels": threshold_pixels,
            "verdict": verdict,
            "ref_url": f"/captures/{ref_path.name}",
            "new_url": f"/captures/{filename}",
            "heatmap_url": heatmap_url,
            "contour_url": contour_url,
            "text_summary": text_summary,
            "ai_analysis": ai_analysis,
            "source_url": url,
            "ref_date": ref_date,
            "capture_count": len(previous_captures) + 1,
            "regions": result["regions"],
            "img_width": result["img_width"],
            "img_height": result["img_height"],
        })

        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "uid": uid,
                "label": label.strip(),
                "verdict": verdict,
                "threshold_ssim": threshold_ssim,
                "threshold_pixels": threshold_pixels,
                "from_history": False,
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
                "ref_date": ref_date,
                "capture_count": len(previous_captures) + 1,
                "regions": result["regions"],
                "img_width": result["img_width"],
                "img_height": result["img_height"],
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
    background_tasks: BackgroundTasks,
    image_ref: UploadFile = File(...),
    image_new: UploadFile = File(...),
    threshold: int = Form(default=30),
    label: str = Form(default=""),
    threshold_ssim: int = Form(default=95),
    threshold_pixels: float = Form(default=2.0),
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

    # Analyse IA (optionnelle — lancée en arrière-plan, ne bloque pas la réponse)
    ai_analysis = None
    background_tasks.add_task(
        _ai_background_task, uid,
        ref_bytes, new_bytes,
        result["score_ssim"], result["diff_percent"], result["num_regions"],
    )

    verdict = "pass" if result["score_ssim"] >= threshold_ssim / 100 and result["diff_percent"] <= threshold_pixels else "fail"
    save_report(uid, label, "file", {
        "score_ssim": result["score_ssim"],
        "diff_percent": result["diff_percent"],
        "num_regions": result["num_regions"],
        "threshold": threshold,
        "threshold_ssim": threshold_ssim,
        "threshold_pixels": threshold_pixels,
        "verdict": verdict,
        "ref_url": f"/uploads/{ref_path.name}",
        "new_url": f"/uploads/{new_path.name}",
        "heatmap_url": heatmap_url,
        "contour_url": contour_url,
        "text_summary": text_summary,
        "ai_analysis": ai_analysis,
        "source_url": None,
        "regions": result["regions"],
        "img_width": result["img_width"],
        "img_height": result["img_height"],
    })

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "uid": uid,
            "label": label.strip(),
            "verdict": verdict,
            "threshold_ssim": threshold_ssim,
            "threshold_pixels": threshold_pixels,
            "from_history": False,
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
            "regions": result["regions"],
            "img_width": result["img_width"],
            "img_height": result["img_height"],
        },
    )


# ---------------------------------------------------------------------------
# Historique
# ---------------------------------------------------------------------------

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Page listant toutes les comparaisons enregistrées."""
    reports = []
    for p in sorted(HISTORY_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            reports.append(data)
        except Exception:
            pass
    return templates.TemplateResponse("history.html", {"request": request, "reports": reports})


@app.get("/ai/result/{uid}")
async def ai_result(uid: str):
    """Retourne le statut de l'analyse IA pour un rapport donné (polling frontend)."""
    if not all(c.isalnum() or c in "-_" for c in uid):
        return JSONResponse({"error": "Identifiant invalide"}, status_code=400)
    path = HISTORY_DIR / f"{uid}.json"
    if not path.exists():
        return JSONResponse({"status": "pending", "analysis": None})
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    ai = data.get("ai_analysis")
    if ai:
        return JSONResponse({"status": "done", "analysis": ai})
    return JSONResponse({"status": "pending", "analysis": None})



@app.get("/history/{uid}", response_class=HTMLResponse)
async def history_detail(request: Request, uid: str):
    """Rouvre un rapport archivé."""
    # Validation anti path-traversal : uid alphanumérique uniquement
    if not all(c.isalnum() or c in "-_" for c in uid):
        return JSONResponse({"error": "Identifiant invalide"}, status_code=400)
    path = HISTORY_DIR / f"{uid}.json"
    if not path.exists():
        return JSONResponse({"error": "Rapport introuvable"}, status_code=404)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "from_history": True, **data},
    )


@app.get("/capture/reference")
async def capture_reference(url: str):
    """Retourne les informations sur la capture de référence existante pour une URL."""
    import hashlib
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
    captures = get_capture_history(url_hash)
    if not captures:
        return JSONResponse({"has_reference": False})
    ref = captures[-1]
    ref_ts = ref.stem.replace(url_hash + "_", "")
    try:
        date_str = datetime.strptime(ref_ts, "%Y%m%d_%H%M%S").strftime("%d/%m/%Y à %H:%M")
    except ValueError:
        date_str = ref_ts
    return JSONResponse({
        "has_reference": True,
        "filename": ref.name,
        "date": date_str,
        "count": len(captures),
        "url": f"/captures/{ref.name}",
    })


# ---------------------------------------------------------------------------
# Statut IA (Ollama)
# ---------------------------------------------------------------------------
@app.get("/ai/status")
async def ai_status():
    """Vérifie si Ollama est disponible, installé et si le modèle est téléchargé."""
    installed = _find_ollama_exe() is not None
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            tags = resp.json()
        models = [m["name"] for m in tags.get("models", [])]
        model_available = any(m.startswith(OLLAMA_MODEL) for m in models)
        return JSONResponse({
            "connected": True,
            "installed": installed,
            "model": OLLAMA_MODEL,
            "model_available": model_available,
        })
    except Exception:
        if installed:
            # Ollama installé mais pas actif — tente de le démarrer
            asyncio.create_task(_ensure_ollama_running())
        return JSONResponse({
            "connected": False,
            "installed": installed,
            "model": OLLAMA_MODEL,
            "model_available": False,
        })


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
