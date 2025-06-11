#!/usr/bin/env python3
"""
🔧 AUTOMATIC INTEGRATION SCRIPT
==============================
Automatically integrates Smart Hybrid Storage with existing main.py
"""

import os
import shutil
import sys
from pathlib import Path

def backup_original():
    """Backup original main.py"""
    if Path('main.py').exists():
        shutil.copy('main.py', 'main_original_backup.py')
        print("✅ Backed up original main.py to main_original_backup.py")

def integrate_imports():
    """Add imports to main.py"""
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Add import after existing imports
    import_line = "from smart_hybrid_storage import SmartHybridStorage"
    
    if import_line not in content:
        # Find the last import line
        lines = content.split('\n')
        last_import_line = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import_line = i
        
        # Insert after last import
        lines.insert(last_import_line + 1, import_line)
        
        with open('main.py', 'w') as f:
            f.write('\n'.join(lines))
        
        print("✅ Added import for SmartHybridStorage")

def integrate_controller():
    """Integrate storage manager with FishFeederController"""
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Add storage_manager to __init__
    if 'self.storage_manager = None' not in content:
        init_pattern = 'def __init__(self):'
        if init_pattern in content:
            content = content.replace(
                init_pattern,
                init_pattern + '\n        # Smart Hybrid Storage\n        self.storage_manager = None'
            )
    
    # Add initialization in initialize() method
    init_code = '''
        # Initialize Smart Hybrid Storage
        try:
            self.logger.info("🚀 Initializing Smart Hybrid Storage...")
            self.storage_manager = SmartHybridStorage()
        except Exception as e:
            self.logger.error(f"Storage manager init failed: {e}")
            self.storage_manager = None
'''
    
    if 'SmartHybridStorage()' not in content:
        # Find initialize method and add storage initialization
        initialize_pattern = 'def initialize(self):'
        if initialize_pattern in content:
            # Add after camera manager initialization
            camera_init_end = 'self.logger.info("✅ Camera manager initialized")'
            if camera_init_end in content:
                content = content.replace(camera_init_end, camera_init_end + init_code)
    
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("✅ Integrated storage manager with FishFeederController")

def integrate_webapi():
    """Integrate storage manager with WebAPI"""
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Update WebAPI __init__ to include storage_mgr
    webapi_init = 'def __init__(self, arduino_mgr, firebase_mgr, camera_mgr, feed_history_mgr, config_mgr, logger):'
    webapi_init_new = 'def __init__(self, arduino_mgr, firebase_mgr, camera_mgr, feed_history_mgr, config_mgr, storage_mgr, logger):'
    
    if webapi_init in content and webapi_init_new not in content:
        content = content.replace(webapi_init, webapi_init_new)
        # Add storage_mgr assignment
        content = content.replace(
            'self.logger = logger',
            'self.storage_mgr = storage_mgr\n        self.logger = logger'
        )
    
    # Add new routes
    new_routes = '''
        # Smart Hybrid Storage Routes
        @self.app.route('/api/camera/record/start', methods=['POST'])
        def start_recording():
            try:
                data = request.get_json() or {}
                session_id = data.get('session_id', f"session_{int(time.time())}")
                
                if self.storage_mgr:
                    result = self.storage_mgr.start_recording(session_id, self.camera_mgr)
                else:
                    result = {'status': 'error', 'message': 'Storage manager not available'}
                
                return jsonify(result)
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/camera/record/stop', methods=['POST'])
        def stop_recording():
            try:
                if self.storage_mgr:
                    result = self.storage_mgr.stop_recording()
                else:
                    result = {'status': 'error', 'message': 'Storage manager not available'}
                
                return jsonify(result)
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/pagekite/start', methods=['POST'])
        def start_pagekite():
            try:
                if self.storage_mgr:
                    url = self.storage_mgr.start_pagekite()
                    if url:
                        return jsonify({'status': 'success', 'tunnel_url': url})
                    else:
                        return jsonify({'status': 'error', 'message': 'Failed to start PageKite'}), 500
                else:
                    return jsonify({'status': 'error', 'message': 'Storage manager not available'}), 500
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/pagekite/stop', methods=['POST'])
        def stop_pagekite():
            try:
                if self.storage_mgr:
                    self.storage_mgr.stop_pagekite()
                    return jsonify({'status': 'success', 'message': 'PageKite stopped'})
                else:
                    return jsonify({'status': 'error', 'message': 'Storage manager not available'}), 500
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/storage/status', methods=['GET'])
        def storage_status():
            try:
                if self.storage_mgr:
                    status = self.storage_mgr.get_status()
                    return jsonify({'status': 'success', 'storage': status})
                else:
                    return jsonify({'status': 'error', 'message': 'Storage manager not available'}), 500
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
'''
    
    # Insert new routes before the run method
    run_method_pattern = '    def run(self):'
    if run_method_pattern in content and '/api/camera/record/start' not in content:
        content = content.replace(run_method_pattern, new_routes + '\n' + run_method_pattern)
    
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("✅ Added new API routes for Smart Hybrid Storage")

def update_main_function():
    """Update main() function to pass storage manager"""
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Update WebAPI initialization
    old_webapi_call = '''web_api = WebAPI(
        arduino_mgr=controller.arduino_mgr,
        firebase_mgr=controller.firebase_mgr,
        camera_mgr=controller.camera_mgr,
        feed_history_mgr=controller.feed_history_mgr,
        config_mgr=controller.config_mgr,
        logger=controller.logger
    )'''
    
    new_webapi_call = '''web_api = WebAPI(
        arduino_mgr=controller.arduino_mgr,
        firebase_mgr=controller.firebase_mgr,
        camera_mgr=controller.camera_mgr,
        feed_history_mgr=controller.feed_history_mgr,
        config_mgr=controller.config_mgr,
        storage_mgr=controller.storage_manager,
        logger=controller.logger
    )'''
    
    if old_webapi_call in content:
        content = content.replace(old_webapi_call, new_webapi_call)
        
        with open('main.py', 'w') as f:
            f.write(content)
        
        print("✅ Updated main() function to include storage manager")

def create_startup_script():
    """Create easy startup script"""
    script_content = '''#!/bin/bash
# 🚀 Fish Feeder Startup Script with Smart Hybrid Storage

echo "🐟 Starting Fish Feeder with Smart Hybrid Storage..."

# Check if running as pi user
if [ "$USER" != "pi" ]; then
    echo "⚠️  Warning: Should run as pi user"
fi

# Check if in correct directory
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found. Please run from pi-mqtt-server directory"
    exit 1
fi

# Check dependencies
python3 -c "import smart_hybrid_storage" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements_enhanced.txt
fi

# Create directories if needed
mkdir -p /home/pi/fish_feeder_data/{videos,photos,temp,processing,logs}

# Set proper permissions
sudo chown -R pi:pi /home/pi/fish_feeder_data 2>/dev/null || true

# Start the system
echo "🚀 Launching Fish Feeder system..."
python3 main.py

echo "👋 Fish Feeder stopped"
'''
    
    with open('start_fish_feeder.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('start_fish_feeder.sh', 0o755)
    print("✅ Created startup script: start_fish_feeder.sh")

def main():
    """Main integration function"""
    print("🔧 SMART HYBRID STORAGE INTEGRATION")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('main.py').exists():
        print("❌ main.py not found. Please run from pi-mqtt-server directory")
        return
    
    if not Path('smart_hybrid_storage.py').exists():
        print("❌ smart_hybrid_storage.py not found")
        return
    
    print("📋 Integration steps:")
    print("1. Backup original main.py")
    print("2. Add imports")
    print("3. Integrate with FishFeederController")
    print("4. Add new API routes")
    print("5. Update main() function")
    print("6. Create startup script")
    print()
    
    if input("Continue with integration? (y/n): ").lower() != 'y':
        print("Integration cancelled")
        return
    
    try:
        backup_original()
        integrate_imports()
        integrate_controller()
        integrate_webapi()
        update_main_function()
        create_startup_script()
        
        print("\n" + "🎉" * 50)
        print("🎉 INTEGRATION COMPLETE!")
        print("🎉" * 50)
        print()
        print("📋 Next steps:")
        print("1. Install dependencies: pip3 install -r requirements_enhanced.txt")
        print("2. Copy your serviceAccountKey.json to this directory")
        print("3. Run setup: python3 setup_hybrid_storage.py")
        print("4. Start system: ./start_fish_feeder.sh")
        print()
        print("🌐 Features added:")
        print("- Smart video recording with cloud upload")
        print("- Firebase → Google Drive auto-migration")
        print("- PageKite tunneling for external access")
        print("- 128GB local storage management")
        print("- New API endpoints for storage control")
        print()
        
    except Exception as e:
        print(f"❌ Integration failed: {e}")
        
        # Restore backup if exists
        if Path('main_original_backup.py').exists():
            shutil.copy('main_original_backup.py', 'main.py')
            print("✅ Restored original main.py from backup")

if __name__ == "__main__":
    main() 