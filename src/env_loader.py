import os
from pathlib import Path


def load_project_env(env_path: str | Path | None = None) -> Path:
    if env_path:
        resolved_env_path = Path(env_path)
        if resolved_env_path.exists():
            _load_env_file(resolved_env_path)
        return resolved_env_path

    for candidate_path in _default_env_paths():
        if candidate_path.exists():
            _load_env_file(candidate_path)
            return candidate_path

    return _default_env_paths()[0]


def _load_env_file(resolved_env_path: Path) -> None:
    for raw_line in resolved_env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), _normalize_env_value(value.strip()))


def _default_env_paths() -> list[Path]:
    project_root = Path(__file__).resolve().parent.parent
    return [
        project_root / ".env",
    ]


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]

    return value
