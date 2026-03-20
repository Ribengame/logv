from __future__ import annotations

from pathlib import Path
import json
import time
from typing import Iterable

from logv.filters import LogFilter, build_filter
from logv.live import BurstDetector, LiveFollower
from logv.parser import LogEvent, LogParser
from logv.timeline import build_timeline, summarize_spikes
from logv.utils import (
    DEFAULT_MAX_EVENTS,
    ensure_readable_file,
    is_interactive_terminal,
    iter_file_lines,
    tail_lines,
)


def _require_runtime_dependencies() -> tuple[object, object]:
    try:
        import typer
        from rich.console import Console
    except ModuleNotFoundError as exc:
        missing = exc.name or "runtime dependency"
        raise SystemExit(
            f"Missing dependency: {missing}. Install runtime packages with `pip install -r requirements.txt`."
        ) from exc
    return typer, Console


typer, Console = _require_runtime_dependencies()
app = typer.Typer(
    add_completion=False,
    help="Fast terminal log viewer with streaming parser, filters, timeline, and live mode.",
)


def export_events(path: Path, events: list[LogEvent]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(event.raw)
            handle.write("\n")


def stream_plain(
    path: Path,
    active_filter: LogFilter,
    follow: bool,
    max_events: int,
    group_repeats: bool,
    export_path: Path | None,
    save_session: Path | None,
) -> None:
    from logv.highlighter import build_console, render_event

    console = build_console()
    parser = LogParser()
    burst_detector = BurstDetector()
    export_handle = export_path.open("w", encoding="utf-8") if export_path is not None else None
    exported_count = 0
    session_events: list[LogEvent] | None = [] if save_session is not None else None
    pending: tuple[LogEvent, int] | None = None

    def flush_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        event, count = pending
        console.print(render_event(event, count=count))
        pending = None

    def emit(events: Iterable[LogEvent]) -> None:
        nonlocal exported_count, pending
        for event in events:
            if not active_filter.matches(event):
                continue
            burst = burst_detector.observe(event)
            if export_handle is not None:
                export_handle.write(event.raw)
                export_handle.write("\n")
            exported_count += 1
            if session_events is not None:
                session_events.append(event)
            if group_repeats:
                if pending and pending[0].fingerprint == event.fingerprint:
                    pending = (pending[0], pending[1] + 1)
                else:
                    flush_pending()
                    pending = (event, 1)
            else:
                console.print(render_event(event))
            if burst is not None:
                flush_pending()
                console.print(
                    f"[bold red]error burst[/] {burst.count} errors in {burst.window_seconds}s"
                )

    if follow:
        emit(parser.parse_stream(tail_lines(path, max_events * 3)))
        flush_pending()
    else:
        emit(parser.parse_stream(iter_file_lines(path)))

    if follow:
        follower = LiveFollower(path)
        follower.start(start_at_end=True)
        try:
            while True:
                lines = follower.read_available()
                if lines:
                    emit(parser.parse_stream(lines))
                    flush_pending()
                time.sleep(0.5)
        except KeyboardInterrupt:
            flush_pending()
            console.print("[cyan]stopped[/]")
    else:
        flush_pending()

    if export_handle is not None:
        export_handle.close()
        console.print(f"[green]exported[/] {exported_count} events to {export_path}")

    if save_session is not None:
        assert session_events is not None
        save_session.write_text(
            json.dumps(
                {
                    "path": str(path),
                    "follow": follow,
                    "event_count": len(session_events),
                    "filter": active_filter.describe(),
                    "spikes": summarize_spikes(build_timeline(session_events)),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        console.print(f"[green]session saved[/] {save_session}")


@app.command()
def main(
    path: Path = typer.Argument(..., help="Path to the log file."),
    follow: bool = typer.Option(False, "-f", "--follow", help="Tail the log file."),
    level: list[str] = typer.Option(None, "--level", help="Filter one or more log levels."),
    regex: str | None = typer.Option(None, "--regex", help="Regex filter."),
    search: str | None = typer.Option(None, "--search", help="Case-insensitive text search."),
    plain: bool = typer.Option(False, "--plain", help="Disable Textual TUI."),
    group: bool = typer.Option(False, "--group", help="Group repeated consecutive messages."),
    max_events: int = typer.Option(
        DEFAULT_MAX_EVENTS, "--max-events", min=100, help="Maximum events kept in the live buffer."
    ),
    export: Path | None = typer.Option(None, "--export", help="Export matched events to a file."),
    save_session: Path | None = typer.Option(
        None, "--save-session", help="Store a JSON summary of the current session."
    ),
) -> None:
    log_path = ensure_readable_file(path)
    active_filter = build_filter(levels=level, regex=regex, text=search)

    if plain or not is_interactive_terminal():
        stream_plain(
            path=log_path,
            active_filter=active_filter,
            follow=follow,
            max_events=max_events,
            group_repeats=group,
            export_path=export,
            save_session=save_session,
        )
        return

    try:
        from logv.tui import run_tui
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Missing dependency: {exc.name}. Install runtime packages with `pip install -r requirements.txt`."
        ) from exc

    run_tui(
        path=log_path,
        follow=follow,
        initial_filter=active_filter,
        max_events=max_events,
        group_repeats=group,
    )


def app_entry() -> None:
    app()
