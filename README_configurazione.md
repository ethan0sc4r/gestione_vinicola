# Configurazione Lettore Seriale - Applicazione Gestione Vinicola

## Come funziona la configurazione modificabile

L'applicazione ora utilizza un file di configurazione JSON esterno (`config_serial.json`) che rimane modificabile anche dopo la compilazione con PyInstaller.

## ✅ Funzionamento completamente OFFLINE

L'applicazione è stata configurata per funzionare **completamente offline** senza connessione internet:

- ✅ **Bootstrap CSS/JS**: File locali in `static/css/bootstrap.min.css` e `static/js/bootstrap.bundle.min.js`
- ✅ **Font Awesome**: File locale in `static/css/all.min.css`
- ✅ **jQuery**: File locale in `static/js/jquery-3.6.0.min.js`
- ✅ **Template**: Tutti i template HTML inclusi
- ✅ **Configurazione**: File JSON modificabile esternamente

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
├── app.exe                     (Eseguibile principale)
├── config_serial.json          (File di configurazione MODIFICABILE)
├── templates/                  (Template HTML di Flask)
│   ├── barcode_scanner.html
│   ├── dashboard.html
│   ├── login.html
│   └── [altri template...]
├── static/                     (File statici OFFLINE)
│   ├── css/
│   │   ├── bootstrap.min.css   (Bootstrap CSS offline)
│   │   └── all.min.css         (Font Awesome offline)
│   ├── js/
│   │   ├── bootstrap.bundle.min.js (Bootstrap JS offline)
│   │   └── jquery-3.6.0.min.js    (jQuery offline)
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

### Template non visualizzati correttamente senza internet
- ✅ **RISOLTO**: Tutti i file CSS/JS sono ora locali
- Verifica che i file in `dist/static/css/` e `dist/static/js/` esistano
- Esegui `verify_build.bat` per controllare tutti i file

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
- ✅ **RISOLTO**: Tutti i file sono ora locali
- Verifica che la cartella `dist/static/` esista con tutti i file CSS/JS
- Controlla che il logo e i suoni siano presenti

## Script di utilità

- **`build.bat`** - Compila l'applicazione includendo tutti i file necessari e verifica i file offline
- **`verify_build.bat`** - Verifica che tutti i file siano stati inclusi correttamente (include controllo file offline)

## Backup della configurazione

Si consiglia di fare una copia di backup del file `config_serial.json` prima di apportare modifiche:

```cmd
copy config_serial.json config_serial_backup.json
```

## Note tecniche

- PyInstaller include automaticamente tutte le dipendenze Python
- I template HTML e file statici sono inclusi manualmente tramite `--add-data`
- Il file di configurazione JSON rimane sempre esterno e modificabile
- **Tutti i file CSS/JS sono locali - nessuna connessione internet richiesta**
- Bootstrap 5.2.3, Font Awesome e jQuery funzionano completamente offline

## File offline inclusi

| File | Descrizione | Percorso |
|------|-------------|----------|
| `bootstrap.min.css` | Bootstrap CSS completo | `static/css/bootstrap.min.css` |
| `all.min.css` | Font Awesome completo | `static/css/all.min.css` |
| `bootstrap.bundle.min.js` | Bootstrap JS + Popper | `static/js/bootstrap.bundle.min.js` |
| `jquery-3.6.0.min.js` | jQuery completo | `static/js/jquery-3.6.0.min.js` |

## 🎯 Vantaggi della versione offline

- ✅ **Nessuna dipendenza da internet**
- ✅ **Velocità di caricamento superiore**
- ✅ **Funziona in ambienti isolati**
- ✅ **Affidabilità totale**
- ✅ **Configurazione sempre modificabile** 