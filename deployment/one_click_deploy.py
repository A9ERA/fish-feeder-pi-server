#!/usr/bin/env python3
"""
🚀 ONE-CLICK DEPLOY TO RASPBERRY PI
===================================
Complete automated deployment and setup for Fish Feeder Smart Hybrid Storage
"""

import subprocess
import sys
import time
import json
from pathlib import Path

def print_banner():
    print("🚀" * 50)
    print("🚀 ONE-CLICK DEPLOY - FISH FEEDER SMART SYSTEM")
    print("🚀" * 50)
    print()

def get_pi_config():
    """Get Pi connection configuration"""
    print("📡 Pi Connection Setup")
    print("=" * 30)
    
    # Try to load from config file
    config_file = Path("deploy_config.json")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"✅ Found config: {config['user']}@{config['host']}")
        
        if input("Use this configuration? (y/n): ").lower() == 'y':
            return config
    
    # Get new configuration
    print("\n🔧 Enter Pi connection details:")
    config = {
        'user': input("Pi username (default: pi): ").strip() or 'pi',
        'host': input("Pi hostname/IP (default: raspberrypi.local): ").strip() or 'raspberrypi.local',
        'path': '/home/pi/pi-mqtt-server'
    }
    
    # Save configuration
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved: {config['user']}@{config['host']}")
    return config

def check_prerequisites():
    """Check if all required files exist"""
    print("\n🔍 Checking prerequisites...")
    
    required_files = [
        'main.py',
        'smart_hybrid_storage.py',
        'google_drive_credentials.json',
        'storage_config.json',
        'requirements_enhanced.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
        else:
            print(f"   ✅ {file}")
    
    if missing_files:
        print(f"\n❌ Missing required files:")
        for file in missing_files:
            print(f"   ❌ {file}")
        return False
    
    print("✅ All required files found")
    return True

def test_pi_connection(config):
    """Test connection to Pi"""
    print(f"\n🔗 Testing connection to {config['host']}...")
    
    try:
        # Test ping
        result = subprocess.run(['ping', '-c', '1', config['host']], 
                              capture_output=True, timeout=10)
        if result.returncode != 0:
            print(f"❌ Cannot ping {config['host']}")
            return False
        
        # Test SSH
        ssh_cmd = f"ssh {config['user']}@{config['host']} 'echo connection_test'"
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, timeout=10)
        if result.returncode != 0:
            print(f"❌ SSH connection failed")
            print("💡 Make sure SSH is enabled on Pi and you can connect without password")
            return False
        
        print(f"✅ Connection to {config['host']} successful")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"❌ Connection timeout")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def deploy_files(config):
    """Deploy all files to Pi"""
    print(f"\n📦 Deploying files to {config['user']}@{config['host']}...")
    
    # Create directories
    ssh_cmd = f"ssh {config['user']}@{config['host']} 'mkdir -p {config['path']}/logs'"
    subprocess.run(ssh_cmd, shell=True)
    
    # Files to copy
    files_to_copy = [
        'main.py',
        'smart_hybrid_storage.py',
        'google_drive_credentials.json',
        'storage_config.json',
        'google_drive_setup.py',
        'test_google_drive.py',
        'setup_hybrid_storage.py',
        'pagekite_setup.py',
        'requirements_enhanced.txt',
        'start_pagekite.sh',
        'stop_pagekite.sh',
        'status_pagekite.sh',
        'README_HYBRID_STORAGE.md',
        'SETUP_COMPLETE.md',
        'serviceAccountKey.json'  # Optional
    ]
    
    for file in files_to_copy:
        if Path(file).exists():
            scp_cmd = f"scp {file} {config['user']}@{config['host']}:{config['path']}/"
            result = subprocess.run(scp_cmd, shell=True, capture_output=True)
            if result.returncode == 0:
                print(f"   ✅ {file}")
            else:
                print(f"   ⚠️  {file} (failed)")
        else:
            print(f"   ⚠️  {file} (not found)")
    
    # Set permissions
    ssh_cmd = f"ssh {config['user']}@{config['host']} 'chmod +x {config['path']}/*.sh {config['path']}/*.py'"
    subprocess.run(ssh_cmd, shell=True)
    
    print("✅ File deployment completed")

def create_auto_setup_script(config):
    """Create auto setup script on Pi"""
    print("\n🤖 Creating auto setup script on Pi...")
    
    setup_script = f'''#!/bin/bash
# 🤖 AUTO SETUP ON RASPBERRY PI
echo "🤖 Starting automatic setup on Raspberry Pi..."

cd {config['path']}

# Update system
echo "📦 Updating system packages..."
sudo apt update -y
sudo apt install -y python3-pip python3-venv git

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements_enhanced.txt

# Install PageKite
echo "🌐 Installing PageKite..."
pip3 install pagekite

# Setup directory structure
echo "📁 Setting up storage directories..."
sudo mkdir -p /home/pi/fish_feeder_data/{{videos,photos,temp,processing,logs}}
sudo chown -R pi:pi /home/pi/fish_feeder_data
chmod 755 -R /home/pi/fish_feeder_data

# Test installations
echo "🧪 Testing installations..."
python3 test_google_drive.py

# Create systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/fish-feeder.service > /dev/null <<EOL
[Unit]
Description=Fish Feeder Smart Hybrid Storage
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory={config['path']}
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH={config['path']}

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo "✅ AUTO SETUP COMPLETED!"
echo "========================"
echo ""
echo "📋 Next steps:"
echo "1. Run Google Drive OAuth: python3 google_drive_setup.py"
echo "2. Test system: python3 main.py"
echo "3. Enable auto-start: sudo systemctl enable fish-feeder"
echo "4. Start now: sudo systemctl start fish-feeder"
echo ""
echo "🌐 URLs when running:"
echo "- Local: http://localhost:5000"
echo "- PageKite: https://b65iee02.pagekite.me"
echo "- Web App: https://fish-feeder-test-1.web.app"
echo ""
echo "🎮 Control commands:"
echo "- Start PageKite: ./start_pagekite.sh"
echo "- Stop PageKite: ./stop_pagekite.sh"
echo "- Check status: ./status_pagekite.sh"
'''
    
    # Write script to Pi
    ssh_cmd = f"ssh {config['user']}@{config['host']} 'cat > {config['path']}/auto_setup_pi.sh'"
    process = subprocess.Popen(ssh_cmd, shell=True, stdin=subprocess.PIPE, text=True)
    process.communicate(input=setup_script)
    
    # Make executable
    ssh_cmd = f"ssh {config['user']}@{config['host']} 'chmod +x {config['path']}/auto_setup_pi.sh'"
    subprocess.run(ssh_cmd, shell=True)
    
    print("✅ Auto setup script created on Pi")

def run_auto_setup(config):
    """Run the auto setup script on Pi"""
    print(f"\n🚀 Running auto setup on Pi...")
    print("This may take a few minutes...")
    
    ssh_cmd = f"ssh {config['user']}@{config['host']} 'cd {config['path']} && ./auto_setup_pi.sh'"
    
    try:
        # Run with real-time output
        process = subprocess.Popen(ssh_cmd, shell=True, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT, 
                                 universal_newlines=True)
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"📡 {output.strip()}")
        
        if process.returncode == 0:
            print("✅ Auto setup completed successfully!")
            return True
        else:
            print("❌ Auto setup failed")
            return False
            
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False

def show_final_instructions(config):
    """Show final instructions to user"""
    print("\n" + "🎉" * 50)
    print("🎉 DEPLOYMENT SUCCESSFUL!")
    print("🎉" * 50)
    print()
    print("🔥 Your Fish Feeder Smart Hybrid Storage is ready!")
    print()
    print("📋 Final steps to complete setup:")
    print("=" * 40)
    print()
    print("1️⃣ Connect to Pi and setup Google Drive OAuth:")
    print(f"   ssh {config['user']}@{config['host']}")
    print(f"   cd {config['path']}")
    print("   python3 google_drive_setup.py")
    print()
    print("2️⃣ Test the system:")
    print("   python3 main.py")
    print()
    print("3️⃣ Enable auto-start (optional):")
    print("   sudo systemctl enable fish-feeder")
    print("   sudo systemctl start fish-feeder")
    print()
    print("🌐 Access URLs:")
    print("=" * 15)
    print("• Web App: https://fish-feeder-test-1.web.app")
    print("• Local Pi: http://localhost:5000")
    print("• PageKite: https://b65iee02.pagekite.me")
    print()
    print("🎮 PageKite Controls:")
    print("=" * 20)
    print("• Start tunnel: ./start_pagekite.sh")
    print("• Check status: ./status_pagekite.sh")
    print("• Stop tunnel: ./stop_pagekite.sh")
    print()
    print("💾 Storage Summary:")
    print("=" * 18)
    print("• Pi Local: 128GB (live recording)")
    print("• Firebase: 5GB (immediate upload)")
    print("• Google Drive: 200GB (long-term archive)")
    print("• Total: 333GB effective storage")
    print()
    print("🚀 Happy fish feeding with video recording!")

def main():
    """Main deployment function"""
    print_banner()
    
    print("🎯 This script will automatically deploy and setup your")
    print("   Fish Feeder Smart Hybrid Storage system on Raspberry Pi")
    print()
    
    if input("Continue with deployment? (y/n): ").lower() != 'y':
        print("Deployment cancelled")
        return
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Please ensure all required files are present")
        return
    
    # Get Pi configuration
    config = get_pi_config()
    
    # Test connection
    if not test_pi_connection(config):
        print("\n❌ Cannot connect to Pi. Please check connection and try again")
        return
    
    # Deploy files
    deploy_files(config)
    
    # Create auto setup script
    create_auto_setup_script(config)
    
    # Ask if user wants to run auto setup
    print("\n🤖 Auto setup will install dependencies and configure the system")
    if input("Run auto setup now? (y/n): ").lower() == 'y':
        if run_auto_setup(config):
            show_final_instructions(config)
        else:
            print("\n⚠️  Auto setup failed. You can run it manually:")
            print(f"   ssh {config['user']}@{config['host']}")
            print(f"   cd {config['path']}")
            print("   ./auto_setup_pi.sh")
    else:
        print("\n📋 Manual setup:")
        print(f"   ssh {config['user']}@{config['host']}")
        print(f"   cd {config['path']}")
        print("   ./auto_setup_pi.sh")

if __name__ == "__main__":
    main() 