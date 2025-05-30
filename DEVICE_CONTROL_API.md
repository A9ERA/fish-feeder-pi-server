# Device Control API Documentation

This document describes the API endpoints for controlling Arduino devices connected via serial communication.

## Overview

The Pi Server now includes device control functionality that allows you to send commands to Arduino devices via the serial connection. The supported devices are:
- **Blower**: For controlling fan/blower operations
- **Actuator Motor**: For linear actuator control

## API Endpoints

### Blower Control

**Endpoint:** `POST /api/control/blower`

**Request Body:**
```json
{
    "action": "start|stop|speed|direction_reverse|direction_normal",
    "value": 100  // Required only for "speed" action
}
```

**Actions:**
- `start` - Start the blower
- `stop` - Stop the blower
- `speed` - Set blower speed (requires `value` parameter)
- `direction_reverse` - Set blower direction to reverse
- `direction_normal` - Set blower direction to normal

**Examples:**

Start blower:
```bash
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```

Set blower speed:
```bash
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "speed", "value": 150}'
```

Stop blower:
```bash
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'
```

**Response:**
```json
{
    "status": "success",
    "message": "Blower start command sent successfully"
}
```

### Actuator Motor Control

**Endpoint:** `POST /api/control/actuator`

**Request Body:**
```json
{
    "action": "up|down|stop"
}
```

**Actions:**
- `up` - Move actuator motor up
- `down` - Move actuator motor down
- `stop` - Stop actuator motor

**Examples:**

Move actuator up:
```bash
curl -X POST http://localhost:5000/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "up"}'
```

Move actuator down:
```bash
curl -X POST http://localhost:5000/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "down"}'
```

Stop actuator:
```bash
curl -X POST http://localhost:5000/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'
```

**Response:**
```json
{
    "status": "success",
    "message": "Actuator motor up command sent successfully"
}
```

## Arduino Command Format

The control service sends commands to the Arduino in the following format:
```
[control]:device:action:value\n
```

**Examples of commands sent to Arduino:**
- `[control]:blower:start\n`
- `[control]:blower:stop\n`
- `[control]:blower:speed:100\n`
- `[control]:blower:direction:reverse\n`
- `[control]:blower:direction:normal\n`
- `[control]:actuatormotor:up\n`
- `[control]:actuatormotor:down\n`
- `[control]:actuatormotor:stop\n`

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