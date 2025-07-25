# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file per Gestione Vinicola - Versione Console

import sys
from pathlib import Path

# Percorso base del progetto
base_path = Path('.')

a = Analysis(
    ['app.py'],
    pathex=[str(base_path)],
    binaries=[],
    datas=[
        # File di configurazione
        ('config_serial.json', '.'),
        ('config_serial_windows.json', '.'),
        
        # Templates e static files
        ('templates', 'templates'),
        ('static', 'static'),
        
        # File di requirements (opzionale, per riferimento)
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        # Dipendenze Flask base
        'flask',
        'flask_sqlalchemy', 
        'flask_login',
        'sqlalchemy',
        'werkzeug',
        
        # Dipendenze per serial communication
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        
        # Database
        'sqlite3',
        
        # Altri moduli necessari
        'json',
        'threading',
        'hashlib',
        'decimal',
        'datetime',
        'logging',
        'time',
        
        # Per emulazione tastiera
        'keyboard',
        'pynput',
        'pynput.keyboard',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Esclude pacchetti non necessari
        'matplotlib',
        'tkinter',
        'pystray',
        'PIL',
        # Escludi SocketIO problematico
        'flask_socketio',
        'socketio',
        'engineio',
        'eventlet',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Gestione_Vinicola_Console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Mantieni console per versione tradizionale
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
