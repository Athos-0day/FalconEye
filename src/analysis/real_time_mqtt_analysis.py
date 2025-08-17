"""
Realtime MQTT-based analyzer with global and per-key cooldown.
"""

import json
import logging
import ssl
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# ---------- CONFIG ----------
BROKER_HOST = "mosquitto"
BROKER_PORT = 8883
CLIENT_ID = "analysis"
CERT_DIR = "/app/certs"

PUBLISH_TOPIC_BASE = "aircraft/alerts"

# Smoothing & cooldowns
EMA_ALPHA = 0.25        # smoothing factor (0..1)
COOLDOWN_SECONDS = 30   # per-key cooldown
MAX_PUBS_PER_SECOND = 10  # global limit

# Per-measurement rules: min, max, rate_thresh, deltaT_target
RULES = {
    "temperature": (40.0, 1200.0, 2.0, 5.0),
    "oil_pressure": (0.0, 10.0, 0.5, 3.0),
    "vibrations": (0.0, 50.0, 5.0, 1.0),
    "pressure": (0.0, 350.0, 10.0, 3.0),
    "acceleration": (0.0, 20.0, 2.0, 1.0),
    "airspeed": (0.0, 2500.0, 50.0, 1.0),
    "angle_of_attack": (-15.0, 25.0, 1.0, 1.0),
    "control_surface_position": (-30.0, 30.0, 5.0, 1.0),
}

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------- Helpers ----------
def parse_iso_ts(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None

def make_alert_payload(measurement, value, unit, rate, level, source, aircraft_zone, ts):
    return {
        "timestamp": ts,
        "measurement": measurement,
        "value": value,
        "unit": unit,
        "rate_per_s": rate,
        "level": level,
        "source": source,
        "aircraft_zone": aircraft_zone
    }

# ---------- State ----------
state = defaultdict(lambda: {
    "ema": None,
    "last_ts": None,
    "last_ema": None,
    "cooldown_until": 0
})

# Global cooldown tracker
last_pub_times = deque()

def safe_publish(topic, payload):
    now = time.time()
    # Remove timestamps older than 1 sec
    while last_pub_times and now - last_pub_times[0] > 1:
        last_pub_times.popleft()

    if len(last_pub_times) < MAX_PUBS_PER_SECOND:
        mqtt_client.publish(topic, payload)
        last_pub_times.append(now)
        logging.info("Published alert: %s", topic)
    else:
        logging.warning("Ratelimit hit — alert dropped for topic %s", topic)

# ---------- MQTT setup ----------
mqtt_client = mqtt.Client(client_id=CLIENT_ID, userdata=None, protocol=mqtt.MQTTv311)
mqtt_client.username_pw_set(username="analysis", password="analysis")
mqtt_client.tls_set(
    ca_certs=f"{CERT_DIR}/ca.crt",
    certfile=f"{CERT_DIR}/analysis.crt",
    keyfile=f"{CERT_DIR}/analysis.key",
    tls_version=ssl.PROTOCOL_TLSv1_2
)
mqtt_client.tls_insecure_set(False)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT broker")
        client.subscribe("aircraft/#")
    else:
        logging.error("Failed to connect, rc=%s", rc)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        logging.warning("Invalid JSON payload on %s: %s", msg.topic, e)
        return

    parts = msg.topic.split("/")
    if len(parts) < 3:
        return
    measurement = parts[1]
    field = parts[2]

    source = payload.get("source", "unknown")
    zone = payload.get("aircraft_zone", "unknown")
    key = f"{measurement}.{field}.{source}.{zone}"

    if field == "position":
        return

    if not {"timestamp", "value", "unit"}.issubset(payload):
        logging.debug("Incomplete message: %s", payload)
        return

    ts = parse_iso_ts(payload["timestamp"])
    value = safe_float(payload["value"])
    unit = payload["unit"]
    if value is None:
        return

    s = state[key]
    prev_ema = s["ema"]
    ema = value if prev_ema is None else EMA_ALPHA * value + (1 - EMA_ALPHA) * prev_ema

    rate = 0.0
    last_ts = s["last_ts"]
    if last_ts is not None:
        dt = (ts - last_ts).total_seconds()
        if dt > 0:
            prev_ema_for_rate = s["last_ema"] if s["last_ema"] is not None else prev_ema
            if prev_ema_for_rate is None:
                prev_ema_for_rate = prev_ema
            rate = (ema - prev_ema_for_rate) / dt

    s["last_ts"] = ts
    s["last_ema"] = ema
    s["ema"] = ema

    rule = RULES.get(field)
    if rule is None:
        for k in RULES.keys():
            if k in field or field in k:
                rule = RULES[k]
                break

    level = None
    if rule:
        min_val, max_val, rate_thresh, _ = rule
        if value < min_val or value > max_val:
            level = "threshold"
        elif abs(rate) > rate_thresh:
            level = "slope"
    else:
        return

    now_ts = time.time()
    if level and now_ts >= s["cooldown_until"]:
        alert = make_alert_payload(
            measurement=f"{measurement}.{field}",
            value=value,
            unit=unit,
            rate=round(rate, 6),
            level=level,
            source=source,
            aircraft_zone=zone,
            ts=payload["timestamp"]
        )
        out_topic = f"{PUBLISH_TOPIC_BASE}/{measurement}.{field}/1"
        safe_publish(out_topic, json.dumps(alert))
        s["cooldown_until"] = now_ts + COOLDOWN_SECONDS

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def main():
    mqtt_client.connect(BROKER_HOST, BROKER_PORT)
    logging.info("Starting realtime analyzer loop with global cooldown")
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
