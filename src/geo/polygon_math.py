from src.geo.geojson_polygon_parser import Polygon, Ring


def point_in_ring(longitude: float, latitude: float, ring: Ring) -> bool:
    inside = False

    if len(ring) < 3:
        return False

    previous_longitude, previous_latitude = ring[-1]

    for current_longitude, current_latitude in ring:
        intersects = (
            (current_latitude > latitude) != (previous_latitude > latitude)
        ) and (
            longitude
            < (previous_longitude - current_longitude)
            * (latitude - current_latitude)
            / ((previous_latitude - current_latitude) or 1e-12)
            + current_longitude
        )
        if intersects:
            inside = not inside
        previous_longitude, previous_latitude = current_longitude, current_latitude

    return inside


def point_in_polygon(longitude: float, latitude: float, polygon: Polygon) -> bool:
    if not polygon:
        return False

    if not point_in_ring(longitude, latitude, polygon[0]):
        return False

    for hole in polygon[1:]:
        if point_in_ring(longitude, latitude, hole):
            return False

    return True


def point_in_any_polygon(
    longitude: float,
    latitude: float,
    polygons: list[Polygon],
) -> bool:
    return any(
        point_in_polygon(longitude, latitude, polygon) for polygon in polygons
    )


def bounding_box(polygons: list[Polygon]) -> tuple[float, float, float, float]:
    longitudes: list[float] = []
    latitudes: list[float] = []

    for polygon in polygons:
        for ring in polygon:
            for longitude, latitude in ring:
                longitudes.append(longitude)
                latitudes.append(latitude)

    if not longitudes or not latitudes:
        raise ValueError("No polygon coordinates found in Gaza area GeoJSON")

    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)
