import os
import random
import uuid
import logging
import requests
from datetime import datetime, timedelta
from shapely.geometry import Polygon as ShapelyPolygon
from apscheduler.schedulers.background import BackgroundScheduler
import time
from pydantic import BaseModel, field_validator
from typing import List, Tuple, Literal

# Configure logging to display in console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration (override via .env / docker-compose)
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://666skt42-3000.uks1.devtunnels.ms/api/polygons",
)
API_KEY = os.getenv("API_KEY", "adminkey123456789")
POLYGON_INTERVAL_SECONDS = int(os.getenv("POLYGON_INTERVAL_SECONDS", "30"))
POLYGON_EXPIRY_MINUTES = int(os.getenv("POLYGON_EXPIRY_MINUTES", "3"))

# Authentication Headers
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
}

# Coordinate Boundaries (Mediterranean Sea, Israel, and Gaza)
TOTAL_MIN_LON = float(os.getenv("TOTAL_MIN_LON", "33.50"))
TOTAL_MAX_LON = float(os.getenv("TOTAL_MAX_LON", "35.90"))
TOTAL_MIN_LAT = float(os.getenv("TOTAL_MIN_LAT", "29.45"))
TOTAL_MAX_LAT = float(os.getenv("TOTAL_MAX_LAT", "33.30"))

# In-memory database tracking active shapes to prevent overlaps
active_polygons = []

# ========================================================
# GeoJSON Validation Schema (Pydantic translation of Zod)
# ========================================================
Coordinate = Tuple[float, float]

class GeoJsonPolygonSchema(BaseModel):
    type: Literal['Polygon']
    coordinates: List[List[Coordinate]]

    @field_validator('coordinates')
    @classmethod
    def validate_polygon_coordinates(cls, v: List[List[Coordinate]]):
        for ring in v:
            if len(ring) < 4:
                raise ValueError('A polygon linear ring must have at least 4 positions (including the closure)')
            if ring[0] != ring[-1]:
                raise ValueError('The first and last positions of a polygon linear ring must be identical')
        return v

# ========================================================
# Geometry & Classification Functions
# ========================================================
def generate_raw_polygon():
    num_vertices = random.randint(4, 7)
    max_radius = random.uniform(0.005, 0.06)
    
    center_lon = random.uniform(TOTAL_MIN_LON, TOTAL_MAX_LON)
    center_lat = random.uniform(TOTAL_MIN_LAT, TOTAL_MAX_LAT)
    
    points = []
    for _ in range(num_vertices):
        lon = center_lon + random.uniform(-max_radius, max_radius)
        lat = center_lat + random.uniform(-max_radius, max_radius)
        points.append((lon, lat))
        
    return ShapelyPolygon(points).convex_hull

def classify_zone_by_coordinates(lon, lat):
    if lon <= 34.60:
        if lat < 31.35: return "GAZA_SOUTH"
        elif lat < 31.48: return "GAZA_CENTER"
        else: return "GAZA_NORTH"
    else:
        if lat < 31.30: return "ISRAEL_SOUTH"
        elif lat < 32.30: return "ISRAEL_CENTER"
        else: return "ISRAEL_NORTH"

# ========================================================
# API Integration (Creation and Expiry Management)
# ========================================================
def clean_expired_polygons():
    """ Identifies expired polygons and tracks out an HTTP DELETE request """
    global active_polygons
    now = datetime.now()
    
    expired_polygons = [p for p in active_polygons if p['expiry_date'] <= now]
    
    for expired in expired_polygons:
        poly_id = expired['id']
        try:
            delete_url = f"{API_BASE_URL}/{poly_id}"
            response = requests.delete(delete_url, headers=HEADERS, timeout=5)
            
            if response.status_code in [200, 204]:
                logger.info(f"[API DELETE SUCCESS] Polygon {poly_id} expired and removed from DB.")
            else:
                logger.error(f"[API DELETE ERROR] Server returned status code {response.status_code} for ID: {poly_id}")
                
        except requests.RequestException as e:
            logger.error(f"[API DELETE NETWORK ERROR] Communication failure while deleting polygon {poly_id}: {e}")

    active_polygons = [p for p in active_polygons if p['expiry_date'] > now]

def generate_and_save_forbidden_polygon():
    """ Executed by the Scheduler every 30 seconds to push a newly generated polygon """
    global active_polygons
    
    # 1. Housekeeping: remove expired records first
    clean_expired_polygons()
    
    shapely_poly = None
    for _ in range(100):
        candidate_poly = generate_raw_polygon()
        has_overlap = any(candidate_poly.intersects(active['shapely_object']) for active in active_polygons)
        if not has_overlap:
            shapely_poly = candidate_poly
            break
            
    if not shapely_poly:
        logger.warning("[GENERATOR WARNING] Map is congested. No vacant space found for a new polygon in this cycle.")
        return

    # 2. Build GeoJSON Structure
    coords = list(shapely_poly.exterior.coords)
    geojson_coords = [[round(pt[0], 6), round(pt[1], 6)] for pt in coords]
    geojson_data = {
        "type": "Polygon",
        "coordinates": [geojson_coords]
    }
    
    # Validation Check
    try:
        GeoJsonPolygonSchema(**geojson_data)
    except Exception as e:
        logger.error(f"[VALIDATION FAILED] Structural GeoJSON discrepancy detected. Generation aborted: {e}")
        return

    now = datetime.now()
    expiry = now + timedelta(minutes=POLYGON_EXPIRY_MINUTES)
    matched_zone = classify_zone_by_coordinates(shapely_poly.centroid.x, shapely_poly.centroid.y)
    
    polygon_id = str(uuid.uuid4())
    expiry_iso_z = expiry.isoformat(timespec='milliseconds') + 'Z'

    # Build exact schema required by your API Docs
    payload = {
        "name": f"Forbidden Area - {now.strftime('%H:%M:%S')}",
        "geojson": geojson_data,
        "zone": matched_zone,
        "expiry_date": expiry_iso_z
    }
    
    # 4. Update the localized collision memory
    active_polygons.append({
        "id": polygon_id,
        "shapely_object": shapely_poly,
        "expiry_date": expiry
    })
    
    # 5. Dispatch POST request
    try:
        response = requests.post(API_BASE_URL, json=payload, headers=HEADERS, timeout=5)
        
        if response.status_code in [200, 201]:
            # Overwrite temporary local ID with the persistent DB ID if returned
            try:
                response_data = response.json()
                if "id" in response_data:
                    active_polygons[-1]["id"] = str(response_data["id"])
            except Exception:
                pass
                
            logger.info(f"[{now.strftime('%H:%M:%S')}] [API CREATE SUCCESS] Polygon dispatched to DB! Zone: {matched_zone}")
        else:
            logger.error(f"[API CREATE ERROR] Server rejected payroll payload with status code {response.status_code}. Details: {response.text}")
    except requests.RequestException as e:
        logger.error(f"[API CREATE NETWORK ERROR] Pipeline connection error during polygon push: {e}")


# ========================================================
# Main Execution Process Task Thread (Interval: 30s)
# ========================================================
def run_polygon_worker(stop_event=None):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=generate_and_save_forbidden_polygon,
        trigger="interval",
        seconds=POLYGON_INTERVAL_SECONDS,
    )

    scheduler.start()
    logger.info(
        "--- Background task runner initialized! Dispatching polygons every %s seconds ---",
        POLYGON_INTERVAL_SECONDS,
    )

    try:
        while stop_event is None or not stop_event.is_set():
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown(wait=False)
        logger.info("--- Background task runner terminated cleanly ---")


if __name__ == "__main__":
    run_polygon_worker()
