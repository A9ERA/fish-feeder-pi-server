#!/usr/bin/env python3
"""
🌐 PAGEKITE SETUP SCRIPT
========================
Easy setup for PageKite tunnel with subdomain b65iee02.pagekite.me
"""

import json
import subprocess
import sys
from pathlib import Path

def create_pagekite_config():
    """Create PageKite configuration"""
    print("🌐 Setting up PageKite for b65iee02.pagekite.me")
    
    # Update storage config
    config_file = 'storage_config.json'
    
    if Path(config_file).exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        print("❌ storage_config.json not found. Run setup_hybrid_storage.py first")
        return False
    
    # Update PageKite settings
    if 'pagekite' not in config:
        config['pagekite'] = {}
    
    config['pagekite']['enabled'] = True
    config['pagekite']['subdomain'] = 'b65iee02'
    config['pagekite']['backend_port'] = 5000
    config['pagekite']['auto_start'] = False  # Manual start for security
    
    # Save updated config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ PageKite config updated:")
    print(f"   - Subdomain: b65iee02.pagekite.me")
    print(f"   - Backend Port: 5000")
    print(f"   - Auto-start: Disabled (manual control)")
    
    return True

def check_pagekite_installation():
    """Check if PageKite is installed"""
    try:
        result = subprocess.run(['pagekite.py', '--help'], 
                              capture_output=True, timeout=5)
        print("✅ PageKite is installed")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ PageKite not found. Installing...")
        return install_pagekite()

def install_pagekite():
    """Install PageKite"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pagekite'], check=True)
        print("✅ PageKite installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install PageKite")
        print("💡 Try manually: pip3 install pagekite")
        return False

def create_pagekite_scripts():
    """Create PageKite control scripts"""
    
    # Start script
    start_script = '''#!/bin/bash
# 🚀 Start PageKite Tunnel for Fish Feeder

echo "🌐 Starting PageKite tunnel..."
echo "🔗 URL: https://b65iee02.pagekite.me"

# Start PageKite in background
pagekite.py 5000 b65iee02.pagekite.me &

# Save PID for stopping later
echo $! > pagekite.pid

echo "✅ PageKite tunnel started!"
echo "🌐 Access your Fish Feeder at: https://b65iee02.pagekite.me"
echo "🛑 To stop: ./stop_pagekite.sh"
'''

    # Stop script  
    stop_script = '''#!/bin/bash
# 🛑 Stop PageKite Tunnel

echo "🛑 Stopping PageKite tunnel..."

if [ -f "pagekite.pid" ]; then
    PID=$(cat pagekite.pid)
    kill $PID 2>/dev/null
    rm pagekite.pid
    echo "✅ PageKite tunnel stopped"
else
    # Fallback: kill any pagekite process
    pkill -f pagekite.py
    echo "✅ PageKite processes terminated"
fi
'''

    # Status script
    status_script = '''#!/bin/bash
# 📊 Check PageKite Status

echo "📊 PageKite Status:"

if [ -f "pagekite.pid" ]; then
    PID=$(cat pagekite.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ PageKite is running (PID: $PID)"
        echo "🌐 URL: https://b65iee02.pagekite.me"
    else
        echo "❌ PageKite not running (stale PID file)"
        rm pagekite.pid
    fi
else
    if pgrep -f pagekite.py > /dev/null; then
        echo "⚠️  PageKite running but no PID file"
    else
        echo "❌ PageKite not running"
    fi
fi

echo ""
echo "💡 Commands:"
echo "   Start:  ./start_pagekite.sh"
echo "   Stop:   ./stop_pagekite.sh" 
echo "   Status: ./status_pagekite.sh"
'''

    # Write scripts
    scripts = {
        'start_pagekite.sh': start_script,
        'stop_pagekite.sh': stop_script,
        'status_pagekite.sh': status_script
    }
    
    for filename, content in scripts.items():
        with open(filename, 'w') as f:
            f.write(content)
        Path(filename).chmod(0o755)
        print(f"✅ Created {filename}")

def test_pagekite_connection():
    """Test PageKite connection"""
    print("\n🧪 Testing PageKite...")
    
    # Test if we can reach pagekite.net
    try:
        import requests
        response = requests.get('https://pagekite.net', timeout=10)
        if response.status_code == 200:
            print("✅ Can reach pagekite.net")
        else:
            print("⚠️  pagekite.net reachable but returned non-200")
    except Exception as e:
        print(f"❌ Cannot reach pagekite.net: {e}")
        print("💡 Check internet connection")
        return False
    
    return True

def show_pagekite_instructions():
    """Show PageKite usage instructions"""
    print("\n" + "🌐" * 50)
    print("🌐 PAGEKITE SETUP COMPLETE!")
    print("🌐" * 50)
    print()
    print("🔗 Your Fish Feeder URL: https://b65iee02.pagekite.me")
    print()
    print("📋 Usage:")
    print("1. Start tunnel:  ./start_pagekite.sh")
    print("2. Check status:  ./status_pagekite.sh") 
    print("3. Stop tunnel:   ./stop_pagekite.sh")
    print()
    print("🎮 API Control:")
    print("- Start via API:  curl -X POST http://localhost:5000/api/pagekite/start")
    print("- Stop via API:   curl -X POST http://localhost:5000/api/pagekite/stop")
    print("- Check status:   curl http://localhost:5000/api/pagekite/status")
    print()
    print("⚠️  Security Notes:")
    print("- PageKite tunnel is PUBLIC on the internet")
    print("- Only start when needed")
    print("- Stop when not in use")
    print("- Monitor usage (2GB free monthly limit)")
    print()
    print("📊 Expected Usage:")
    print("- Fish feeding 3x/day = ~150MB/day")
    print("- Monthly total = ~4.5GB")
    print("- Consider upgrading if exceeding 2GB")
    print()

def main():
    """Main PageKite setup"""
    print("🌐 PAGEKITE SETUP FOR b65iee02.pagekite.me")
    print("=" * 50)
    print()
    print("📋 This script will:")
    print("1. Update storage_config.json with PageKite settings")
    print("2. Install PageKite if needed") 
    print("3. Create control scripts")
    print("4. Test connection")
    print()
    
    if input("Continue? (y/n): ").lower() != 'y':
        return
    
    # Run setup steps
    success = True
    
    if not create_pagekite_config():
        success = False
    
    if not check_pagekite_installation():
        success = False
    
    if success:
        create_pagekite_scripts()
        
        if test_pagekite_connection():
            show_pagekite_instructions()
        else:
            print("⚠️  PageKite setup completed but connection test failed")
    else:
        print("❌ PageKite setup failed")

if __name__ == "__main__":
    main() 