#!/bin/sh
set -e

python /app/flask_server.py &
python /app/data-simulator/polygons/generate_polygon.py &
python /app/flight-simulator/flight_simulator.py &

wait
