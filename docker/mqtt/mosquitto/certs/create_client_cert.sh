#!/bin/bash

set -e

SENSORS=("engine" "flightcontrol" "hydraulic" "navigation" "structural")
CERT_DIR="config/certs"
CLIENT_DIR="docker/mqtt/mosquitto/certs"

echo "Creating client certificates..."

for sensor in "${SENSORS[@]}"; do
    echo " → Processing $sensor"

    # Generate private key
    openssl genpkey -algorithm EC -out "$sensor.key" -pkeyopt ec_paramgen_curve:P-256

    # Generate CSR
    openssl req -new -key "$sensor.key" -out "$sensor.csr" -subj "/CN=$sensor"

    # Sign the CSR with the CA
    openssl x509 -req -in "$sensor.csr" -CA $CLIENT_DIR/ca.crt -CAkey $CLIENT_DIR/ca.key -CAcreateserial -out "$sensor.crt" -days 3650 -sha256

    # Move to target directory
    mkdir -p "$CERT_DIR"
    cp "$sensor.key" "$sensor.crt" "$sensor.csr" "$CERT_DIR/"

    # Clean up temp files
    rm "$sensor.key" "$sensor.crt" "$sensor.csr"

    echo " ✓ Certificate for $sensor created and stored in $CERT_DIR"
done

echo "InfluxDB certificate"

# Generate private key
openssl genpkey -algorithm EC -out "influxdb.key" -pkeyopt ec_paramgen_curve:P-256

# Generate CSR
openssl req -new -key "influxdb.key" -out "influxdb.csr" -subj "/CN=dashboard"

# Sign the CSR with the CA
openssl x509 -req -in "influxdb.csr" -CA $CLIENT_DIR/ca.crt -CAkey $CLIENT_DIR/ca.key -CAcreateserial -out "influxdb.crt" -days 3650 -sha256

# Move to target directory
mkdir -p "$CERT_DIR"
cp "influxdb.key" "influxdb.crt" "influxdb.csr" "$CERT_DIR/"

# Clean up temp files
rm "influxdb.key" "influxdb.crt" "influxdb.csr"
