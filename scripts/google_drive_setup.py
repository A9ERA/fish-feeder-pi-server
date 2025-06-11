#!/usr/bin/env python3
"""
🗂️ GOOGLE DRIVE SETUP SCRIPT
============================
Step-by-step setup for Google Drive integration with Fish Feeder
"""

import json
import webbrowser
import sys
from pathlib import Path

def print_banner():
    """Print setup banner"""
    print("🗂️" * 50)
    print("🗂️ GOOGLE DRIVE INTEGRATION SETUP")
    print("🗂️" * 50)
    print()

def show_google_cloud_instructions():
    """Show detailed Google Cloud Console instructions"""
    print("📋 STEP-BY-STEP GOOGLE DRIVE SETUP:")
    print("=" * 50)
    print()
    
    print("🌐 STEP 1: Access Google Cloud Console")
    print("   1. Go to: https://console.cloud.google.com/")
    print("   2. Sign in with your Google account (the one with 200GB Drive)")
    print()
    
    print("📂 STEP 2: Create or Select Project")
    print("   1. Click 'Select a project' dropdown")
    print("   2. Click 'NEW PROJECT'")
    print("   3. Project name: 'Fish-Feeder-Storage'")
    print("   4. Click 'CREATE'")
    print()
    
    print("🔌 STEP 3: Enable Google Drive API")
    print("   1. Go to 'APIs & Services' > 'Library'")
    print("   2. Search for 'Google Drive API'")
    print("   3. Click on 'Google Drive API'")
    print("   4. Click 'ENABLE'")
    print()
    
    print("🔑 STEP 4: Create Credentials")
    print("   1. Go to 'APIs & Services' > 'Credentials'")
    print("   2. Click '+ CREATE CREDENTIALS'")
    print("   3. Select 'OAuth client ID'")
    print("   4. If prompted, configure OAuth consent screen:")
    print("      - User Type: External")
    print("      - App name: Fish Feeder Storage")
    print("      - User support email: your email")
    print("      - Developer contact: your email")
    print("      - Save and continue through all steps")
    print("   5. Application type: 'Desktop application'")
    print("   6. Name: 'Fish Feeder Pi'")
    print("   7. Click 'CREATE'")
    print()
    
    print("📥 STEP 5: Download Credentials")
    print("   1. Click 'DOWNLOAD JSON' button")
    print("   2. Save the file to your computer")
    print("   3. Rename it to: google_drive_credentials.json")
    print()

def check_credentials_file():
    """Check if credentials file exists"""
    cred_file = Path('google_drive_credentials.json')
    
    if cred_file.exists():
        print("✅ Found google_drive_credentials.json")
        
        # Validate JSON format
        try:
            with open(cred_file, 'r') as f:
                creds = json.load(f)
            
            if 'installed' in creds and 'client_id' in creds['installed']:
                print("✅ Credentials file looks valid")
                return True
            else:
                print("❌ Invalid credentials format")
                return False
                
        except json.JSONDecodeError:
            print("❌ Invalid JSON format")
            return False
    else:
        print("❌ google_drive_credentials.json not found")
        return False

def test_google_drive_connection():
    """Test Google Drive API connection"""
    print("\n🧪 Testing Google Drive connection...")
    
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = None
        
        # Load token if exists
        token_file = 'google_drive_token.json'
        if Path(token_file).exists():
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
        # Get new credentials if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing expired token...")
                creds.refresh(Request())
            else:
                print("🔐 Starting OAuth flow...")
                print("📱 Your browser will open for authorization")
                print("📝 Please sign in and grant permissions")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'google_drive_credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print("✅ Token saved for future use")
        
        # Test API connection
        print("🔍 Testing API connection...")
        service = build('drive', 'v3', credentials=creds)
        
        # Try to list files (just to test connection)
        results = service.files().list(pageSize=1).execute()
        print("✅ Google Drive API connection successful!")
        
        # Create Fish Feeder folder
        print("📂 Creating Fish Feeder Videos folder...")
        folder_name = 'Fish Feeder Videos'
        
        # Check if folder exists
        folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        existing = service.files().list(q=folder_query).execute()
        
        if existing['files']:
            folder_id = existing['files'][0]['id']
            print(f"✅ Found existing folder: {folder_name}")
        else:
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder['id']
            print(f"✅ Created new folder: {folder_name}")
        
        # Update storage config with folder ID
        update_storage_config(folder_id)
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("💡 Install with: pip3 install google-auth google-auth-oauthlib google-api-python-client")
        return False
    except Exception as e:
        print(f"❌ Google Drive setup failed: {e}")
        return False

def update_storage_config(folder_id):
    """Update storage config with Google Drive settings"""
    config_file = 'storage_config.json'
    
    if Path(config_file).exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        print("⚠️  storage_config.json not found, creating basic config")
        config = {"google_drive": {}}
    
    # Update Google Drive settings
    config['google_drive'] = {
        "enabled": True,
        "folder_name": "Fish Feeder Videos",
        "folder_id": folder_id,
        "credentials_file": "google_drive_credentials.json",
        "token_file": "google_drive_token.json"
    }
    
    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Updated storage_config.json with Google Drive settings")

def show_completion_message():
    """Show setup completion message"""
    print("\n" + "🎉" * 50)
    print("🎉 GOOGLE DRIVE SETUP COMPLETE!")
    print("🎉" * 50)
    print()
    print("📊 Google Drive Integration Ready:")
    print("   - 200GB storage available")
    print("   - Auto-migration from Firebase")
    print("   - Long-term video archive")
    print()
    print("🔄 Migration Process:")
    print("   1. Videos recorded locally (Pi)")
    print("   2. Uploaded to Firebase (immediate)")
    print("   3. Migrated to Google Drive (after 24h)")
    print("   4. Cleaned from local storage (after 7 days)")
    print()
    print("📁 Files created:")
    print("   - google_drive_credentials.json (keep secure)")
    print("   - google_drive_token.json (auto-generated)")
    print("   - storage_config.json (updated)")
    print()
    print("💡 Pro Tips:")
    print("   - Check folder: https://drive.google.com")
    print("   - Monitor usage in Google account settings")
    print("   - Videos will be in 'Fish Feeder Videos' folder")
    print()

def main():
    """Main Google Drive setup"""
    print_banner()
    
    print("🎯 This script will set up Google Drive integration for your Fish Feeder")
    print("📦 You'll get 200GB storage for long-term video archive")
    print()
    
    # Step 1: Show instructions
    show_google_cloud_instructions()
    
    print("💡 INSTRUCTIONS SUMMARY:")
    print("1. Create Google Cloud project")
    print("2. Enable Google Drive API")
    print("3. Create OAuth credentials")
    print("4. Download as google_drive_credentials.json")
    print("5. Place file in pi-mqtt-server directory")
    print()
    
    if input("Have you completed the above steps? (y/n): ").lower() != 'y':
        print("📖 Please complete the setup steps and run this script again")
        return
    
    # Step 2: Check credentials
    if not check_credentials_file():
        print("\n❌ Credentials file issue")
        print("💡 Please:")
        print("   1. Download credentials from Google Cloud Console")
        print("   2. Rename to: google_drive_credentials.json")
        print("   3. Place in this directory")
        return
    
    # Step 3: Test connection and setup
    if test_google_drive_connection():
        show_completion_message()
    else:
        print("\n❌ Google Drive setup failed")
        print("💡 Check the error messages above and try again")

if __name__ == "__main__":
    main() 