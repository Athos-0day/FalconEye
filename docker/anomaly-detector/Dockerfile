FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt

COPY ../../src/analysis/influxdb_backfill_analysis.py .
COPY ../../src/analysis/real_time_mqtt_analysis.py .

CMD ["python", "real_time_mqtt_analysis.py"]