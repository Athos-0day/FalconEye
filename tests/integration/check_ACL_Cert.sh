#!/bin/bash

set -e

NETWORK="falconnet"
CERTS_DIR="$(pwd)/config/certs"
TOPIC="aircraft/engine/test/1"
FORBIDDEN_TOPIC="aircraft/forbidden/topic"
MESSAGE="test message from docker"

echo "Shutting down and rebuilding..."
docker compose down > /dev/null 2>&1
docker compose build > /dev/null 2>&1
docker compose up -d > /dev/null 2>&1

echo "Waiting for services to initialize..."
sleep 2

function test_pub_sub {
  local user_cert=$1
  local user_key=$2
  local username=$3
  local password=$4
  local topic=$5
  local expect_success=$6

  echo "Testing pub/sub for user='$username' on topic='$topic' with cert='$user_cert'..."

  # Start mosquitto_sub in background
  docker run --rm --network "$NETWORK" -v "$CERTS_DIR":/app/certs eclipse-mosquitto \
    mosquitto_sub \
    --cafile /app/certs/ca.crt \
    ${user_cert:+--cert /app/certs/$user_cert} \
    ${user_key:+--key /app/certs/$user_key} \
    -u influxdb -P influxdb \
    -h mosquitto -p 8883 -t "$topic" -C 1 > received_message.txt &

  SUB_PID=$!

  sleep 1  # wait for subscriber to be ready

  # Publish the message
  docker run --rm --network "$NETWORK" -v "$CERTS_DIR":/app/certs eclipse-mosquitto \
    mosquitto_pub \
    --cafile /app/certs/ca.crt \
    ${user_cert:+--cert /app/certs/$user_cert} \
    ${user_key:+--key /app/certs/$user_key} \
    -h mosquitto -p 8883 -t "$topic" -u "$username" -P "$password" -m "$MESSAGE" -d

  # Wait for message reception (timeout 5 seconds)
  timeout=5
  while [ $timeout -gt 0 ]; do
    if [ -s received_message.txt ]; then
      break
    fi
    sleep 1
    timeout=$((timeout - 1))
  done

  kill $SUB_PID 2>/dev/null || true

  if [ "$expect_success" == "true" ]; then
    if grep -q "$MESSAGE" received_message.txt; then
      echo "Test passed: message received"
    else
      echo "Test failed: message NOT received"
      cat received_message.txt
      exit 1
    fi
  else
    # Expecting failure (no message received)
    if grep -q "$MESSAGE" received_message.txt; then
      echo "Test failed: message received but expected failure"
      exit 1
    else
      echo "Test passed: no message received as expected"
    fi
  fi

  rm -f received_message.txt
}

echo
echo "=== Test 1: valid user + valid cert + allowed topic ==="
test_pub_sub "engine.crt" "engine.key" "engine" "engine" "$TOPIC" true

echo
echo "=== Test 2: valid user + valid cert + forbidden topic ==="
test_pub_sub "engine.crt" "engine.key" "engine" "engine" "$FORBIDDEN_TOPIC" false

echo
echo "=== Test 3: valid user + wrong password ==="
echo "Testing publish for user='engine' with wrong password (expect failure)..."

output=$(docker run --rm --network "$NETWORK" -v "$CERTS_DIR":/app/certs eclipse-mosquitto \
  mosquitto_pub \
  --cafile /app/certs/ca.crt \
  --cert /app/certs/engine.crt \
  --key /app/certs/engine.key \
  -h mosquitto -p 8883 -t "$TOPIC" -u "engine" -P "wrongpassword" -m "$MESSAGE" -d 2>&1 || true)

if echo "$output" | grep -q "Client null received CONNACK (5)"; then
  echo "Test passed: connection refused due to wrong password"
else
  echo "Test failed: publish succeeded or wrong error"
  echo "$output"
  exit 1
fi


echo
echo "=== Test 4: valid user + no client certificate ==="
# Publish without cert/key: remove cert params
function test_pub_no_cert {
  echo "Testing publish for user='engine' without client cert on topic='$TOPIC' (expect failure)..."
  if docker run --rm --network "$NETWORK" -v "$CERTS_DIR":/app/certs eclipse-mosquitto \
      mosquitto_pub \
      --cafile /app/certs/ca.crt \
      -h mosquitto -p 8883 -t "$TOPIC" -u "engine" -P "engine" -m "$MESSAGE" -d 2>&1 | grep -q "Error"; then
    echo "Test passed: publish failed without client certificate"
  else
    echo "Test failed: publish succeeded without client certificate"
    exit 1
  fi
}

test_pub_no_cert

echo
echo "All tests completed."
