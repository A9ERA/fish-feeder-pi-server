# Pi Server API Testing Guide

## Quick Start

### 1. Start the Server
```bash
cd /path/to/pi-server
python3 main.py
```

### 2. Test Server Health
```bash
curl -X GET http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "uptime": "0h 0m 15s",
  "timestamp": "2024-01-15 14:30:45",
  "version": "1.0.0"
}
```

## Individual Device Control Tests

### Blower Control Tests
```bash
# Start blower
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'

# Stop blower
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'

# Set blower speed to 50
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "speed", "value": 50}'

# Set blower direction to reverse
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "direction_reverse"}'

# Set blower direction to normal
curl -X POST http://localhost:5000/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "direction_normal"}'
```

### Actuator Control Tests
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

### Auger Control Tests
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

# Set auger speed to 75
curl -X POST http://localhost:5000/api/control/auger \
  -H "Content-Type: application/json" \
  -d '{"action": "setspeed", "value": 75}'
```

### Relay Control Tests
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

# Turn all relays off (emergency stop)
curl -X POST http://localhost:5000/api/control/relay \
  -H "Content-Type: application/json" \
  -d '{"device": "all", "action": "off"}'
```

## Feeder Process Tests

### Test 1: Quick Feeding Process (7 seconds total)
```bash
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 25,
    "actuatorUp": 1,
    "actuatorDown": 1,
    "augerDuration": 2,
    "blowerDuration": 3
  }'
```

### Test 2: Standard Feeding Process (20 seconds total)
```bash
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 100,
    "actuatorUp": 3,
    "actuatorDown": 2,
    "augerDuration": 8,
    "blowerDuration": 7
  }'
```

### Test 3: Large Feeding Process (53 seconds total)
```bash
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 250,
    "actuatorUp": 8,
    "actuatorDown": 5,
    "augerDuration": 20,
    "blowerDuration": 20
  }'
```

### Expected Success Response:
```json
{
  "status": "success",
  "message": "Feeding process completed successfully",
  "feed_size": 100,
  "total_duration": 20,
  "steps_completed": [
    "Actuator up: 3s",
    "Actuator down: 2s", 
    "Auger forward: 8s",
    "Blower: 7s"
  ]
}
```

## Error Testing

### Test Invalid Parameters
```bash
# Missing parameters
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{"feedSize": 100}'

# Invalid parameter types
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": "not_a_number",
    "actuatorUp": 1,
    "actuatorDown": 1,
    "augerDuration": 1,
    "blowerDuration": 1
  }'

# Negative values
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 100,
    "actuatorUp": -1,
    "actuatorDown": 1,
    "augerDuration": 1,
    "blowerDuration": 1
  }'

# Values exceeding safety limit (>300 seconds)
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 100,
    "actuatorUp": 350,
    "actuatorDown": 1,
    "augerDuration": 1,
    "blowerDuration": 1
  }'
```

## Sensor Data Tests

### Get All Sensors
```bash
curl -X GET http://localhost:5000/api/sensors
```

### Get Specific Sensor
```bash
curl -X GET http://localhost:5000/api/sensors/temperature
curl -X GET http://localhost:5000/api/sensors/humidity
curl -X GET http://localhost:5000/api/sensors/ph
curl -X GET http://localhost:5000/api/sensors/dissolved_oxygen
```

### Sync Sensors to Firebase
```bash
curl -X POST http://localhost:5000/api/sensors/sync
```

## Testing Scripts

### Save as `test_all_endpoints.sh`
```bash
#!/bin/bash

BASE_URL="http://localhost:5000"

echo "Testing Pi Server API..."
echo "========================"

echo "1. Testing health endpoint..."
curl -s $BASE_URL/health | jq .

echo -e "\n2. Testing blower control..."
curl -s -X POST $BASE_URL/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}' | jq .

sleep 2

curl -s -X POST $BASE_URL/api/control/blower \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}' | jq .

echo -e "\n3. Testing actuator control..."
curl -s -X POST $BASE_URL/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "up"}' | jq .

sleep 1

curl -s -X POST $BASE_URL/api/control/actuator \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}' | jq .

echo -e "\n4. Testing quick feeding process..."
curl -s -X POST $BASE_URL/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feedSize": 25,
    "actuatorUp": 1,
    "actuatorDown": 1,
    "augerDuration": 1,
    "blowerDuration": 1
  }' | jq .

echo -e "\nAll tests completed!"
```

### Make executable and run:
```bash
chmod +x test_all_endpoints.sh
./test_all_endpoints.sh
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   curl: (7) Failed to connect to localhost port 5000: Connection refused
   ```
   - Solution: Make sure the server is running with `python3 main.py`

2. **Serial Communication Error**
   ```json
   {
     "status": "error",
     "message": "Failed to send command to device"
   }
   ```
   - Solution: Check Arduino connection and ensure it's programmed correctly

3. **Feeding Process Already Running**
   ```json
   {
     "status": "error", 
     "message": "Feeding process is already running"
   }
   ```
   - Solution: Wait for current process to complete or restart the server

### Debug Commands

```bash
# Check if server is running
curl -I http://localhost:5000/health

# Monitor server logs
tail -f /path/to/server/logs

# Test with verbose output
curl -v -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{"feedSize": 10, "actuatorUp": 1, "actuatorDown": 1, "augerDuration": 1, "blowerDuration": 1}'
```

## Tips for Testing

1. **Start Small**: Begin with short durations (1-2 seconds) when testing
2. **Monitor Logs**: Watch server console output for detailed step-by-step progress
3. **Use jq**: Install `jq` for pretty JSON formatting: `brew install jq` (macOS) or `sudo apt install jq` (Ubuntu)
4. **Safety First**: Never exceed 300 seconds for any single operation
5. **Sequential Testing**: Wait for one operation to complete before starting another
6. **Emergency Stop**: Use relay "all off" command or restart server if needed 