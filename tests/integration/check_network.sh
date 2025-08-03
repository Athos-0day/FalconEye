#!/bin/bash

set -e

NETWORK="falconnet"
SERVICES=("mosquitto" "influxdb" "mqtt_collector_influxdb" "engine_simulator" "grafana" "hydraulics_simulator" "navigation_simulator" "structural_simulator" "flightcontrol_simulator")

echo "Shutting down and rebuilding..."
docker compose down > /dev/null 2>&1
docker compose build > /dev/null 2>&1
docker compose up -d > /dev/null 2>&1

echo "Waiting for services to initialize..."
sleep 2

echo "Checking that all services are attached to network: $NETWORK"
docker network inspect "$NETWORK" > /tmp/network_inspect.json

for service in "${SERVICES[@]}"; do
  if grep -q "$service" /tmp/network_inspect.json; then
    echo "$service is connected to $NETWORK"
  else
    echo "$service is NOT connected to $NETWORK"
  fi
done

echo -e "\nTesting connectivity from mqtt_collector_influxdb to other services..."

for target in "mosquitto" "influxdb"; do
  echo "mqtt_collector_influxdb → $target"
  docker exec mqtt_collector_influxdb ping -c 1 "$target" &>/dev/null && \
    echo "  Ping successful" || echo "  Ping failed"
done

echo -e "\nTesting HTTP access to InfluxDB from collector..."
docker exec mqtt_collector_influxdb curl -s http://influxdb:8086/health | grep -q '"status":"pass"' && \
  echo " InfluxDB is reachable and healthy" || echo " Could not reach InfluxDB from collector"

docker compose down
