#Requires -Version 5.1
<#
.SYNOPSIS
    Désinstallation propre de DataViz TNR.
    Supprime les composants installés par start.ps1 avec confirmation à chaque étape.

.NOTES
    IMPORTANT : ce script doit rester synchronisé avec start.ps1.
    Toute modification de start.ps1 (nouveau composant installé, nouveau répertoire
    généré, changement de chemin) doit être répercutée dans ce script.
#>

$ErrorActionPreference = "Continue"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_DIR   = Join-Path $SCRIPT_DIR ".venv"

# ─── Fonctions d'affichage ─────────────────────────────────────────────────
function Title { param($t) Write-Host ("  " + $t) -ForegroundColor Cyan }
function OK    { param($t) Write-Host ("    OK  " + $t) -ForegroundColor Green }
function Skip  { param($t) Write-Host ("    --  " + $t) -ForegroundColor DarkGray }
function Warn  { param($t) Write-Host ("    !!  " + $t) -ForegroundColor Yellow }
function Info  { param($t) Write-Host ("    >>  " + $t) -ForegroundColor Gray }

function Ask {
    param($Question, $Default = "N")
    $hint = if ($Default -eq "O") { "[O/n]" } else { "[o/N]" }
    $ans = Read-Host ("  " + $Question + " " + $hint)
    if ([string]::IsNullOrWhiteSpace($ans)) { $ans = $Default }
    return ($ans -match "^[oOyY]")
}

function Remove-Dir {
    param($Path, $Label)
    if (Test-Path $Path) {
        $size = (Get-ChildItem $Path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($size / 1MB, 1)
        OK ("$Label supprimé ($sizeMB Mo libérés)")
        Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Skip ("$Label : absent, rien à faire")
    }
}

function Clear-Dir {
    param($Path, $Label)
    if (Test-Path $Path) {
        $items = Get-ChildItem $Path -ErrorAction SilentlyContinue
        if ($items.Count -gt 0) {
            $size = ($items | Get-ChildItem -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            $sizeMB = [math]::Round($size / 1MB, 1)
            Remove-Item (Join-Path $Path "*") -Recurse -Force -ErrorAction SilentlyContinue
            OK ("$Label vidé ($sizeMB Mo libérés — dossier conservé)")
        } else {
            Skip ("$Label : déjà vide")
        }
    } else {
        Skip ("$Label : absent")
    }
}

# ─── En-tête ───────────────────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor White
Write-Host "    DataViz TNR  —  Désinstallation propre" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor White
Write-Host ""
Write-Host "  Ce script supprime les composants installés par start.bat." -ForegroundColor DarkGray
Write-Host "  Vos fichiers source (app.py, templates, static…) ne sont PAS touchés." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Composants concernés :" -ForegroundColor DarkGray
Write-Host "    1. Données générées (captures, résultats, uploads, historique)" -ForegroundColor DarkGray
Write-Host "    2. Environnement virtuel Python (.venv) + tous les packages pip" -ForegroundColor DarkGray
Write-Host "    3. Navigateur Chromium (cache Playwright)" -ForegroundColor DarkGray
Write-Host "    4. Modèles IA Ollama (gros fichiers)" -ForegroundColor DarkGray
Write-Host "    5. Application Ollama elle-même" -ForegroundColor DarkGray
Write-Host ""

if (-not (Ask "Continuer la désinstallation ?")) {
    Write-Host "  Annulé." -ForegroundColor DarkGray
    exit 0
}
Write-Host ""

# ─── 1. Données générées ──────────────────────────────────────────────────
Title "1/5 — Données générées (captures, résultats, uploads, historique)"
Write-Host ""
Write-Host "  Ces dossiers contiennent les images et rapports produits par DataViz." -ForegroundColor DarkGray
Write-Host "  Le contenu sera supprimé, mais les dossiers vides seront conservés." -ForegroundColor DarkGray
Write-Host ""

if (Ask "Supprimer les données générées ?" "N") {
    Clear-Dir (Join-Path $SCRIPT_DIR "captures") "captures/"
    Clear-Dir (Join-Path $SCRIPT_DIR "results")  "results/"
    Clear-Dir (Join-Path $SCRIPT_DIR "uploads")  "uploads/"
    Clear-Dir (Join-Path $SCRIPT_DIR "history")  "history/"
} else {
    Skip "Données générées conservées"
}
Write-Host ""

# ─── 2. Environnement virtuel Python ─────────────────────────────────────
Title "2/5 — Environnement virtuel Python (.venv)"
Write-Host ""
Write-Host "  Contient : Python, FastAPI, OpenCV, scikit-image, Pillow, httpx, Playwright…" -ForegroundColor DarkGray
Write-Host "  Dossier  : $VENV_DIR" -ForegroundColor DarkGray
Write-Host ""

if (Test-Path $VENV_DIR) {
    $venvSize = (Get-ChildItem $VENV_DIR -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $venvMB = [math]::Round($venvSize / 1MB, 1)
    Write-Host "  Taille détectée : $venvMB Mo" -ForegroundColor DarkGray
    Write-Host ""
    if (Ask "Supprimer le venv (.venv) ?" "N") {
        Remove-Dir $VENV_DIR ".venv"
    } else {
        Skip ".venv conservé"
    }
} else {
    Skip ".venv : absent"
}
Write-Host ""

# ─── 3. Chromium (Playwright) ────────────────────────────────────────────
Title "3/5 — Navigateur Chromium (Playwright)"
Write-Host ""

$playwrightCache = Join-Path $env:LOCALAPPDATA "ms-playwright"

if (Test-Path $playwrightCache) {
    $chromiumSize = (Get-ChildItem $playwrightCache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $chromiumMB = [math]::Round($chromiumSize / 1MB, 1)
    Write-Host "  Cache Playwright : $playwrightCache" -ForegroundColor DarkGray
    Write-Host "  Taille détectée  : $chromiumMB Mo" -ForegroundColor DarkGray
    Write-Host ""
    Warn "Attention : ce cache est partagé par TOUS les projets Playwright sur ce PC."
    Warn "Ne supprimez que si DataViz est le seul projet Playwright installé."
    Write-Host ""
    if (Ask "Supprimer le cache Chromium Playwright ?" "N") {
        Remove-Dir $playwrightCache "Cache Playwright (ms-playwright)"
    } else {
        Skip "Cache Playwright conservé"
    }
} else {
    Skip "Cache Playwright : absent ($playwrightCache)"
}
Write-Host ""

# ─── 4. Modèles Ollama ───────────────────────────────────────────────────
Title "4/5 — Modèles IA Ollama"
Write-Host ""

$ollamaRunning = $false
try {
    Invoke-WebRequest "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop | Out-Null
    $ollamaRunning = $true
} catch {}

if ($ollamaRunning) {
    try {
        $tags = (Invoke-WebRequest "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5 | ConvertFrom-Json)
        $models = $tags.models
        if ($models -and $models.Count -gt 0) {
            Write-Host "  Modèles installés :" -ForegroundColor DarkGray
            foreach ($mdl in $models) {
                $sizeMB = [math]::Round($mdl.size / 1MB, 0)
                Write-Host ("    - " + $mdl.name + "  (~" + $sizeMB + " Mo)") -ForegroundColor DarkGray
            }
            Write-Host ""

            $ollamaExe = $null
            $candidates = @(
                (Get-Command ollama -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
                (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
                (Join-Path $env:ProgramFiles  "Ollama\ollama.exe")
            )
            foreach ($p in $candidates) {
                if ($p -and (Test-Path $p -ErrorAction SilentlyContinue)) { $ollamaExe = $p; break }
            }

            if (Ask "Supprimer TOUS les modèles Ollama listés ci-dessus ?" "N") {
                foreach ($mdl in $models) {
                    if ($ollamaExe) {
                        Info ("Suppression de " + $mdl.name + "...")
                        & $ollamaExe rm $mdl.name 2>&1 | Out-Null
                        if ($LASTEXITCODE -eq 0) { OK ($mdl.name + " supprimé") }
                        else { Warn ("Échec pour " + $mdl.name + " — supprimez-le manuellement : ollama rm " + $mdl.name) }
                    } else {
                        Warn ("ollama.exe introuvable — supprimez manuellement : ollama rm " + $mdl.name)
                    }
                }
            } else {
                Skip "Modèles Ollama conservés"
            }
        } else {
            Skip "Aucun modèle Ollama installé"
        }
    } catch {
        Warn "Impossible de lister les modèles Ollama : $_"
    }
} else {
    Write-Host "  Ollama n'est pas actif — impossible de lister les modèles." -ForegroundColor DarkGray
    Write-Host "  Pour supprimer les modèles manuellement :" -ForegroundColor DarkGray
    Write-Host "    1. Lancez : ollama serve" -ForegroundColor DarkGray
    Write-Host "    2. Puis   : ollama list" -ForegroundColor DarkGray
    Write-Host "    3. Puis   : ollama rm <nom-du-modele>" -ForegroundColor DarkGray
    Write-Host ""
    Skip "Modèles Ollama : non traités (Ollama inactif)"
}
Write-Host ""

# ─── 5. Application Ollama ───────────────────────────────────────────────
Title "5/5 — Application Ollama"
Write-Host ""

$ollamaAppDir = $null
$candidatesApp = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Ollama"),
    (Join-Path $env:ProgramFiles  "Ollama")
)
foreach ($p in $candidatesApp) {
    if ($p -and (Test-Path $p -ErrorAction SilentlyContinue)) { $ollamaAppDir = $p; break }
}

if ($ollamaAppDir) {
    Write-Host "  Dossier Ollama détecté : $ollamaAppDir" -ForegroundColor DarkGray
    Write-Host ""
    Warn "Attention : Ollama peut être utilisé par d'autres projets sur ce PC."
    Warn "Assurez-vous que DataViz est le seul projet qui l'utilise avant de supprimer."
    Write-Host ""

    if (Ask "Désinstaller Ollama complètement ?" "N") {
        # Arrêter le process ollama s'il tourne
        $proc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
        if ($proc) {
            Info "Arrêt du service Ollama en cours..."
            Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
            Start-Sleep 2
        }

        # Chercher un désinstallateur officiel
        $uninstallerPath = $null
        $candidates = @(
            (Join-Path $ollamaAppDir "OllamaUninstall.exe"),
            (Join-Path $ollamaAppDir "unins000.exe"),
            (Join-Path $env:LOCALAPPDATA "Programs\Ollama\unins000.exe")
        )
        foreach ($u in $candidates) {
            if (Test-Path $u -ErrorAction SilentlyContinue) { $uninstallerPath = $u; break }
        }

        if ($uninstallerPath) {
            Info "Lancement du désinstallateur officiel Ollama..."
            Start-Process $uninstallerPath -ArgumentList "/S" -Wait
            OK "Ollama désinstallé via le désinstallateur officiel"
        } else {
            # Suppression manuelle du dossier
            Warn "Désinstallateur officiel non trouvé — suppression manuelle du dossier"
            Remove-Dir $ollamaAppDir "Application Ollama"
        }

        # Nettoyage du dossier de données Ollama (~HOME/.ollama)
        $ollamaDataDir = Join-Path $env:USERPROFILE ".ollama"
        if (Test-Path $ollamaDataDir) {
            $ollamaDataSize = (Get-ChildItem $ollamaDataDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            $ollamaDataMB = [math]::Round($ollamaDataSize / 1MB, 0)
            Write-Host ""
            Write-Host "  Dossier de données Ollama détecté : $ollamaDataDir (~$ollamaDataMB Mo)" -ForegroundColor DarkGray
            if (Ask "Supprimer aussi le dossier de données Ollama (~/.ollama) ?" "N") {
                Remove-Dir $ollamaDataDir "Données Ollama (~/.ollama)"
            } else {
                Skip "Données Ollama conservées"
            }
        }
    } else {
        Skip "Application Ollama conservée"
    }
} else {
    Skip "Ollama : non installé ou déjà supprimé"
}
Write-Host ""

# ─── Récapitulatif ────────────────────────────────────────────────────────
Write-Host "  ============================================" -ForegroundColor White
Write-Host "    Désinstallation terminée." -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor White
Write-Host ""
Write-Host "  Les fichiers source de DataViz (app.py, templates, static, docs…) n'ont" -ForegroundColor DarkGray
Write-Host "  pas été supprimés. Pour les supprimer, effacez simplement ce dossier." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Pour réinstaller DataViz, relancez start.bat." -ForegroundColor DarkGray
Write-Host ""
Read-Host "  Appuyez sur Entrée pour fermer"
