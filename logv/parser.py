from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import json
import re
from typing import Any

LEVEL_ALIASES = {
    "critical": "ERROR",
    "crit": "ERROR",
    "fatal": "ERROR",
    "error": "ERROR",
    "err": "ERROR",
    "warning": "WARN",
    "warn": "WARN",
    "notice": "INFO",
    "info": "INFO",
    "debug": "DEBUG",
    "trace": "DEBUG",
}

LEVEL_RE = re.compile(
    r"\b(?P<level>critical|crit|fatal|error|err|warning|warn|notice|info|debug|trace)\b",
    re.IGNORECASE,
)
ISO_TIMESTAMP_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?)"
)
ALT_TIMESTAMP_RE = re.compile(r"(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
BRACKET_TIMESTAMP_RE = re.compile(
    r"\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?)\]"
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
URL_RE = re.compile(r"https?://\S+")
NUMBER_RE = re.compile(r"\b\d+\b")
HEX_RE = re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE)
STACK_TRACE_PREFIXES = (
    "Traceback (most recent call last):",
    "Caused by:",
    "During handling of the above exception",
)
STACK_TRACE_TAIL_RE = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning|Failure|Fault)|RuntimeError|TypeError|ValueError)\b"
)


@dataclass(slots=True)
class LogEvent:
    raw: str
    message: str
    timestamp: datetime | None
    level: str
    fields: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    kind: str = "text"
    line_start: int = 0
    line_count: int = 1
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            self.fingerprint = make_fingerprint(self.level, self.message)


def normalize_level(value: str | None) -> str:
    if not value:
        return "INFO"
    key = value.strip().lower()
    return LEVEL_ALIASES.get(key, key.upper())


def make_fingerprint(level: str, message: str) -> str:
    normalized = message.lower()
    normalized = URL_RE.sub("<url>", normalized)
    normalized = IP_RE.sub("<ip>", normalized)
    normalized = HEX_RE.sub("<hex>", normalized)
    normalized = NUMBER_RE.sub("<num>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return f"{level}:{normalized}"


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace(",", ".")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    if re.search(r"[+-]\d{4}$", normalized):
        normalized = normalized[:-5] + normalized[-5:-2] + ":" + normalized[-2:]
    formats = (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


class LogParser:
    timestamp_fields = ("timestamp", "time", "ts", "@timestamp", "date")
    level_fields = ("level", "severity", "lvl", "log_level")
    message_fields = ("message", "msg", "event", "log")
    source_fields = ("logger", "service", "component", "module", "name")

    def parse_stream(self, lines: Iterable[str]) -> Iterator[LogEvent]:
        current: LogEvent | None = None
        for line_number, line in enumerate(lines, start=1):
            stripped = line.rstrip("\n")
            if current and self._is_continuation(stripped):
                current.raw = f"{current.raw}\n{stripped}"
                current.message = f"{current.message}\n{stripped}"
                current.line_count += 1
                current.fingerprint = make_fingerprint(current.level, current.message)
                continue
            event = self.parse_line(stripped, line_number)
            if current is not None:
                yield current
            current = event
        if current is not None:
            yield current

    def parse_line(self, line: str, line_number: int = 1) -> LogEvent:
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            parsed = self._parse_json_line(stripped, line_number)
            if parsed is not None:
                return parsed
        return self._parse_text_line(line, line_number)

    def _parse_json_line(self, line: str, line_number: int) -> LogEvent | None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        timestamp = parse_timestamp(self._first_value(payload, self.timestamp_fields))
        level = normalize_level(self._first_value(payload, self.level_fields))
        message = self._first_value(payload, self.message_fields) or json.dumps(
            payload, ensure_ascii=True, sort_keys=True
        )
        source = self._first_value(payload, self.source_fields)
        return LogEvent(
            raw=line,
            message=str(message),
            timestamp=timestamp,
            level=level,
            fields=payload,
            source=str(source) if source is not None else None,
            kind="json",
            line_start=line_number,
        )

    def _parse_text_line(self, line: str, line_number: int) -> LogEvent:
        timestamp = self._extract_timestamp(line)
        level_match = LEVEL_RE.search(line)
        level = normalize_level(level_match.group("level") if level_match else None)
        source = None
        logger_match = re.search(r"\b([A-Za-z0-9_.-]+):\s", line)
        if logger_match:
            source = logger_match.group(1)
        return LogEvent(
            raw=line,
            message=line,
            timestamp=timestamp,
            level=level,
            source=source,
            kind="text",
            line_start=line_number,
        )

    def _extract_timestamp(self, line: str) -> datetime | None:
        for pattern in (ISO_TIMESTAMP_RE, BRACKET_TIMESTAMP_RE, ALT_TIMESTAMP_RE):
            match = pattern.search(line)
            if match:
                parsed = parse_timestamp(match.group("ts"))
                if parsed is not None:
                    return parsed
        return None

    def _first_value(self, payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        return None

    def _is_continuation(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if self._looks_like_new_entry(line):
            return False
        if line.startswith((" ", "\t")):
            return True
        if any(stripped.startswith(prefix) for prefix in STACK_TRACE_PREFIXES):
            return True
        if stripped.startswith("File ") and ", line " in stripped:
            return True
        if stripped.startswith("at "):
            return True
        if STACK_TRACE_TAIL_RE.match(stripped):
            return True
        return False

    def _looks_like_new_entry(self, line: str) -> bool:
        stripped = line.lstrip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return True
        if ISO_TIMESTAMP_RE.match(stripped):
            return True
        if BRACKET_TIMESTAMP_RE.match(stripped):
            return True
        if ALT_TIMESTAMP_RE.match(stripped):
            return True
        if LEVEL_RE.match(stripped):
            return True
        return False
