import time
import random
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883
PUBLISH_INTERVAL = 1  # seconds

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER_HOST, BROKER_PORT)

# Valeurs initiales dans les plages normales
angle_of_attack = 20.0  # début vers milieu de plage 15°-25°
control_surface_position = 0.0  # milieu de -30° à +30°

def evolve_value(current, min_val, max_val, step=0.5, anomaly_chance=0.05, anomaly_step=10):
    """
    Fait évoluer la valeur proche de la précédente,
    avec une petite chance d'anomalie (grand saut).
    """
    if random.random() < anomaly_chance:
        # Anomalie: grand saut hors plage normale
        delta = random.uniform(-anomaly_step, anomaly_step)
        new_val = current + delta
        # Possible dépassement volontaire des limites pour simuler anomalie
        return round(new_val, 2)
    else:
        # Petit déplacement cohérent
        delta = random.uniform(-step, step)
        new_val = current + delta
        # Clamp dans la plage autorisée
        new_val = max(min_val, min(max_val, new_val))
        return round(new_val, 2)

def publish(measurement, value, unit):
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "value": value,
        "unit": unit,
        "source": "flight-control-sensor-01",
        "aircraft_zone": "flight_control"
    }
    topic = f"aircraft/flightcontrol/{measurement}/1"
    mqtt_client.publish(topic, json.dumps(message))
    print(f"Sent to {topic}: {message}")

while True:
    angle_of_attack = evolve_value(angle_of_attack, 15, 25)
    control_surface_position = evolve_value(control_surface_position, -30, 30)

    publish("angle_of_attack", angle_of_attack, "degrees")
    publish("control_surface_position", control_surface_position, "degrees")

    time.sleep(PUBLISH_INTERVAL)
