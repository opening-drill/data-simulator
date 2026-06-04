import json
from typing import Any

from src.config.constants import (
    DEFAULT_POSTGRES_POLYGON_TABLE,
    ENV_POSTGRES_POLYGON_TABLE,
)
from src.services.postgres.connection import resolve_postgres_relation_name


def fetch_restricted_zone_rows(connection: Any) -> list[dict[str, Any]]:
    restricted_zone_table = resolve_postgres_relation_name(
        default_table_name=DEFAULT_POSTGRES_POLYGON_TABLE,
        table_env_var_name=ENV_POSTGRES_POLYGON_TABLE,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, name, geojson, zone, create_date
            FROM {restricted_zone_table}
            """
        )
        rows = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]

    return [
        _normalize_polygon_row(dict(zip(column_names, row, strict=False)))
        for row in rows
    ]


def _normalize_polygon_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized_row = dict(row)
    geojson_value = normalized_row.get("geojson")

    if isinstance(geojson_value, str):
        normalized_row["geojson"] = json.loads(geojson_value)

    return normalized_row
