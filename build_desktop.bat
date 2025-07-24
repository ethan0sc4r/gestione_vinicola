@echo off
echo Compilazione dell'applicazione Gestione Vinicola Desktop...
echo.

REM Verifica che il file di configurazione esista
if not exist "config_serial.json" (
    echo Creazione file di configurazione predefinito...
    copy "config_serial_windows.json" "config_serial.json"
)

REM Installa dipendenze necessarie per la compilazione
echo Installazione dipendenze necessarie...
pip install pyinstaller
pip install -r requirements.txt
pip install -r requirements_launcher.txt

REM Verifica che tutti i file necessari per offline esistano
echo Verifica file offline necessari...
if not exist "static\css\bootstrap.min.css" (
    echo ERRORE: File bootstrap.min.css non trovato in static\css\
    echo Scaricare Bootstrap CSS e salvarlo come static\css\bootstrap.min.css
    pause
    exit /b 1
)

if not exist "static\css\all.min.css" (
    echo ERRORE: File all.min.css di Font Awesome non trovato in static\css\
    echo Scaricare Font Awesome CSS e salvarlo come static\css\all.min.css
    pause
    exit /b 1
)

if not exist "static\js\bootstrap.bundle.min.js" (
    echo ERRORE: File bootstrap.bundle.min.js non trovato in static\js\
    echo Scaricare Bootstrap JS e salvarlo come static\js\bootstrap.bundle.min.js
    pause
    exit /b 1
)

if not exist "static\js\jquery-3.6.0.min.js" (
    echo ERRORE: File jquery-3.6.0.min.js non trovato in static\js\
    echo Scaricare jQuery e salvarlo come static\js\jquery-3.6.0.min.js
    pause
    exit /b 1
)

if not exist "static\js\socket.io.js" (
    echo ERRORE: File socket.io.js non trovato in static\js\
    echo Scaricare Socket.IO client e salvarlo come static\js\socket.io.js
    pause
    exit /b 1
)
echo [OK] Tutti i file offline sono presenti

REM Pulisce la cartella dist precedente per evitare conflitti
echo Pulizia cartella dist precedente...
if exist "dist" (
    rmdir /s /q "dist"
)

REM Compila ENTRAMBE le versioni
echo.
echo Compilazione versione DESKTOP (con tray icon)...
pyinstaller launcher.spec

if not exist "dist\Gestione_Vinicola_Desktop.exe" (
    echo ERRORE: Compilazione versione desktop fallita!
    pause
    exit /b 1
)

echo.
echo Compilazione versione CONSOLE (tradizionale)...
pyinstaller app.spec

if not exist "dist\Gestione_Vinicola_Console.exe" (
    echo ERRORE: Compilazione versione console fallita!
    pause
    exit /b 1
)

REM Copia il file di configurazione nella cartella dist (per sovrascrivere quello incluso)
echo Copia file di configurazione modificabile...
copy "config_serial.json" "dist\config_serial.json"

REM Crea file di istruzioni
echo Creazione file istruzioni...
echo. > "dist\ISTRUZIONI.txt"
echo GESTIONE VINICOLA - GUIDA RAPIDA >> "dist\ISTRUZIONI.txt"
echo ================================= >> "dist\ISTRUZIONI.txt"
echo. >> "dist\ISTRUZIONI.txt"
echo DUE VERSIONI DISPONIBILI: >> "dist\ISTRUZIONI.txt"
echo. >> "dist\ISTRUZIONI.txt"
echo 1. VERSIONE DESKTOP (CONSIGLIATA): >> "dist\ISTRUZIONI.txt"
echo    - File: Gestione_Vinicola_Desktop.exe >> "dist\ISTRUZIONI.txt"
echo    - Console nascosta >> "dist\ISTRUZIONI.txt"
echo    - Icona nella tray >> "dist\ISTRUZIONI.txt"
echo    - Browser si apre automaticamente >> "dist\ISTRUZIONI.txt"
echo    - Menu con tasto destro sulla tray icon >> "dist\ISTRUZIONI.txt"
echo. >> "dist\ISTRUZIONI.txt"
echo 2. VERSIONE CONSOLE (TRADIZIONALE): >> "dist\ISTRUZIONI.txt"
echo    - File: Gestione_Vinicola_Console.exe >> "dist\ISTRUZIONI.txt"
echo    - Console visibile >> "dist\ISTRUZIONI.txt"
echo    - Funziona come sempre >> "dist\ISTRUZIONI.txt"
echo. >> "dist\ISTRUZIONI.txt"
echo CONFIGURAZIONE: >> "dist\ISTRUZIONI.txt"
echo - Modifica config_serial.json per impostare la porta seriale >> "dist\ISTRUZIONI.txt"
echo. >> "dist\ISTRUZIONI.txt"
echo FUNZIONA COMPLETAMENTE OFFLINE! >> "dist\ISTRUZIONI.txt"

echo.
echo ======================================
echo COMPILAZIONE COMPLETATA CON SUCCESSO!
echo ======================================
echo.
echo VERSIONI CREATE:
echo [DESKTOP]  dist\Gestione_Vinicola_Desktop.exe  (CON TRAY ICON)
echo [CONSOLE]  dist\Gestione_Vinicola_Console.exe  (TRADIZIONALE)
echo.
echo File inclusi:
echo - Configurazione: dist\config_serial.json
echo - Templates: dist\templates\
echo - File statici offline: dist\static\
echo   - Bootstrap CSS: dist\static\css\bootstrap.min.css
echo   - Font Awesome CSS: dist\static\css\all.min.css
echo   - Bootstrap JS: dist\static\js\bootstrap.bundle.min.js
echo   - jQuery: dist\static\js\jquery-3.6.0.min.js
echo   - Socket.IO: dist\static\js\socket.io.js
echo   - Logo: dist\static\logo.png
echo   - Suoni: dist\static\sounds\
echo - Istruzioni: dist\ISTRUZIONI.txt
echo.
echo L'applicazione funziona completamente OFFLINE!
echo Il file di configurazione config_serial.json e' modificabile nella cartella dist\
echo.
echo VERSIONE DESKTOP: Doppio click su Gestione_Vinicola_Desktop.exe
echo VERSIONE CONSOLE: Doppio click su Gestione_Vinicola_Console.exe
echo.
pause