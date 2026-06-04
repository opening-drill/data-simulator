import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_simulation_flight_count
from src.env_loader import load_project_env
from src.simulator.user_simulator.simulation_service import generate_simulation_messages
from src.geo.config import load_combined_region_geojson
from src.services.postgres import (
    close_postgres_connection,
    commit_postgres_transaction,
    fetch_restricted_zone_rows,
    generate_unused_event_id,
    open_postgres_connection_from_env,
    rollback_postgres_transaction,
    select_random_free_aircraft_id,
)
from src.utils import configure_runtime

configure_runtime(__file__, 3)


def build_simulation_output(
    flight_count: int,
    postgres_connection,
) -> dict[str, object] | list[dict[str, object]]:
    allowed_region_geojson = load_combined_region_geojson()
    restricted_zone_rows = fetch_restricted_zone_rows(postgres_connection)
    return generate_simulation_messages(
        flight_count=flight_count,
        next_event_id_supplier=lambda: generate_unused_event_id(postgres_connection),
        free_aircraft_id_supplier=lambda: select_random_free_aircraft_id(
            postgres_connection
        ),
        allowed_region_geojson=allowed_region_geojson,
        restricted_zone_rows=restricted_zone_rows,
    )


def run_simulator() -> dict[str, object] | list[dict[str, object]]:
    load_project_env()
    flight_count = get_simulation_flight_count()
    postgres_connection = open_postgres_connection_from_env()

    try:
        simulation_output = build_simulation_output(
            flight_count=flight_count,
            postgres_connection=postgres_connection,
        )
        commit_postgres_transaction(postgres_connection)
        return simulation_output
    except Exception:
        rollback_postgres_transaction(postgres_connection)
        raise
    finally:
        close_postgres_connection(postgres_connection)


if __name__ == "__main__":
    run_simulator()
