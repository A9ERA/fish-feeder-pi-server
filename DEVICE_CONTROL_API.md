# Device Control API Documentation

## Overview
This API provides endpoints to control various devices connected to the Arduino via serial communication, including blower, actuator, auger, relay, weight sensor, and feeding operations.

## Arduino Commands Supported
The following commands are supported by the Arduino:

```
[control]:blower:start
[control]:blower:stop
[control]:blower:speed:100
[control]:blower:direction:reverse
[control]:blower:direction:normal
[control]:actuator:up
[control]:actuator:down
[control]:actuator:stop
[control]:auger:forward
[control]:auger:backward
[control]:auger:stop
[control]:auger:speedtest
[control]:auger:setspeed:100
[control]:relay:led:on
[control]:relay:led:off
[control]:relay:fan:on
[control]:relay:fan:off
[control]:relay:all:off
[control]:weight:calibrate
```

## API Endpoints

### 1. Blower Control
**Endpoint:** `POST /api/control/blower`

**Request Body:**
```json
{
  "action": "start|stop|speed|direction_reverse|direction_normal",
  "value": 100  // Required only for speed action
}
```

**Examples:**
```bash
# Start blower
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'

# Stop blower
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'

# Set blower speed
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "speed", "value": 100}'

# Set blower direction to reverse
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "direction_reverse"}'
```

### 2. Actuator Control
**Endpoint:** `POST /api/control/actuator`

**Request Body:**
```json
{
  "action": "up|down|stop"
}
```

**Examples:**
```bash
# Move actuator up
curl -X POST http://localhost:5000/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "up"}'

# Move actuator down
curl -X POST http://localhost:5000/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "down"}'

# Stop actuator
curl -X POST http://localhost:5000/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'
```

### 3. Auger Control
**Endpoint:** `POST /api/control/auger`

**Request Body:**
```json
{
  "action": "forward|backward|stop|speedtest|setspeed",
  "value": 100  // Required only for setspeed action
}
```

**Examples:**
```bash
# Move auger forward
curl -X POST http://localhost:5000/api/control/auger \
  -H "Content-Type: application/json" \
  -d '{"action": "forward"}'

# Move auger backward
curl -X POST http://localhost:5000/api/control/auger \
  -H "Content-Type: application/json" \
  -d '{"action": "backward"}'

# Stop auger
curl -X POST http://localhost:5000/api/control/auger \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'

# Run auger speed test
curl -X POST http://localhost:5000/api/control/auger \
  -H "Content-Type: application/json" \
  -d '{"action": "speedtest"}'

# Set auger speed
curl -X POST http://localhost:5000/api/control/auger \
  -H "Content-Type: application/json" \
  -d '{"action": "setspeed", "value": 100}'
```

### 4. Relay Control
**Endpoint:** `POST /api/control/relay`

**Request Body:**
```json
{
  "device": "led|fan|all",
  "action": "on|off"
}
```

**Note:** For device "all", only action "off" is supported.

**Examples:**
```bash
# Turn LED on
curl -X POST http://localhost:5000/api/control/relay \
  -H "Content-Type: application/json" \
  -d '{"device": "led", "action": "on"}'

# Turn LED off
curl -X POST http://localhost:5000/api/control/relay \
  -H "Content-Type: application/json" \
  -d '{"device": "led", "action": "off"}'

# Turn fan on
curl -X POST http://localhost:5000/api/control/relay \
  -H "Content-Type: application/json" \
  -d '{"device": "fan", "action": "on"}'

# Turn fan off
curl -X POST http://localhost:5000/api/control/relay \
  -H "Content-Type: application/json" \
  -d '{"device": "fan", "action": "off"}'

# Turn all relays off
curl -X POST http://localhost:5000/api/control/relay \
  -H "Content-Type: application/json" \
  -d '{"device": "all", "action": "off"}'
```

### 5. Weight Calibration
**Endpoint:** `POST /api/control/weight`

**Description:** 
This endpoint initiates the weight sensor calibration process. The calibration helps ensure accurate weight measurements by adjusting the sensor's internal parameters.

**Request Body:**
```json
{
  "action": "calibrate"
}
```

**Examples:**
```bash
# Start weight calibration
curl -X POST http://localhost:5000/api/control/weight \
  -H "Content-Type: application/json" \
  -d '{"action": "calibrate"}'
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Weight calibration started",
  "action": "calibrate",
  "timestamp": "2024-01-01 12:00:00"
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Failed to start weight calibration",
  "action": "calibrate",
  "timestamp": "2024-01-01 12:00:00"
}
```

**Parameter Validation:**
- Only `"action": "calibrate"` is supported
- Request must be in JSON format

**Arduino Integration:**
- Sends command: `[control]:weight:calibrate`
- Arduino should respond with calibration status messages
- Calibration process may take time to complete

### 6. Feeder Control
**Endpoint:** `POST /api/feeder/start`

**Description:** 
This endpoint starts an automated feeding process that executes a sequence of operations:
1. Move actuator up for specified duration, then stop
2. Move actuator down for specified duration, then stop  
3. Run auger forward for specified duration, then stop
4. Run blower for specified duration, then stop

**Endpoint:** `POST /api/feeder/stop`

**Description:** 
This endpoint immediately stops any running feeding process (Emergency Stop). It sends a `[control]:feeder:stop` command to the Arduino to interrupt the current feeding sequence.

**Request Body:**
```json
{
  // No parameters required for emergency stop
}
```

**Examples:**
```bash
# Emergency stop feeding process
curl -X POST http://localhost:5000/api/feeder/stop \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Emergency stop command sent to Arduino"
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Failed to send stop command: connection error"
}
```

**Arduino Integration:**
- Sends command: `[control]:feeder:stop`
- Arduino should immediately stop all feeding operations
- Interrupts any running feeding sequence
- Safe to call even when no feeding is in progress

**Start Feeder Endpoint:**

**Request Body:**
```json
{
  "feedSize": 100,        // Feed size in grams (for reference/logging)
  "actuatorUp": 5,        // Duration in seconds for actuator up movement
  "actuatorDown": 3,      // Duration in seconds for actuator down movement
  "augerDuration": 10,    // Duration in seconds for auger operation
  "blowerDuration": 15    // Duration in seconds for blower operation
}
```

**Parameter Validation:**
- All parameters are required and must be integers
- All duration parameters must be non-negative
- Safety limit: No single operation can exceed 300 seconds (5 minutes)
- Feed size: Any positive integer (used for logging/reference only)

**Examples:**
```bash
# Basic feeding process
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 50,
    "actuatorUp": 2,
    "actuatorDown": 2,
    "augerDuration": 5,
    "blowerDuration": 3
  }'

# Large feeding process
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 200,
    "actuatorUp": 10,
    "actuatorDown": 8,
    "augerDuration": 20,
    "blowerDuration": 15
  }'

# Quick feeding process
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 25,
    "actuatorUp": 1,
    "actuatorDown": 1,
    "augerDuration": 3,
    "blowerDuration": 2
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Feeding process completed successfully",
  "feed_size": 100,
  "total_duration": 33,
  "steps_completed": [
    "Actuator up: 5s",
    "Actuator down: 3s", 
    "Auger forward: 10s",
    "Blower: 15s"
  ]
}
```

**Error Response Examples:**
```json
// Missing parameters
{
  "status": "error",
  "message": "All parameters are required: feedSize, actuatorUp, actuatorDown, augerDuration, blowerDuration"
}

// Invalid parameter type
{
  "status": "error", 
  "message": "All parameters must be integers"
}

// Safety limit exceeded
{
  "status": "error",
  "message": "Duration parameters cannot exceed 300 seconds for safety"
}

// Process already running
{
  "status": "error",
  "message": "Feeding process is already running"
}
```

**Safety Features:**
- Thread-safe operation (only one feeding process can run at a time)
- Emergency stop functionality - if any step fails, all devices are stopped
- Parameter validation with safety limits
- Comprehensive error handling and logging
- Device status checking before each operation

### 7. Schedule Sync (New)
**Endpoint:** `POST /api/schedule/sync`

**Description:** 
This endpoint syncs schedule data from Firebase Realtime Database to local storage file (`schedule_data.jsonc`). It retrieves data from Firebase reference `/schedule_data` and stores it locally for offline access.

**Request Body:**
```json
// No request body required
```

**Examples:**
```bash
# Sync schedule data from Firebase
curl -X POST http://localhost:5000/api/schedule/sync \
  -H "Content-Type: application/json"
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Schedule data synced successfully from Firebase",
  "data_synced": true,
  "records_count": 5,
  "sync_timestamp": "2024-01-15T14:30:45.123456",
  "file_path": "/path/to/pi-server/src/data/schedule_data.jsonc"
}
```

**Warning Response (No Data):**
```json
{
  "status": "warning",
  "message": "No schedule data found in Firebase",
  "data_synced": false
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Failed to sync schedule data from Firebase: Connection timeout",
  "data_synced": false
}
```

**Features:**
- Pulls data from Firebase `/schedule_data` reference
- Stores data in local `schedule_data.jsonc` file with metadata
- Includes sync timestamp and source information
- Handles cases when no data exists in Firebase
- Comprehensive error handling for network/Firebase issues

### 8. Feed Preset Sync (New)
**Endpoint:** `POST /api/feed-preset/sync`

**Description:** 
This endpoint syncs feed preset data from Firebase Realtime Database to local storage file (`feed_preset_data.jsonc`). It retrieves feeding preset configurations from Firebase reference `/feed_preset` and stores them locally for quick access during feeding operations.

**Request Body:**
```json
// No request body required
```

**Examples:**
```bash
# Sync feed preset data from Firebase
curl -X POST http://localhost:5000/api/feed-preset/sync \
  -H "Content-Type: application/json"
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Feed preset data synced successfully from Firebase",
  "data_synced": true,
  "records_count": 3,
  "sync_timestamp": "2024-01-15T14:30:45.123456",
  "file_path": "/path/to/pi-server/src/data/feed_preset_data.jsonc"
}
```

**Warning Response (No Data):**
```json
{
  "status": "warning",
  "message": "No feed preset data found in Firebase",
  "data_synced": false
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Failed to sync feed preset data from Firebase: Connection timeout",
  "data_synced": false
}
```

**Sample Feed Preset Structure:**
```json
[
  {
    "id": "quick_feed",
    "name": "Quick Feed",
    "feedSize": 50,
    "actuatorUp": 2,
    "actuatorDown": 1,
    "augerDuration": 5,
    "blowerDuration": 3,
    "description": "Fast feeding for small portions",
    "enabled": true,
    "created_at": "2024-01-15T10:00:00.000Z"
  },
  {
    "id": "standard_feed",
    "name": "Standard Feed", 
    "feedSize": 100,
    "actuatorUp": 3,
    "actuatorDown": 2,
    "augerDuration": 8,
    "blowerDuration": 7,
    "description": "Normal feeding preset",
    "enabled": true,
    "created_at": "2024-01-15T10:00:00.000Z"
  }
]
```

**Features:**
- Pulls data from Firebase `/feed_preset` reference
- Stores preset configurations for feeding operations
- Compatible with `/api/feeder/start` endpoint parameters
- Includes metadata with sync timestamp and source
- Handles empty preset collections gracefully
- Error handling for Firebase connectivity issues

## Response Format

### Success Response
```json
{
  "status": "success",
  "message": "Command sent successfully"
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description"
}
```

## Error Codes
- `400 Bad Request` - Invalid request format or parameters
- `500 Internal Server Error` - Failed to send command to device

## Testing

You can test all endpoints using the provided curl commands above. Make sure the server is running on `http://localhost:5000` before testing.

### Quick Test Commands

```bash
# Test server health
curl -X GET http://localhost:5000/health

# Test individual device controls
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'

curl -X POST http://localhost:5000/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "up"}'

curl -X POST http://localhost:5000/api/control/auger \
  -H "Content-Type: application/json" \
  -d '{"action": "forward"}'

curl -X POST http://localhost:5000/api/control/weight \
  -H "Content-Type: application/json" \
  -d '{"action": "calibrate"}'

# Test complete feeding process
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 30,
    "actuatorUp": 1,
    "actuatorDown": 1,
    "augerDuration": 2,
    "blowerDuration": 2
  }'
```

### Testing Tips

1. **Start with short durations** when testing the feeder endpoint to avoid long waits
2. **Check serial connection** - ensure Arduino is connected and responding
3. **Monitor logs** - server logs will show each step of the feeding process
4. **Emergency stop** - if needed, restart the server to stop all operations
5. **Test error cases** - try invalid parameters to ensure proper validation

## Implementation Notes

1. All commands are sent to Arduino via serial communication with the format: `[control]:<command>\n`
2. The API validates all input parameters before sending commands
3. Serial connection status is checked before sending commands
4. Thread-safe command sending using locks to prevent concurrent access
5. Comprehensive error handling for both invalid requests and device communication failures

## Web Interface

You can also control the devices using the web interface at `http://localhost:5000`. The interface includes:
- Camera controls (existing functionality)
- Blower controls with start/stop, speed setting, and direction control
- Actuator motor controls with up/down/stop actions
- Weight sensor calibration controls

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `500` - Internal server error (communication failure)

**Error Response Example:**
```json
{
    "status": "error",
    "message": "Invalid action. Valid actions are: start, stop, speed, direction_reverse, direction_normal"
}
```

## Requirements

- Serial connection to Arduino device must be established
- Arduino must be programmed to handle the control commands in the specified format
- The `controlSensor()` function should be called in the Arduino's main loop to process incoming commands 