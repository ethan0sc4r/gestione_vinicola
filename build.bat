@echo off
echo Compilazione dell'applicazione Gestione Vinicola...
echo.

REM Verifica che il file di configurazione esista
if not exist "config_serial.json" (
    echo Creazione file di configurazione predefinito...
    copy "config_serial_windows.json" "config_serial.json"
)

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
    echo Scaricare jQuery e salvarlo come static\js\socket.io.js
    pause
    exit /b 1
)
echo [OK] Tutti i file offline sono presenti

REM Pulisce la cartella dist precedente per evitare conflitti
echo Pulizia cartella dist precedente...
if exist "dist" (
    rmdir /s /q "dist"
)

REM Compila l'applicazione usando il file .spec
echo Compilazione in corso...
pyinstaller app.spec

REM Verifica che la compilazione sia riuscita
if not exist "dist\Gestione_Vinicola_Console.exe" (
    echo ERRORE: Compilazione fallita!
    pause
    exit /b 1
)

REM Copia il file di configurazione nella cartella dist (per sovrascrivere quello incluso)
echo Copia file di configurazione modificabile...
copy "config_serial.json" "dist\config_serial.json"

echo.
echo Compilazione completata con successo!
echo.
echo File inclusi:
echo - Eseguibile: dist\app.exe
echo - Configurazione: dist\config_serial.json
echo - Templates: dist\templates\
echo - File statici offline: dist\static\
echo   - Bootstrap CSS: dist\static\css\bootstrap.min.css
echo   - Font Awesome CSS: dist\static\css\all.min.css
echo   - Bootstrap JS: dist\static\js\bootstrap.bundle.min.js
echo   - jQuery: dist\static\js\jquery-3.6.0.min.js
echo   - Logo: dist\static\logo.png
echo   - Suoni: dist\static\sounds\
echo.
echo L'applicazione funziona completamente offline!
echo Il file di configurazione config_serial.json è modificabile nella cartella dist\
echo.
pause 