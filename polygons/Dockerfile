# ========================================================
# Stage 1: Build & Dependency Installation
# ========================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies required for building wheels (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements to leverage Docker caching layers
COPY src/flight_simulator/requirements.txt .

# Install dependencies into a local directory
RUN pip install --no-cache-dir --user -r requirements.txt


# ========================================================
# Stage 2: Final Lightweight Runtime Environment
# ========================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime GIS dependencies required by Shapely
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from the builder stage
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Ensure the installed packages are in the python path
ENV PATH=/root/.local/bin:$PATH

# Copy your actual application source code
COPY src/flight_simulator/ /app/

# Environment flags (keeps python from buffering outputs for clean docker logs)
ENV PYTHONUNBUFFERED=1

# Run the script as a non-root user for security compliance
USER 1001

# Command to kickstart your background generator script
CMD ["python", "generate_polygon.py"]