# FalconEye Avionics Simulation

FalconEye is a containerized avionics simulation environment. It simulates aircraft subsystems (navigation, flight control, hydraulics, engine, structure), publishes sensor data via MQTT, stores the data in InfluxDB, and visualizes it in Grafana dashboards.

---

## Architecture

```mermaid
graph TD
  subgraph falconnet
    nav[Navigation Simulator] --> mqtt[Mosquitto (MQTT Broker)]
    ctrl[Flight Control Simulator] --> mqtt
    hydr[Hydraulics Simulator] --> mqtt
    engine[Engine Simulator] --> mqtt
    struct[Structure Simulator] --> mqtt
    mqtt --> collector[MQTT Collector → InfluxDB]
    collector --> influx[InfluxDB]
    influx --> grafana[Grafana]
  end
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/falconeye.git
   cd falconeye
   ```

2. Launch the infrastructure:
   ```bash
   docker-compose up -d
   ```

3. Access Grafana at [http://localhost:3000](http://localhost:3000)  
   Default credentials:  
   - **Username**: `admin`  
   - **Password**: `adminpass`  

   Same credentials apply to InfluxDB.

---

## Configuration

- All services are isolated in the `falconnet` Docker network.
- The system includes:
  - `mosquitto`: MQTT broker
  - `influxdb`: time-series database
  - `grafana`: dashboards
  - `mqtt-collector-influxdb`: validates and stores MQTT messages
  - Simulators:
    - `navigation_simulator.py`
    - `flight_control_simulator.py`
    - `hydraulic_simulator.py`
    - `engine_simulator.py`
    - `structural_simulator.py`

- Dashboards are auto-loaded from the `/dashboards/` folder.

---

## 📊 Dashboards

- **Navigation Monitoring**: GPS coordinates and airspeed
- **Flight Control Monitoring**: Angle of attack, control surface positions
- **Hydraulic Monitoring**: Pressure and pump status
- **Engine Monitoring**: Temperature, Oil pressure and Vibrations
- **Structural Monitoring**: Acceleration

Dashboards are refreshed every 3 seconds and show the last 5 minutes of data.

---

## Testing

### End-to-End Test

Run an integration test to verify the full data flow from sensor to dashboard (but not possible with the integration of the others simulator):

```bash
docker-compose run --rm end_to_end_test
```

This test checks:
- MQTT publication
- JSON message validation
- Data insertion into InfluxDB
- Grafana data availability

### Network Test

Use the included `check_network.sh` script to verify:
- All containers are connected to `falconnet`
- Critical communication paths:
  - mosquitto → mqtt-collector-influxdb → influxdb

```bash
bash test/integration/check_network.sh
```

---

## 📄 License

This project is licensed under the **MIT License**.

---
