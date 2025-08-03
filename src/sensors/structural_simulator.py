import time
import random
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883
PUBLISH_INTERVAL = 1  # seconds

acceleration = 5.0  # g (initial values)

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER_HOST, BROKER_PORT)

def evolve_value(current, normal_min, normal_max, anomaly_chance=0.03, step=1, anomaly_step=5):
    is_anomaly = random.random() < anomaly_chance
    if is_anomaly:
        direction = random.choice([-1, 1])
        delta = direction * random.uniform(anomaly_step * 0.8, anomaly_step * 1.2)
    else:
        delta = random.uniform(-step, step)

    new_value = current + delta
    safe_min = max(0, normal_min - 0.1 * abs(normal_min))
    safe_max = normal_max + 0.2 * abs(normal_max)
    return round(max(safe_min, min(new_value, safe_max)), 2)

def publish_measurement(measurement, value, unit, zone="fuselage"):
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "value": value,
        "unit": unit,
        "source": "sensor-structure-01",
        "aircraft_zone": zone
    }
    topic = f"aircraft/structure/{measurement}/1"
    mqtt_client.publish(topic, json.dumps(message))
    print(f"Sent to {topic}: {message}")

while True:
    acceleration = evolve_value(acceleration, 0, 20)
    publish_measurement("acceleration", acceleration, "g")
    time.sleep(PUBLISH_INTERVAL)
