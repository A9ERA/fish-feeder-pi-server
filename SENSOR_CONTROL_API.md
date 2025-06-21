# Sensor Control API

## Endpoint
`POST /api/control/sensor`

## Description
This endpoint allows you to control sensor operations including starting, stopping, setting intervals, and getting status.

## Request Format
```json
{
  "action": "start|stop|interval|status",
  "interval": 1000  // Required only for "interval" action
}
```

## Supported Actions

### 1. Start Sensors
**Request:**
```json
{
  "action": "start"
}
```

**Arduino Command Sent:** `[control]:sensors:start`

**Response:**
```json
{
  "status": "success",
  "message": "Start sensors command sent successfully",
  "action": "start",
  "timestamp": "2025-06-21 18:30:45"
}
```

### 2. Stop Sensors
**Request:**
```json
{
  "action": "stop"
}
```

**Arduino Command Sent:** `[control]:sensors:stop`

**Response:**
```json
{
  "status": "success",
  "message": "Stop sensors command sent successfully",
  "action": "stop",
  "timestamp": "2025-06-21 18:30:45"
}
```

### 3. Set Sensor Interval
**Request:**
```json
{
  "action": "interval",
  "interval": 1000
}
```

**Arduino Command Sent:** `[control]:sensors:interval:1000`

**Response:**
```json
{
  "status": "success",
  "message": "Set sensor interval to 1000ms command sent successfully",
  "action": "interval",
  "timestamp": "2025-06-21 18:30:45"
}
```

### 4. Get Sensor Status
**Request:**
```json
{
  "action": "status"
}
```

**Arduino Command Sent:** `[control]:sensors:status`

**Arduino Response:** 
- `[INFO] - Sensor service status: ACTIVE` (or INACTIVE)
- `[INFO] - Print interval: 1000ms`

**API Response:**
```json
{
  "status": "success",
  "message": "Sensor status retrieved successfully",
  "action": "status",
  "timestamp": "2025-06-21 18:30:45",
  "sensor_status": "ACTIVE",
  "is_running": true,
  "interval": 1000,
  "raw_responses": [
    "[INFO] - Sensor service status: ACTIVE",
    "[INFO] - Print interval: 1000ms"
  ]
}
```

**Error Response (No Arduino Response):**
```json
{
  "status": "error",
  "message": "Failed to get sensor status: No response from Arduino",
  "action": "status",
  "timestamp": "2025-06-21 18:30:45"
}
```

## Error Responses

### Missing Action
```json
{
  "status": "error",
  "message": "Action is required"
}
```

### Invalid Action
```json
{
  "status": "error",
  "message": "Invalid action. Must be one of: start, stop, interval, status"
}
```

### Missing Interval for Interval Action
```json
{
  "status": "error",
  "message": "Interval value is required for interval action"
}
```

### Invalid Interval Value
```json
{
  "status": "error",
  "message": "Interval must be a positive integer"
}
```

### Serial Communication Error
```json
{
  "status": "error",
  "message": "Failed to send start sensors command"
}
```

## Usage Examples

### Using curl

**Start sensors:**
```bash
curl -X POST http://localhost:5000/api/control/sensor \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```

**Stop sensors:**
```bash
curl -X POST http://localhost:5000/api/control/sensor \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'
```

**Set interval to 1000ms:**
```bash
curl -X POST http://localhost:5000/api/control/sensor \
  -H "Content-Type: application/json" \
  -d '{"action": "interval", "interval": 1000}'
```

**Get status:**
```bash
curl -X POST http://localhost:5000/api/control/sensor \
  -H "Content-Type: application/json" \
  -d '{"action": "status"}'
```

### Using JavaScript fetch

```javascript
// Start sensors
const startSensors = async () => {
  const response = await fetch('/api/control/sensor', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action: 'start'
    })
  });
  const data = await response.json();
  console.log(data);
};

// Set interval
const setSensorInterval = async (interval) => {
  const response = await fetch('/api/control/sensor', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action: 'interval',
      interval: interval
    })
  });
  const data = await response.json();
  console.log(data);
};
```

## Notes
- All commands are sent via serial communication to the Arduino
- The API only confirms that the command was sent successfully, not that it was executed by the Arduino
- The interval value must be a positive integer representing milliseconds
- Commands follow the format: `[control]:sensors:{action}` or `[control]:sensors:{action}:{value}` 