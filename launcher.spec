# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file per Gestione Vinicola Desktop Launcher (senza SocketIO)

import sys
from pathlib import Path

# Percorso base del progetto
base_path = Path('.')

a = Analysis(
    ['launcher.py'],
    pathex=[str(base_path)],
    binaries=[],
    datas=[
        # File di configurazione
        ('config_serial.json', '.'),
        ('config_serial_windows.json', '.'),
        
        # Templates e static files per Flask
        ('templates', 'templates'),
        ('static', 'static'),
        
        # File Python dell'app Flask (necessario per il subprocess)
        ('app.py', '.'),
        
        # File di requirements (opzionale, per riferimento)
        ('requirements.txt', '.'),
        ('requirements_launcher.txt', '.'),
    ],
    hiddenimports=[
        # Dipendenze Flask base (senza SocketIO)
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'sqlalchemy',
        'werkzeug',
        
        # Dipendenze per serial communication
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        
        # Dipendenze tray icon
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        
        # Windows API
        'win32gui',
        'win32con',
        'win32api',
        
        # Database
        'sqlite3',
        
        # Per emulazione tastiera
        'pynput',
        'pynput.keyboard',
        
        # Altri moduli che potrebbero essere necessari
        'json',
        'threading',
        'subprocess',
        'webbrowser',
        'tkinter',
        'tkinter.messagebox',
        'hashlib',
        'decimal',
        'datetime',
        'logging',
        'time',
        'pytz',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Esclude pacchetti non necessari per ridurre dimensioni
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'jupyter',
        'notebook',
        'IPython',
        # Escludi SocketIO problematico
        'flask_socketio',
        'socketio',
        'engineio',
        'eventlet',
        'dns',
        'dns.resolver',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Gestione_Vinicola_Desktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Nascondi console per applicazione desktop
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Aggiungi un file .ico se disponibile
    version=None,  # Aggiungi informazioni versione se necessario
)