@echo off
cd /d "%~dp0"
echo Starting VisionForge...
start "" ".venv\Scripts\pythonw.exe" "ui\launcher.py"
