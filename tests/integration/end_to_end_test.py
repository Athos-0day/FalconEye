import json
import time
import requests
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

# --------- CONFIGURATION ---------
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "aircraft/flightcontrol/angle_of_attack/1"

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "supersecrettoken"
INFLUX_ORG = "falconeye"
INFLUX_BUCKET = "mybucket"

TEST_VALUE = 22.5
# ----------------------------------

# Publish a value with MQTT
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

message = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "value": TEST_VALUE,
    "unit": "degrees",
    "source": "sim-fc-01",
    "aircraft_zone": "wing"
}

print(f"[MQTT] Publishing test message: {message}")
client.publish(MQTT_TOPIC, json.dumps(message))
client.disconnect()

# Waiting to be sure that InfluxDB has received the message
time.sleep(5)

# Request InfluxDB
query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -2m)
  |> filter(fn: (r) => r._measurement == "flightcontrol" and r._field == "angle_of_attack")
  |> last()
'''

headers = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "application/vnd.flux",
    "Accept": "application/csv"
}

response = requests.post(
    f"{INFLUX_URL}/api/v2/query?org={INFLUX_ORG}",
    data=query,
    headers=headers
)

if response.status_code != 200:
    print("[ERROR] InfluxDB query failed:", response.text)
    exit(1)

lines = response.text.splitlines()
for line in lines:
    if not line.startswith("#") and len(line.strip()) > 0:
        fields = line.split(",")
        value = float(fields[-1])
        if abs(value - TEST_VALUE) < 0.01:
            print("[SUCCESS] Value found in InfluxDB:", value)
            break
else:
    print("[FAIL] Value not found or mismatched.")
