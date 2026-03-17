@echo off
chcp 65001 >nul 2>&1
echo.
echo  DataViz TNR -- Creation du ZIP de distribution...
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_zip.ps1" %*
