# 🌐 Web App Integration Guide - Updated Sensor Data Format

## 📊 **Updated Sensor Data Structure**

The Pi Server now provides **comprehensive sensor data** with enhanced structure:

### ✅ **New Enhanced Format:**

```javascript
// GET /api/sensors response
{
  "timestamp": "2025-12-06T14:30:00.000Z",
  "arduino_connected": true,
  
  // Enhanced structure with value, unit, timestamp
  "BATTERY_STATUS": {
    "voltage": {"value": 11.89, "unit": "V", "timestamp": "2025-12-06T14:30:00.000Z"},
    "current": {"value": 2.10, "unit": "A", "timestamp": "2025-12-06T14:30:00.000Z"},
    "soc": {"value": 78.0, "unit": "%", "timestamp": "2025-12-06T14:30:00.000Z"},
    "power": {"value": 24.97, "unit": "W", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  
  "SOLAR_VOLTAGE": {
    "voltage": {"value": 12.45, "unit": "V", "timestamp": "2025-12-06T14:30:00.000Z"}
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

## 🔧 **Web App Code Changes Required:**

### 1. **Sensor Data Access Pattern**

**❌ Old way:**
```javascript
const temperature = sensorData.FEED_TEMPERATURE?.temperature || 0;
const humidity = sensorData.FEED_HUMIDITY?.humidity || 0;
```

**✅ New way:**
```javascript
const temperature = sensorData.FEED_TEMPERATURE?.temperature?.value || 0;
const humidity = sensorData.FEED_HUMIDITY?.humidity?.value || 0;
const unit = sensorData.FEED_TEMPERATURE?.temperature?.unit || '°C';
```

### 2. **Helper Function for Sensor Data**

```javascript
// Utility function to extract sensor values
function getSensorValue(sensorData, sensorName, measurementType, defaultValue = 0) {
  return sensorData?.[sensorName]?.[measurementType]?.value ?? defaultValue;
}

function getSensorUnit(sensorData, sensorName, measurementType, defaultUnit = '') {
  return sensorData?.[sensorName]?.[measurementType]?.unit ?? defaultUnit;
}

function getSensorTimestamp(sensorData, sensorName, measurementType) {
  return sensorData?.[sensorName]?.[measurementType]?.timestamp;
}

// Usage examples:
const batteryVoltage = getSensorValue(sensors, 'BATTERY_STATUS', 'voltage');
const batterySOC = getSensorValue(sensors, 'BATTERY_STATUS', 'soc');
const feedTemp = getSensorValue(sensors, 'FEED_TEMPERATURE', 'temperature');
const feedHumidity = getSensorValue(sensors, 'FEED_HUMIDITY', 'humidity');
const weight = getSensorValue(sensors, 'WEIGHT', 'weight');
const soilMoisture = getSensorValue(sensors, 'SOIL_MOISTURE', 'moisture');
```

### 3. **Updated Component Examples**

**Temperature Component:**
```vue
<template>
  <div class="sensor-card">
    <h3>Temperature Sensors</h3>
    <div class="sensor-row">
      <span>Feed Area:</span>
      <span>{{ feedTemp }}{{ tempUnit }}</span>
      <small>{{ formatTime(feedTempTime) }}</small>
    </div>
    <div class="sensor-row">
      <span>Control Area:</span>
      <span>{{ controlTemp }}{{ tempUnit }}</span>
      <small>{{ formatTime(controlTempTime) }}</small>
    </div>
  </div>
</template>

<script>
export default {
  props: ['sensorData'],
  computed: {
    feedTemp() {
      return this.getSensorValue('FEED_TEMPERATURE', 'temperature')?.toFixed(1) || '--';
    },
    controlTemp() {
      return this.getSensorValue('CONTROL_TEMPERATURE', 'temperature')?.toFixed(1) || '--';
    },
    tempUnit() {
      return this.getSensorUnit('FEED_TEMPERATURE', 'temperature') || '°C';
    },
    feedTempTime() {
      return this.getSensorTimestamp('FEED_TEMPERATURE', 'temperature');
    },
    controlTempTime() {
      return this.getSensorTimestamp('CONTROL_TEMPERATURE', 'temperature');
    }
  },
  methods: {
    getSensorValue(sensor, measurement) {
      return this.sensorData?.[sensor]?.[measurement]?.value;
    },
    getSensorUnit(sensor, measurement) {
      return this.sensorData?.[sensor]?.[measurement]?.unit;
    },
    getSensorTimestamp(sensor, measurement) {
      return this.sensorData?.[sensor]?.[measurement]?.timestamp;
    },
    formatTime(timestamp) {
      return timestamp ? new Date(timestamp).toLocaleTimeString() : '';
    }
  }
}
</script>
```

**Battery Component:**
```vue
<template>
  <div class="battery-card">
    <h3>Battery Status</h3>
    <div class="battery-info">
      <div class="battery-main">
        <span class="voltage">{{ voltage }}V</span>
        <span class="soc">{{ soc }}%</span>
      </div>
      <div class="battery-details">
        <span>Current: {{ current }}A</span>
        <span>Power: {{ power }}W</span>
        <span>Updated: {{ formatTime(timestamp) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['sensorData'],
  computed: {
    voltage() {
      return this.getBatteryValue('voltage')?.toFixed(2) || '--';
    },
    current() {
      return this.getBatteryValue('current')?.toFixed(2) || '--';
    },
    soc() {
      return this.getBatteryValue('soc')?.toFixed(0) || '--';
    },
    power() {
      return this.getBatteryValue('power')?.toFixed(1) || '--';
    },
    timestamp() {
      return this.sensorData?.BATTERY_STATUS?.voltage?.timestamp;
    }
  },
  methods: {
    getBatteryValue(measurement) {
      return this.sensorData?.BATTERY_STATUS?.[measurement]?.value;
    },
    formatTime(timestamp) {
      return timestamp ? new Date(timestamp).toLocaleTimeString() : '';
    }
  }
}
</script>
```

## 🔄 **Migration Checklist:**

- [ ] Update all sensor data access to use `.value` property
- [ ] Add unit display using `.unit` property  
- [ ] Add timestamp display using `.timestamp` property
- [ ] Update chart/graph components for new data structure
- [ ] Test null/undefined handling for missing sensors
- [ ] Update Firebase listeners for new data format
- [ ] Update dashboard widgets and cards
- [ ] Test real-time updates with WebSocket

## 📈 **Benefits of New Format:**

✅ **Standardized** - All sensors follow same pattern  
✅ **Timestamped** - Know exactly when each reading was taken  
✅ **Units included** - No guessing what units are used  
✅ **Type safety** - Clear value/unit/timestamp structure  
✅ **Extensible** - Easy to add new measurement types

## 🎯 **Next Steps:**

1. **Update Web App** components to use new format
2. **Test thoroughly** with real Arduino data
3. **Update documentation** as needed
4. **Deploy and monitor** for any issues 