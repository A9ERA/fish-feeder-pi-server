# 📋 Changelog - Fish Feeder Smart Hybrid Storage

## 🚀 Version 2.0.0 (2025-01-06)
### 🎉 Major Features
- **Smart Hybrid Storage System** - 333GB total storage capacity
- **PageKite Integration** - External access via `https://b65iee02.pagekite.me`
- **Google Drive Integration** - Long-term cloud storage (200GB)
- **Firebase Storage** - Immediate cloud backup (5GB)
- **Automatic Video Recording** - Records during fish feeding
- **One-Click Deployment** - Complete auto-deploy to Raspberry Pi

### 🔧 Technical Improvements
- **Multi-tier Storage Strategy**: Pi Local → Firebase → Google Drive
- **Auto Migration System**: Smart file movement based on age and storage limits
- **Systemd Service**: Auto-start on Pi boot
- **Real-time Storage Monitoring**: Track usage across all storage tiers
- **Enhanced API Endpoints**: Video recording, PageKite control, storage management

### 📦 Deployment & Setup
- **Auto Deploy Scripts**: `one_click_deploy.py` and `deploy_to_pi.sh`
- **Auto Setup Scripts**: Complete Pi configuration automation
- **Documentation**: Comprehensive Thai language setup guides
- **Configuration Management**: Organized config files and credentials

### 🛠️ Storage Features
- **Pi Local Storage**: 128GB for recent recordings
- **Automatic Cleanup**: Remove old files when storage is full
- **Cloud Backup**: Instant Firebase upload + 24hr Google Drive migration
- **Video Management**: MP4 format with timestamp naming
- **Storage Status API**: Real-time monitoring and alerts

### 🌐 External Access
- **PageKite Tunnel**: Secure external access without port forwarding
- **Web App Integration**: `https://fish-feeder-test-1.web.app`
- **Mobile Responsive**: Full mobile device support
- **API Access**: RESTful endpoints for all functions

### 📱 User Interface
- **Enhanced Control Panel**: Video recording controls
- **Storage Dashboard**: Real-time storage usage display
- **PageKite Status**: Tunnel connection monitoring
- **Feeding History**: Video playback and management

---

## 📜 Version 1.x.x
- Basic fish feeder functionality
- Firebase integration
- Local Pi control
- Web interface 