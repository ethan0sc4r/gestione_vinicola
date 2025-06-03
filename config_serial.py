# Configurazione del lettore di codici a barre seriale
# Inserire questo file come "config_serial.py" nella cartella principale del progetto

"""
Modulo di configurazione per il lettore di codici a barre seriale.
Carica la configurazione dal file config_serial.json esterno.
"""

import json
import os
import sys

def get_config_path():
    """
    Determina il percorso del file di configurazione.
    Se l'app è compilata con PyInstaller, cerca nella cartella dell'eseguibile.
    Altrimenti cerca nella cartella dello script.
    """
    if getattr(sys, 'frozen', False):
        # Se l'applicazione è compilata con PyInstaller
        application_path = os.path.dirname(sys.executable)
    else:
        # Se l'applicazione è in modalità sviluppo
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(application_path, 'config_serial.json')

def create_default_config():
    """Crea un file di configurazione predefinito se non esiste."""
    default_config = {
        "serial": {
            "port": "/dev/ttyUSB0",
            "baudrate": 9600,
            "timeout": 1,
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
            "encoding": "utf-8",
            "errors": "replace",
            "terminators": ["\r", "\n", "\r\n"],
            "rtscts": False,
            "dsrdtr": False,
            "xonxoff": False
        },
        "reader": {
            "polling_interval": 0.1,
            "read_buffer_size": 1024,
            "max_history_size": 5,
            "duplicate_timeout": 3.0,
            "ignore_prefix": "",
            "ignore_suffix": "",
            "uppercase": False,
            "lowercase": False,
            "strip_spaces": True
        },
        "logging": {
            "enabled": True,
            "log_file": "scanner.log",
            "log_level": "INFO",
            "log_events": {
                "connection": True,
                "read_success": True,
                "read_error": True,
                "employee_found": True,
                "employee_not_found": True
            }
        },
        "error_recovery": {
            "auto_reconnect": True,
            "max_reconnect_attempts": 5,
            "reconnect_delay": 3.0,
            "reset_on_error": True
        }
    }
    return default_config

def load_config():
    """Carica e restituisce la configurazione del lettore seriale dal file JSON."""
    config_path = get_config_path()
    
    try:
        # Prova a caricare il file di configurazione
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"Configurazione caricata da: {config_path}")
        else:
            # Se il file non esiste, crea quello predefinito
            config = create_default_config()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"File di configurazione creato: {config_path}")
            
    except Exception as e:
        print(f"Errore nel caricamento della configurazione: {e}")
        print("Uso configurazione predefinita")
        config = create_default_config()
    
    return config

def save_config(config):
    """Salva la configurazione nel file JSON."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"Configurazione salvata in: {config_path}")
        return True
    except Exception as e:
        print(f"Errore nel salvataggio della configurazione: {e}")
        return False

# Backward compatibility - mantiene le variabili originali per compatibilità
def _load_legacy_vars():
    """Carica le variabili per compatibilità con il codice esistente."""
    config = load_config()
    
    global SERIAL_PORT, READER_SETTINGS, LOGGING, ERROR_RECOVERY
    SERIAL_PORT = config['serial']
    READER_SETTINGS = config['reader']
    LOGGING = config['logging']
    ERROR_RECOVERY = config['error_recovery']

# Carica le variabili all'importazione del modulo
_load_legacy_vars()

# Istruzioni per l'utilizzo
"""
Per utilizzare questa configurazione con PyInstaller:

1. Il file config_serial.json verrà cercato nella stessa cartella dell'eseguibile
2. Se non esiste, verrà creato automaticamente con i valori predefiniti
3. Puoi modificare il file JSON direttamente per cambiare le impostazioni
4. Le modifiche saranno rilevate automaticamente al riavvio dell'applicazione

Per la compilazione con PyInstaller:
1. Aggiungi questo al tuo file .spec o usa il comando:
   
   pyinstaller --add-data "config_serial.json;." app.py
   
   Oppure su Linux/Mac:
   pyinstaller --add-data "config_serial.json:." app.py

2. Il file JSON sarà copiato insieme all'eseguibile e rimarrà modificabile

Uso nel codice:
   from config_serial import load_config
   
   # Ottieni la configurazione sempre aggiornata
   config = load_config()
   
   # Oppure usa le variabili globali (compatibilità)
   from config_serial import SERIAL_PORT, READER_SETTINGS
"""