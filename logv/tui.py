from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static

from logv.filters import LogFilter, parse_filter_expression
from logv.highlighter import render_event
from logv.live import BurstDetector, LiveFollower
from logv.parser import LogEvent, LogParser
from logv.timeline import build_timeline, render_sparkline, summarize_spikes
from logv.utils import DEFAULT_MAX_EVENTS, clamp_last, is_small_file, iter_file_lines, tail_lines


@dataclass(slots=True)
class ViewRow:
    event: LogEvent
    count: int = 1


class LogViewerApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #table {
        width: 1fr;
    }

    #sidebar {
        width: 34;
        min-width: 30;
        border: round $surface;
    }

    #stats, #timeline, #help {
        height: auto;
        padding: 1 2;
        border-bottom: solid $boost;
    }

    #command {
        dock: bottom;
        display: none;
    }

    #command.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("/", "search", "Search"),
        Binding("f", "filter", "Filter"),
        Binding("g", "toggle_group", "Group"),
        Binding("t", "toggle_timeline", "Timeline"),
        Binding("r", "reload", "Reload"),
        Binding("?", "toggle_help", "Help"),
    ]

    def __init__(
        self,
        path: Path,
        follow: bool = False,
        initial_filter: LogFilter | None = None,
        max_events: int = DEFAULT_MAX_EVENTS,
        group_repeats: bool = False,
    ) -> None:
        super().__init__()
        self.path = path
        self.follow = follow
        self.max_events = max_events
        self.group_repeats = group_repeats
        self.current_filter = initial_filter or LogFilter()
        self.search_term = ""
        self.command_mode = "search"
        self.show_timeline = True
        self.show_help = False
        self.events: list[LogEvent] = []
        self.rows: list[ViewRow] = []
        self.follower: LiveFollower | None = None
        self.burst_detector = BurstDetector()
        self.last_burst = "none"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            yield DataTable(id="table", zebra_stripes=True)
            with Vertical(id="sidebar"):
                yield Static(id="stats")
                yield Static(id="timeline")
                yield Static(id="help")
        yield Input(id="command", placeholder="Enter search or filter expression")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns("Time", "Level", "Message", "Count")
        self.query_one("#help", Static).display = False
        self.query_one("#timeline", Static).display = self.show_timeline
        self._load_initial_events()
        self._refresh_view()
        if self.follow:
            self.follower = LiveFollower(self.path)
            self.follower.start(start_at_end=True)
            self.set_interval(0.5, self._poll_live_updates)
        table.focus()

    def action_search(self) -> None:
        self.command_mode = "search"
        self._show_command("Search text or regex")

    def action_filter(self) -> None:
        self.command_mode = "filter"
        self._show_command("Filter expression: /error level:error,warn regex:timeout")

    def action_toggle_group(self) -> None:
        self.group_repeats = not self.group_repeats
        self._refresh_view()

    def action_toggle_timeline(self) -> None:
        self.show_timeline = not self.show_timeline
        self.query_one("#timeline", Static).display = self.show_timeline

    def action_reload(self) -> None:
        self._load_initial_events()
        self._refresh_view()

    def action_toggle_help(self) -> None:
        self.show_help = not self.show_help
        help_widget = self.query_one("#help", Static)
        help_widget.display = self.show_help
        if self.show_help:
            help_widget.update(
                "Keys\n"
                "/ search\n"
                "f filter\n"
                "g group repeats\n"
                "t toggle timeline\n"
                "r reload\n"
                "q quit"
            )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if self.command_mode == "search":
            self.search_term = value
        else:
            self.current_filter = parse_filter_expression(value)
        self._hide_command()
        self._refresh_view()

    def on_input_blurred(self, event: Input.Blurred) -> None:
        if event.input.id == "command":
            self._hide_command()

    def _show_command(self, placeholder: str) -> None:
        command = self.query_one("#command", Input)
        command.placeholder = placeholder
        command.value = ""
        command.add_class("visible")
        command.focus()

    def _hide_command(self) -> None:
        command = self.query_one("#command", Input)
        command.remove_class("visible")
        self.query_one("#table", DataTable).focus()

    def _load_initial_events(self) -> None:
        parser = LogParser()
        if is_small_file(self.path) and not self.follow:
            lines = iter_file_lines(self.path)
            self.events = list(parser.parse_stream(lines))
        else:
            lines = tail_lines(self.path, self.max_events * 3)
            self.events = clamp_last(list(parser.parse_stream(lines)), self.max_events)

    def _poll_live_updates(self) -> None:
        if self.follower is None:
            return
        lines = self.follower.read_available()
        if not lines:
            return
        parser = LogParser()
        new_events = list(parser.parse_stream(lines))
        if not new_events:
            return
        for item in new_events:
            burst = self.burst_detector.observe(item)
            if burst is not None:
                self.last_burst = f"{burst.count} errors/{burst.window_seconds}s @ {burst.ended_at:%H:%M:%S}"
        self.events.extend(new_events)
        self.events = clamp_last(self.events, self.max_events)
        self._refresh_view()

    def _refresh_view(self) -> None:
        filtered = [event for event in self.events if self._matches_search(event) and self.current_filter.matches(event)]
        self.rows = self._group_rows(filtered) if self.group_repeats else [ViewRow(event) for event in filtered]
        self._render_table(self.rows)
        self._render_stats(filtered)
        self._render_timeline(filtered)

    def _matches_search(self, event: LogEvent) -> bool:
        if not self.search_term:
            return True
        if self.search_term.startswith("re:"):
            pattern = self.search_term[3:]
            try:
                return re.search(pattern, event.raw, re.IGNORECASE) is not None
            except re.error:
                return pattern.lower() in event.raw.lower()
        return self.search_term.lower() in event.raw.lower()

    def _group_rows(self, events: Iterable[LogEvent]) -> list[ViewRow]:
        grouped: list[ViewRow] = []
        for event in events:
            if grouped and grouped[-1].event.fingerprint == event.fingerprint:
                grouped[-1].count += 1
                continue
            grouped.append(ViewRow(event=event))
        return grouped

    def _render_table(self, rows: list[ViewRow]) -> None:
        table = self.query_one("#table", DataTable)
        table.clear()
        for row in rows:
            event = row.event
            timestamp = event.timestamp.strftime("%H:%M:%S") if event.timestamp else "-"
            table.add_row(timestamp, event.level, render_event(event, count=row.count), str(row.count))

    def _render_stats(self, filtered: list[LogEvent]) -> None:
        error_count = sum(1 for event in filtered if event.level == "ERROR")
        warn_count = sum(1 for event in filtered if event.level == "WARN")
        info_count = sum(1 for event in filtered if event.level == "INFO")
        debug_count = sum(1 for event in filtered if event.level == "DEBUG")
        mode = "follow" if self.follow else "static"
        self.query_one("#stats", Static).update(
            "Stats\n"
            f"mode: {mode}\n"
            f"events: {len(filtered)}/{len(self.events)}\n"
            f"errors: {error_count}\n"
            f"warn: {warn_count}\n"
            f"info: {info_count}\n"
            f"debug: {debug_count}\n"
            f"burst: {self.last_burst}\n"
            f"filter: {self.current_filter.describe()}\n"
            f"search: {self.search_term or 'none'}"
        )

    def _render_timeline(self, events: list[LogEvent]) -> None:
        report = build_timeline(events)
        self.query_one("#timeline", Static).update(
            "Timeline\n"
            f"{render_sparkline(report)}\n"
            f"spikes: {summarize_spikes(report)}"
        )


def run_tui(
    path: Path,
    follow: bool = False,
    initial_filter: LogFilter | None = None,
    max_events: int = DEFAULT_MAX_EVENTS,
    group_repeats: bool = False,
) -> None:
    LogViewerApp(
        path=path,
        follow=follow,
        initial_filter=initial_filter,
        max_events=max_events,
        group_repeats=group_repeats,
    ).run()
