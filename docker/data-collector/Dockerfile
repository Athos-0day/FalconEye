# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the Python files into the container
COPY collector.py .

# Install required dependencies
RUN pip install --no-cache-dir paho-mqtt influxdb-client
RUN apt-get update && apt-get install -y curl iputils-ping && rm -rf /var/lib/apt/lists/*

# Command to run the collector script
CMD ["python3", "collector.py"]

