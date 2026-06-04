import random
from typing import Any

from src.config import get_allowed_point_max_attempts
from src.simulator.user_simulator.generation.message_builders import (
    build_location_payload,
)
from src.geo import bounding_box, extract_polygons, point_in_any_polygon


def sample_allowed_region_point(
    allowed_region_geojson: dict[str, Any],
    restricted_zone_rows: Any,
    max_attempts: int | None = None,
) -> dict[str, float]:
    resolved_max_attempts = max_attempts or get_allowed_point_max_attempts()
    allowed_polygons = extract_polygons(allowed_region_geojson)
    restricted_polygons = extract_polygons(restricted_zone_rows)

    if not allowed_polygons:
        raise ValueError("Allowed region GeoJSON does not contain any polygons")

    min_longitude, min_latitude, max_longitude, max_latitude = bounding_box(
        allowed_polygons
    )

    for _ in range(resolved_max_attempts):
        longitude = random.uniform(min_longitude, max_longitude)
        latitude = random.uniform(min_latitude, max_latitude)

        if not point_in_any_polygon(longitude, latitude, allowed_polygons):
            continue

        if point_in_any_polygon(longitude, latitude, restricted_polygons):
            continue

        return build_location_payload(latitude=latitude, longitude=longitude)

    raise RuntimeError(
        "Failed to generate a point inside the allowed region and outside "
        f"restricted polygons after {resolved_max_attempts} attempts"
    )
