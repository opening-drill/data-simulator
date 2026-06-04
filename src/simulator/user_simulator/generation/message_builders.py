def build_location_payload(latitude: float, longitude: float) -> dict[str, float]:
    return {
        "latitude": latitude,
        "longitude": longitude,
    }


def build_simulation_payload(
    event_id: str,
    aircraft_id: str,
    start: dict[str, float],
    end: dict[str, float],
    urgency: str,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "aircraft_id": aircraft_id,
        "start": start,
        "end": end,
        "urgency": urgency,
    }
