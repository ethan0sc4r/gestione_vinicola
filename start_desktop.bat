@echo off
echo Installazione dipendenze Gestione Vinicola Desktop...

REM Installa le dipendenze base se non già installate
pip install -r requirements.txt

REM Installa le dipendenze aggiuntive per il launcher desktop
pip install -r requirements_launcher.txt

echo.
echo Avvio Gestione Vinicola Desktop...
echo L'applicazione si aprirà automaticamente nel browser.
echo Cerca l'icona nella system tray per gestire l'applicazione.
echo.

REM Avvia il launcher desktop
python launcher.py

pause