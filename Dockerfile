FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 8888 appuser \
    && chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
COPY --chown=appuser:appuser flask_server.py /app/
COPY --chown=appuser:appuser flight-simulator/flight_simulator.py /app/flight-simulator/
COPY --chown=appuser:appuser data-simulator/polygons/generate_polygon.py /app/data-simulator/polygons/

RUN chmod +x /app/entrypoint.sh

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000

EXPOSE 5000

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
