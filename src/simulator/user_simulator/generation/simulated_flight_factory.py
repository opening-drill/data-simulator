from random import choice
from typing import Any, Callable

from src.simulator.user_simulator.generation.message_builders import (
    build_simulation_payload,
)
from src.simulator.user_simulator.generation.region_point_sampler import (
    sample_allowed_region_point,
)
from src.config import URGENCY_LEVELS


def build_simulated_flight(
    event_id: str,
    aircraft_id: str,
    allowed_region_geojson: dict[str, Any],
    restricted_zone_rows: Any,
) -> dict[str, object]:
    start = sample_allowed_region_point(
        allowed_region_geojson=allowed_region_geojson,
        restricted_zone_rows=restricted_zone_rows,
    )
    end = sample_allowed_region_point(
        allowed_region_geojson=allowed_region_geojson,
        restricted_zone_rows=restricted_zone_rows,
    )

    while start == end:
        end = sample_allowed_region_point(
            allowed_region_geojson=allowed_region_geojson,
            restricted_zone_rows=restricted_zone_rows,
        )

    return build_simulation_payload(
        event_id=event_id,
        aircraft_id=aircraft_id,
        start=start,
        end=end,
        urgency=choice(URGENCY_LEVELS),
    )


def build_simulation_messages(
    flight_count: int,
    next_event_id_supplier: Callable[[], str],
    free_aircraft_id_supplier: Callable[[], str],
    allowed_region_geojson: dict[str, Any],
    restricted_zone_rows: Any,
) -> dict[str, object] | list[dict[str, object]]:
    if flight_count < 1:
        raise ValueError("flight_count must be at least 1")

    simulated_flights = [
        build_simulated_flight(
            event_id=next_event_id_supplier(),
            aircraft_id=free_aircraft_id_supplier(),
            allowed_region_geojson=allowed_region_geojson,
            restricted_zone_rows=restricted_zone_rows,
        )
        for _ in range(flight_count)
    ]

    if flight_count == 1:
        return simulated_flights[0]

    return simulated_flights
