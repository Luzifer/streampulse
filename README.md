# Luzifer / streampulse

This project is a simple connector of a heart-rate-sensor to a MQTT broker to display my heart-rate within my stream.

Used components:

- Heart-Rate-Sensor: Polar OH1 (but should work with a Polar H10 out of the box)
- Mosquitto MQTT server
- BlueZ daemon to connect to the device itself

In my case the script is running as a Systemd service, reporting my heart-rate to my MQTT server. A simple overlay using HTML / Vue / paho-mqtt receives the data and displays it to my stream.
