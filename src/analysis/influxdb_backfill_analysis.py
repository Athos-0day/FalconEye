#!/usr/bin/env python3
"""
Backfill/Batch analyzer that queries InfluxDB for recent points and checks the same rules.
Publishes alerts to MQTT (needs same TLS config).
"""

import json
import logging
import ssl
import time
from datetime import timedelta
from influxdb_client import InfluxDBClient
from paho.mqtt import client as mqtt_client

# ---------- CONFIG ----------
INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "supersecrettoken"
INFLUX_ORG = "falconeye"
INFLUX_BUCKET = "mybucket"

BROKER_HOST = "mosquitto"
BROKER_PORT = 8883
CERT_DIR = "/app/certs"
CLIENT_ID = "influx-backfill-analyzer"

# same RULES as realtime (copy/paste or import)
RULES = {
    "temperature": (40.0, 1200.0, 2.0, 5.0),
    "oil_pressure": (0.0, 10.0, 0.5, 3.0),
    "vibrations": (0.0, 50.0, 5.0, 1.0),
    "pressure": (0.0, 350.0, 10.0, 3.0),
    "acceleration": (0.0, 20.0, 2.0, 1.0),
    "airspeed": (0.0, 2500.0, 50.0, 1.0),
    "angle_of_attack": (-15.0, 25.0, 1.0, 1.0),
}

# query window
WINDOW_MINUTES = 10

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------- Setup clients ----------
influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = influx.query_api()

mqtt = mqtt_client.Client(client_id=CLIENT_ID, userdata=None, protocol=mqtt_client.MQTTv311)
mqtt.username_pw_set(username="analysis", password="analysis")
mqtt.tls_set(ca_certs=f"{CERT_DIR}/ca.crt",
             certfile=f"{CERT_DIR}/analysis.crt",
             keyfile=f"{CERT_DIR}/analysis.key",
             tls_version=ssl.PROTOCOL_TLSv1_2)
mqtt.tls_insecure_set(False)
mqtt.connect(BROKER_HOST, BROKER_PORT)

def check_series(measurement, field, records):
    # records: list of (time (datetime), value, unit, source, aircraft_zone)
    alerts = []
    # compute EMA and rate using pairwise approach
    ema = None
    prev_time = None
    prev_ema = None
    for rec in records:
        t, val, unit, src, zone = rec
        if val is None:
            continue
        if ema is None:
            ema = val
        else:
            ema = 0.25 * val + 0.75 * ema
        if prev_time is not None:
            dt = (t - prev_time).total_seconds()
            if dt > 0:
                rate = (ema - prev_ema) / dt
            else:
                rate = 0.0
        else:
            rate = 0.0
        prev_time = t
        prev_ema = ema

        # apply rule
        rule = RULES.get(field)
        if not rule:
            continue
        min_val, max_val, rate_thresh, _ = rule
        level = None
        if val < min_val or val > max_val:
            level = "threshold"
        elif abs(rate) > rate_thresh:
            level = "slope"
        if level:
            alerts.append({
                "timestamp": t.isoformat(),
                "measurement": f"{measurement}.{field}",
                "value": val,
                "unit": unit,
                "rate_per_s": rate,
                "level": level,
                "source": src,
                "aircraft_zone": zone
            })
    return alerts

def run():
    # for each measurement/field we query the last WINDOW_MINUTES
    q_base = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -{WINDOW_MINUTES}m)'
    # pivot pattern: we rely on measurement and field names stored as _measurement and _field with _value
    # loop through RULES fields
    all_alerts = []
    for field in RULES.keys():
        # query for measurements that have this field
        flux = q_base + f' |> filter(fn: (r) => r._field == "{field}") |> sort(columns: ["_time"])'
        try:
            tables = query_api.query(flux)
            # collect records
            records = []
            for table in tables:
                for row in table.records:
                    t = row.get_time()
                    v = row.get_value()
                    # tags:
                    src = row.values.get("source", "unknown")
                    zone = row.values.get("aircraft_zone", "unknown")
                    records.append((t, float(v) if v is not None else None, row.values.get("unit", ""), src, zone))
            if not records:
                continue
            alerts = check_series(measurement="*", field=field, records=records)
            all_alerts.extend(alerts)
        except Exception as e:
            logging.exception("Query error for field %s: %s", field, e)
    # publish alerts
    for a in all_alerts:
        topic = f"aircraft/alerts/{a['measurement']}/1"
        mqtt.publish(topic, json.dumps(a))
        logging.info("Published alert to %s : %s", topic, a)

if __name__ == "__main__":
    run()
