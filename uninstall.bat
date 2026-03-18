@echo off
chcp 65001 >nul 2>&1
echo.
echo  DataViz TNR -- Desinstallation...
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  Une erreur s'est produite. Consultez le message ci-dessus.
    pause
)
