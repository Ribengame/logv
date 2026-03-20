from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from logv.live import BurstDetector, LiveFollower
from logv.parser import LogEvent


class LiveTests(unittest.TestCase):
    def test_follower_reads_new_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text("start\n", encoding="utf-8")
            follower = LiveFollower(path)
            follower.start(start_at_end=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("next\n")
                handle.flush()
            self.assertEqual(follower.read_available(), ["next\n"])
            follower.close()

    def test_burst_detector_triggers(self) -> None:
        detector = BurstDetector(window_seconds=10, threshold=3)
        timestamps = [datetime(2026, 3, 20, 10, 0, second) for second in (1, 2, 3)]
        state = None
        for ts in timestamps:
            state = detector.observe(LogEvent(raw="x", message="x", timestamp=ts, level="ERROR"))
        self.assertIsNotNone(state)
        self.assertEqual(state.count, 3)


if __name__ == "__main__":
    unittest.main()
