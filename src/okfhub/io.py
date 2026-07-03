"""Persistence helpers for intermediate artifacts."""

from pathlib import Path
from typing import TypeVar

import orjson
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def write_json(path: Path, payload: object) -> None:
    """Write JSON payload with deterministic formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))


def read_json(path: Path) -> object:
    """Read JSON payload from file."""

    return orjson.loads(path.read_bytes())


def write_model_list(path: Path, items: list[BaseModel]) -> None:
    """Write list of pydantic models as JSON."""

    write_json(path, [item.model_dump(mode="json") for item in items])


def read_model_list(path: Path, model_type: type[T]) -> list[T]:
    """Read JSON list and parse as pydantic model instances."""

    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list at {path}")
    return [model_type.model_validate(item) for item in payload]
