"""
Application settings and configuration
"""

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_SUB = "sensor/data"
TOPIC_PUB = "esp32/control"

# Firebase Configuration
FIREBASE_URL = "https://addsensorvalue-bp4gxqhmza-uc.a.run.app"

# Command Configuration
COMMAND_INTERVAL = 5  # seconds
COMMANDS = ["on_in1", "on_in2", "off_all"]

# Application Configuration
APP_NAME = "Pi MQTT Server"
DEBUG = False
LOG_LEVEL = "INFO" 