FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt

COPY ../../src/sensors/engine_simulator.py .
COPY ../../src/sensors/hydraulic_simulator.py .
COPY ../../src/sensors/structural_simulator.py .
COPY ../../src/sensors/navigation_simulator.py .
COPY ../../src/sensors/flight_control_simulator.py .

CMD ["python", "engine_simulator.py"]
