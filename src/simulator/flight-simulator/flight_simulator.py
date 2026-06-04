import json
import os
import sched
import threading
import time

import redis

from src.config import get_redis_retry_seconds
from src.services.redis import get_redis_client


def advance_drone_step(
    scheduler_instance: sched.scheduler,
    flight_id: str,
    interval_seconds: float,
) -> None:
    try:
        r = get_redis_client()
        flight_key = f"flight:{flight_id}"
        raw_flight_data = r.get(flight_key)

        if not raw_flight_data:
            print(f"[{time.strftime('%X')}] Flight {flight_id}: data not found, retrying later.")
            scheduler_instance.enter(
                interval_seconds,
                1,
                advance_drone_step,
                (scheduler_instance, flight_id, interval_seconds),
            )
            return

        flight_data = json.loads(raw_flight_data)
        path_coords = flight_data.get("path", [])
        current_location = flight_data.get("current_location")
    except redis.exceptions.RedisError as exc:
        print(
            f"[{time.strftime('%X')}] Flight {flight_id}: Redis unavailable ({exc}). Retrying later."
        )
        scheduler_instance.enter(
            get_redis_retry_seconds(),
            1,
            advance_drone_step,
            (scheduler_instance, flight_id, interval_seconds),
        )
        return
    except (json.JSONDecodeError, TypeError):
        print(f"[{time.strftime('%X')}] Flight {flight_id}: error parsing JSON.")
        scheduler_instance.enter(
            interval_seconds,
            1,
            advance_drone_step,
            (scheduler_instance, flight_id, interval_seconds),
        )
        return

    if not path_coords:
        print(f"[{time.strftime('%X')}] Flight {flight_id}: path is empty.")
        scheduler_instance.enter(
            interval_seconds,
            1,
            advance_drone_step,
            (scheduler_instance, flight_id, interval_seconds),
        )
        return

    current_index = -1
    if current_location is not None and current_location in path_coords:
        current_index = path_coords.index(current_location)

    if current_index == -1:
        print(
            f"[{time.strftime('%X')}] Flight {flight_id}: current location not found in path."
        )
        scheduler_instance.enter(
            interval_seconds,
            1,
            advance_drone_step,
            (scheduler_instance, flight_id, interval_seconds),
        )
        return

    next_index = current_index + 1
    if next_index >= len(path_coords):
        current_time = time.strftime("%X")
        flight_data["arrival_time"] = current_time
        r.set(flight_key, json.dumps(flight_data))
        print(f"[{current_time}] Flight {flight_id} reached destination.")
        return

    next_location = path_coords[next_index]
    flight_data["current_location"] = next_location
    r.set(flight_key, json.dumps(flight_data))
    print(
        f"[{time.strftime('%X')}] Flight {flight_id} advanced to point {next_index}: {next_location}"
    )
    scheduler_instance.enter(
        interval_seconds,
        1,
        advance_drone_step,
        (scheduler_instance, flight_id, interval_seconds),
    )


def run_single_drone_thread(flight_id: str, interval_seconds: float) -> None:
    local_scheduler = sched.scheduler(time.time, time.sleep)
    local_scheduler.enter(
        0,
        1,
        advance_drone_step,
        (local_scheduler, flight_id, interval_seconds),
    )
    local_scheduler.run()


def track_all_flights(interval_seconds: float, stop_event=None) -> None:
    tracked_flight_ids: set[str] = set()

    try:
        while stop_event is None or not stop_event.is_set():
            print("Scanning Redis for active flights...")
            flight_ids = set()

            try:
                for key in get_redis_client().scan_iter(match="flight:*"):
                    parts = key.split(":")
                    if len(parts) >= 2:
                        flight_ids.add(parts[1])
            except redis.exceptions.RedisError as exc:
                print(f"Flight tracker: Redis unavailable ({exc}). Retrying later.")
                if stop_event is not None:
                    if stop_event.wait(get_redis_retry_seconds()):
                        break
                else:
                    time.sleep(get_redis_retry_seconds())
                continue

            new_flight_ids = sorted(flight_ids - tracked_flight_ids)
            if not new_flight_ids:
                print("No new flights found in Redis.")
            else:
                print(
                    f"Found {len(new_flight_ids)} new flights: {new_flight_ids}. Launching threads..."
                )

            for flight_id in new_flight_ids:
                thread = threading.Thread(
                    target=run_single_drone_thread,
                    args=(flight_id, interval_seconds),
                    daemon=True,
                )
                tracked_flight_ids.add(flight_id)
                thread.start()
                print(f"Started tracking thread for flight: {flight_id}")

            if stop_event is not None:
                if stop_event.wait(interval_seconds):
                    break
            else:
                time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopping all flight tracking.")


def run_flight_tracker(stop_event=None) -> None:
    interval_seconds = float(os.getenv("FLIGHT_INTERVAL_SECONDS", "3"))
    track_all_flights(interval_seconds=interval_seconds, stop_event=stop_event)


if __name__ == "__main__":
    run_flight_tracker()
