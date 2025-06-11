#!/bin/bash
# 🚀 AUTO DEPLOY TO RASPBERRY PI
# ===============================
# Automatically copy all files and setup Smart Hybrid Storage on Pi

# Configuration
PI_USER="pi"
PI_HOST="raspberrypi.local"  # หรือ IP address ของ Pi
PI_PATH="/home/pi/pi-mqtt-server"

echo "🚀 DEPLOYING FISH FEEDER TO RASPBERRY PI"
echo "========================================"
echo "📡 Target: $PI_USER@$PI_HOST:$PI_PATH"
echo ""

# Check if Pi is reachable
echo "🔍 Checking Pi connection..."
if ping -c 1 $PI_HOST > /dev/null 2>&1; then
    echo "✅ Pi is reachable at $PI_HOST"
else
    echo "❌ Cannot reach Pi at $PI_HOST"
    echo "💡 Please check:"
    echo "   - Pi is powered on"
    echo "   - Connected to same network"
    echo "   - SSH is enabled on Pi"
    exit 1
fi

# Create directory on Pi
echo "📁 Creating directories on Pi..."
ssh $PI_USER@$PI_HOST "mkdir -p $PI_PATH"
ssh $PI_USER@$PI_HOST "mkdir -p $PI_PATH/logs"

# Copy core files
echo "📦 Copying core system files..."
scp main.py $PI_USER@$PI_HOST:$PI_PATH/
scp serviceAccountKey.json $PI_USER@$PI_HOST:$PI_PATH/ 2>/dev/null || echo "⚠️  serviceAccountKey.json not found - you'll need to copy this manually"
scp requirements.txt $PI_USER@$PI_HOST:$PI_PATH/

# Copy Smart Hybrid Storage files
echo "🗂️ Copying Smart Hybrid Storage system..."
scp smart_hybrid_storage.py $PI_USER@$PI_HOST:$PI_PATH/
scp google_drive_credentials.json $PI_USER@$PI_HOST:$PI_PATH/
scp storage_config.json $PI_USER@$PI_HOST:$PI_PATH/
scp google_drive_setup.py $PI_USER@$PI_HOST:$PI_PATH/
scp test_google_drive.py $PI_USER@$PI_HOST:$PI_PATH/

# Copy PageKite files
echo "🌐 Copying PageKite control scripts..."
scp start_pagekite.sh $PI_USER@$PI_HOST:$PI_PATH/
scp stop_pagekite.sh $PI_USER@$PI_HOST:$PI_PATH/
scp status_pagekite.sh $PI_USER@$PI_HOST:$PI_PATH/

# Copy setup and control scripts
echo "🛠️ Copying setup scripts..."
scp setup_hybrid_storage.py $PI_USER@$PI_HOST:$PI_PATH/
scp pagekite_setup.py $PI_USER@$PI_HOST:$PI_PATH/
scp integrate_hybrid_storage.py $PI_USER@$PI_HOST:$PI_PATH/

# Copy enhanced requirements
echo "📋 Copying enhanced requirements..."
scp requirements_enhanced.txt $PI_USER@$PI_HOST:$PI_PATH/

# Copy documentation
echo "📖 Copying documentation..."
scp README_HYBRID_STORAGE.md $PI_USER@$PI_HOST:$PI_PATH/
scp QUICK_SETUP.md $PI_USER@$PI_HOST:$PI_PATH/
scp SETUP_COMPLETE.md $PI_USER@$PI_HOST:$PI_PATH/

# Set permissions
echo "🔒 Setting permissions..."
ssh $PI_USER@$PI_HOST "chmod +x $PI_PATH/*.sh"
ssh $PI_USER@$PI_HOST "chmod +x $PI_PATH/*.py"

# Create auto setup script on Pi
echo "🤖 Creating auto setup script on Pi..."
cat << 'EOF' | ssh $PI_USER@$PI_HOST "cat > $PI_PATH/auto_setup_pi.sh"
#!/bin/bash
# 🤖 AUTO SETUP ON RASPBERRY PI
echo "🤖 Starting automatic setup on Raspberry Pi..."

cd /home/pi/pi-mqtt-server

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt install -y python3-pip python3-venv git

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements_enhanced.txt

# Install PageKite
echo "🌐 Installing PageKite..."
pip3 install pagekite

# Setup directory structure
echo "📁 Setting up storage directories..."
sudo mkdir -p /home/pi/fish_feeder_data/{videos,photos,temp,processing,logs}
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
WorkingDirectory=/home/pi/pi-mqtt-server
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/pi/pi-mqtt-server

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd
sudo systemctl daemon-reload

echo "✅ Auto setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Run Google Drive OAuth: python3 google_drive_setup.py"
echo "2. Test system: python3 main.py"
echo "3. Enable auto-start: sudo systemctl enable fish-feeder"
echo "4. Start now: sudo systemctl start fish-feeder"
echo ""
echo "🌐 URLs:"
echo "- Local: http://localhost:5000"
echo "- PageKite: https://b65iee02.pagekite.me (after starting tunnel)"
echo "- Web App: https://fish-feeder-test-1.web.app"
EOF

ssh $PI_USER@$PI_HOST "chmod +x $PI_PATH/auto_setup_pi.sh"

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================="
echo ""
echo "📋 Files copied to Pi:"
echo "   ✅ Core system (main.py, etc.)"
echo "   ✅ Smart Hybrid Storage"
echo "   ✅ PageKite control scripts"
echo "   ✅ Setup and configuration"
echo "   ✅ Documentation"
echo ""
echo "🚀 Next step - Run on Pi:"
echo "   ssh $PI_USER@$PI_HOST"
echo "   cd $PI_PATH"
echo "   ./auto_setup_pi.sh"
echo ""
echo "🎯 After auto setup:"
echo "   python3 google_drive_setup.py  # OAuth setup"
echo "   python3 main.py                # Test system"
echo "   sudo systemctl enable fish-feeder  # Auto-start"
echo ""
echo "🌐 Access URLs:"
echo "   - Local: http://localhost:5000"
echo "   - PageKite: https://b65iee02.pagekite.me"
echo "   - Web App: https://fish-feeder-test-1.web.app" 