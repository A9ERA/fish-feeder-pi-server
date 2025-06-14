# Device Control API Documentation

## Overview
This API provides endpoints to control various devices connected to the Arduino via serial communication.

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
[control]:relay:led:on
[control]:relay:led:off
[control]:relay:fan:on
[control]:relay:fan:off
[control]:relay:all:off
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
  "action": "forward|backward|stop|speedtest"
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