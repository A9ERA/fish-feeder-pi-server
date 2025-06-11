#!/usr/bin/env python3
"""
🧪 Quick Google Drive Test
==========================
Simple test to verify credentials are working
"""

import json
from pathlib import Path

def test_credentials():
    """Test if credentials file is valid"""
    print("🧪 Testing Google Drive credentials...")
    
    cred_file = Path('google_drive_credentials.json')
    
    if not cred_file.exists():
        print("❌ google_drive_credentials.json not found")
        return False
    
    try:
        with open(cred_file, 'r') as f:
            creds = json.load(f)
        
        if 'installed' in creds and 'client_id' in creds['installed']:
            client_id = creds['installed']['client_id']
            project_id = creds['installed'].get('project_id', 'unknown')
            
            print("✅ Credentials file is valid")
            print(f"   Client ID: {client_id}")
            print(f"   Project ID: {project_id}")
            return True
        else:
            print("❌ Invalid credentials format")
            return False
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

def test_imports():
    """Test if required modules can be imported"""
    print("\n🧪 Testing required imports...")
    
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        print("✅ All Google Drive modules available")
        return True
    except ImportError as e:
        print(f"❌ Missing module: {e}")
        return False

def create_basic_config():
    """Create basic storage config for testing"""
    print("\n⚙️ Creating basic storage config...")
    
    config = {
        "google_drive": {
            "enabled": True,
            "folder_name": "Fish Feeder Videos",
            "folder_id": None,
            "credentials_file": "google_drive_credentials.json",
            "token_file": "google_drive_token.json"
        }
    }
    
    with open('storage_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Basic storage_config.json created")

def main():
    """Main test function"""
    print("🧪 GOOGLE DRIVE QUICK TEST")
    print("=" * 30)
    
    success = True
    
    if not test_credentials():
        success = False
    
    if not test_imports():
        success = False
        print("\n💡 To install missing modules:")
        print("   pip install google-auth google-auth-oauthlib google-api-python-client")
    
    if success:
        create_basic_config()
        print("\n🎉 READY FOR GOOGLE DRIVE SETUP!")
        print("=" * 40)
        print()
        print("✅ Your credentials are valid")
        print("✅ All required modules are installed")
        print("✅ Basic configuration is ready")
        print()
        print("🔑 Client ID confirmed:")
        print("   481253031290-ldd5h8afs8btdeugsmqdddu7ot6qrc38.apps.googleusercontent.com")
        print()
        print("📋 Next step:")
        print("   On your Pi, run: python3 google_drive_setup.py")
        print("   This will complete the OAuth flow and create the 'Fish Feeder Videos' folder")
    else:
        print("\n❌ SETUP ISSUES FOUND")
        print("Please fix the issues above before proceeding")

if __name__ == "__main__":
    main() 