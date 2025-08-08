import time
import random
import json
import logging
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import ssl

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BROKER_HOST = "mosquitto"
BROKER_PORT = 8883
PUBLISH_INTERVAL = 1  # seconds

# Initial values
hydraulic_pressure = 200.0  # bars
pump_state = "ON"

# Anomaly trackers
anomaly_state = {
    "hydraulic_pressure": False,
    "pump_state": False,
}

anomaly_duration = {
    "hydraulic_pressure": 0,
    "pump_state": 0,
}

mqtt_client = mqtt.Client(client_id="hydraulic-simulator", userdata=None, protocol=mqtt.MQTTv311)
mqtt_client.username_pw_set(username="hydraulic", password="hydraulic")
mqtt_client.tls_set(
    ca_certs="/app/certs/ca.crt",
    certfile="/app/certs/hydraulic.crt",
    keyfile="/app/certs/hydraulic.key",
    tls_version=ssl.PROTOCOL_TLSv1_2
)
mqtt_client.tls_insecure_set(False)
mqtt_client.connect(BROKER_HOST, BROKER_PORT)

def evolve_pressure(current, normal_min, normal_max, anomaly_chance=0.03, step=10, anomaly_step=50):
    if anomaly_state["hydraulic_pressure"]:
        anomaly_duration["hydraulic_pressure"] -= 1
        if anomaly_duration["hydraulic_pressure"] <= 0:
            anomaly_state["hydraulic_pressure"] = False
        delta = random.uniform(anomaly_step * -1, anomaly_step)
    else:
        if random.random() < anomaly_chance:
            anomaly_state["hydraulic_pressure"] = True
            anomaly_duration["hydraulic_pressure"] = random.randint(3, 6)
            delta = random.uniform(anomaly_step * -1, anomaly_step)
        else:
            delta = random.uniform(-step, step)

    new_value = current + delta
    safe_min = normal_min - 0.1 * abs(normal_min)
    safe_max = normal_max + 0.2 * abs(normal_max)
    return round(max(safe_min, min(new_value, safe_max)), 2)

def evolve_pump_state():
    if anomaly_state["pump_state"]:
        anomaly_duration["pump_state"] -= 1
        if anomaly_duration["pump_state"] <= 0:
            anomaly_state["pump_state"] = False
        return "OFF"

    if random.random() < 0.01:
        anomaly_state["pump_state"] = True
        anomaly_duration["pump_state"] = random.randint(5, 10)
        return "OFF"
    
    return "ON"

def publish_measurement(measurement, value, unit, zone="central"):
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "value": value,
        "unit": unit,
        "source": "sensor-02",
        "aircraft_zone": zone
    }
    topic = f"aircraft/hydraulics/{measurement}/1"
    mqtt_client.publish(topic, json.dumps(message))
    logging.info(f"Sent to {topic}: {message}")

while True:
    hydraulic_pressure = evolve_pressure(hydraulic_pressure, 50, 300)
    pump_state = evolve_pump_state()

    publish_measurement("pressure", hydraulic_pressure, "bar")
    publish_measurement("pump_state", 1 if pump_state == "ON" else 0, "binary")

    time.sleep(PUBLISH_INTERVAL)
