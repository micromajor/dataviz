#Requires -Version 5.1
param([switch]$SkipDeps)

$ErrorActionPreference = "Continue"
$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_DIR    = Join-Path $SCRIPT_DIR ".venv"
$PYTHON_VENV = Join-Path $VENV_DIR "Scripts\python.exe"
$APP_PORT    = 8000

$m = Select-String -Path (Join-Path $SCRIPT_DIR "app.py") -Pattern 'OLLAMA_MODEL\s*=\s*"([^"]+)"' | Select-Object -First 1
$OLLAMA_MODEL = if ($m) { $m.Matches.Groups[1].Value } else { "minicpm-v" }

# Etapes totales
$TOTAL_STEPS = if ($SkipDeps) { 6 } else { 8 }
$STEP = 0

function Step {
    param($t)
    $script:STEP++
    $label = "[" + $script:STEP + "/" + $script:TOTAL_STEPS + "] " + $t
    Write-Host ""
    Write-Host $label -ForegroundColor Cyan
    Write-Host ("    " + ("-" * ($label.Length - 4))) -ForegroundColor DarkGray
}
function OK   { param($t) Write-Host ("    OK  " + $t) -ForegroundColor Green }
function Warn { param($t) Write-Host ("    !!  " + $t) -ForegroundColor Yellow }
function Err  { param($t) Write-Host ("    XX  " + $t) -ForegroundColor Red }
function Info { param($t) Write-Host ("    >>  " + $t) -ForegroundColor Gray }

# Spinner pour les operations longues
# Usage : $job = Start-Job { ... } ; Spin $job "Message"
function Spin {
    param($Job, $Msg)
    $frames = @("|", "/", "-", "\")
    $i = 0
    while ($Job.State -eq "Running") {
        $f = $frames[$i % 4]
        Write-Host ("`r    " + $f + "   " + $Msg + "   ") -NoNewline -ForegroundColor DarkYellow
        Start-Sleep -Milliseconds 150
        $i++
    }
    Write-Host ("`r" + (" " * ($Msg.Length + 12)) + "`r") -NoNewline
    Receive-Job $Job -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $Job -Force
}

# Attente avec compteur pour Ollama
function WaitOllama {
    param($MaxSeconds)
    for ($i = 0; $i -lt $MaxSeconds; $i += 2) {
        Start-Sleep 2
        Write-Host ("`r    En attente d'Ollama... " + $i + "s/" + $MaxSeconds + "s  ") -NoNewline -ForegroundColor DarkYellow
        try {
            Invoke-WebRequest "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
            Write-Host "`r    Ollama repond !                           " -ForegroundColor Green
            return $true
        } catch {}
    }
    Write-Host "`r    Timeout - Ollama ne repond pas.          " -ForegroundColor Red
    return $false
}

# En-tete
Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor White
Write-Host "    DataViz TNR  -  Demarrage automatique" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor White
if ($SkipDeps) {
    Write-Host "    Mode rapide (-SkipDeps) : installation ignoree" -ForegroundColor DarkGray
}
Write-Host ""

#  1. Python 
Step "Verification de Python 3.11+"
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $v = & $cmd --version 2>&1
        if ($v -match "Python (\d+\.\d+)" -and [Version]$Matches[1] -ge [Version]"3.11") {
            $python = $cmd; break
        }
    } catch {}
}
if (-not $python) {
    Err "Python 3.11+ introuvable. Telechargez-le : https://www.python.org/downloads/"
    Write-Host ""
    Read-Host "    Appuyez sur Entree pour quitter"
    exit 1
}
OK ($python + " detecte")

#  2. Venv 
Step "Environnement virtuel Python"
if (-not (Test-Path $PYTHON_VENV)) {
    Info "Creation du venv (premiere fois)..."
    $job = Start-Job { param($p,$v) & $p -m venv $v } -ArgumentList $python, $VENV_DIR
    Spin $job "Creation de l'environnement virtuel"
}
OK "Venv pret"

#  3. Dependances 
if (-not $SkipDeps) {
    Step "Installation des dependances Python"
    Write-Host ""
    Write-Host "    Packages qui vont etre installes :" -ForegroundColor DarkGray
    Write-Host "      - FastAPI / Uvicorn   : serveur web de l'application" -ForegroundColor DarkGray
    Write-Host "      - OpenCV              : traitement d'images (comparaison pixel a pixel)" -ForegroundColor DarkGray
    Write-Host "      - scikit-image        : calcul du score SSIM (similarite structurelle)" -ForegroundColor DarkGray
    Write-Host "      - Pillow              : lecture et conversion des formats d'images" -ForegroundColor DarkGray
    Write-Host "      - Playwright          : pilote de navigateur (capture d'ecran par URL)" -ForegroundColor DarkGray
    Write-Host "      - httpx               : appels HTTP vers Ollama (analyse IA)" -ForegroundColor DarkGray
    Write-Host "      - Jinja2              : moteur de templates HTML" -ForegroundColor DarkGray
    Write-Host ""
    Info "Mise a jour de pip..."
    & $PYTHON_VENV -m pip install --quiet --upgrade pip 2>&1 | Out-Null

    $req = Join-Path $SCRIPT_DIR "requirements.txt"
    $packages = Get-Content $req | Where-Object { $_ -match "\S" -and $_ -notmatch "^#" }
    $total = $packages.Count
    $failed = @()
    $failedErrors = @{}
    Write-Host ""
    for ($pi = 0; $pi -lt $total; $pi++) {
        $pkg  = $packages[$pi].Trim()
        $done = $pi + 1
        $pct  = [math]::Round($done * 20 / $total)
        $bar  = ("#" * $pct) + ("-" * (20 - $pct))
        Write-Host ("`r    [" + $bar + "] " + $done + "/" + $total + "  " + $pkg + "                    ") -NoNewline -ForegroundColor DarkYellow
        $out = & $PYTHON_VENV -m pip install --quiet $pkg 2>&1
        if ($LASTEXITCODE -ne 0) {
            $failed += $pkg
            $errLine = $out | Where-Object { $_ -match "ERROR|error|Could not|No matching" } | Select-Object -First 1
            if ($errLine) { $failedErrors[$pkg] = $errLine.ToString().Trim() }
        }
    }
    Write-Host ("`r    [####################] " + $total + "/" + $total + "  Termine !                         ") -ForegroundColor Green
    Write-Host ""
    if ($failed.Count -eq 0) { OK "Tous les packages sont installes" }
    else {
        Warn ("Packages en echec (" + $failed.Count + "/" + $total + ") :")
        foreach ($fp in $failed) {
            $reason = if ($failedErrors.ContainsKey($fp)) { " -> " + $failedErrors[$fp] } else { "" }
            Write-Host ("      - " + $fp + $reason) -ForegroundColor DarkGray
        }
        Write-Host ""
        Warn "Causes possibles : proxy d'entreprise, pas d'internet, antivirus bloquant pip."
        Info "Aide proxy : https://pip.pypa.io/en/stable/topics/configuration/#proxy"
        Info ("Commande reparation : & '" + $PYTHON_VENV + "' -m pip install " + ($failed -join " "))
    }
}

#  4. Playwright 
if (-not $SkipDeps) {
    Step "Installation du navigateur Chromium"
    # Verifier que playwright est bien installe avant de lancer chromium
    & $PYTHON_VENV -c "import playwright" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Warn "Le package 'playwright' n'est pas installe (echec en etape 3)."
        Warn "Chromium ne peut pas etre installe. Corrigez l'etape 3 et relancez start.bat."
    } else {
        Write-Host ""
        Write-Host "    A quoi ca sert :" -ForegroundColor DarkGray
        Write-Host "      Chromium est un navigateur headless (invisible) utilise par DataViz" -ForegroundColor DarkGray
        Write-Host "      pour photographier une page web a partir de son URL." -ForegroundColor DarkGray
        Write-Host "      Sans Chromium, seul le mode 'Comparer des fichiers' est disponible." -ForegroundColor DarkGray
        Write-Host ""
        Info "Telechargement de Chromium si absent (~170 Mo la premiere fois. Patientez.)"
        $pwOut = & $PYTHON_VENV -m playwright install chromium --with-deps 2>&1
        if ($LASTEXITCODE -eq 0) { OK "Chromium pret" }
        else {
            Warn "Installation partielle - la capture par URL peut ne pas fonctionner"
            $pwOut | Where-Object { $_ -match "error|Error|failed|Failed" } | Select-Object -Last 5 | ForEach-Object { Write-Host ("      " + $_) -ForegroundColor DarkGray }
        }
    }
}

#  5. Ollama 
Step "Verification d'Ollama (IA vision locale)"
$ollamaExe = $null
$candidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
    (Join-Path $env:ProgramFiles  "Ollama\ollama.exe")
)
$inPath = Get-Command ollama -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue
if ($inPath) { $candidates = @($inPath) + $candidates }
foreach ($p in $candidates) {
    if ($p -and (Test-Path $p -ErrorAction SilentlyContinue)) { $ollamaExe = $p; break }
}

if (-not $ollamaExe) {
    Warn "Ollama non installe."
    Info "Telechargement de l'installateur (~500 Mo). Patientez..."
    Info "  NE FERMEZ PAS CETTE FENETRE."
    $installer = Join-Path $env:TEMP "OllamaSetup.exe"
    try {
        $uri = "https://ollama.com/download/OllamaSetup.exe"
        # Taille totale via HEAD
        try {
            $head = [System.Net.WebRequest]::Create($uri)
            $head.Method = "HEAD"
            $headResp = $head.GetResponse()
            $totalBytes = $headResp.ContentLength
            $headResp.Close()
        } catch { $totalBytes = 0 }
        $totalMB = if ($totalBytes -gt 0) { [math]::Round($totalBytes / 1MB, 1) } else { "?" }

        # Telechargement avec progression
        $webReq  = [System.Net.WebRequest]::Create($uri)
        $webResp = $webReq.GetResponse()
        $stream  = $webResp.GetResponseStream()
        $fs      = [System.IO.File]::OpenWrite($installer)
        $buf     = New-Object byte[] 65536
        $downloaded = 0
        while (($read = $stream.Read($buf, 0, $buf.Length)) -gt 0) {
            $fs.Write($buf, 0, $read)
            $downloaded += $read
            $dlMB = [math]::Round($downloaded / 1MB, 1)
            if ($totalBytes -gt 0) {
                $pct = [math]::Round($downloaded * 100 / $totalBytes)
                $bar = "#" * [math]::Floor($pct / 5)
                $empty = "-" * (20 - $bar.Length)
                Write-Host ("`r    [" + $bar + $empty + "] " + $pct + "%  " + $dlMB + " Mo / " + $totalMB + " Mo   ") -NoNewline -ForegroundColor DarkYellow
            } else {
                Write-Host ("`r    Telechargement : " + $dlMB + " Mo...   ") -NoNewline -ForegroundColor DarkYellow
            }
        }
        $fs.Close(); $stream.Close(); $webResp.Close()
        Write-Host ("`r    Telechargement termine : " + [math]::Round($downloaded / 1MB, 1) + " Mo                              ") -ForegroundColor Green

        Info "Lancement de l'installateur Ollama..."
        Info "  L'installateur s'ouvre - cliquez sur 'Install' puis patientez jusqu'a sa fermeture."
        # Ne pas utiliser -Wait : l'installateur Ollama ne se ferme pas proprement.
        # On surveille plutot l'apparition de ollama.exe sur le disque (90s max).
        Start-Process $installer -ArgumentList "/S"
        $found = $false
        for ($i = 0; $i -lt 45; $i++) {
            Start-Sleep 2
            foreach ($p in $candidates) {
                if ($p -and (Test-Path $p -ErrorAction SilentlyContinue)) {
                    $ollamaExe = $p; $found = $true; break
                }
            }
            if ($found) { break }
            Write-Host ("`r    Installation en cours... " + ($i * 2) + "s  ") -NoNewline -ForegroundColor DarkYellow
        }
        Write-Host ("`r" + (" " * 50) + "`r") -NoNewline
        if ($ollamaExe) { OK ("Ollama installe : " + $ollamaExe) }
        else { Warn "Ollama installe - relancez start.bat pour finaliser." }
        # Nettoyage de l'installateur (~500 Mo)
        if (Test-Path $installer) {
            Remove-Item $installer -Force -ErrorAction SilentlyContinue
            Info "Installateur supprime (liberation de ~500 Mo)"
        }
    } catch {
        Warn "Impossible de telecharger Ollama : installez-le manuellement sur https://ollama.com"
        # Nettoyage de l'installateur en cas d'erreur
        if (Test-Path $installer) { Remove-Item $installer -Force -ErrorAction SilentlyContinue }
    }
} else {
    OK ("Ollama detecte : " + $ollamaExe)
}

#  6. Demarrage ollama serve 
Step "Demarrage du service Ollama"
$ollamaRunning = $false
if ($ollamaExe) {
    try {
        Invoke-WebRequest "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null
        $ollamaRunning = $true
        OK "Ollama est deja actif"
    } catch {}

    if (-not $ollamaRunning) {
        # Verifier si un process ollama est deja en cours de demarrage
        $ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
        if ($ollamaProc) {
            Info "Ollama est en cours de demarrage, attente..."
        } else {
            Info "Lancement d'Ollama en arriere-plan..."
            Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        }
        $ollamaRunning = WaitOllama -MaxSeconds 20
        if ($ollamaRunning) { OK "Ollama est demarre et repond" }
        else { Warn "Ollama lent a demarrer - nouvelle tentative en etape 8" }
    }
} else {
    Warn "Ollama absent - analyse IA desactivee"
}

#  7. Lancement DataViz 
Step "Lancement de DataViz"
Set-Location $SCRIPT_DIR
$uvicornExe = Join-Path $VENV_DIR "Scripts\uvicorn.exe"
$appArgs = "app:app --host 127.0.0.1 --port $APP_PORT"
if (Test-Path $uvicornExe) {
    Start-Process -FilePath $uvicornExe -ArgumentList $appArgs -WorkingDirectory $SCRIPT_DIR
} else {
    Start-Process -FilePath $PYTHON_VENV -ArgumentList ("-m uvicorn " + $appArgs) -WorkingDirectory $SCRIPT_DIR
}

Info "Attente du demarrage du serveur..."
Start-Sleep 3
Start-Process ("http://localhost:" + $APP_PORT)
OK ("DataViz ouvert sur http://localhost:" + $APP_PORT)
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ("    DataViz TNR est accessible sur http://localhost:" + $APP_PORT) -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""

#  8. Modele IA (en avant-plan, app deja lancee) 
if ($ollamaExe) {
    Step ("Modele IA : " + $OLLAMA_MODEL)

    # Si Ollama n'etait pas encore pret a l'etape 6, on retente ici
    if (-not $ollamaRunning) {
        Info "Nouvelle tentative de connexion a Ollama..."
        # Si le process ollama n'est plus en vie, le relancer
        $ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
        if (-not $ollamaProc) {
            Info "Relancement d'Ollama serve..."
            Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        }
        $ollamaRunning = WaitOllama -MaxSeconds 30
        if ($ollamaRunning) { OK "Ollama repond" }
        else {
            Warn "Ollama inaccessible apres 50s au total - modele non installe"
            Warn "Relancez start.bat pour retenter le telechargement du modele."
        }
    }
    if ($ollamaRunning) {
        try {
            $tags = (Invoke-WebRequest "http://localhost:11434/api/tags" -UseBasicParsing | ConvertFrom-Json)
            $modelPresent = $tags.models | Where-Object { $_.name -like ($OLLAMA_MODEL + "*") }
            if ($modelPresent) {
                OK ("Modele " + $OLLAMA_MODEL + " disponible - analyse IA active")
                Write-Host ""
                Write-Host "    Pour arreter DataViz, fermez sa fenetre de terminal." -ForegroundColor DarkGray
                Write-Host "    Prochain demarrage rapide : start.bat -SkipDeps" -ForegroundColor DarkGray
                Write-Host ""
                Read-Host "    Appuyez sur Entree pour fermer cette fenetre"
            } else {
                Warn ("Modele " + $OLLAMA_MODEL + " absent - lancement du telechargement en arriere-plan")
                Write-Host ""
                # Lancement non bloquant : une fenetre separee s'ouvre et telecharge le modele
                # L'application est deja utilisable pendant ce temps
                Start-Process $ollamaExe -ArgumentList ("pull " + $OLLAMA_MODEL) -WindowStyle Normal
                Write-Host ""
                Write-Host "    Une fenetre de telechargement vient de s'ouvrir." -ForegroundColor Cyan
                Write-Host ("    Modele : " + $OLLAMA_MODEL + "  (~5.5 Go pour minicpm-v, 5 a 30 min selon votre connexion)") -ForegroundColor Cyan
                Write-Host "    L'analyse IA sera disponible automatiquement une fois termine." -ForegroundColor Cyan
                Write-Host ""
                Write-Host "    Pour arreter DataViz, fermez sa fenetre de terminal." -ForegroundColor DarkGray
                Write-Host "    Prochain demarrage rapide : start.bat -SkipDeps" -ForegroundColor DarkGray
                Write-Host ""
                Read-Host "    Appuyez sur Entree pour fermer cette fenetre"
            }
        } catch {
            Warn ("Impossible de verifier le modele : " + $_)
            Write-Host ""
            Read-Host "    Appuyez sur Entree pour fermer cette fenetre"
        }
    } else {
        Write-Host "    Pour arreter DataViz, fermez sa fenetre de terminal." -ForegroundColor DarkGray
        Write-Host "    Prochain demarrage rapide : start.bat -SkipDeps" -ForegroundColor DarkGray
        Write-Host ""
        Read-Host "    Appuyez sur Entree pour fermer cette fenetre"
    }
}