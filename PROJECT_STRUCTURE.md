# 🐟 Fish Feeder Pi Project Structure

## 📁 Core Files
- `main.py` - Main application server (Flask + WebSocket + Arduino control)
- `sensor_history_manager.py` - Sensor data storage and analytics
- `serviceAccountKey.json` - Firebase authentication credentials
- `requirements.txt` - Python dependencies
- `README.md` - Project documentation
- `API_REFERENCE.md` - Complete JSON API documentation
- `PROJECT_STRUCTURE.md` - Project organization guide
- `VERSION` - Version information
- `.gitignore` - Git ignore rules

## 📁 Directories

### `config/`
- `storage_config.json` - Storage configuration
- `google_drive_credentials.json` - Google Drive API credentials  
- `client_secret_1_*.json` - Google OAuth client secret

### `data/`
- `sensor_history/` - Historical sensor data storage

### `docs/`
- Complete documentation including:
  - FINAL_STATUS_v2.0.0.md
  - RELEASE_NOTES_v2.0.0.md
  - SETUP_COMPLETE.md
  - DEPLOY_INSTRUCTIONS.md
  - And more...

### `logs/`
- System and sensor logs (auto-generated)

## 📋 Project Status
✅ **CLEANED & ORGANIZED**
- Removed duplicate files
- Deleted unused scripts and archives
- Organized configuration files
- Clean project structure
- All dependencies properly defined

## 🚀 Usage
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

## 🔧 Key Features
- Arduino sensor monitoring
- Real-time WebSocket updates
- Firebase cloud sync
- Web dashboard interface
- Automated fish feeding control
- Energy monitoring (solar/battery)
- Historical data analytics 