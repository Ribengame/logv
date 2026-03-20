from __future__ import annotations

import unittest

from logv.parser import LogParser


class ParserTests(unittest.TestCase):
    def test_parses_json_levels_and_source(self) -> None:
        parser = LogParser()
        events = list(
            parser.parse_stream(
                [
                    '{"timestamp":"2026-03-20T10:00:11Z","level":"error","service":"gateway","message":"request failed"}'
                ]
            )
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].level, "ERROR")
        self.assertEqual(events[0].source, "gateway")
        self.assertEqual(events[0].message, "request failed")

    def test_groups_stack_trace_as_single_event(self) -> None:
        parser = LogParser()
        events = list(
            parser.parse_stream(
                [
                    "2026-03-20 10:00:07 ERROR api.server: upstream failed",
                    "Traceback (most recent call last):",
                    '  File "/srv/app.py", line 51, in handle_request',
                    "    raise RuntimeError('database timeout')",
                    "RuntimeError: database timeout",
                    "2026-03-20 10:01:00 INFO worker.sync: recovered",
                ]
            )
        )
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].level, "ERROR")
        self.assertIn("Traceback", events[0].message)
        self.assertEqual(events[0].line_count, 5)
        self.assertEqual(events[1].level, "INFO")


if __name__ == "__main__":
    unittest.main()
