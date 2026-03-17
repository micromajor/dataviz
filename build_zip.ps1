$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$VERSION    = "1.0"
$DATE       = Get-Date -Format "yyyyMMdd"
$ZIP_NAME   = "DataViz-TNR_v" + $VERSION + "_" + $DATE + ".zip"
$ZIP_PATH   = Join-Path $SCRIPT_DIR $ZIP_NAME
$TEMP_DIR   = Join-Path $env:TEMP ("dataviz_dist_" + $DATE)

$INCLUDE = @("app.py","requirements.txt","README.md","start.bat","start.ps1","static","templates","docs")

Write-Host ""
Write-Host "DataViz TNR - Creation du ZIP de distribution" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $TEMP_DIR) { Remove-Item $TEMP_DIR -Recurse -Force }
New-Item -ItemType Directory -Path $TEMP_DIR | Out-Null

foreach ($item in $INCLUDE) {
    $src = Join-Path $SCRIPT_DIR $item
    if (Test-Path $src) {
        Copy-Item $src -Destination $TEMP_DIR -Recurse -Force
        Write-Host ("  + " + $item) -ForegroundColor Gray
    } else {
        Write-Host ("  ! " + $item + " introuvable, ignore") -ForegroundColor Yellow
    }
}

if (Test-Path $ZIP_PATH) { Remove-Item $ZIP_PATH -Force }
Compress-Archive -Path ("$TEMP_DIR\*") -DestinationPath $ZIP_PATH -CompressionLevel Optimal
Remove-Item $TEMP_DIR -Recurse -Force

$size = [math]::Round((Get-Item $ZIP_PATH).Length / 1KB)
Write-Host ""
Write-Host ("  ZIP cree : " + $ZIP_NAME + " (" + $size + " Ko)") -ForegroundColor Green
Write-Host ("  Emplacement : " + $ZIP_PATH) -ForegroundColor White
Write-Host ""
Write-Host "  Contenu : app.py, requirements.txt, README.md, start.bat, start.ps1, static/, templates/, docs/" -ForegroundColor DarkGray
Write-Host "  Exclus  : .venv/, uploads/, results/, captures/, history/, __pycache__/" -ForegroundColor DarkGray
Write-Host ""