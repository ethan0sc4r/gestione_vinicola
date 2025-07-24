# Gestione Vinicola - Versione Desktop

## Avvio Rapido

1. **Doppio click su `start_desktop.bat`**
   - Installa automaticamente le dipendenze necessarie
   - Avvia l'applicazione in modalità desktop
   - Apre automaticamente il browser
   - Nasconde la console

2. **L'applicazione si avvierà con:**
   - Server Flask in background (porta automatica)
   - Tray icon nella barra di sistema
   - Browser che si apre automaticamente
   - Console nascosta

## Gestione tramite Tray Icon

Cerca l'icona **"V"** nella system tray (barra delle applicazioni). 

**Click destro sull'icona per vedere il menu:**
- **Apri Browser**: Riapre il browser alla pagina dell'applicazione
- **Mostra Console**: Mostra la finestra della console per debug
- **Riavvia**: Riavvia completamente l'applicazione
- **Chiudi Applicazione**: Termina l'applicazione

## Installazione Manuale Dipendenze

Se il file batch non funziona, esegui manualmente:

```bash
pip install -r requirements.txt
pip install -r requirements_launcher.txt
```

## Avvio Manuale

```bash
python launcher.py
```

## Caratteristiche Desktop

- ✅ **Apertura automatica del browser** all'avvio
- ✅ **Console nascosta** per un aspetto più professionale
- ✅ **Tray icon** per controllo rapido
- ✅ **Menu contestuale** con tasto destro
- ✅ **Riavvio rapido** dell'applicazione
- ✅ **Gestione automatica delle porte** (evita conflitti)
- ✅ **Notifiche di sistema** per stato applicazione

## Risoluzione Problemi

### Errore "Moduli GUI non installati"
```bash
pip install pystray pillow pywin32
```

### Porta già in uso
Il launcher trova automaticamente porte libere. Se continui ad avere problemi:
1. Chiudi tutte le istanze dell'applicazione
2. Riavvia il computer
3. Lancia nuovamente `start_desktop.bat`

### Console non si nasconde
Assicurati di avere installato `pywin32`:
```bash
pip install pywin32
```

### Tray icon non appare
Su alcuni sistemi Windows potrebbe essere necessario:
1. Controllare le impostazioni delle notifiche
2. Verificare che l'applicazione abbia i permessi necessari

## Note Tecniche

- **Flask Server**: Si avvia su porta automatica (default 5000+)
- **SocketIO**: Utilizza porta separata per WebSocket
- **Tray Icon**: Libreria `pystray` con icona personalizzata
- **Browser**: Utilizza il browser predefinito del sistema
- **Console**: Gestita tramite API Windows (`pywin32`)

## Supporto

Per problemi o domande, controlla:
1. I log nella console (menu "Mostra Console")
2. Il file `vinicola.log` nella cartella dell'applicazione
3. La compatibilità delle dipendenze Python