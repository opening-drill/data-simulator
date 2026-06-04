import sys
from pathlib import Path


def disable_bytecode_writes() -> None:
    sys.dont_write_bytecode = True


def ensure_project_root_on_path(current_file: str | Path, root_parent_index: int) -> None:
    project_root = Path(current_file).resolve().parents[root_parent_index]
    project_root_as_text = str(project_root)

    if project_root_as_text not in sys.path:
        sys.path.insert(0, project_root_as_text)


def configure_runtime(current_file: str | Path, root_parent_index: int) -> None:
    disable_bytecode_writes()
    ensure_project_root_on_path(current_file, root_parent_index)
