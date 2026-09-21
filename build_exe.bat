@echo off
rem Rebuild Perievodchik.exe (single file). Requires: pip install pyinstaller
cd /d "%~dp0"

python -m PyInstaller --noconfirm --onefile --windowed --name OfflineTranslator ^
  --collect-all ctranslate2 ^
  --collect-all minisbd ^
  --collect-all pystray ^
  --collect-all customtkinter ^
  --hidden-import pystray.win32 ^
  --exclude-module torch ^
  --exclude-module spacy ^
  --exclude-module sklearn ^
  --exclude-module pandas ^
  --exclude-module matplotlib ^
  --exclude-module IPython ^
  app.py

if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)

echo BUILD OK - dist\OfflineTranslator.exe
