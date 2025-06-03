# Configurazione Lettore Seriale - Applicazione Gestione Vinicola

## Come funziona la configurazione modificabile

L'applicazione ora utilizza un file di configurazione JSON esterno (`config_serial.json`) che rimane modificabile anche dopo la compilazione con PyInstaller.

## Compilazione dell'applicazione

### Metodo 1: Script automatico (Windows) - CONSIGLIATO
```cmd
build.bat
```

### Metodo 2: Comando manuale
```cmd
pyinstaller app.spec
copy config_serial.json dist\
```

### Metodo 3: Comando PyInstaller diretto
```cmd
pyinstaller --add-data "config_serial.json;." --add-data "templates;templates" --add-data "static;static" app.py
```

### Verifica della compilazione
Dopo la compilazione, esegui:
```cmd
verify_build.bat
```

## Struttura dei file dopo la compilazione

```
dist/
├── app.exe                  (Eseguibile principale)
├── config_serial.json       (File di configurazione MODIFICABILE)
├── templates/               (Template HTML di Flask)
│   ├── barcode_scanner.html
│   ├── dashboard.html
│   ├── login.html
│   └── [altri template...]
├── static/                  (File statici: CSS, JS, immagini)
│   ├── logo.png
│   └── sounds/
└── [altri file di PyInstaller]
```

## Modifica della configurazione

### 1. Aprire il file config_serial.json
Il file si trova nella stessa cartella dell'eseguibile (`dist/config_serial.json`)

### 2. Parametri principali da modificare

**Porta seriale (Windows):**
```json
{
    "serial": {
        "port": "COM1"    // Cambia in COM2, COM3, etc.
    }
}
```

**Porta seriale (Linux):**
```json
{
    "serial": {
        "port": "/dev/ttyUSB0"    // Cambia in /dev/ttyUSB1, /dev/ttyACM0, etc.
    }
}
```

**Velocità di comunicazione:**
```json
{
    "serial": {
        "baudrate": 9600    // Cambia in 115200, 38400, etc.
    }
}
```

### 3. Applicare le modifiche
1. Salva il file `config_serial.json`
2. Riavvia l'applicazione
3. Le nuove impostazioni saranno caricate automaticamente

## Esempi di configurazione

### Lettore USB standard
```json
{
    "serial": {
        "port": "COM3",
        "baudrate": 9600,
        "timeout": 1
    }
}
```

### Lettore ad alta velocità
```json
{
    "serial": {
        "port": "COM1",
        "baudrate": 115200,
        "timeout": 0.5
    }
}
```

## Risoluzione problemi

### Template non trovati (TemplateNotFound)
- Verifica che la cartella `dist/templates/` esista e contenga i file HTML
- Esegui `verify_build.bat` per controllare i file inclusi
- Ricompila con `build.bat` se mancano file

### Il file di configurazione non viene trovato
- Assicurati che `config_serial.json` sia nella stessa cartella dell'eseguibile
- Se non esiste, l'applicazione ne creerà uno automaticamente

### Le modifiche non vengono applicate
- Riavvia completamente l'applicazione
- Verifica che il file JSON sia sintatticamente corretto

### Errori di connessione seriale
1. Verifica che la porta specificata esista
2. Controlla che nessun altro programma stia usando la porta
3. Prova velocità di comunicazione diverse (9600, 19200, 38400, 115200)

### File statici non caricati
- Verifica che la cartella `dist/static/` esista
- Controlla che il logo e i suoni siano presenti

## Script di utilità

- **`build.bat`** - Compila l'applicazione includendo tutti i file necessari
- **`verify_build.bat`** - Verifica che tutti i file siano stati inclusi correttamente

## Backup della configurazione

Si consiglia di fare una copia di backup del file `config_serial.json` prima di apportare modifiche:

```cmd
copy config_serial.json config_serial_backup.json
```

## Note tecniche

- PyInstaller include automaticamente tutte le dipendenze Python
- I template HTML e file statici sono inclusi manualmente tramite `--add-data`
- Il file di configurazione JSON rimane sempre esterno e modificabile 