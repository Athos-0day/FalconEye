import time
import random
import json
import logging
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883
PUBLISH_INTERVAL = 1  # seconds

# Initial values
temperature = 600.0     # °C
oil_pressure = 5.0      # bars
vibrations = 10.0       # g

# Anomaly state tracker
anomaly_state = {
    "temperature": False,
    "oil_pressure": False,
    "vibrations": False,
}

anomaly_duration = {
    "temperature": 0,
    "oil_pressure": 0,
    "vibrations": 0,
}

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER_HOST, BROKER_PORT)

def evolve_value(name, current, normal_min, normal_max, anomaly_chance=0.05, step=5, anomaly_step=20):
    # Check if anomaly is already active
    if anomaly_state[name]:
        anomaly_duration[name] -= 1
        if anomaly_duration[name] <= 0:
            anomaly_state[name] = False
        delta = random.uniform(anomaly_step * -1, anomaly_step)
    else:
        if random.random() < anomaly_chance:
            anomaly_state[name] = True
            anomaly_duration[name] = random.randint(3, 6)  # lasts 3–6 cycles
            delta = random.uniform(anomaly_step * -1, anomaly_step)
        else:
            delta = random.uniform(-step, step)

    new_value = current + delta
    safe_min = normal_min - 0.1 * abs(normal_min)
    safe_max = normal_max + 0.2 * abs(normal_max)
    return round(max(safe_min, min(new_value, safe_max)), 2)

def publish_measurement(measurement, value, unit, zone="rear"):
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "value": value,
        "unit": unit,
        "source": "sensor-01",
        "aircraft_zone": zone
    }
    topic = f"aircraft/engine/{measurement}/1"
    mqtt_client.publish(topic, json.dumps(message))
    logging.info(f"Sent to {topic}: {message}")

while True:
    temperature = evolve_value("temperature", temperature, 40, 1100, anomaly_chance=0.03, anomaly_step=100)
    oil_pressure = evolve_value("oil_pressure", oil_pressure, 1, 8, anomaly_chance=0.03, anomaly_step=2)
    vibrations = evolve_value("vibrations", vibrations, 0, 30, anomaly_chance=0.03, anomaly_step=10)

    publish_measurement("temperature", temperature, "Celsius")
    publish_measurement("oil_pressure", oil_pressure, "bar")
    publish_measurement("vibrations", vibrations, "g")

    time.sleep(PUBLISH_INTERVAL)