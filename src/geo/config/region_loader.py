import json
from pathlib import Path
from typing import Any

from src.config.constants import REGION_GEOJSON_FILE_NAME


def load_combined_region_geojson() -> dict[str, Any]:
    region_path = Path(__file__).with_name(REGION_GEOJSON_FILE_NAME)

    with region_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)
