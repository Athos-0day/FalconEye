#!/bin/bash

NETWORK="falconnet"
SERVICES=( "engine_simulator" "hydraulics_simulator" "navigation_simulator" "structural_simulator" "flightcontrol_simulator" )

# Notification function (works on macOS and Linux)
notify() {
    local title="$1"
    local message="$2"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e "display notification \"$message\" with title \"$title\""
    elif command -v notify-send >/dev/null 2>&1; then
        # Linux
        notify-send "$title" "$message"
    else
        # Fallback: just print
        echo "[$title] $message"
    fi
}

while true; do
    # Refresh network data
    if ! docker network inspect "$NETWORK" > /tmp/network_inspect.json 2>/dev/null; then
        notify "Network Monitor" "Network $NETWORK not found!"
        echo "[$(date)] Network $NETWORK not found!"
        sleep 5
        continue
    fi

    # Extract container names from the network
    containers=$(jq -r '.[0].Containers[].Name' /tmp/network_inspect.json)

    for service in "${SERVICES[@]}"; do
        if ! grep -q "$service" <<< "$containers"; then
            notify "Service Missing" "$service is not connected to $NETWORK"
            echo "[$(date)] ALERT: $service is missing from $NETWORK"
        fi
    done

    sleep 5
done
