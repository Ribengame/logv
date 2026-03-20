from __future__ import annotations

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.text import Text
from rich.theme import Theme

from logv.parser import LogEvent

LOG_THEME = Theme(
    {
        "log.error": "bold red",
        "log.warn": "bold yellow",
        "log.info": "bold green",
        "log.debug": "bold blue",
        "log.timestamp": "cyan",
        "log.ip": "magenta",
        "log.url": "underline bright_blue",
        "log.http_status": "bold bright_red",
        "log.stack": "dim italic",
        "log.source": "bright_black",
        "log.group": "bright_white on dark_green",
    }
)


class LogHighlighter(RegexHighlighter):
    base_style = "log."
    highlights = [
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ][0-9:.,+\-Z]+)",
        r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)",
        r"(?P<url>https?://\S+)",
        r"(?P<http_status>\b(?:404|429|500|502|503|504)\b)",
        r"(?P<stack>Traceback \(most recent call last\):|Caused by:|File \".+?\", line \d+|^\s+at .+$)",
    ]


HIGHLIGHTER = LogHighlighter()


def build_console() -> Console:
    return Console(theme=LOG_THEME)


def level_style(level: str) -> str:
    return {
        "ERROR": "log.error",
        "WARN": "log.warn",
        "INFO": "log.info",
        "DEBUG": "log.debug",
    }.get(level, "white")


def highlight_text(message: str) -> Text:
    text = Text(message)
    HIGHLIGHTER.highlight(text)
    return text


def render_event(event: LogEvent, count: int = 1) -> Text:
    rendered = Text()
    if event.timestamp is not None:
        rendered.append(f"{event.timestamp:%Y-%m-%d %H:%M:%S} ", style="log.timestamp")
    rendered.append(f"{event.level:<5} ", style=level_style(event.level))
    if event.source:
        rendered.append(f"[{event.source}] ", style="log.source")
    rendered.append_text(highlight_text(event.message))
    if count > 1:
        rendered.append(f" x{count}", style="log.group")
    return rendered
