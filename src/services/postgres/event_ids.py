import uuid
from typing import Any

from src.config.constants import (
    DEFAULT_POSTGRES_EVENT_TABLE,
    ENV_POSTGRES_EVENT_TABLE,
)
from src.config import get_unused_event_id_max_attempts
from src.services.postgres.connection import resolve_postgres_relation_name


def generate_unused_event_id(
    connection: Any,
    max_attempts: int | None = None,
) -> str:
    resolved_max_attempts = max_attempts or get_unused_event_id_max_attempts()

    for _ in range(resolved_max_attempts):
        candidate = uuid.uuid4()
        if not _event_id_exists(connection, str(candidate)):
            return str(candidate)

    raise RuntimeError(
        "Failed to generate a unique event id that is not present in the event table"
    )


def _event_id_exists(connection: Any, event_id: str) -> bool:
    event_table = resolve_postgres_relation_name(
        default_table_name=DEFAULT_POSTGRES_EVENT_TABLE,
        table_env_var_name=ENV_POSTGRES_EVENT_TABLE,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT 1 FROM {event_table} WHERE id = %s LIMIT 1",
            (event_id,),
        )
        return cursor.fetchone() is not None
