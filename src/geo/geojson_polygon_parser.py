import json
from typing import Any


Coordinate = tuple[float, float]
Ring = list[Coordinate]
Polygon = list[Ring]


def geometry_to_polygons(geometry: dict[str, Any] | None) -> list[Polygon]:
    if not geometry:
        return []

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "Polygon":
        return [coordinates]

    if geometry_type == "MultiPolygon":
        return list(coordinates)

    return []


def extract_polygons(geojson: Any) -> list[Polygon]:
    if geojson is None:
        return []

    if isinstance(geojson, str):
        try:
            return extract_polygons(json.loads(geojson))
        except json.JSONDecodeError:
            return []

    if isinstance(geojson, list):
        polygons: list[Polygon] = []
        for item in geojson:
            polygons.extend(extract_polygons(item))
        return polygons

    if not isinstance(geojson, dict):
        return []

    if "geojson" in geojson:
        return extract_polygons(geojson.get("geojson"))

    geojson_type = geojson.get("type")

    if geojson_type == "FeatureCollection":
        polygons: list[Polygon] = []
        for feature in geojson.get("features", []):
            polygons.extend(extract_polygons(feature))
        return polygons

    if geojson_type == "Feature":
        return geometry_to_polygons(geojson.get("geometry"))

    return geometry_to_polygons(geojson)
