# Esempio di implementazione WebSocket per barcode scanner
from flask_socketio import SocketIO, emit
import threading
import time

# Aggiungi a app.py
socketio = SocketIO(app, cors_allowed_origins="*")

# Modifica la funzione di lettura seriale
def read_barcode_serial_websocket():
    """Versione WebSocket della lettura seriale."""
    global serial_port
    buffer = ""
    
    while True:
        try:
            if serial_port and serial_port.is_open:
                data = serial_port.read(serial_port.in_waiting or 1)
                
                if data:
                    text = data.decode('utf-8', errors='replace')
                    buffer += text
                    
                    if '\n' in buffer or '\r' in buffer:
                        barcode = buffer.strip()
                        
                        # Cerca il dipendente
                        employee = Employee.query.filter_by(code=barcode).first()
                        
                        if employee:
                            # Invia immediatamente via WebSocket
                            socketio.emit('barcode_scanned', {
                                'success': True,
                                'barcode': barcode,
                                'employee': employee.to_dict()
                            })
                        else:
                            socketio.emit('barcode_scanned', {
                                'success': False,
                                'barcode': barcode,
                                'message': 'Dipendente non trovato'
                            })
                        
                        buffer = ""
            
            time.sleep(0.1)
            
        except Exception as e:
            socketio.emit('scanner_error', {'error': str(e)})
            time.sleep(1)

@socketio.on('connect')
def handle_connect():
    print('Client connesso')
    emit('scanner_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnesso')

@socketio.on('request_scanner_status')
def handle_scanner_status():
    status = {
        'connected': serial_port is not None and serial_port.is_open if serial_port else False,
        'port': SERIAL_CONFIG['port']
    }
    emit('scanner_status', status)

# JavaScript lato client
"""
// Nel template
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
<script>
    const socket = io();
    
    socket.on('connect', function() {
        console.log('Connesso al server');
        updateScannerStatus('connected');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnesso dal server');
        updateScannerStatus('disconnected');
    });
    
    socket.on('barcode_scanned', function(data) {
        if (data.success) {
            processEmployeeData(data.employee);
        } else {
            showToast(data.message, 'warning');
        }
    });
    
    socket.on('scanner_error', function(data) {
        showToast('Errore scanner: ' + data.error, 'danger');
        updateScannerStatus('disconnected');
    });
    
    socket.on('scanner_status', function(data) {
        updateScannerStatus(data.connected ? 'connected' : 'disconnected');
    });
</script>
"""

# Dipendenze aggiuntive per requirements.txt
"""
flask-socketio==5.3.0
python-socketio==5.8.0
eventlet==0.33.3
"""

# Modifica per PyInstaller in app.spec
"""
a = Analysis(
    ['app.py'],
    # ...
    hiddenimports=[
        'eventlet.hubs.epolls',
        'eventlet.hubs.kqueue', 
        'eventlet.hubs.selects',
        'dns.resolver',
        'dns.reversename',
    ],
    # ...
)
""" 