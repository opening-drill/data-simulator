from typing import Any

from src.config import get_postgres_busy_status, get_postgres_free_status
from src.config.constants import (
    DEFAULT_POSTGRES_AIRCRAFT_TABLE,
    ENV_POSTGRES_AIRCRAFT_TABLE,
)
from src.services.postgres.connection import resolve_postgres_relation_name


def select_random_free_aircraft_id(
    connection: Any,
    free_status: str | None = None,
    busy_status: str | None = None,
) -> str:
    resolved_free_status = free_status or get_postgres_free_status()
    resolved_busy_status = busy_status or get_postgres_busy_status()
    aircraft_table = resolve_postgres_relation_name(
        default_table_name=DEFAULT_POSTGRES_AIRCRAFT_TABLE,
        table_env_var_name=ENV_POSTGRES_AIRCRAFT_TABLE,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            WITH selected_aircraft AS (
                SELECT id
                FROM {aircraft_table}
                WHERE status = %s
                ORDER BY RANDOM()
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE {aircraft_table}
            SET
                status = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE id IN (SELECT id FROM selected_aircraft)
            RETURNING id
            """,
            (resolved_free_status, resolved_busy_status),
        )
        row = cursor.fetchone()

    if row is None:
        raise RuntimeError("No aircraft with status FREE was found")

    return str(row[0])
