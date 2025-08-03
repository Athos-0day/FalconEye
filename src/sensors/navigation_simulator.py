import time
import random
import json
import math
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883
PUBLISH_INTERVAL = 1  # seconds

# Initial position (somewhere over Europe)
latitude = 48.8566
longitude = 2.3522
airspeed = 800.0  # km/h

# Direction en degrés (0 = nord, 90 = est, etc.)
heading = random.uniform(0, 360)

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER_HOST, BROKER_PORT)

def evolve_heading(current_heading, max_change=5):
    """Fait légèrement varier le cap (direction de l'avion)."""
    return (current_heading + random.uniform(-max_change, max_change)) % 360

def move_gps(lat, lon, speed_kmh, heading_deg):
    """Déplace la position selon la vitesse et le cap."""
    # Conversion vitesse en km/s
    distance_km = speed_kmh / 3600.0

    # Convertir le cap en radians
    heading_rad = math.radians(heading_deg)

    # Approximation : 1° ≈ 111 km pour la latitude
    delta_lat = distance_km * math.cos(heading_rad) / 111.0
    delta_lon = distance_km * math.sin(heading_rad) / (111.0 * math.cos(math.radians(lat)))

    new_lat = lat + delta_lat
    new_lon = lon + delta_lon
    return new_lat, new_lon

def evolve_speed(current, min_val, max_val, anomaly_chance=0.03, step=30, anomaly_step=500):
    if random.random() < anomaly_chance:
        delta = random.uniform(-anomaly_step, anomaly_step)
    else:
        delta = random.uniform(-step, step)
    new_speed = max(min_val, min(max_val, current + delta))
    return round(new_speed, 2)

def publish(measurement, value, unit):
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "value": value,
        "unit": unit,
        "source": "nav-sensor-01",
        "aircraft_zone": "cockpit"
    }
    topic = f"aircraft/navigation/{measurement}/1"
    mqtt_client.publish(topic, json.dumps(message))
    print(f"Sent to {topic}: {message}")

def publish_position(lat, lon):
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "unit": "degrees",
        "source": "nav-sensor-01",
        "aircraft_zone": "cockpit"
    }
    topic = "aircraft/navigation/position/1"
    mqtt_client.publish(topic, json.dumps(message))
    print(f"Sent to {topic}: {message}")

# Boucle principale
while True:
    heading = evolve_heading(heading)
    latitude, longitude = move_gps(latitude, longitude, airspeed, heading)
    airspeed = evolve_speed(airspeed, 0, 2500)

    publish_position(latitude, longitude)
    publish("airspeed", airspeed, "km/h")

    time.sleep(PUBLISH_INTERVAL)
