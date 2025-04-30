from pathlib import Path
from typing import Optional, Iterable
from agent_core.cli import local_work_space


def find_file(name: str, exts: Iterable[str] = (".py",),  root: Path = Path(local_work_space) )-> Optional[Path]:
    target_names = {name} | {f"{name}{ext}" for ext in exts}
    for path in root.rglob("*"):
        if path.is_file() and path.name in target_names:
            return path.resolve()
    return None
