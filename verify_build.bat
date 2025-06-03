@echo off
echo Verifica della compilazione...
echo.

REM Verifica che la cartella dist esista
if not exist "dist" (
    echo ERRORE: Cartella dist non trovata. Eseguire prima build.bat
    pause
    exit /b 1
)

echo Verifica file nella cartella dist:
echo.

REM Verifica eseguibile
if exist "dist\app.exe" (
    echo [OK] app.exe trovato
) else (
    echo [ERRORE] app.exe non trovato
)

REM Verifica configurazione
if exist "dist\config_serial.json" (
    echo [OK] config_serial.json trovato
) else (
    echo [ERRORE] config_serial.json non trovato
)

REM Verifica cartella templates
if exist "dist\templates" (
    echo [OK] Cartella templates trovata
    dir /b "dist\templates" | find /c /v "" > temp_count.txt
    set /p template_count=<temp_count.txt
    del temp_count.txt
    echo     - Numero di template: %template_count%
) else (
    echo [ERRORE] Cartella templates non trovata
)

REM Verifica cartella static
if exist "dist\static" (
    echo [OK] Cartella static trovata
) else (
    echo [ERRORE] Cartella static non trovata
)

REM Verifica file template specifico che stava causando errore
if exist "dist\templates\barcode_scanner.html" (
    echo [OK] barcode_scanner.html trovato
) else (
    echo [ERRORE] barcode_scanner.html non trovato
)

echo.
echo === Verifica file offline ===

REM Verifica Bootstrap CSS
if exist "dist\static\css\bootstrap.min.css" (
    echo [OK] Bootstrap CSS trovato (dist\static\css\bootstrap.min.css)
) else (
    echo [ERRORE] Bootstrap CSS non trovato
)

REM Verifica Font Awesome CSS
if exist "dist\static\css\all.min.css" (
    echo [OK] Font Awesome CSS trovato (dist\static\css\all.min.css)
) else (
    echo [ERRORE] Font Awesome CSS non trovato
)

REM Verifica Bootstrap JS
if exist "dist\static\js\bootstrap.bundle.min.js" (
    echo [OK] Bootstrap JS trovato (dist\static\js\bootstrap.bundle.min.js)
) else (
    echo [ERRORE] Bootstrap JS non trovato
)

REM Verifica jQuery
if exist "dist\static\js\jquery-3.6.0.min.js" (
    echo [OK] jQuery trovato (dist\static\js\jquery-3.6.0.min.js)
) else (
    echo [ERRORE] jQuery non trovato
)

REM Verifica logo
if exist "dist\static\logo.png" (
    echo [OK] Logo trovato (dist\static\logo.png)
) else (
    echo [AVVISO] Logo non trovato
)

REM Verifica cartella suoni
if exist "dist\static\sounds" (
    echo [OK] Cartella suoni trovata (dist\static\sounds\)
) else (
    echo [AVVISO] Cartella suoni non trovata
)

echo.
echo === Risultato ===
echo Verifica completata!
echo Se tutti i file [OK] sono presenti, l'applicazione funzionerà offline.
echo.
pause 