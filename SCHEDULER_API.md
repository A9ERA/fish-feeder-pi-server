# Scheduler API Documentation

## Overview
The Scheduler API provides endpoints to manage automated sync operations with dynamic intervals based on Firebase settings. The scheduler automatically syncs data between local storage and Firebase at configurable intervals.

## Firebase Settings Structure

The scheduler reads settings from Firebase at `/app_setting` with the following structure:

```json
{
  "duration": {
    "syncSensors": 10,     // Interval in seconds for syncing sensors TO Firebase
    "syncSchedule": 10,    // Interval in seconds for syncing schedule FROM Firebase
    "syncFeedPreset": 10   // Interval in seconds for syncing feed presets FROM Firebase
  }
}
```

## Scheduler Operations

The scheduler runs three types of automated sync operations:

1. **syncSensors**: Syncs local sensor data TO Firebase every X seconds
2. **syncSchedule**: Syncs schedule data FROM Firebase every X seconds
3. **syncFeedPreset**: Syncs feed preset data FROM Firebase every X seconds

## API Endpoints

### 1. Get Scheduler Status
**Endpoint:** `GET /api/scheduler/status`

**Description:** 
Get current status of the scheduler service including running state, current settings, and active jobs.

**Examples:**
```bash
# Get scheduler status
curl -X GET http://localhost:5000/api/scheduler/status
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Scheduler status retrieved successfully",
  "scheduler_status": {
    "running": true,
    "current_settings": {
      "syncSensors": 10,
      "syncSchedule": 10,
      "syncFeedPreset": 10
    },
    "active_jobs": ["syncSensors", "syncSchedule", "syncFeedPreset", "settings_monitor"],
    "thread_count": 4
  }
}
```

### 2. Start Scheduler
**Endpoint:** `POST /api/scheduler/start`

**Description:** 
Start the scheduler service. This will begin all automated sync operations according to current settings.

**Request Body:**
```json
// No request body required
```

**Examples:**
```bash
# Start scheduler
curl -X POST http://localhost:5000/api/scheduler/start \
  -H "Content-Type: application/json"
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Scheduler started successfully"
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Scheduler is already running"
}
```

### 3. Stop Scheduler
**Endpoint:** `POST /api/scheduler/stop`

**Description:** 
Stop the scheduler service. This will halt all automated sync operations.

**Request Body:**
```json
// No request body required
```

**Examples:**
```bash
# Stop scheduler
curl -X POST http://localhost:5000/api/scheduler/stop \
  -H "Content-Type: application/json"
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Scheduler stopped successfully"
}
```

### 4. Update Scheduler Settings (Manual)
**Endpoint:** `POST /api/scheduler/update`

**Description:** 
Manually update scheduler sync intervals and sync to Firebase. This will update both local settings and Firebase `/app_setting` path.

**Request Body:**
```json
{
  "syncSensors": 15,     // Optional: New interval for sensor sync (seconds)
  "syncSchedule": 20,    // Optional: New interval for schedule sync (seconds)
  "syncFeedPreset": 30   // Optional: New interval for feed preset sync (seconds)
}
```

**Examples:**
```bash
# Update all sync intervals
curl -X POST http://localhost:5000/api/scheduler/update \
  -H "Content-Type: application/json" \
  -d '{
    "syncSensors": 15,
    "syncSchedule": 20,
    "syncFeedPreset": 30
  }'

# Update only sensor sync interval
curl -X POST http://localhost:5000/api/scheduler/update \
  -H "Content-Type: application/json" \
  -d '{
    "syncSensors": 5
  }'

# Disable a sync job (set to 0)
curl -X POST http://localhost:5000/api/scheduler/update \
  -H "Content-Type: application/json" \
  -d '{
    "syncSchedule": 0
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Settings updated and synced to Firebase successfully",
  "new_settings": {
    "syncSensors": 15,
    "syncSchedule": 20,
    "syncFeedPreset": 30
  },
  "firebase_synced": true
}
```

**Note:** This endpoint will:
1. Update local scheduler settings
2. Sync the updated settings to Firebase `/app_setting` path  
3. Restart running scheduler jobs with new intervals
4. Save settings to local backup file

**Error Response:**
```json
{
  "status": "error",
  "message": "Invalid value for syncSensors. Must be non-negative integer."
}
```

## Scheduler Behavior

### Automatic Settings Updates
- The scheduler checks Firebase settings every 30 seconds
- If settings change in Firebase, the scheduler automatically restarts with new intervals
- Local settings file is maintained as backup when Firebase is unavailable

### Job Management
- Each sync operation runs in its own thread
- If interval is set to 0, that sync job is disabled
- Jobs restart automatically when settings change
- Thread-safe operations prevent concurrent sync conflicts

### Error Handling
- If a sync operation fails, it logs the error and continues on schedule
- If Firebase is unavailable, the scheduler uses local settings file
- Network issues don't stop the scheduler from running

### Fallback Mechanism
- Settings are cached locally in `src/data/app_settings.jsonc`
- If Firebase is unavailable, uses local cache
- Default intervals are 10 seconds for all sync operations

## Testing

### Quick Test Commands

```bash
# Check if scheduler is running
curl -X GET http://localhost:5000/api/scheduler/status

# Start the scheduler
curl -X POST http://localhost:5000/api/scheduler/start \
  -H "Content-Type: application/json"

# Check status after starting
curl -X GET http://localhost:5000/api/scheduler/status

# Update settings for faster testing
curl -X POST http://localhost:5000/api/scheduler/update \
  -H "Content-Type: application/json" \
  -d '{
    "syncSensors": 5,
    "syncSchedule": 5,
    "syncFeedPreset": 5
  }'

# Stop the scheduler
curl -X POST http://localhost:5000/api/scheduler/stop \
  -H "Content-Type: application/json"
```

### Testing Tips

1. **Monitor Logs**: Watch server console for scheduler activity
2. **Start Small**: Use short intervals (5-10 seconds) for testing
3. **Check Firebase**: Verify data is being synced in Firebase console
4. **Status Monitoring**: Use `/api/scheduler/status` to monitor active jobs
5. **Graceful Shutdown**: Always stop scheduler before server shutdown

## Firebase Setup

### Required Firebase Database Structure

Ensure your Firebase Realtime Database has these references:

```
/app_setting
  /duration
    /syncSensors: 10
    /syncSchedule: 10
    /syncFeedPreset: 10

/sensors_data
  // Sensor data will be synced here

/schedule_data
  // Schedule data to be synced from here

/feed_preset
  // Feed preset data to be synced from here
```

### Database Rules

Ensure Firebase database rules allow read/write access:

```json
{
  "rules": {
    "app_setting": {
      ".read": true,
      ".write": true
    },
    "sensors_data": {
      ".read": true,
      ".write": true
    },
    "schedule_data": {
      ".read": true,
      ".write": true
    },
    "feed_preset": {
      ".read": true,
      ".write": true
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Scheduler Not Starting**
   ```json
   {
     "status": "error",
     "message": "Failed to initialize Firebase"
   }
   ```
   - Check Firebase credentials and connection
   - Verify `app_setting` exists in Firebase

2. **No Firebase Settings**
   ```
   [Scheduler] Failed to get settings from Firebase, using local file
   ```
   - This is normal if `/app_setting` doesn't exist in Firebase
   - Scheduler will use default 10-second intervals

3. **Sync Failures**
   ```
   [Scheduler] Failed to sync sensors to Firebase
   ```
   - Check Firebase connection and database rules
   - Monitor network connectivity

### Debug Commands

```bash
# Check scheduler logs
curl -X GET http://localhost:5000/api/scheduler/status | jq .

# Test with verbose curl
curl -v -X POST http://localhost:5000/api/scheduler/start

# Monitor real-time status
watch -n 2 'curl -s http://localhost:5000/api/scheduler/status | jq .scheduler_status'
```

## Integration

The scheduler automatically starts when the server starts and can be controlled via these API endpoints. It integrates with:

- **Firebase Service**: For reading settings and syncing data
- **Sensor Data Service**: For collecting sensor data to sync
- **API Service**: For accessing sync methods

The scheduler runs independently in the background and requires no manual intervention once configured. 