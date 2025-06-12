# 🔌 Fish Feeder JSON API Summary

## 📊 **SENSOR DATA APIs**

### 1. Arduino → Pi Server (JSON Format)
```json
// Compact JSON format from Arduino
{
  "sensors": {
    "sol_v": 12.45,     // Solar voltage (V)
    "sol_i": 1.85,      // Solar current (A)
    "bat_v": 11.89,     // Battery voltage (V)
    "bat_i": 2.10,      // Battery current (A)
    "charging": 1,      // Charging status (0/1)
    "feed_temp": 25.3,  // Feed temperature (°C)
    "ctrl_temp": 28.1,  // Control temperature (°C)
    "feed_hum": 65.2,   // Feed humidity (%)
    "ctrl_hum": 58.7,   // Control humidity (%)
    "weight": 1250.5,   // Weight (grams)
    "soil": 45.8,       // Soil moisture (%)
    "system": {
      "temp_ok": true,
      "voltage_ok": true,
      "weight_ok": true,
      "motors_enabled": true,
      "system_ok": true
    }
  }
}
```

### 2. Pi Server → Web App (GET /api/sensors)
```json
{
  "timestamp": "2025-12-06T14:30:00.000Z",
  "arduino_connected": true,
  "SOLAR_VOLTAGE": {
    "voltage": {"value": 12.45, "unit": "V", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "SOLAR_CURRENT": {
    "current": {"value": 1.85, "unit": "A", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "BATTERY_STATUS": {
    "voltage": {"value": 11.89, "unit": "V", "timestamp": "2025-12-06T14:30:00.000Z"},
    "current": {"value": 2.10, "unit": "A", "timestamp": "2025-12-06T14:30:00.000Z"},
    "soc": {"value": 78.0, "unit": "%", "timestamp": "2025-12-06T14:30:00.000Z"},
    "power": {"value": 24.97, "unit": "W", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "FEED_TEMPERATURE": {
    "temperature": {"value": 25.3, "unit": "°C", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "CONTROL_TEMPERATURE": {
    "temperature": {"value": 28.1, "unit": "°C", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "FEED_HUMIDITY": {
    "humidity": {"value": 65.2, "unit": "%", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "CONTROL_HUMIDITY": {
    "humidity": {"value": 58.7, "unit": "%", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "WEIGHT": {
    "weight": {"value": 1250.5, "unit": "g", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "SOIL_MOISTURE": {
    "moisture": {"value": 45.8, "unit": "%", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "SYSTEM_HEALTH": {
    "temp_ok": true,
    "voltage_ok": true,
    "weight_ok": true,
    "motors_enabled": true,
    "system_ok": true,
    "timestamp": "2025-12-06T14:30:00.000Z"
  }
}
```

## ⚡ **ENERGY SYSTEM API**

### GET /api/energy/status
```json
{
  "status": "success",
  "data": {
    "battery": {
      "voltage": 11.89,
      "current": 2.10,
      "power": 24.97,
      "soc": 78,
      "status": "normal",
      "charging": true
    },
    "solar": {
      "voltage": 12.45,
      "current": 1.85,
      "power": 23.03
    },
    "system": {
      "efficiency": 88.1,
      "net_power": -1.94,
      "load_power": 24.97
    }
  },
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

## 🎮 **CONTROL COMMAND APIs**

### 1. Feed Control (POST /api/feed)
```json
// Request
{
  "action": "medium",        // small, medium, large, xl, custom, stop
  "amount": 100,            // grams
  "actuator_up": 3,         // seconds
  "actuator_down": 2,       // seconds
  "auger_duration": 20,     // seconds
  "blower_duration": 15     // seconds
}

// Response
{
  "success": true,
  "message": "Feed command executed successfully",
  "feed_id": "feed_20251206_143000",
  "estimated_duration": 40,
  "timestamp": "2025-12-06T14:30:00.000Z",
  "photo_url": "/photos/feed_20251206_143000.jpg"
}
```

### 2. Blower Control (POST /api/control/blower)
```json
// Request
{
  "action": "start",    // start, stop, toggle, speed
  "speed": 255          // 0-255 (PWM speed)
}

// Response
{
  "status": "success",
  "action": "start",
  "command": "B:255",
  "speed": 255,
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

### 3. Actuator Control (POST /api/control/actuator)
```json
// Request
{
  "action": "up",       // up, down, extend, retract, stop
  "duration": 3.0       // seconds
}

// Response
{
  "status": "success",
  "action": "up",
  "command": "U:3.0",
  "duration": 3.0,
  "actuator_id": 1,
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

### 4. Direct Arduino Command (POST /api/control/direct)
```json
// Request
{
  "command": "G:20"     // Direct Arduino command
}

// Response
{
  "status": "success",
  "command": "G:20",
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

### 5. Weight Calibration (POST /api/control/weight/calibrate)
```json
// Request
{
  "known_weight": 1000  // grams
}

// Response
{
  "status": "success",
  "message": "HX711 calibration completed with 1.000 kg",
  "known_weight_grams": 1000,
  "known_weight_kg": 1.000,
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

## 🔧 **ARDUINO COMMAND PROTOCOL**

### Control Commands (Pi → Arduino)
```
G:duration     - Auger motor (seconds)
B:speed        - Blower control (0=off, 1=on, 2=toggle, 0-255=PWM)
U:duration     - Actuator up (seconds)
D:duration     - Actuator down (seconds)
A:0            - Stop actuator
R:device       - Relay control (1=LED, 2=Fan, 3=Pump)
CAL:weight:kg  - Weight calibration
CAL:tare       - Weight tare (zero)
CAL:reset      - Reset calibration
```

### Feed Presets
```json
{
  "small": {
    "amount": 50,
    "actuator_up": 2,
    "actuator_down": 2,
    "auger_duration": 10,
    "blower_duration": 8
  },
  "medium": {
    "amount": 100,
    "actuator_up": 3,
    "actuator_down": 2,
    "auger_duration": 20,
    "blower_duration": 15
  },
  "large": {
    "amount": 200,
    "actuator_up": 4,
    "actuator_down": 3,
    "auger_duration": 40,
    "blower_duration": 30
  },
  "xl": {
    "amount": 1000,
    "actuator_up": 5,
    "actuator_down": 4,
    "auger_duration": 120,
    "blower_duration": 60
  }
}
```

## 📷 **CAMERA APIs**

### Camera Status (GET /api/camera/status)
```json
{
  "status": "success",
  "camera_active": true,
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

### Take Photo (POST /api/camera/photo)
```json
{
  "success": true,
  "photo_url": "/photos/photo_20251206_143000.jpg",
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

## 🔍 **SYSTEM STATUS APIs**

### Health Check (GET /api/health)
```json
{
  "status": "ok",
  "serial_connected": true,
  "firebase_connected": true,
  "timestamp": "2025-12-06T14:30:00.000Z",
  "server_info": {
    "version": "3.0.0",
    "uptime_seconds": 86400
  },
  "sensors_available": [
    "SOLAR_VOLTAGE", "SOLAR_CURRENT", "BATTERY_STATUS",
    "FEED_TEMPERATURE", "WEIGHT", "SYSTEM_HEALTH"
  ]
}
```

### Feed History (GET /api/feed/history)
```json
{
  "data": [
    {
      "id": "feed_20251206_143000",
      "timestamp": "2025-12-06T14:30:00.000Z",
      "amount": 100,
      "type": "manual",
      "preset": "medium",
      "device_timings": {
        "actuator_up": 3,
        "actuator_down": 2,
        "auger_duration": 20,
        "blower_duration": 15
      },
      "photo_url": "/photos/feed_20251206_143000.jpg"
    }
  ]
}
```

## 🌐 **WEBSOCKET EVENTS**

### Client → Server
```javascript
// Request sensor data
socket.emit('request_sensor_data');

// Request system status
socket.emit('request_system_status');

// Send feed command
socket.emit('feed_command', {
  action: 'medium',
  amount: 100
});
```

### Server → Client
```javascript
// Real-time sensor updates
socket.on('sensor_update', (data) => {
  // data contains latest sensor readings
});

// System status updates
socket.on('system_status', (data) => {
  // data contains system health info
});

// Feed operation updates
socket.on('feed_status', (data) => {
  // data contains feed operation status
});
```

## 🔄 **ERROR HANDLING**

### Standard Error Response
```json
{
  "status": "error",
  "message": "Detailed error message",
  "timestamp": "2025-12-06T14:30:00.000Z"
}
```

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (sensor/endpoint not found)
- `500` - Internal Server Error 