from typing import Any

from src.config import (
    get_postgres_aircraft_table_name,
    get_postgres_connection_settings,
    get_postgres_event_table_name,
    get_postgres_polygon_table_name,
    get_postgres_schema_name,
)
from src.config.constants import (
    ENV_POSTGRES_AIRCRAFT_TABLE,
    ENV_POSTGRES_EVENT_TABLE,
    ENV_POSTGRES_POLYGON_TABLE,
)


def open_postgres_connection(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    sslmode: str | None = None,
):
    psycopg_module = _load_postgres_driver()
    connect_kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
    }

    if sslmode:
        connect_kwargs["sslmode"] = sslmode

    return psycopg_module.connect(**connect_kwargs)


def open_postgres_connection_from_env():
    return open_postgres_connection(**get_postgres_connection_settings())


def close_postgres_connection(connection: Any) -> None:
    connection.close()


def commit_postgres_transaction(connection: Any) -> None:
    connection.commit()


def rollback_postgres_transaction(connection: Any) -> None:
    connection.rollback()


def resolve_postgres_relation_name(
    default_table_name: str,
    table_env_var_name: str,
) -> str:
    schema_name = get_postgres_schema_name()
    table_name = _resolve_table_name(default_table_name, table_env_var_name)
    return (
        f"{_quote_postgres_identifier(schema_name)}."
        f"{_quote_postgres_identifier(table_name)}"
    )


def _quote_postgres_identifier(identifier: str) -> str:
    escaped_identifier = identifier.replace('"', '""')
    return f'"{escaped_identifier}"'


def _resolve_table_name(default_table_name: str, table_env_var_name: str) -> str:
    table_name_by_env_var = {
        ENV_POSTGRES_AIRCRAFT_TABLE: get_postgres_aircraft_table_name,
        ENV_POSTGRES_EVENT_TABLE: get_postgres_event_table_name,
        ENV_POSTGRES_POLYGON_TABLE: get_postgres_polygon_table_name,
    }
    table_name_getter = table_name_by_env_var.get(table_env_var_name)
    if table_name_getter is None:
        return default_table_name

    return table_name_getter()


def _load_postgres_driver():
    try:
        import psycopg

        return psycopg
    except ModuleNotFoundError:
        try:
            import psycopg2

            return psycopg2
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "A PostgreSQL driver is required. Install `psycopg` or `psycopg2`."
            ) from error
