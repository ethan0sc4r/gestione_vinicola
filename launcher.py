#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Launcher per Applicazione Gestione Vinicola
-------------------------------------------
Launcher desktop con system tray, apertura automatica browser e gestione console.
"""

import sys
import os
import time
import threading
import webbrowser
import subprocess
import socket
import json
from pathlib import Path

# Importazioni per GUI e system tray
try:
    import tkinter as tk
    from tkinter import messagebox
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except ImportError as e:
    print(f"Errore: Moduli GUI non installati. Installa con: pip install pystray pillow")
    print(f"Dettaglio errore: {e}")
    sys.exit(1)

class VinicoleApplicationLauncher:
    def __init__(self):
        self.flask_process = None
        self.flask_port = 5000
        self.socketio_port = 8100
        self.flask_host = "127.0.0.1"
        self.flask_url = f"http://{self.flask_host}:{self.flask_port}"
        self.tray_icon = None
        self.console_window = None
        self.app_running = False
        
        # Nascondi la console all'avvio
        self.hide_console()
        
    def hide_console(self):
        """Nasconde la finestra della console"""
        try:
            import win32gui
            import win32con
            
            # Trova la finestra della console
            console_window = win32gui.GetForegroundWindow()
            if console_window:
                # Nasconde la console
                win32gui.ShowWindow(console_window, win32con.SW_HIDE)
                self.console_window = console_window
        except ImportError:
            # Se win32gui non è disponibile, prova metodo alternativo
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except:
                pass
    
    def show_console(self):
        """Mostra la finestra della console"""
        try:
            import win32gui
            import win32con
            
            if self.console_window:
                win32gui.ShowWindow(self.console_window, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(self.console_window)
        except ImportError:
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)
            except:
                pass
    
    def create_tray_icon(self):
        """Crea l'icona nella system tray"""
        # Crea un'icona più professionale
        image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Disegna un cerchio di sfondo
        draw.ellipse([4, 4, 60, 60], fill='darkblue', outline='navy', width=2)
        
        # Disegna una "V" stilizzata per Vinicola
        try:
            # Prova a usare un font più grande se disponibile
            draw.text((18, 15), "V", fill='white', stroke_width=1, stroke_fill='darkblue')
        except:
            # Fallback senza font avanzati
            draw.text((18, 15), "V", fill='white')
        
        # Menu contestuale
        menu = pystray.Menu(
            item('Apri Browser', self.open_browser),
            item('Mostra Console', self.show_console),
            pystray.Menu.SEPARATOR,
            item('Riavvia', self.restart_application),
            item('Chiudi Applicazione', self.quit_application)
        )
        
        # Crea l'icona del tray
        self.tray_icon = pystray.Icon(
            "Gestione Vinicola",
            image,
            "Gestione Vinicola - Sistema attivo",
            menu
        )
        
        return self.tray_icon
    
    def find_available_port(self, start_port=5000):
        """Trova una porta disponibile"""
        for port in range(start_port, start_port + 10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.flask_host, port))
                    return port
            except OSError:
                continue
        return start_port
    
    def check_ports_available(self):
        """Controlla che le porte necessarie siano disponibili"""
        # Trova porte disponibili
        self.flask_port = self.find_available_port(5000)
        self.socketio_port = self.find_available_port(8100)
        
        # Se la porta Flask coincide con quella SocketIO, trova un'alternativa
        if self.flask_port == self.socketio_port:
            self.socketio_port = self.find_available_port(self.flask_port + 1)
        
        self.flask_url = f"http://{self.flask_host}:{self.flask_port}"
        
        print(f"Porta Flask: {self.flask_port}")
        print(f"Porta SocketIO: {self.socketio_port}")
    
    def wait_for_flask(self, timeout=30):
        """Attende che Flask sia pronto"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex((self.flask_host, self.flask_port))
                    if result == 0:
                        return True
            except:
                pass
            time.sleep(0.5)
        return False
    
    def start_flask_app(self):
        """Avvia l'applicazione Flask"""
        try:
            # Controlla le porte disponibili
            self.check_ports_available()
            
            # Prepara il comando per avviare Flask
            python_exe = sys.executable
            app_script = os.path.join(os.path.dirname(__file__), 'app.py')
            
            # Avvia Flask come processo separato
            env = os.environ.copy()
            env['FLASK_RUN_PORT'] = str(self.flask_port)
            env['FLASK_RUN_HOST'] = self.flask_host
            env['FLASK_DEBUG'] = 'False'  # Disabilita debug per produzione
            
            self.flask_process = subprocess.Popen(
                [python_exe, app_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            print(f"Avvio Flask su {self.flask_url}")
            
            # Attendi che Flask sia pronto
            if self.wait_for_flask():
                print("Flask avviato con successo!")
                self.app_running = True
                return True
            else:
                print("Timeout nell'avvio di Flask")
                return False
                
        except Exception as e:
            print(f"Errore nell'avvio di Flask: {e}")
            return False
    
    def stop_flask_app(self):
        """Ferma l'applicazione Flask"""
        if self.flask_process:
            try:
                self.flask_process.terminate()
                self.flask_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.flask_process.kill()
            except Exception as e:
                print(f"Errore nel fermare Flask: {e}")
            finally:
                self.flask_process = None
                self.app_running = False
    
    def open_browser(self, icon=None, item=None):
        """Apre il browser alla pagina dell'applicazione"""
        try:
            webbrowser.open(self.flask_url)
            print(f"Browser aperto su: {self.flask_url}")
        except Exception as e:
            print(f"Errore nell'apertura del browser: {e}")
            # Mostra messaggio di errore
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Errore", f"Impossibile aprire il browser:\n{e}")
            root.destroy()
    
    def restart_application(self, icon=None, item=None):
        """Riavvia l'applicazione"""
        print("Riavvio applicazione...")
        
        # Ferma Flask
        self.stop_flask_app()
        
        # Attendi un po'
        time.sleep(2)
        
        # Riavvia Flask
        if self.start_flask_app():
            # Apri il browser automaticamente
            threading.Timer(2.0, self.open_browser).start()
            
            # Mostra notifica
            if self.tray_icon:
                self.tray_icon.notify("Applicazione riavviata con successo", "Gestione Vinicola")
        else:
            if self.tray_icon:
                self.tray_icon.notify("Errore nel riavvio", "Gestione Vinicola")
    
    def quit_application(self, icon=None, item=None):
        """Chiude completamente l'applicazione"""
        print("Chiusura applicazione...")
        
        # Ferma Flask
        self.stop_flask_app()
        
        # Chiudi l'icona del tray
        if self.tray_icon:
            self.tray_icon.stop()
        
        # Esci
        sys.exit(0)
    
    def run(self):
        """Avvia l'applicazione completa"""
        print("Avvio Gestione Vinicola...")
        
        # Avvia Flask
        if not self.start_flask_app():
            # Se Flask non si avvia, mostra errore
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Errore di Avvio", 
                "Impossibile avviare il server Flask.\nControlla che non ci siano altre istanze in esecuzione."
            )
            root.destroy()
            return
        
        # Crea l'icona del tray
        tray_icon = self.create_tray_icon()
        
        # Apri il browser automaticamente dopo un breve ritardo
        threading.Timer(3.0, self.open_browser).start()
        
        # Avvia il tray icon (questo blocca il thread principale)
        try:
            tray_icon.run()
        except KeyboardInterrupt:
            print("Interruzione da tastiera ricevuta")
        finally:
            self.quit_application()

def main():
    """Funzione principale"""
    try:
        launcher = VinicoleApplicationLauncher()
        launcher.run()
    except Exception as e:
        print(f"Errore critico: {e}")
        # Mostra messaggio di errore
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Errore Critico", f"Errore nell'avvio dell'applicazione:\n{e}")
            root.destroy()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()