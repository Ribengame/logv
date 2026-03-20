from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import os
from typing import TypeVar

DEFAULT_MAX_EVENTS = 5000
SMALL_FILE_THRESHOLD = 20 * 1024 * 1024
DEFAULT_ENCODING = "utf-8"
T = TypeVar("T")


def ensure_readable_file(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"log file not found: {resolved}")
    if not resolved.is_file():
        raise IsADirectoryError(f"expected a file, got: {resolved}")
    return resolved


def iter_file_lines(path: Path, encoding: str = DEFAULT_ENCODING) -> Iterator[str]:
    with path.open("r", encoding=encoding, errors="replace") as handle:
        yield from handle


def tail_lines(path: Path, limit: int, chunk_size: int = 64 * 1024) -> list[str]:
    if limit <= 0:
        return []
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        chunks: list[bytes] = []
        newline_count = 0
        while position > 0 and newline_count <= limit:
            step = min(chunk_size, position)
            position -= step
            handle.seek(position)
            block = handle.read(step)
            chunks.append(block)
            newline_count += block.count(b"\n")
        data = b"".join(reversed(chunks))
    lines = data.splitlines()
    return [line.decode(DEFAULT_ENCODING, errors="replace") for line in lines[-limit:]]


def is_small_file(path: Path, threshold: int = SMALL_FILE_THRESHOLD) -> bool:
    return path.stat().st_size <= threshold


def is_interactive_terminal() -> bool:
    return os.isatty(0) and os.isatty(1)


def clamp_last(items: list[T], limit: int) -> list[T]:
    if limit <= 0:
        return []
    return items[-limit:]
