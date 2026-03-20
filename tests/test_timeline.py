from __future__ import annotations

from datetime import datetime
import unittest

from logv.parser import LogEvent
from logv.timeline import build_timeline, render_sparkline


class TimelineTests(unittest.TestCase):
    def test_builds_timeline_and_detects_spike(self) -> None:
        events = [
            LogEvent(raw="a", message="a", timestamp=datetime(2026, 3, 20, 10, 0, 1), level="INFO"),
            LogEvent(raw="b", message="b", timestamp=datetime(2026, 3, 20, 10, 1, 1), level="ERROR"),
            LogEvent(raw="c", message="c", timestamp=datetime(2026, 3, 20, 10, 1, 2), level="ERROR"),
            LogEvent(raw="d", message="d", timestamp=datetime(2026, 3, 20, 10, 1, 3), level="ERROR"),
            LogEvent(raw="e", message="e", timestamp=datetime(2026, 3, 20, 10, 2, 1), level="WARN"),
        ]
        report = build_timeline(events)
        self.assertEqual(len(report.buckets), 3)
        self.assertEqual(len(report.spikes), 1)
        self.assertEqual(len(render_sparkline(report)), 3)


if __name__ == "__main__":
    unittest.main()
