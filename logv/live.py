from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import os

from logv.parser import LogEvent


class LiveFollower:
    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self.path = path
        self.encoding = encoding
        self._handle = None
        self._inode: int | None = None
        self._position = 0

    def start(self, start_at_end: bool = True) -> None:
        self._open_handle()
        if self._handle is None:
            return
        if start_at_end:
            self._handle.seek(0, os.SEEK_END)
        else:
            self._handle.seek(0)
        self._position = self._handle.tell()

    def read_available(self) -> list[str]:
        self._reopen_if_rotated()
        if self._handle is None:
            self.start(start_at_end=False)
        if self._handle is None:
            return []
        if self.path.exists() and self.path.stat().st_size < self._position:
            self._handle.seek(0)
            self._position = 0
        lines: list[str] = []
        while True:
            line = self._handle.readline()
            if not line:
                break
            lines.append(line)
        self._position = self._handle.tell()
        return lines

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def _open_handle(self) -> None:
        if not self.path.exists():
            return
        self._handle = self.path.open("r", encoding=self.encoding, errors="replace")
        self._inode = self.path.stat().st_ino

    def _reopen_if_rotated(self) -> None:
        if not self.path.exists():
            return
        inode = self.path.stat().st_ino
        if self._handle is None:
            self._open_handle()
            return
        if self._inode != inode:
            self._handle.close()
            self._open_handle()
            if self._handle is not None:
                self._handle.seek(0)
                self._position = 0


@dataclass(slots=True)
class BurstState:
    count: int
    window_seconds: int
    started_at: datetime
    ended_at: datetime


class BurstDetector:
    def __init__(self, window_seconds: int = 10, threshold: int = 5) -> None:
        self.window_seconds = window_seconds
        self.threshold = threshold
        self._errors: deque[datetime] = deque()

    def observe(self, event: LogEvent) -> BurstState | None:
        if event.level != "ERROR" or event.timestamp is None:
            return None
        self._errors.append(event.timestamp)
        cutoff = event.timestamp - timedelta(seconds=self.window_seconds)
        while self._errors and self._errors[0] < cutoff:
            self._errors.popleft()
        if len(self._errors) >= self.threshold:
            return BurstState(
                count=len(self._errors),
                window_seconds=self.window_seconds,
                started_at=self._errors[0],
                ended_at=self._errors[-1],
            )
        return None
