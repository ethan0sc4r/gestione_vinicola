# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Gestione Vinicola** is a Flask-based employee credit management system designed for a wine company. It features barcode scanning integration, secure credit transactions, and comprehensive administrative controls for managing employee purchases and credit loading.

## Development Commands

### Building and Running
```bash
# Build the application (Windows)
build.bat

# Verify build integrity
verify_build.bat

# Run the application directly (development)
python app.py

# Install dependencies
pip install -r requirements.txt
```

### Database Operations
The application uses SQLite with automatic schema creation. Database file is located at `instance/vinicola.db`.

### Serial Configuration
Serial port settings are managed through `config_serial.json`. The application automatically copies `config_serial_windows.json` to `config_serial.json` if it doesn't exist during build.

## Architecture Overview

### Core Components

**Flask Application Structure:**
- **Main App**: Single-file Flask application (`app.py`) with all routes and models
- **Database**: SQLAlchemy with SQLite backend, models include Employee, Admin, Operator, Product, Transaction, GlobalSetting
- **Authentication**: Dual system - Flask-Login for employees, session-based for admins
- **Serial Integration**: PySerial for barcode reader communication with background threading
- **Real-time Updates**: SocketIO for live browser updates from barcode scans

### Key Models
- `Employee` - Credit management with SHA256 hash integrity verification
- `Admin` - Role-based admin access (super admin and regular admin roles)
- `Operator` - Credit loading users (10 standard operators with auto-generated passwords)
- `Product` - Item catalog with inventory tracking
- `Transaction` - Complete audit trail of all credit operations

### Security Features
- Credit integrity protection using SHA256 hashes
- Automatic credit integrity verification and repair
- Role-based access control
- Transaction audit logging

## Project Structure

```
├── app.py                          # Main Flask application
├── app.spec                        # PyInstaller specification
├── config_serial.json              # Serial port configuration (runtime)
├── config_serial_windows.json      # Default Windows serial config
├── requirements.txt                # Python dependencies
├── build.bat                       # Build script for Windows
├── verify_build.bat               # Build verification script
├── templates/                      # Jinja2 HTML templates
├── static/                         # Static assets (CSS, JS, images, sounds)
│   ├── css/                       # Bootstrap and FontAwesome (offline)
│   ├── js/                        # jQuery and Bootstrap JS (offline)
│   └── sounds/                    # Audio feedback files
├── instance/                      # Flask instance folder
│   └── vinicola.db               # SQLite database
└── dist/                          # PyInstaller build output
```

## Offline Functionality

The application is designed to work completely offline:
- Bootstrap CSS/JS, FontAwesome, and jQuery are included locally
- All templates and static assets are bundled in the PyInstaller build
- No external dependencies during runtime

## Serial Communication

The barcode reader integration uses:
- Configurable serial port settings via JSON
- Background threading for continuous reading
- Duplicate prevention and buffer management
- Real-time WebSocket updates to connected clients
- Fallback graceful degradation if serial port unavailable

## Database Initialization

On first run, the application automatically creates:
- Database tables and relationships
- Default admin account (admin/admin)
- 10 standard operators with auto-generated passwords
- "Cassa" user for cash transactions
- Default global credit limits

## Development Notes

- The application runs on Flask development server by default
- SocketIO server runs on port 8100
- Logging is configured to both file (`vinicola.log`) and console
- Credit integrity checks run automatically and log security violations
- PyInstaller bundles everything into a single executable with external config file

## Configuration Management

The `config_serial.json` file remains external and editable after compilation, allowing users to modify serial port settings without rebuilding. The build process ensures this file is always available and writable.