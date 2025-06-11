#!/usr/bin/env python3
"""
🛠️ SETUP SCRIPT FOR SMART HYBRID STORAGE
========================================
Easy setup and configuration for Smart Hybrid Storage + PageKite
Run this on your Raspberry Pi to configure everything
"""

import os
import json
import sys
import subprocess
from pathlib import Path

def print_banner():
    """Print setup banner"""
    print("🚀" * 50)
    print("🐟 FISH FEEDER - SMART HYBRID STORAGE SETUP")
    print("🚀" * 50)
    print()

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        return False
    print("✅ Python version:", sys.version.split()[0])
    return True

def install_dependencies():
    """Install required packages"""
    print("\n📦 Installing dependencies...")
    
    # Update package list
    try:
        subprocess.run(['sudo', 'apt', 'update'], check=True)
        print("✅ Package list updated")
    except subprocess.CalledProcessError:
        print("⚠️ Failed to update package list")
    
    # Install system dependencies
    system_packages = [
        'python3-pip',
        'python3-venv',
        'libglib2.0-dev',
        'libgtk-3-dev',
        'libcairo2-dev',
        'libgirepository1.0-dev'
    ]
    
    for package in system_packages:
        try:
            subprocess.run(['sudo', 'apt', 'install', '-y', package], check=True)
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to install {package}")
    
    # Install Python packages
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_enhanced.txt'], check=True)
        print("✅ Python packages installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python packages")
        return False
    
    return True

def setup_directories():
    """Create required directories"""
    print("\n📁 Setting up directories...")
    
    base_path = Path('/home/pi/fish_feeder_data')
    directories = [
        base_path,
        base_path / 'videos',
        base_path / 'photos',
        base_path / 'temp',
        base_path / 'processing',
        base_path / 'logs'
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")
    
    # Set proper permissions
    try:
        subprocess.run(['sudo', 'chown', '-R', 'pi:pi', str(base_path)], check=True)
        subprocess.run(['chmod', '-R', '755', str(base_path)], check=True)
        print("✅ Permissions set")
    except subprocess.CalledProcessError:
        print("⚠️ Failed to set permissions")

def create_default_config():
    """Create default storage configuration"""
    print("\n⚙️ Creating default configuration...")
    
    config = {
        "local_storage": {
            "base_path": "/home/pi/fish_feeder_data",
            "max_size_gb": 100,
            "video_retention_days": 7,
            "cleanup_threshold_percent": 85
        },
        "firebase": {
            "enabled": True,
            "bucket_name": "fish-feeder-test-1.firebasestorage.app",
            "max_file_size_mb": 100,
            "retention_days": 30
        },
        "google_drive": {
            "enabled": False,  # Will be enabled after OAuth setup
            "folder_name": "Fish Feeder Videos",
            "folder_id": None,
            "credentials_file": "google_drive_credentials.json",
            "token_file": "google_drive_token.json"
        },
        "pagekite": {
            "enabled": False,  # Will be enabled manually
            "subdomain": "fishfeeder",
            "backend_port": 5000,
            "auto_start": False
        },
        "video_settings": {
            "resolution": [640, 480],
            "fps": 12,
            "quality": 40,
            "max_duration_seconds": 300,
            "auto_stop_after_feeding": True
        },
        "migration": {
            "enabled": True,
            "schedule_hour": 2,
            "min_age_hours": 24,
            "batch_size": 10
        }
    }
    
    with open('storage_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Default configuration created")

def setup_google_drive():
    """Setup Google Drive integration"""
    print("\n🗂️ Google Drive Setup")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project or select existing")
    print("3. Enable Google Drive API")
    print("4. Create credentials (Desktop application)")
    print("5. Download credentials JSON file")
    print("6. Rename it to 'google_drive_credentials.json'")
    print("7. Place it in this directory")
    
    if input("\nHave you completed the above steps? (y/n): ").lower() == 'y':
        if Path('google_drive_credentials.json').exists():
            print("✅ Google Drive credentials found")
            return True
        else:
            print("❌ Credentials file not found")
            return False
    return False

def setup_pagekite():
    """Setup PageKite"""
    print("\n🌐 PageKite Setup")
    print("1. Go to: https://pagekite.net/")
    print("2. Sign up for free account (2GB/month)")
    print("3. Choose your subdomain")
    
    subdomain = input("\nEnter your desired subdomain (e.g., fishfeeder): ").strip()
    if subdomain:
        # Update config
        with open('storage_config.json', 'r') as f:
            config = json.load(f)
        
        config['pagekite']['subdomain'] = subdomain
        config['pagekite']['enabled'] = True
        
        with open('storage_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ PageKite configured: https://{subdomain}.pagekite.me")
        return True
    
    return False

def test_camera():
    """Test camera functionality"""
    print("\n📷 Testing camera...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("✅ Camera working")
                return True
            else:
                print("❌ Camera not capturing")
        else:
            print("❌ Camera not found")
    except ImportError:
        print("❌ OpenCV not installed")
    
    return False

def create_systemd_service():
    """Create systemd service for auto-start"""
    print("\n🔧 Creating systemd service...")
    
    service_content = f"""[Unit]
Description=Fish Feeder Smart Hybrid Storage
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory={os.getcwd()}
ExecStart={sys.executable} main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path('/etc/systemd/system/fish-feeder.service')
    
    try:
        # Write service file
        with open('fish-feeder.service', 'w') as f:
            f.write(service_content)
        
        # Copy to systemd
        subprocess.run(['sudo', 'cp', 'fish-feeder.service', str(service_path)], check=True)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        
        print("✅ Systemd service created")
        print("To enable auto-start: sudo systemctl enable fish-feeder")
        print("To start now: sudo systemctl start fish-feeder")
        
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create systemd service")
        return False

def show_final_instructions():
    """Show final setup instructions"""
    print("\n" + "🎉" * 50)
    print("🎉 SETUP COMPLETE!")
    print("🎉" * 50)
    print()
    print("📋 Next steps:")
    print("1. Place your Firebase serviceAccountKey.json in this directory")
    print("2. Configure Google Drive (if not done):")
    print("   python3 -c 'from smart_hybrid_storage import SmartHybridStorage; s=SmartHybridStorage()'")
    print("3. Test the system: python3 main.py")
    print("4. Enable auto-start: sudo systemctl enable fish-feeder")
    print()
    print("🌐 Access your system:")
    print("- Local: http://localhost:5000")
    print("- Web App: https://fish-feeder-test-1.web.app")
    if Path('storage_config.json').exists():
        with open('storage_config.json', 'r') as f:
            config = json.load(f)
            if config['pagekite']['enabled']:
                subdomain = config['pagekite']['subdomain']
                print(f"- PageKite: https://{subdomain}.pagekite.me")
    print()
    print("📊 Storage Summary:")
    print("- Local: 128GB Pi Storage")
    print("- Firebase: 5GB (immediate upload)")
    print("- Google Drive: 200GB (auto-migration)")
    print("- Total: ~333GB effective storage")
    print()

def main():
    """Main setup function"""
    print_banner()
    
    if not check_python_version():
        return
    
    print("🔧 This script will set up Smart Hybrid Storage for your Fish Feeder")
    print("💾 Storage Strategy:")
    print("   1. Local Pi Storage (128GB) - Live recording")
    print("   2. Firebase Storage (5GB) - Immediate upload")
    print("   3. Google Drive (200GB) - Long-term archive")
    print("   4. PageKite Tunnel - External access")
    print()
    
    if input("Continue with setup? (y/n): ").lower() != 'y':
        print("Setup cancelled")
        return
    
    # Run setup steps
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Setting up directories", setup_directories),
        ("Creating configuration", create_default_config),
        ("Testing camera", test_camera),
        ("Creating systemd service", create_systemd_service)
    ]
    
    for step_name, step_func in steps:
        print(f"\n⚡ {step_name}...")
        if not step_func():
            print(f"❌ {step_name} failed")
            if input("Continue anyway? (y/n): ").lower() != 'y':
                return
    
    # Optional setups
    print("\n🔧 Optional Setups:")
    
    if input("Setup Google Drive integration? (y/n): ").lower() == 'y':
        setup_google_drive()
    
    if input("Setup PageKite tunnel? (y/n): ").lower() == 'y':
        setup_pagekite()
    
    show_final_instructions()

if __name__ == "__main__":
    main() 