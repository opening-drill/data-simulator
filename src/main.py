import importlib.util
import json
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask_server import run_server

from src.config import get_json_output_indent, get_simulation_interval_seconds
from src.env_loader import load_project_env
from src.simulator.user_simulator.simulator_runner import run_simulator
from src.services.api import dispatch_simulation_payloads
from src.utils import configure_runtime

configure_runtime(__file__, 1)

WorkerTarget = Callable[[], None]


def run_dispatch_worker(stop_event: threading.Event) -> None:
    output_indent = get_json_output_indent()
    interval_seconds = get_simulation_interval_seconds()

    while not stop_event.is_set():
        try:
            simulation_output = run_simulator()
            print(json.dumps(simulation_output, indent=output_indent))
            dispatch_response = dispatch_simulation_payloads(simulation_output)
            print(json.dumps(dispatch_response, indent=output_indent))
        except Exception as exc:
            print(f"Simulation iteration failed: {exc}")

        if stop_event.wait(interval_seconds):
            break


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_worker(name: str, stop_event: threading.Event, target: WorkerTarget) -> None:
    try:
        print(f"Starting {name}.")
        target()
    except Exception as exc:
        print(f"{name} stopped unexpectedly: {exc}")
        stop_event.set()
        raise


def main() -> None:
    env_path = load_project_env()
    print(f"Loaded environment from {env_path}")

    polygon_module = _load_module(
        "polygon_worker_module",
        PROJECT_ROOT
        / "src"
        / "simulator"
        / "data-simulator"
        / "polygons"
        / "generate_polygon.py",
    )
    flight_module = _load_module(
        "flight_tracker_module",
        PROJECT_ROOT
        / "src"
        / "simulator"
        / "flight-simulator"
        / "flight_simulator.py",
    )

    stop_event = threading.Event()
    workers: list[tuple[str, WorkerTarget]] = [
        ("dispatch-worker", lambda: run_dispatch_worker(stop_event)),
        ("polygon-worker", lambda: polygon_module.run_polygon_worker(stop_event)),
        ("flight-tracker", lambda: flight_module.run_flight_tracker(stop_event)),
        ("flask-server", run_server),
    ]

    threads = [
        threading.Thread(
            target=_run_worker,
            args=(name, stop_event, target),
            daemon=True,
            name=name,
        )
        for name, target in workers
    ]

    for thread in threads:
        thread.start()

    try:
        while not stop_event.is_set():
            stopped_workers = [thread.name for thread in threads if not thread.is_alive()]
            if stopped_workers:
                raise RuntimeError(
                    f"Worker threads stopped unexpectedly: {', '.join(stopped_workers)}"
                )

            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping simulator workers.")
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2)


if __name__ == "__main__":
    main()
