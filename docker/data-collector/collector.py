import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import time

# InfluxDB config - hostname docker service
INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "supersecrettoken"
INFLUX_ORG = "falconeye"
INFLUX_BUCKET = "mybucket"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe("aircraft/#")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    print(f"Received message on topic {msg.topic}: {msg.payload}", flush=True)
    try:
        payload = json.loads(msg.payload.decode())

        topic_parts = msg.topic.split('/')
        if len(topic_parts) < 3:
            print("Invalid topic:", msg.topic)
            return

        measurement = topic_parts[1]
        field_name = topic_parts[2]

        if field_name == "position":
            if not {"timestamp", "latitude", "longitude"}.issubset(payload):
                print("Incomplete GPS message:", payload)
                return

            point = (
                Point(measurement)
                .tag("source", payload.get("source", "unknown"))
                .tag("unit", payload.get("unit", "degrees"))
                .tag("aircraft_zone", payload.get("aircraft_zone", "unknown"))
                .field("latitude", float(payload["latitude"]))
                .field("longitude", float(payload["longitude"]))
                .time(payload["timestamp"])
            )
        else:
            if not {"timestamp", "value", "unit"}.issubset(payload):
                print("Incomplete sensor message:", payload)
                return

            point = (
                Point(measurement)
                .tag("source", payload.get("source", "unknown"))
                .tag("unit", payload["unit"])
                .tag("aircraft_zone", payload.get("aircraft_zone", "unknown"))
                .field(field_name, float(payload["value"]))
                .time(payload["timestamp"])
            )

        print(point, flush=True)
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print(f"→ Data inserted into {measurement}:", point.to_line_protocol(), flush=True)

    except Exception as e:
        print("Error:", e)


influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.enable_logger()  

connected = False
while not connected:
    try:
        mqtt_client.connect("mosquitto", 1883)
        connected = True
    except Exception as e:
        print("Waiting for MQTT broker to be ready...", e)
        time.sleep(2)

print("MQTT → InfluxDB collector started, listening on 'aircraft/#'", flush=True)
mqtt_client.loop_forever()
