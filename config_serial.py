# Configurazione del lettore di codici a barre seriale
# Inserire questo file come "config_serial.py" nella cartella principale del progetto

"""
Modulo di configurazione per il lettore di codici a barre seriale.
"""

# Impostazioni porta seriale
SERIAL_PORT = {
    # Porta seriale - modificare in base alla configurazione del sistema
    'port': '/dev/ttyUSB0',  # Linux (tipicamente /dev/ttyUSB0 o /dev/ttyACM0)
    # 'port': 'COM1',        # Windows (tipicamente COM1, COM2, ecc.)
    
    # Parametri di comunicazione - modificare in base al lettore utilizzato
    'baudrate': 9600,        # Velocità di comunicazione (tipicamente 9600 baud)
    'timeout': 1,            # Timeout in secondi
    'bytesize': 8,           # Dimensione dei dati (tipicamente 8 bit)
    'parity': 'N',           # Parità: N(none), E(even), O(odd), M(mark), S(space)
    'stopbits': 1,           # Bit di stop (tipicamente 1)
    
    # Impostazioni di decodifica
    'encoding': 'utf-8',     # Codifica dei caratteri
    'errors': 'replace',     # Gestione errori di decodifica
    
    # Caratteri terminatori - modificare in base al lettore
    'terminators': ['\r', '\n', '\r\n'],  # Caratteri che indicano la fine del codice
    
    # Impostazioni avanzate
    'rtscts': False,         # Controllo di flusso hardware RTS/CTS
    'dsrdtr': False,         # Controllo di flusso hardware DSR/DTR
    'xonxoff': False,        # Controllo di flusso software XON/XOFF
}

# Impostazioni per la gestione del lettore
READER_SETTINGS = {
    # Intervallo di polling per la lettura (secondi)
    'polling_interval': 0.1,
    
    # Dimensione massima del buffer di lettura
    'read_buffer_size': 1024,
    
    # Numero massimo di codici da memorizzare nella cronologia
    'max_history_size': 5,
    
    # Tempo minimo tra due letture consecutive dello stesso codice (secondi)
    'duplicate_timeout': 3.0,
    
    # Prefisso/suffisso da ignorare nel codice letto (alcuni lettori aggiungono caratteri)
    'ignore_prefix': '',
    'ignore_suffix': '',
    
    # Trasformazioni da applicare al codice letto
    'uppercase': False,      # Converti in maiuscolo
    'lowercase': False,      # Converti in minuscolo
    'strip_spaces': True,    # Rimuovi spazi iniziali e finali
}

# Configurazione del sistema di logging
LOGGING = {
    'enabled': True,         # Abilita il logging degli eventi del lettore
    'log_file': 'scanner.log',  # File di log
    'log_level': 'INFO',     # Livello di logging: DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # Eventi da registrare
    'log_events': {
        'connection': True,      # Connessione/disconnessione
        'read_success': True,    # Lettura codice avvenuta con successo
        'read_error': True,      # Errori di lettura
        'employee_found': True,  # Dipendente trovato
        'employee_not_found': True,  # Dipendente non trovato
    }
}

# Procedure di recupero in caso di errore
ERROR_RECOVERY = {
    'auto_reconnect': True,      # Tenta di riconnettere automaticamente in caso di disconnessione
    'max_reconnect_attempts': 5,  # Numero massimo di tentativi di riconnessione
    'reconnect_delay': 3.0,      # Attesa tra i tentativi (secondi)
    'reset_on_error': True,      # Resetta il lettore in caso di errori persistenti
}

# Funzione per caricare la configurazione
def load_config():
    """Carica e restituisce la configurazione del lettore seriale."""
    config = {
        'serial': SERIAL_PORT,
        'reader': READER_SETTINGS,
        'logging': LOGGING,
        'error_recovery': ERROR_RECOVERY
    }
    return config

# Istruzioni per l'utilizzo
"""
Per utilizzare questa configurazione:

1. Salva questo file come 'config_serial.py' nella cartella principale del progetto
2. Nel file app.py, importa la configurazione:
   
   from config_serial import load_config
   
   # Ottieni la configurazione
   serial_config = load_config()
   
   # Configura il lettore usando i parametri
   port = serial_config['serial']['port']
   baudrate = serial_config['serial']['baudrate']
   # ...etc
   
3. Assicurati di avere il pacchetto pyserial installato:
   
   pip install pyserial
   
4. Modifica i parametri in questo file in base alle specifiche del tuo lettore di codici a barre
"""