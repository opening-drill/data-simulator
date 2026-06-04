from typing import Any

from src.geo.geojson_polygon_parser import Polygon, extract_polygons


def polygons_to_multi_polygon_geometry(polygons: list[Polygon]) -> dict[str, Any]:
    if not polygons:
        raise ValueError("At least one polygon is required to build a geometry")

    return {
        "type": "MultiPolygon",
        "coordinates": polygons,
    }


def build_combined_geometry(*geojson_documents: Any) -> dict[str, Any]:
    polygons: list[Polygon] = []

    for geojson_document in geojson_documents:
        polygons.extend(extract_polygons(geojson_document))

    if not polygons:
        raise ValueError("No polygons found in the provided GeoJSON documents")

    merged_geometry = _merge_polygons_if_possible(polygons)
    if merged_geometry is not None:
        return merged_geometry

    return polygons_to_multi_polygon_geometry(polygons)


def build_israel_gaza_west_bank_geometry(
    israel_geojson: Any,
    gaza_geojson: Any,
    west_bank_geojson: Any,
) -> dict[str, Any]:
    return build_combined_geometry(
        israel_geojson,
        gaza_geojson,
        west_bank_geojson,
    )


def build_combined_feature(*geojson_documents: Any) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "name": "Combined Region",
        },
        "geometry": build_combined_geometry(*geojson_documents),
    }


def build_israel_gaza_west_bank_feature(
    israel_geojson: Any,
    gaza_geojson: Any,
    west_bank_geojson: Any,
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "name": "Israel + Gaza + West Bank",
        },
        "geometry": build_israel_gaza_west_bank_geometry(
            israel_geojson=israel_geojson,
            gaza_geojson=gaza_geojson,
            west_bank_geojson=west_bank_geojson,
        ),
    }


def _merge_polygons_if_possible(polygons: list[Polygon]) -> dict[str, Any] | None:
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
    except ModuleNotFoundError:
        return None

    shapely_geometry = unary_union(
        [shape({"type": "Polygon", "coordinates": polygon}) for polygon in polygons]
    )

    geometry_mapping = shapely_geometry.__geo_interface__
    geometry_type = geometry_mapping.get("type")

    if geometry_type == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": _tuples_to_lists(geometry_mapping["coordinates"]),
        }

    if geometry_type == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": _tuples_to_lists(geometry_mapping["coordinates"]),
        }

    return None


def _tuples_to_lists(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_tuples_to_lists(item) for item in value]

    if isinstance(value, list):
        return [_tuples_to_lists(item) for item in value]

    return value
