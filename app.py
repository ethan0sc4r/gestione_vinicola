#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Applicazione di Gestione Vinicola
---------------------------------
Sistema per la gestione del personale e dei crediti in una vinicola,
con supporto per lettore di codici a barre seriale e verifica dell'integrità dei crediti.

Richiede Python 3.10 o superiore.
"""

import os
import csv
import json
import hashlib
import threading
import time
import io
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any, Union

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vinicola.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("vinicola")

# Importazione controllata di Pandas
# L'errore che stai riscontrando è spesso causato da incompatibilità
# tra versioni di numpy e pandas, o da problemi di installazione
try:
    # Prima prova a eseguire un import di numpy per verificare che sia compatibile
    import numpy as np
    logger.info(f"NumPy version: {np.__version__}")
    
    # Poi importa pandas
    import pandas as pd
    logger.info(f"Pandas version: {pd.__version__}")
except (ValueError, ModuleNotFoundError) as e:
    if isinstance(e, ModuleNotFoundError):
        logger.warning(f"Modulo non trovato: {str(e)}. Utilizzo alternative methods.")
        pd = None
    elif "numpy.dtype size changed" in str(e):
        logger.error("Incompatibilità tra NumPy e Pandas. Utilizzo alternative methods.")
        # Useremo CSV nativo invece di pandas
        pd = None
    else:
        raise

# Resto delle importazioni
import pytz
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Configurazione per lettore seriale
# Incapsula in un blocco try/except per rendere opzionale pyserial
try:
    import serial
    logger.info("PySerial disponibile, supporto lettore seriale attivato")
    SERIAL_AVAILABLE = True
except ImportError:
    logger.warning("PySerial non disponibile, supporto lettore seriale disattivato")
    SERIAL_AVAILABLE = False
    serial = None

# Inizializzazione dell'applicazione
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chiave_segreta_molto_sicura')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///vinicola.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
app.config['APP_NAME'] = os.environ.get('APP_NAME', 'Gestione Vinicola')
app.config['APP_VERSION'] = os.environ.get('APP_VERSION', '1.0.0')

# Cartella per uploads temporanei se necessario
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configurazione del lettore di codici a barre seriale
serial_port = None
barcode_thread = None
barcode_data = []
barcode_lock = threading.Lock()
SERIAL_CONFIG = {
    'port': os.environ.get('SERIAL_PORT', '/dev/ttyUSB0'),
    'baudrate': int(os.environ.get('SERIAL_BAUDRATE', 9600)),
    'bytesize': int(os.environ.get('SERIAL_BYTESIZE', 8)),
    'parity': os.environ.get('SERIAL_PARITY', 'N'),
    'stopbits': int(os.environ.get('SERIAL_STOPBITS', 1)),
    'timeout': float(os.environ.get('SERIAL_TIMEOUT', 1.0))
}

#######################
# Definizione Modelli #
#######################

class Admin(db.Model, UserMixin):
    """
    Modello per gli amministratori del sistema.
    Hanno accesso a tutte le funzionalità amministrative.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(200))
    email = db.Column(db.String(100), nullable=True)
    is_super_admin = db.Column(db.Boolean, default=False)  # Super admin ha privilegi speciali
    active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        """Imposta la password criptata."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Verifica la password."""
        return check_password_hash(self.password_hash, password)

class Operator(db.Model):
    """
    Modello per gli operatori che possono caricare credito.
    Ci sono 10 operatori standard con password generate dall'amministratore.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)  # utente1, utente2, ecc.
    password = db.Column(db.String(10))  # Password in chiaro per facilità di uso (5 caratteri)
    active = db.Column(db.Boolean, default=True)
    

class Employee(db.Model):
    """
    Modello per i dipendenti.
    Questi sono gli utenti che possono acquistare utilizzando il loro credito.
    """
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)  # Codice a barre della card
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    rank = db.Column(db.String(100))
    credit = db.Column(db.Numeric(10, 2), default=0)
    credit_hash = db.Column(db.String(64))  # Hash per verificare l'integrità del credito
    credit_limit = db.Column(db.Numeric(10, 2), default=0)  # Limite di credito negativo consentito
    
    def update_credit(self, new_credit):
        """Aggiorna il credito e genera un nuovo hash."""
        self.credit = new_credit
        self.update_credit_hash()
    
    def update_credit_hash(self):
        """Crea un hash del credito con una chiave segreta per verificare l'integrità."""
        secret = app.config['SECRET_KEY']
        data = f"{self.id}:{self.credit}:{self.credit_limit}:{secret}"
        self.credit_hash = hashlib.sha256(data.encode()).hexdigest()
    
    def verify_credit_integrity(self):
        """Verifica che il credito non sia stato manipolato confrontando l'hash."""
        if not self.credit_hash:  # Se non c'è hash, crealo
            self.update_credit_hash()
            db.session.commit()
            return True
            
        secret = app.config['SECRET_KEY']
        data = f"{self.id}:{self.credit}:{self.credit_limit}:{secret}"
        computed_hash = hashlib.sha256(data.encode()).hexdigest()
        return computed_hash == self.credit_hash
    
    def has_sufficient_credit(self, amount):
        """
        Verifica se il dipendente ha credito sufficiente per una spesa,
        considerando anche il limite di credito negativo globale.
        """
        # Se è l'utente "cassa", non ha limiti di credito
        if self.code == 'CASSA':
            return True
            
        # Ottieni il limite di credito globale, se non esiste usa il limite dell'utente
        global_limit = GlobalSetting.get('credit_limit', None)
        
        if global_limit is not None:
            try:
                limit = Decimal(global_limit)
            except:
                limit = self.credit_limit
        else:
            limit = self.credit_limit
            
        return (self.credit - amount) >= -limit
    
    def to_dict(self):
        """Converte l'oggetto in un dizionario."""
        integrity = self.verify_credit_integrity()
        
        if not integrity:
            logger.warning(f"SECURITY: Credit integrity verification failed for employee {self.id}")
        
        return {
            'id': self.id,
            'code': self.code,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'rank': self.rank,
            'credit': float(self.credit) if self.credit else 0,
            'credit_limit': float(self.credit_limit) if self.credit_limit else 0,
            'credit_integrity': integrity
        }

class Product(db.Model):
    """
    Modello per i prodotti che possono essere acquistati.
    Configurati dall'amministratore.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Numeric(10, 2))
    active = db.Column(db.Boolean, default=True)
    inventory = db.Column(db.Integer, default=0)  # Giacenza del prodotto
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': float(self.price) if self.price else 0,
            'active': self.active,
            'inventory': self.inventory
        }
    


class GlobalSetting(db.Model):
    """
    Modello per le impostazioni globali del sistema.
    Contiene configurazioni che si applicano a tutto il sistema.
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(200))
    description = db.Column(db.String(200))
    
    @classmethod
    def get(cls, key, default=None):
        """Ottiene il valore di un'impostazione."""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set(cls, key, value, description=None):
        """Imposta il valore di un'impostazione."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting


class Transaction(db.Model):
    """
    Modello per le transazioni di credito.
    Tiene traccia di tutte le operazioni di carico/scarico credito.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    operator_id = db.Column(db.Integer, db.ForeignKey('operator.id'), nullable=True)  # Chi ha eseguito l'operazione
    amount = db.Column(db.Numeric(10, 2))  # Positivo per ricarica, negativo per consumo
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)  # Prodotto acquistato (se applicabile)
    custom_product_name = db.Column(db.String(100), nullable=True)  # Nome prodotto personalizzato
    transaction_type = db.Column(db.String(20))  # "credit" (ricarica) o "debit" (consumo)
    quantity = db.Column(db.Integer, default=1)  # Quantità del prodotto acquistato
    
    # Relazioni
    employee = db.relationship('Employee', backref=db.backref('transactions', lazy=True, order_by="desc(Transaction.timestamp)"))
    operator = db.relationship('Operator', backref=db.backref('transactions', lazy=True))
    product = db.relationship('Product', backref=db.backref('transactions', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'employee_id': self.employee_id,
            'employee_name': f"{self.employee.first_name} {self.employee.last_name}" if self.employee else None,
            'operator_id': self.operator_id,
            'operator_name': self.operator.username if self.operator else None,
            'amount': float(self.amount) if self.amount else 0,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else self.custom_product_name,
            'transaction_type': self.transaction_type
        }

# Funzione per generare password casuali per gli operatori
def generate_random_password(length=5):
    """Genera una password casuale di lunghezza specificata."""
    import random
    import string
    # Utilizziamo solo lettere maiuscole e numeri per maggiore leggibilità
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Funzione per creare o aggiornare gli operatori standard
def ensure_operators_exist():
    """
    Assicura che esistano i 10 operatori standard.
    Se non esistono, li crea con password casuali.
    """
    for i in range(1, 11):
        username = f"utente{i}"
        operator = Operator.query.filter_by(username=username).first()
        
        if not operator:
            operator = Operator(username=username, password=generate_random_password())
            db.session.add(operator)
    
    db.session.commit()

# Funzione per rigenerare tutte le password degli operatori
def regenerate_all_operator_passwords():
    """Rigenera le password per tutti gli operatori."""
    operators = Operator.query.all()
    passwords = {}
    
    for operator in operators:
        new_password = generate_random_password()
        operator.password = new_password
        passwords[operator.username] = new_password
    
    db.session.commit()
    return passwords

# Funzione per assicurare che esista l'utente "cassa" per gli acquisti anonimi
def ensure_cash_register_exists():
    """
    Assicura che esista l'utente speciale 'cassa' per gli acquisti di utenti non registrati.
    Questo utente è fittizio e non è soggetto a limiti di credito.
    """
    cash_register = Employee.query.filter_by(code='CASSA').first()
    
    if not cash_register:
        cash_register = Employee(
            code='CASSA',
            first_name='Cassa',
            last_name='Centrale',
            rank='Sistema',
            credit=0,
            credit_limit=999999  # Limite di credito molto alto per evitare problemi
        )
        cash_register.update_credit_hash()
        db.session.add(cash_register)
        db.session.commit()
    
    return cash_register

@login_manager.user_loader
def load_user(user_id):
    """Carica l'utente per Flask-Login."""
    return Admin.query.get(int(user_id))


###################################
# Funzioni per il lettore seriale #
###################################

def setup_barcode_reader():
    """Configura e avvia il lettore di codici a barre seriale."""
    global serial_port, barcode_thread
    
    if not SERIAL_AVAILABLE:
        logger.warning("PySerial non installato. Lettore seriale non disponibile.")
        return False
    
    try:
        # Usa i parametri di configurazione
        port = SERIAL_CONFIG['port']
        baud_rate = SERIAL_CONFIG['baudrate']
        
        serial_port = serial.Serial(
            port, 
            baud_rate, 
            bytesize=SERIAL_CONFIG['bytesize'],
            parity=SERIAL_CONFIG['parity'],
            stopbits=SERIAL_CONFIG['stopbits'],
            timeout=SERIAL_CONFIG['timeout']
        )
        logger.info(f"Lettore di codici a barre connesso su {port}")
        
        # Avvio thread per la lettura in background
        barcode_thread = threading.Thread(target=read_barcode_serial, daemon=True)
        barcode_thread.start()
        
        return True
    except Exception as e:
        logger.error(f"Errore configurazione lettore di codici a barre: {str(e)}")
        return False


def read_barcode_serial():
    """Funzione per leggere continuamente dal lettore di codici a barre."""
    global serial_port, barcode_data, barcode_lock
    
    buffer = ""
    
    while True:
        try:
            if serial_port and serial_port.is_open:
                # Leggi i dati dalla porta seriale
                data = serial_port.read(serial_port.in_waiting or 1)
                
                if data:
                    # Decodifica i dati
                    text = data.decode('utf-8', errors='replace')
                    buffer += text
                    
                    # Controlla se abbiamo ricevuto un "invio" (fine codice)
                    if '\n' in buffer or '\r' in buffer:
                        # Pulisci il codice ricevuto
                        barcode = buffer.strip()
                        
                        with barcode_lock:
                            # Aggiungi il codice alla lista
                            barcode_data.append(barcode)
                            # Mantieni solo gli ultimi 5 codici letti
                            if len(barcode_data) > 5:
                                barcode_data.pop(0)
                        
                        logger.info(f"Codice a barre letto: {barcode}")
                        buffer = ""
            
            # Piccola pausa per ridurre l'utilizzo della CPU
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Errore lettura codice a barre: {str(e)}")
            time.sleep(1)  # Pausa più lunga in caso di errore


def get_last_barcode():
    """Ottiene l'ultimo codice a barre letto."""
    global barcode_data, barcode_lock
    
    with barcode_lock:
        if barcode_data:
            return barcode_data[-1]
    
    return None


##########################
# Funzioni di utilità   #
##########################

def get_credit_stats(employee_id):
    """Calcola statistiche sul credito di un dipendente."""
    total_added = db.session.query(db.func.sum(Transaction.amount)).\
        filter(Transaction.employee_id == employee_id, 
               Transaction.transaction_type == 'credit').scalar() or 0
               
    total_spent = db.session.query(db.func.sum(Transaction.amount)).\
        filter(Transaction.employee_id == employee_id, 
               Transaction.transaction_type == 'debit').scalar() or 0
    
    # Converti in float per evitare problemi con Decimal/JSON
    return {
        'total_added': float(total_added),
        'total_spent': abs(float(total_spent))
    }


def get_system_stats():
    """Ottiene statistiche globali del sistema."""
    total_employees = Employee.query.count()
    total_credit = db.session.query(db.func.sum(Employee.credit)).scalar() or 0
    total_transactions = Transaction.query.count()
    
    # Transazioni recenti (ultime 24 ore)
    yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    recent_transactions = Transaction.query.filter(Transaction.timestamp >= yesterday).count()
    
    return {
        'total_employees': total_employees,
        'total_credit': float(total_credit),
        'total_transactions': total_transactions,
        'recent_transactions': recent_transactions
    }


def export_employees_to_csv():
    """Esporta i dipendenti in formato CSV."""
    employees = Employee.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Code', 'First Name', 'Last Name', 'Rank', 'Credit'])
    for employee in employees:
        writer.writerow([
            employee.code, 
            employee.first_name, 
            employee.last_name, 
            employee.rank, 
            float(employee.credit)
        ])
    
    output.seek(0)
    return output.getvalue()


def export_employees_to_excel():
    """Esporta i dipendenti in formato Excel."""
    employees = Employee.query.all()
    
    if pd is None:
        # Se pandas non è disponibile, restituisci un CSV come fallback
        return export_employees_to_csv(), 'csv'
    
    data = {
        'Code': [e.code for e in employees],
        'First Name': [e.first_name for e in employees],
        'Last Name': [e.last_name for e in employees],
        'Rank': [e.rank for e in employees],
        'Credit': [float(e.credit) for e in employees]
    }
    
    df = pd.DataFrame(data)
    
    # Salva il file Excel in un buffer
    output = io.BytesIO()
    
    # Opzioni di salvataggio dipendono dalla versione di pandas
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Employees', index=False)
    except TypeError:
        # Per versioni più vecchie di pandas
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Employees', index=False)
        writer.save()
    
    output.seek(0)
    return output.getvalue(), 'xlsx'


def import_employees_from_file(file):
    """Importa dipendenti da un file CSV o Excel."""
    filename = file.filename
    
    try:
        if filename.endswith('.csv'):
            # Lettura diretta dal file
            file_content = file.read().decode('utf-8')
            
            if pd is not None:
                # Usa pandas se disponibile
                df = pd.read_csv(io.StringIO(file_content))
            else:
                # Altrimenti usa il modulo csv
                reader = csv.DictReader(io.StringIO(file_content))
                records = list(reader)
                
                # Converti in un formato simile a un DataFrame
                df = {'Code': [], 'First Name': [], 'Last Name': [], 'Rank': [], 'Credit': []}
                for record in records:
                    for key in df.keys():
                        df[key].append(record.get(key, ''))
        
        elif filename.endswith('.xlsx'):
            if pd is None:
                return False, "Pandas non disponibile per leggere file Excel"
            
            # Salva temporaneamente il file
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(temp_path)
            
            # Leggi il file Excel
            df = pd.read_excel(temp_path)
            
            # Rimuovi il file temporaneo
            os.remove(temp_path)
        else:
            return False, "Formato file non supportato"
        
        # Verifica colonne richieste
        required_columns = ['Code', 'First Name', 'Last Name', 'Rank']
        
        if pd is not None:
            if not all(col in df.columns for col in required_columns):
                return False, "Il file non contiene tutte le colonne richieste"
            
            # Importa i dipendenti
            for _, row in df.iterrows():
                process_employee_row(row)
        else:
            # Verifica le colonne nel caso di csv senza pandas
            column_names = list(df.keys())
            if not all(col in column_names for col in required_columns):
                return False, "Il file non contiene tutte le colonne richieste"
            
            # Importa riga per riga
            for i in range(len(df['Code'])):
                row = {col: df[col][i] for col in column_names}
                process_employee_row(row)
        
        db.session.commit()
        return True, f"Importati {len(df) if pd is not None else len(df['Code'])} dipendenti"
    
    except Exception as e:
        logger.error(f"Errore importazione: {str(e)}")
        db.session.rollback()
        return False, f"Errore durante l'importazione: {str(e)}"


def process_employee_row(row):
    """Elabora una riga di dati per l'importazione di un dipendente."""
    code = str(row['Code'])
    
    # Cerca l'impiegato esistente
    existing_employee = Employee.query.filter_by(code=code).first()
    
    if existing_employee:
        # Aggiorna l'impiegato esistente
        existing_employee.first_name = row['First Name']
        existing_employee.last_name = row['Last Name']
        existing_employee.rank = row['Rank']
        if 'Credit' in row and row['Credit']:
            try:
                credit_value = float(row['Credit'])
                existing_employee.update_credit(Decimal(str(credit_value)))
            except (ValueError, TypeError):
                pass  # Ignora errori di conversione
    else:
        # Crea un nuovo impiegato
        credit_value = 0
        if 'Credit' in row and row['Credit']:
            try:
                credit_value = float(row['Credit'])
            except (ValueError, TypeError):
                pass  # Ignora errori di conversione
        
        employee = Employee(
            code=code,
            first_name=row['First Name'],
            last_name=row['Last Name'],
            rank=row['Rank'],
            credit=Decimal(str(credit_value))
        )
        employee.set_password(code)  # Password predefinita = codice impiegato
        employee.update_credit_hash()  # Genera l'hash del credito
        db.session.add(employee)


def check_integrity_all_employees():
    """Verifica l'integrità del credito di tutti i dipendenti."""
    employees = Employee.query.all()
    issues = []
    
    for employee in employees:
        if not employee.verify_credit_integrity():
            issues.append({
                'id': employee.id,
                'name': f"{employee.first_name} {employee.last_name}",
                'code': employee.code
            })
            # Rigenera l'hash
            employee.update_credit_hash()
    
    # Salva le modifiche se ci sono stati problemi risolti
    if issues:
        db.session.commit()
        
    return len(issues) == 0, issues


def reset_all_credit_hashes():
    """Rigenera tutti gli hash di integrità."""
    employees = Employee.query.all()
    count = 0
    
    for employee in employees:
        employee.update_credit_hash()
        count += 1
    
    db.session.commit()
    return count


####################
# Routes Flask    #
####################

# Punto di ingresso principale
@app.route('/')
def index():
    """
    Pagina principale che mostra direttamente lo scanner di codici a barre.
    Non è necessario alcun login per utilizzare il sistema base.
    """
    # Reindirizza direttamente alla pagina dello scanner
    return redirect(url_for('barcode_scanner'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Gestione login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for('dashboard'))
        else:
            flash('Username o password non validi.')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Gestione logout."""
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principale."""
    employees = Employee.query.all()
    stats = get_system_stats()
    
    return render_template(
        'dashboard.html', 
        employees=employees, 
        total_employees=stats['total_employees'], 
        total_credit=stats['total_credit'],
        transactions_count=stats['recent_transactions']
    )


@app.route('/employee/new', methods=['GET', 'POST'])
@login_required
def new_employee():
    """Aggiunta nuovo dipendente."""
    if request.method == 'POST':
        code = request.form.get('code')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        rank = request.form.get('rank')
        password = request.form.get('password')
        
        # Verifica se il codice è già esistente
        existing_employee = Employee.query.filter_by(code=code).first()
        if existing_employee:
            flash('Il codice dipendente esiste già.')
            return redirect(url_for('new_employee'))
        
        # Crea il nuovo dipendente
        employee = Employee(
            code=code,
            first_name=first_name,
            last_name=last_name,
            rank=rank,
            credit=0.0
        )
        employee.set_password(password)
        employee.update_credit_hash()
        
        db.session.add(employee)
        db.session.commit()
        flash('Dipendente aggiunto con successo.')
        return redirect(url_for('dashboard'))
    
    return render_template('new_employee.html')


@app.route('/employee/<int:id>')
@login_required
def employee_details(id):
    """Visualizza dettagli dipendente."""
    employee = Employee.query.get_or_404(id)
    transactions = Transaction.query.filter_by(employee_id=id).order_by(Transaction.timestamp.desc()).all()
    
    # Calcola statistiche credito
    credit_stats = get_credit_stats(id)
    
    return render_template(
        'employee_details.html', 
        employee=employee, 
        transactions=transactions,
        credit_stats=credit_stats
    )


@app.route('/employee/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    """Modifica dipendente."""
    employee = Employee.query.get_or_404(id)
    
    # Verifica integrità
    integrity_ok = employee.verify_credit_integrity()
    
    if request.method == 'POST':
        employee.code = request.form.get('code')
        employee.first_name = request.form.get('first_name')
        employee.last_name = request.form.get('last_name')
        employee.rank = request.form.get('rank')
        
        # Cambia password se fornita
        password = request.form.get('password')
        if password:
            employee.set_password(password)
        
        # Ripristina integrità se richiesto
        if request.form.get('restore_integrity') or not integrity_ok:
            employee.update_credit_hash()
        
        db.session.commit()
        flash('Dipendente aggiornato con successo.')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_employee.html', employee=employee)


@app.route('/employee/<int:id>/delete', methods=['POST'])
@login_required
def delete_employee(id):
    """Elimina dipendente."""
    employee = Employee.query.get_or_404(id)
    
    # Verifica che non sia l'utente "cassa"
    if employee.code == 'CASSA':
        flash('Non è possibile eliminare l\'utente "cassa" in quanto è necessario per il sistema.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Elimina tutte le transazioni associate
    Transaction.query.filter_by(employee_id=id).delete()
    
    # Elimina il dipendente
    db.session.delete(employee)
    db.session.commit()
    
    flash('Dipendente eliminato con successo.')
    return redirect(url_for('dashboard'))



@app.route('/add_credit', methods=['GET', 'POST'])
def add_credit():
    """
    Aggiunge credito a un dipendente.
    Richiede una password di operatore valida.
    """
    if request.method == 'GET':
        # Se viene visitata direttamente, mostra la pagina con le istruzioni
        employee_id = request.args.get('employee_id')
        
        if not employee_id:
            flash('Dipendente non specificato.', 'danger')
            return redirect(url_for('barcode_scanner'))
        
        employee = Employee.query.get_or_404(employee_id)
        operators = Operator.query.filter_by(active=True).all()
        
        return render_template(
            'add_credit.html', 
            employee=employee,
            operators=operators
        )
    
    elif request.method == 'POST':
        # Elabora la richiesta di aggiunta credito
        employee_id = request.form.get('employee_id')
        amount = request.form.get('amount')
        operator_password = request.form.get('operator_password')
        
        if not employee_id or not amount or not operator_password:
            return jsonify({
                'success': False,
                'message': 'Tutti i campi sono obbligatori.'
            })
        
        # Trova il dipendente
        employee = Employee.query.get_or_404(employee_id)
        
        # Verifica che la password dell'operatore sia valida
        operator = Operator.query.filter_by(password=operator_password, active=True).first()
        if not operator:
            return jsonify({
                'success': False,
                'message': 'Password operatore non valida.'
            })
        
        try:
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                return jsonify({
                    'success': False,
                    'message': 'L\'importo deve essere maggiore di zero.'
                })
            
            # Aggiorna il credito
            new_credit = employee.credit + amount_decimal
            employee.update_credit(new_credit)
            
            # Registra la transazione
            transaction = Transaction(
                employee_id=employee.id,
                operator_id=operator.id,
                amount=amount_decimal,
                transaction_type='credit',
                custom_product_name="Ricarica credito"
            )
            
            # Aggiorna anche il saldo della cassa
            cash_register = Employee.query.filter_by(code='CASSA').first()
            if cash_register:
                cash_register.update_credit(cash_register.credit + amount_decimal)
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Credito di €{float(amount_decimal):.2f} aggiunto con successo.',
                'new_credit': float(employee.credit)
            })
            
        except Exception as e:
            logger.error(f"Error in add_credit: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Errore: {str(e)}'
            })

@app.route('/barcode_scanner')
def barcode_scanner():
    """
    Pagina scanner codice a barre, che è sempre in ascolto.
    Questa è la pagina principale che tutti gli utenti vedono.
    """
    # Ottieni l'ultimo codice a barre letto dal lettore seriale (se disponibile)
    last_barcode = get_last_barcode()
    
    # Ottieni la lista dei prodotti per la selezione rapida
    products = Product.query.filter_by(active=True).all()
    
    # Ottieni la lista dei dipendenti per la tabella
    employees = Employee.query.order_by(Employee.last_name).all()
    
    return render_template(
        'barcode_scanner.html', 
        last_barcode=last_barcode,
        products=products,
        employees=employees
    )

@app.route('/get_serial_barcode')
def get_serial_barcode():
    """
    Endpoint per ottenere l'ultimo codice a barre letto dal lettore seriale tramite AJAX.
    La pagina principale fa polling di questo endpoint per rilevare nuove scansioni.
    """
    last_barcode = get_last_barcode()
    
    if last_barcode:
        # Se è stato letto un codice, cerca il dipendente
        employee = Employee.query.filter_by(code=last_barcode).first()
        
        if employee:
            # Verifica l'integrità del credito
            if not employee.verify_credit_integrity():
                # Ripristina l'hash e registra il problema
                employee.update_credit_hash()
                db.session.commit()
                logger.warning(f"Credit integrity issue fixed for {employee.first_name} {employee.last_name}")
            
            # Ritorna i dati del dipendente
            return jsonify({
                'success': True,
                'barcode': last_barcode,
                'employee': employee.to_dict()
            })
        else:
            # Codice letto ma dipendente non trovato
            return jsonify({
                'success': False,
                'message': 'Dipendente non trovato.',
                'barcode': last_barcode
            })
    
    # Nessun codice letto
    return jsonify({
        'success': False,
        'message': 'Nessun codice letto.',
        'barcode': None
    })


@app.route('/scan_barcode', methods=['POST'])
def scan_barcode():
    """Endpoint per scansione manuale di un codice a barre o selezione diretta di un dipendente."""
    barcode = request.form.get('barcode')
    employee_id = request.form.get('employee_id')
    
    # Cerca il dipendente per ID o per codice a barre
    if employee_id:
        employee = Employee.query.get(employee_id)
    elif barcode:
        employee = Employee.query.filter_by(code=barcode).first()
    else:
        return jsonify({'success': False, 'message': 'Nessun codice o ID dipendente fornito.'})
    
    if not employee:
        return jsonify({'success': False, 'message': 'Dipendente non trovato.'})
    
    # Verifica l'integrità del credito prima di restituire i dati
    if not employee.verify_credit_integrity():
        # Registra l'incidente di sicurezza
        logger.warning(f"SECURITY ALERT: Credit integrity check failed for employee {employee.id} " +
                      f"({employee.first_name} {employee.last_name})")
        
        # In un sistema reale, qui dovresti avvisare un amministratore e intraprendere azioni di ripristino
        # Per ora, ricrea l'hash e avvisa l'utente
        employee.update_credit_hash()
        db.session.commit()
        
        return jsonify({
            'success': False, 
            'message': 'ATTENZIONE: È stata rilevata una possibile manipolazione del credito. Contattare l\'amministratore.',
            'credit_integrity_failed': True
        })
    
    return jsonify({
        'success': True,
        'employee': employee.to_dict()
    })


@app.route('/deduct_credit', methods=['POST'])
def deduct_credit():
    """
    Scala credito da un dipendente.
    Può essere usato per prodotti multipli con quantità o un importo generico.
    """
    employee_id = request.form.get('employee_id')
    
    # Se non c'è ID dipendente, potrebbe essere un cliente non registrato
    if not employee_id:
        # Usa la "cassa" per gli acquisti anonimi
        cash_register = ensure_cash_register_exists()
        employee_id = cash_register.id
    
    # Ottieni i parametri dalla richiesta
    products_json = request.form.get('products')
    custom_amount = request.form.get('custom_amount')
    custom_product = request.form.get('custom_product')
    
    # Prendi il dipendente dal database
    employee = Employee.query.get_or_404(employee_id)
    
    # Verifica l'integrità del credito
    if not employee.verify_credit_integrity():
        employee.update_credit_hash()
        db.session.commit()
        logger.warning(f"Credit integrity fixed during deduction for employee {employee_id}")
    
    try:
        total_amount = Decimal('0')
        product_descriptions = []
        
        # Determina l'importo da scalare
        if products_json:
            # Se sono stati selezionati dei prodotti
            products = json.loads(products_json)
            
            for product_data in products:
                product_id = product_data['id']
                quantity = int(product_data['quantity'])
                
                if quantity <= 0:
                    continue
                
                product = Product.query.get_or_404(product_id)
                product_price = product.price
                product_total = product_price * quantity
                
                total_amount += product_total
                product_descriptions.append(f"{product.name} (x{quantity})")
                
                # Registra una transazione per ogni prodotto
                transaction = Transaction(
                    employee_id=employee.id,
                    amount=-product_total,  # Negativo perché stiamo sottraendo
                    transaction_type='debit',
                    product_id=product_id,
                    quantity=quantity  # Salva la quantità
                )
                db.session.add(transaction)
                
                # Aggiorna la giacenza del prodotto
                if product.inventory is not None:
                    product.inventory -= quantity
            
            product_description = ", ".join(product_descriptions)
            
        elif custom_amount:
            # Se è stato inserito un importo personalizzato
            total_amount = Decimal(custom_amount)
            product_description = custom_product if custom_product else "Importo personalizzato"
            
            # Registra la transazione per l'importo personalizzato
            transaction = Transaction(
                employee_id=employee.id,
                amount=-total_amount,  # Negativo perché stiamo sottraendo
                transaction_type='debit',
                custom_product_name=product_description
            )
            db.session.add(transaction)
        else:
            return jsonify({
                'success': False,
                'message': 'Nessun prodotto o importo specificato.'
            })
        
        # Controlla se il dipendente ha credito sufficiente (considerando il limite)
        if not employee.has_sufficient_credit(total_amount):
            remaining_credit = float(employee.credit)
            
            # Ottieni il limite di credito globale, se non esiste usa il limite dell'utente
            global_limit = GlobalSetting.get('credit_limit', None)
            
            if global_limit is not None:
                try:
                    credit_limit = float(Decimal(global_limit))
                except:
                    credit_limit = float(employee.credit_limit)
            else:
                credit_limit = float(employee.credit_limit)
            
            return jsonify({
                'success': False,
                'message': f'Credito insufficiente. Disponibile: €{remaining_credit:.2f}, Limite: €{credit_limit:.2f}',
                'remaining_credit': remaining_credit,
                'credit_limit': credit_limit
            })
        
        # Aggiorna il credito
        new_credit = employee.credit - total_amount
        employee.update_credit(new_credit)
        
        # Se l'acquisto è stato fatto dall'utente "cassa", aggiorna il saldo della cassa
        if employee.code == 'CASSA':
            # Aggiungi l'importo alla cassa (l'importo è già negativo, quindi lo sottraiamo)
            cash_register = ensure_cash_register_exists()
            cash_register.update_credit(cash_register.credit + total_amount)
        
        db.session.commit()
            
        return jsonify({
            'success': True,
            'message': f'Scalati €{float(total_amount):.2f} dal credito per {product_description}.',
            'new_credit': float(employee.credit),
            'credit_limit': float(employee.credit_limit)
        })
        
    except Exception as e:
        logger.error(f"Error in deduct_credit: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        })


        
@app.route('/admin')
def admin_login():
    """Pagina di login per l'amministratore."""
    return render_template('admin_login.html')


@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    """Gestisce il login dell'amministratore."""
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Verifica se esiste almeno un admin
    if Admin.query.count() == 0:
        # Crea l'admin predefinito se non esiste nessun admin
        admin = Admin(
            username='admin',
            is_super_admin=True,
            active=True
        )
        admin.set_password('admin')  # Password predefinita
        db.session.add(admin)
        db.session.commit()
        flash('Account amministratore predefinito creato. Username: admin, Password: admin', 'warning')
    
    # Cerca l'admin con lo username fornito
    admin = Admin.query.filter_by(username=username, active=True).first()
    
    if admin and admin.check_password(password):
        session['admin_logged_in'] = True
        session['admin_id'] = admin.id
        session['admin_username'] = admin.username
        session['is_super_admin'] = admin.is_super_admin
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Username o password non validi.', 'danger')
        return redirect(url_for('admin_login'))



@app.route('/admin/dashboard')
def admin_dashboard():
    """Dashboard amministrativa."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    # Statistiche di sistema
    employees_count = Employee.query.count()
    total_credit = db.session.query(db.func.sum(Employee.credit)).scalar() or 0
    transactions_today = Transaction.query.filter(
        Transaction.timestamp >= datetime.today().replace(hour=0, minute=0, second=0)
    ).count()
    
    # Elenco operatori
    operators = Operator.query.all()
    
    # Ottieni il saldo della cassa
    cash_register = Employee.query.filter_by(code='CASSA').first()
    cash_balance = float(cash_register.credit) if cash_register else 0.0
    
    # Aggiungi il tab per gli amministratori se l'utente è un super admin
    is_super_admin = session.get('is_super_admin', False)
    
    return render_template(
        'admin_dashboard.html',
        employees_count=employees_count,
        total_credit=float(total_credit),
        transactions_today=transactions_today,
        operators=operators,
        is_super_admin=is_super_admin,
        cash_balance=cash_balance
    )


@app.route('/admin/withdraw_cash', methods=['POST'])
def admin_withdraw_cash():
    """Preleva il denaro dalla cassa (tutto o parte del saldo)."""
    if session.get('admin_logged_in') != True:
        return jsonify({
            'success': False,
            'message': 'Non sei autorizzato a eseguire questa operazione.'
        })
    
    try:
        # Ottieni i dati dalla richiesta
        data = request.json or {}
        withdrawal_amount = data.get('amount')
        
        # Trova l'utente "cassa"
        cash_register = Employee.query.filter_by(code='CASSA').first()
        
        if not cash_register:
            return jsonify({
                'success': False,
                'message': 'Utente cassa non trovato.'
            })
        
        # Ottieni il saldo attuale
        current_balance = float(cash_register.credit)
        
        if current_balance <= 0:
            return jsonify({
                'success': False,
                'message': 'Il saldo della cassa è già zero o negativo.'
            })
        
        # Se non viene specificato un importo, preleva tutto
        if withdrawal_amount is None:
            withdrawal_amount = current_balance
        else:
            # Converte l'importo in float e verifica che sia valido
            try:
                withdrawal_amount = float(withdrawal_amount)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Importo non valido.'
                })
            
            # Verifica che l'importo sia maggiore di 0.01 (1 centesimo)
            if withdrawal_amount < 0.01:
                return jsonify({
                    'success': False,
                    'message': 'L\'importo minimo da prelevare è €0.01.'
                })
            
            # Verifica che l'importo non superi il saldo disponibile
            if withdrawal_amount > current_balance:
                return jsonify({
                    'success': False,
                    'message': f'Importo superiore al saldo disponibile (€{current_balance:.2f}).'
                })
        
        # Calcola il nuovo saldo
        new_balance = current_balance - withdrawal_amount
        
        # Crea una transazione per il prelievo
        transaction = Transaction(
            employee_id=cash_register.id,
            amount=-withdrawal_amount,  # Negativo perché stiamo sottraendo
            transaction_type='debit',
            custom_product_name="Prelievo cassa da amministratore"
        )
        
        # Aggiorna il saldo della cassa
        cash_register.update_credit(Decimal(str(new_balance)))
        
        # Salva la transazione
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Prelievo di €{withdrawal_amount:.2f} effettuato con successo.',
            'amount': withdrawal_amount,
            'new_balance': new_balance
        })
        
    except Exception as e:
        logger.error(f"Error in admin_withdraw_cash: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Errore durante il prelievo: {str(e)}'
        })


@app.route('/admin/admins')
def admin_admins():
    """Gestione amministratori."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    # Solo i super admin possono gestire gli amministratori
    if not session.get('is_super_admin', False):
        flash('Non hai i permessi per accedere a questa pagina.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Ottieni tutti gli amministratori
    admins = Admin.query.all()
    
    return render_template('admin_admins.html', admins=admins)


@app.route('/admin/admins/add', methods=['POST'])
def admin_add_admin():
    """Aggiunge un nuovo amministratore."""
    if session.get('admin_logged_in') != True or not session.get('is_super_admin', False):
        return redirect(url_for('admin_login'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    is_super_admin = 'is_super_admin' in request.form
    
    # Verifica che le password corrispondano
    if password != confirm_password:
        flash('Le password non corrispondono.', 'danger')
        return redirect(url_for('admin_admins'))
    
    # Verifica che lo username non sia già in uso
    existing_admin = Admin.query.filter_by(username=username).first()
    if existing_admin:
        flash('Nome utente già in uso.', 'danger')
        return redirect(url_for('admin_admins'))
    
    # Crea il nuovo amministratore
    admin = Admin(
        username=username,
        email=email,
        is_super_admin=is_super_admin,
        active=True
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    flash('Amministratore aggiunto con successo.', 'success')
    return redirect(url_for('admin_admins'))


@app.route('/admin/admins/edit', methods=['POST'])
def admin_edit_admin():
    """Modifica un amministratore esistente."""
    if session.get('admin_logged_in') != True or not session.get('is_super_admin', False):
        return redirect(url_for('admin_login'))
    
    admin_id = request.form.get('admin_id')
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    is_super_admin = 'is_super_admin' in request.form
    
    # Trova l'amministratore
    admin = Admin.query.get_or_404(admin_id)
    
    # Non permettere di modificare se stessi
    if int(admin_id) == session.get('admin_id'):
        flash('Non puoi modificare il tuo account da questa pagina.', 'danger')
        return redirect(url_for('admin_admins'))
    
    # Verifica che le password corrispondano se fornite
    if password:
        if password != confirm_password:
            flash('Le password non corrispondono.', 'danger')
            return redirect(url_for('admin_admins'))
        admin.set_password(password)
    
    # Verifica che lo username non sia già in uso da un altro admin
    existing_admin = Admin.query.filter_by(username=username).first()
    if existing_admin and existing_admin.id != int(admin_id):
        flash('Nome utente già in uso.', 'danger')
        return redirect(url_for('admin_admins'))
    
    # Aggiorna i dati
    admin.username = username
    admin.email = email
    admin.is_super_admin = is_super_admin
    
    db.session.commit()
    
    flash('Amministratore aggiornato con successo.', 'success')
    return redirect(url_for('admin_admins'))


@app.route('/admin/admins/toggle_status', methods=['POST'])
def admin_toggle_admin_status():
    """Attiva/disattiva un amministratore."""
    if session.get('admin_logged_in') != True or not session.get('is_super_admin', False):
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per eseguire questa azione.'
        })
    
    data = request.json
    admin_id = data.get('admin_id')
    active = data.get('active')
    
    # Trova l'amministratore
    admin = Admin.query.get_or_404(admin_id)
    
    # Non permettere di disattivare se stessi o un super admin
    if int(admin_id) == session.get('admin_id'):
        return jsonify({
            'success': False,
            'message': 'Non puoi disattivare il tuo account.'
        })
    
    if admin.is_super_admin:
        return jsonify({
            'success': False,
            'message': 'Non puoi disattivare un Super Admin.'
        })
    
    # Aggiorna lo stato
    admin.active = active
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Amministratore {"attivato" if active else "disattivato"} con successo.'
    })


@app.route('/admin/admins/get_data')
def admin_get_admin_data():
    """Ottiene i dati di un amministratore per la modifica."""
    if session.get('admin_logged_in') != True or not session.get('is_super_admin', False):
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per eseguire questa azione.'
        })
    
    admin_id = request.args.get('admin_id')
    
    # Trova l'amministratore
    admin = Admin.query.get_or_404(admin_id)
    
    return jsonify({
        'success': True,
        'admin': {
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'is_super_admin': admin.is_super_admin,
            'active': admin.active
        }
    })


@app.route('/admin/employees')
def admin_employees():
    """Gestione dipendenti per l'amministratore."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    employees = Employee.query.order_by(Employee.last_name).all()
    return render_template('admin_employees.html', employees=employees)


@app.route('/admin/operators')
def admin_operators():
    """Gestione operatori per l'amministratore."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    operators = Operator.query.all()
    return render_template('admin_operators.html', operators=operators)


@app.route('/admin/products')
def admin_products():
    """Gestione prodotti per l'amministratore."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/delete/<int:id>', methods=['POST'])

def admin_delete_product(id):
    # recupera il prodotto dal DB
    product = Product.query.get_or_404(id)
    # elimina e conferma
    db.session.delete(product)
    db.session.commit()
    flash(f"Prodotto #{id} eliminato con successo.", 'success')
    # torna alla lista prodotti
    return redirect(url_for('admin_products')) 

@app.route('/admin/reports')
def admin_reports():
    """Reports giornalieri o per periodo per l'amministratore."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    try:
        # Determina se è un report giornaliero o per periodo
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        date_str = request.args.get('date')
        
        # Imposta il fuso orario locale (Europe/Rome)
        local_tz = pytz.timezone('Europe/Rome')
        
        if start_date_str and end_date_str:
            # Report per periodo
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Imposta l'ora di inizio e fine
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Converti in UTC per il filtro sul database
            start_date_utc = local_tz.localize(start_date).astimezone(pytz.UTC)
            end_date_utc = local_tz.localize(end_date).astimezone(pytz.UTC)
            
            report_title = f"Report dal {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}"
            report_date = end_date  # Usa la data di fine come data di riferimento
        else:
            # Report giornaliero
            if date_str:
                report_date = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                # Data di default = oggi
                report_date = datetime.now()
            
            # Imposta l'ora di inizio e fine
            start_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = report_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Converti in UTC per il filtro sul database
            start_date_utc = local_tz.localize(start_date).astimezone(pytz.UTC)
            end_date_utc = local_tz.localize(end_date).astimezone(pytz.UTC)
            
            report_title = f"Report del {report_date.strftime('%d/%m/%Y')}"
        
        logger.info(f"Filtering transactions between {start_date_utc} and {end_date_utc}")
        
        # Carica le transazioni con le relazioni
        transactions = Transaction.query.filter(
            Transaction.timestamp >= start_date_utc,
            Transaction.timestamp <= end_date_utc
        ).order_by(Transaction.timestamp.desc()).all()
        
        logger.info(f"Found {len(transactions)} transactions")
        
        # Prepara i dati delle transazioni per il template
        transaction_data = []
        for t in transactions:
            # Ottieni i dati del dipendente
            employee_name = f"{t.employee.first_name} {t.employee.last_name}" if t.employee else "N/A"
            
            # Ottieni i dati del prodotto
            if t.product:
                product_name = t.product.name
            else:
                product_name = t.custom_product_name if t.custom_product_name else "N/A"
            
            # Ottieni i dati dell'operatore
            operator_name = t.operator.username if t.operator else "N/A"
            
            # Converti il timestamp UTC in ora locale
            local_timestamp = t.timestamp.replace(tzinfo=pytz.UTC).astimezone(local_tz)
            
            # Aggiungi i dati alla lista
            transaction_data.append({
                'id': t.id,
                'timestamp': local_timestamp,
                'amount': float(t.amount),
                'transaction_type': t.transaction_type,
                'employee_name': employee_name,
                'product_name': product_name,
                'operator_name': operator_name,
                'quantity': t.quantity if t.quantity else 1
            })
        
        # Statistiche del periodo
        credit_sum = sum([t.amount for t in transactions if t.transaction_type == 'credit'])
        debit_sum = sum([abs(t.amount) for t in transactions if t.transaction_type == 'debit'])
        
        # Raggruppa per operatore
        operator_stats = {}
        for t in transactions:
            if t.operator_id:
                operator_name = t.operator.username
                if operator_name not in operator_stats:
                    operator_stats[operator_name] = {'credit': 0, 'debit': 0}
                
                if t.transaction_type == 'credit':
                    operator_stats[operator_name]['credit'] += float(t.amount)
                else:
                    operator_stats[operator_name]['debit'] += float(abs(t.amount))
        
        # Raggruppa per prodotto
        product_stats = {}
        product_total_quantity = 0
        product_total_amount = 0
        
        for t in transactions:
            if t.transaction_type == 'debit':
                # Determina il nome del prodotto e la quantità
                product_name = None
                quantity = t.quantity if t.quantity else 1  # Usa la quantità salvata nella transazione
                
                if t.product:
                    product_name = t.product.name
                elif t.custom_product_name:
                    # Controlla se c'è una quantità nel nome del prodotto personalizzato
                    # Formato: "Nome prodotto (x2)"
                    product_name = t.custom_product_name
                    quantity_match = re.search(r'\(x(\d+)\)', product_name)
                    if quantity_match:
                        try:
                            quantity = int(quantity_match.group(1))
                            # Rimuovi la parte della quantità dal nome
                            product_name = re.sub(r'\s*\(x\d+\)', '', product_name)
                        except ValueError:
                            quantity = 1
                
                # Escludi i prelievi cassa da amministratore dal riepilogo prodotti
                if product_name and product_name != "Prelievo cassa da amministratore":
                    # Aggiungi o aggiorna le statistiche del prodotto
                    if product_name not in product_stats:
                        # Cerca il prodotto nel database per ottenere la giacenza attuale
                        current_inventory = 0
                        if t.product:
                            current_inventory = t.product.inventory
                        
                        product_stats[product_name] = {
                            'quantity': 0, 
                            'total': 0,
                            'inventory': current_inventory,
                            'product_id': t.product_id if t.product else None
                        }
                    
                    product_stats[product_name]['quantity'] += quantity
                    product_stats[product_name]['total'] += float(abs(t.amount))
                    
                    # Aggiorna i totali
                    product_total_quantity += quantity
                    product_total_amount += float(abs(t.amount))
        
        return render_template(
            'admin_reports.html',
            transactions=transaction_data,
            report_date=report_date,
            report_title=report_title,
            is_period_report=bool(start_date_str and end_date_str),
            start_date=start_date if start_date_str else None,
            end_date=end_date if end_date_str else None,
            credit_sum=float(credit_sum),
            debit_sum=float(debit_sum),
            operator_stats=operator_stats,
            product_stats=product_stats,
            product_total_quantity=product_total_quantity,
            product_total_amount=product_total_amount
        )
    
    except Exception as e:
        logger.error(f"Error in admin_reports: {str(e)}")
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/regenerate_passwords', methods=['POST'])
def admin_regenerate_passwords():
    """Rigenera le password di tutti gli operatori."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    passwords = regenerate_all_operator_passwords()
    
    return jsonify({
        'success': True,
        'message': 'Password rigenerate con successo.',
        'passwords': passwords
    })


@app.route('/admin/employee/new', methods=['GET', 'POST'])
def admin_new_employee():
    """Crea un nuovo dipendente."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        rank = request.form.get('rank')
        credit_limit = request.form.get('credit_limit', '0')
        operator_password = request.form.get('operator_password')
        redirect_to = request.form.get('redirect_to', '')
        
        try:
            # Verifica che tutti i campi obbligatori siano presenti
            if not all([code, first_name, last_name, rank]):
                flash('Tutti i campi obbligatori devono essere compilati.', 'danger')
                if redirect_to == 'barcode_scanner' or (request.referrer and 'barcode_scanner' in request.referrer):
                    return redirect(url_for('barcode_scanner'))
                return redirect(url_for('admin_new_employee'))
            
            # Se viene dalla pagina barcode_scanner, verifica la password operatore
            if redirect_to == 'barcode_scanner' or (request.referrer and 'barcode_scanner' in request.referrer):
                if not operator_password:
                    flash('Password operatore richiesta per aggiungere un nuovo dipendente.', 'danger')
                    return redirect(url_for('barcode_scanner'))
                
                # Verifica che la password dell'operatore sia valida
                operator = Operator.query.filter_by(password=operator_password, active=True).first()
                if not operator:
                    flash('Password operatore non valida.', 'danger')
                    return redirect(url_for('barcode_scanner'))
            
            # Controlla se il codice già esiste
            existing = Employee.query.filter_by(code=code).first()
            if existing:
                flash('Esiste già un dipendente con questo codice.', 'danger')
                # Determina dove reindirizzare in caso di errore
                if redirect_to == 'barcode_scanner' or (request.referrer and 'barcode_scanner' in request.referrer):
                    return redirect(url_for('barcode_scanner'))
                return redirect(url_for('admin_new_employee'))
            
            # Crea il nuovo dipendente
            employee = Employee(
                code=code,
                first_name=first_name,
                last_name=last_name,
                rank=rank,
                credit=0,
                credit_limit=Decimal(credit_limit)
            )
            employee.update_credit_hash()
            
            db.session.add(employee)
            db.session.commit()
            
            flash('Dipendente aggiunto con successo.', 'success')
            
            # Determina dove reindirizzare dopo il successo
            if redirect_to == 'barcode_scanner' or (request.referrer and 'barcode_scanner' in request.referrer):
                return redirect(url_for('barcode_scanner'))
            else:
                return redirect(url_for('admin_employees'))
            
        except Exception as e:
            flash(f'Errore: {str(e)}', 'danger')
            # Determina dove reindirizzare in caso di errore
            if redirect_to == 'barcode_scanner' or (request.referrer and 'barcode_scanner' in request.referrer):
                return redirect(url_for('barcode_scanner'))
            return redirect(url_for('admin_new_employee'))
    
    # In caso di GET request, mostra il form
    return render_template('admin_new_employee.html')


@app.route('/admin/employee/<int:id>', methods=['GET', 'POST'])
def admin_edit_employee(id):
    """Modifica un dipendente esistente."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    employee = Employee.query.get_or_404(id)
    
    if request.method == 'POST':
        employee.code = request.form.get('code')
        employee.first_name = request.form.get('first_name')
        employee.last_name = request.form.get('last_name')
        employee.rank = request.form.get('rank')
        
        try:
            credit_limit = Decimal(request.form.get('credit_limit', '0'))
            employee.credit_limit = credit_limit
            
            # Aggiorna l'hash per riflettere il nuovo limite di credito
            employee.update_credit_hash()
            
            db.session.commit()
            flash('Dipendente aggiornato con successo.', 'success')
            return redirect(url_for('admin_employees'))
            
        except Exception as e:
            flash(f'Errore: {str(e)}', 'danger')
    
    return render_template('admin_edit_employee.html', employee=employee)


@app.route('/admin/employee/<int:id>/adjust_credit', methods=['POST'])
def admin_adjust_credit(id):
    """Modifica direttamente il credito di un dipendente (solo per amministratori)."""
    if session.get('admin_logged_in') != True:
        return jsonify({
            'success': False,
            'message': 'Non sei autorizzato a eseguire questa operazione.'
        })
    
    try:
        # Ottieni i dati dalla richiesta
        data = request.json
        new_credit = data.get('new_credit')
        reason = data.get('reason')
        
        if new_credit is None:
            return jsonify({
                'success': False,
                'message': 'Nuovo credito non specificato.'
            })
        
        if not reason or not reason.strip():
            return jsonify({
                'success': False,
                'message': 'Motivo della modifica obbligatorio.'
            })
        
        # Trova il dipendente
        employee = Employee.query.get_or_404(id)
        
        # Salva il credito precedente per il calcolo della differenza
        old_credit = employee.credit
        new_credit_decimal = Decimal(str(new_credit))
        difference = new_credit_decimal - old_credit
        
        # Se non c'è differenza, non fare nulla
        if abs(difference) < Decimal('0.01'):
            return jsonify({
                'success': False,
                'message': 'Il nuovo credito è identico a quello attuale.'
            })
        
        # Aggiorna il credito del dipendente
        employee.update_credit(new_credit_decimal)
        
        # Registra la transazione amministrativa
        # IMPORTANTE: Questa transazione NON influisce sulla cassa
        transaction = Transaction(
            employee_id=employee.id,
            amount=difference,  # La differenza (positiva o negativa)
            transaction_type='admin_adjustment',  # Tipo speciale per distinguerla
            custom_product_name=f"Regolazione amministrativa: {reason.strip()}"
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        # Messaggio di successo
        sign = '+' if difference > 0 else ''
        message = f'Credito modificato con successo. Variazione: {sign}€{float(difference):.2f}'
        
        return jsonify({
            'success': True,
            'message': message,
            'old_credit': float(old_credit),
            'new_credit': float(new_credit_decimal),
            'difference': float(difference)
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': 'Valore del credito non valido.'
        })
    except Exception as e:
        logger.error(f"Error in admin_adjust_credit: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Errore durante la modifica: {str(e)}'
        })


@app.route('/admin/product/new', methods=['GET', 'POST'])
def admin_new_product():
    """Crea un nuovo prodotto."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        inventory = request.form.get('inventory', '0')
        
        try:
            product = Product(
                name=name,
                price=Decimal(price),
                inventory=int(inventory),
                active=True
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('Prodotto aggiunto con successo.', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            flash(f'Errore: {str(e)}', 'danger')
    
    return render_template('admin_new_product.html')


@app.route('/admin/product/<int:id>', methods=['GET', 'POST'])
def admin_edit_product(id):
    """Modifica un prodotto esistente."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = Decimal(request.form.get('price'))
        product.active = 'active' in request.form
        
        # Aggiorna la giacenza se fornita
        if 'inventory' in request.form:
            try:
                product.inventory = int(request.form.get('inventory'))
            except ValueError:
                flash('Valore di giacenza non valido.', 'danger')
                return redirect(url_for('admin_edit_product', id=id))
        
        db.session.commit()
        flash('Prodotto aggiornato con successo.', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin_edit_product.html', product=product)


@app.route('/admin/product/<int:id>/restock', methods=['POST'])
def admin_restock_product(id):
    """Ricarica la giacenza di un prodotto."""
    if session.get('admin_logged_in') != True:
        return redirect(url_for('admin_login'))
    
    product = Product.query.get_or_404(id)
    
    try:
        quantity = int(request.form.get('quantity', 0))
        
        if quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'La quantità deve essere maggiore di zero.'
            })
        
        # Aggiorna la giacenza
        product.inventory += quantity
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Giacenza aggiornata con successo. Nuova giacenza: {product.inventory}',
            'new_inventory': product.inventory
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Valore di quantità non valido.'
        })
    except Exception as e:
        logger.error(f"Error in admin_restock_product: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        })

    
@app.route('/admin/logout')
def admin_logout():
    """Gestisce il logout dell'amministratore."""
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    session.pop('is_super_admin', None)
    return redirect(url_for('barcode_scanner'))

@app.route('/import_export')
@login_required
def import_export():
    """Pagina import/export."""
    return render_template('import_export.html')


@app.route('/export_csv')
@login_required
def export_csv():
    """Esporta dipendenti in CSV."""
    output = export_employees_to_csv()
    return output, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=employees.csv'
    }


@app.route('/export_excel')
@login_required
def export_excel():
    """Esporta dipendenti in Excel."""
    try:
        output, ext = export_employees_to_excel()
        
        if ext == 'csv':
            # Fallback a CSV se Excel non è disponibile
            return output, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename=employees.csv'
            }
        else:
            # Restituisci Excel
            return output, 200, {
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'Content-Disposition': 'attachment; filename=employees.xlsx'
            }
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        flash(f'Errore durante l\'esportazione: {str(e)}', 'danger')
        return redirect(url_for('import_export'))


@app.route('/import_csv', methods=['POST'])
@login_required
def import_csv():
    """Importa dipendenti da CSV o Excel."""
    if 'file' not in request.files:
        flash('Nessun file selezionato.', 'warning')
        return redirect(url_for('import_export'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nessun file selezionato.', 'warning')
        return redirect(url_for('import_export'))
    
    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        success, message = import_employees_from_file(file)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    else:
        flash('Formato file non supportato. Utilizzare CSV o XLSX.', 'warning')
    
    return redirect(url_for('import_export'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Pagina impostazioni."""
    if request.method == 'POST':
        # Gestisci l'aggiornamento del limite di credito globale
        if 'global_credit_limit' in request.form:
            try:
                credit_limit = Decimal(request.form.get('global_credit_limit', '0'))
                GlobalSetting.set('credit_limit', str(credit_limit), 'Limite di credito negativo globale')
                flash('Limite di credito globale aggiornato con successo.', 'success')
            except Exception as e:
                flash(f'Errore durante l\'aggiornamento del limite di credito: {str(e)}', 'danger')
        
        return redirect(url_for('settings'))
    
    # Ottieni il limite di credito globale
    global_credit_limit = GlobalSetting.get('credit_limit', '0')
    
    # Ottieni le statistiche di sistema
    stats = get_system_stats()
    
    return render_template(
        'settings.html', 
        global_credit_limit=global_credit_limit,
        **stats
    )


@app.route('/change_admin_password', methods=['POST'])
@login_required
def change_admin_password():
    """Cambia password admin."""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    admin = Admin.query.get(current_user.id)
    
    if not admin.check_password(current_password):
        flash('Password attuale non corretta.', 'danger')
    elif new_password != confirm_password:
        flash('Le nuove password non corrispondono.', 'danger')
    elif len(new_password) < 6:
        flash('La nuova password deve essere di almeno 6 caratteri.', 'danger')
    else:
        admin.set_password(new_password)
        db.session.commit()
        flash('Password modificata con successo.', 'success')
    
    return redirect(url_for('settings'))


@app.route('/check_all_integrity')
@login_required
def check_all_integrity():
    """Verifica integrità di tutti i dipendenti."""
    ok, issues = check_integrity_all_employees()
    
    if ok:
        return jsonify({
            'success': True,
            'message': 'Verifica integrità completata. Nessun problema rilevato.',
            'issues': []
        })
    else:
        return jsonify({
            'success': True,
            'message': f'Verifica integrità completata. Rilevati {len(issues)} problemi e risolti automaticamente.',
            'issues': issues
        })


@app.route('/reset_all_hashes')
@login_required
def reset_all_hashes():
    """Ripristina tutti gli hash di integrità."""
    count = reset_all_credit_hashes()
    
    return jsonify({
        'success': True,
        'message': f'Rigenerati {count} hash di integrità con successo.',
        'count': count
    })


@app.route('/api/system_stats')
@login_required
def api_system_stats():
    """API per ottenere statistiche del sistema."""
    return jsonify(get_system_stats())


@app.route('/api/serial_status')
@login_required
def api_serial_status():
    """API per verificare lo stato del lettore seriale."""
    status = {
        'available': SERIAL_AVAILABLE,
        'connected': serial_port is not None and serial_port.is_open if serial_port else False,
        'last_barcode': get_last_barcode(),
        'config': SERIAL_CONFIG
    }
    return jsonify(status)


@app.route('/update_serial_config', methods=['POST'])
@login_required
def update_serial_config():
    """Aggiorna configurazione lettore seriale."""
    global SERIAL_CONFIG, serial_port
    
    # Aggiorna la configurazione
    SERIAL_CONFIG['port'] = request.form.get('serial_port', SERIAL_CONFIG['port'])
    SERIAL_CONFIG['baudrate'] = int(request.form.get('baud_rate', SERIAL_CONFIG['baudrate']))
    SERIAL_CONFIG['bytesize'] = int(request.form.get('data_bits', SERIAL_CONFIG['bytesize']))
    SERIAL_CONFIG['parity'] = request.form.get('parity', SERIAL_CONFIG['parity'])
    SERIAL_CONFIG['stopbits'] = int(request.form.get('stop_bits', SERIAL_CONFIG['stopbits']))
    
    # Riavvia il lettore
    if serial_port and serial_port.is_open:
        serial_port.close()
    
    success = setup_barcode_reader()
    
    if success:
        flash('Configurazione del lettore aggiornata con successo.', 'success')
    else:
        flash('Impossibile connettersi al lettore con i nuovi parametri.', 'danger')
    
    return redirect(url_for('settings'))


@app.context_processor
def inject_app_info():
    """Inietta informazioni sull'app in tutti i template."""
    now = datetime.now()
    
    return {
        'app_name': app.config['APP_NAME'],
        'app_version': app.config['APP_VERSION'],
        'now': now
    }


if __name__ == '__main__':
    """Punto di ingresso principale."""
    # Crea tabelle e dati iniziali
    with app.app_context():
        db.create_all()
        
        # Crea l'admin se non esiste
        if not Admin.query.first():
            admin = Admin(
                username='admin',
                is_super_admin=True,
                active=True
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            logger.info("Super admin account created")
        
        # Crea gli operatori standard
        ensure_operators_exist()
        
        # Crea l'utente "cassa" per acquisti anonimi
        ensure_cash_register_exists()
        
        # Inizializza il limite di credito globale se non esiste
        if not GlobalSetting.get('credit_limit'):
            GlobalSetting.set('credit_limit', '50', 'Limite di credito negativo globale')
            logger.info("Initialized global credit limit")
        
        # Aggiorna gli hash del credito per i dipendenti esistenti che non ne hanno
        employees = Employee.query.all()
        count = 0
        for employee in employees:
            if not employee.credit_hash:
                employee.update_credit_hash()
                count += 1
        
        if count > 0:
            db.session.commit()
            logger.info(f"Updated credit hash for {count} employees")
    
    # Avvia il lettore di codici a barre seriale se disponibile
    try:
        if SERIAL_AVAILABLE:
            setup_barcode_reader()
    except Exception as e:
        logger.warning(f"Barcode reader not initialized: {str(e)}")
    
    # Avvia il server
    app.run(debug=True, host='0.0.0.0', port=8100)
