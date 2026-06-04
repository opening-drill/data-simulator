from typing import Any, Callable

from src.simulator.user_simulator.generation.simulated_flight_factory import (
    build_simulation_messages,
)


def generate_simulation_messages(
    flight_count: int,
    next_event_id_supplier: Callable[[], str],
    free_aircraft_id_supplier: Callable[[], str],
    allowed_region_geojson: dict[str, Any],
    restricted_zone_rows: Any,
) -> dict[str, object] | list[dict[str, object]]:
    return build_simulation_messages(
        flight_count=flight_count,
        next_event_id_supplier=next_event_id_supplier,
        free_aircraft_id_supplier=free_aircraft_id_supplier,
        allowed_region_geojson=allowed_region_geojson,
        restricted_zone_rows=restricted_zone_rows,
    )
