#!/bin/sh
set -e

python /app/data-simulator/polygons/generate_polygon.py &
python /app/flight-simulator/flight_simulator.py &

wait
