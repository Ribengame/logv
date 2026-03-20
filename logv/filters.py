from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Pattern

from logv.parser import LogEvent, normalize_level

KNOWN_LEVELS = {"ERROR", "WARN", "INFO", "DEBUG"}


@dataclass(slots=True)
class LogFilter:
    levels: frozenset[str] = frozenset()
    pattern: Pattern[str] | None = None
    text: str = ""

    def matches(self, event: LogEvent) -> bool:
        if self.levels and event.level not in self.levels:
            return False
        target = event.raw
        if self.pattern and not self.pattern.search(target):
            return False
        if self.text and self.text.lower() not in target.lower():
            return False
        return True

    def describe(self) -> str:
        parts: list[str] = []
        if self.levels:
            parts.append("levels=" + ",".join(sorted(self.levels)))
        if self.pattern:
            parts.append(f"regex={self.pattern.pattern}")
        if self.text:
            parts.append(f"text={self.text}")
        return " ".join(parts) if parts else "none"


def compile_pattern(value: str | None) -> Pattern[str] | None:
    if not value:
        return None
    return re.compile(value, re.IGNORECASE)


def build_filter(
    levels: list[str] | tuple[str, ...] | None = None,
    regex: str | None = None,
    text: str | None = None,
) -> LogFilter:
    normalized = frozenset(
        level for level in (normalize_level(item) for item in (levels or [])) if level in KNOWN_LEVELS
    )
    return LogFilter(levels=normalized, pattern=compile_pattern(regex), text=(text or "").strip())


def parse_filter_expression(expression: str) -> LogFilter:
    expression = expression.strip()
    if not expression:
        return LogFilter()
    if expression.startswith("/"):
        token = expression[1:].strip()
        normalized = normalize_level(token)
        if normalized in KNOWN_LEVELS:
            return LogFilter(levels=frozenset({normalized}))
        return LogFilter(pattern=compile_pattern(token))

    levels: list[str] = []
    regex_parts: list[str] = []
    text_parts: list[str] = []
    for token in expression.split():
        if token.startswith("level:"):
            values = token.split(":", 1)[1]
            levels.extend(part.strip() for part in values.split(",") if part.strip())
            continue
        if token.startswith("regex:"):
            regex_parts.append(token.split(":", 1)[1])
            continue
        normalized = normalize_level(token)
        if normalized in KNOWN_LEVELS and token.lower() == token:
            levels.append(normalized)
        else:
            text_parts.append(token)
    regex = "|".join(regex_parts) if regex_parts else None
    return build_filter(levels=levels, regex=regex, text=" ".join(text_parts))
