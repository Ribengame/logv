from __future__ import annotations

import unittest

from logv.filters import build_filter, parse_filter_expression
from logv.parser import LogEvent


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = LogEvent(
            raw="2026-03-20 ERROR api.server: timeout contacting 10.0.0.5",
            message="2026-03-20 ERROR api.server: timeout contacting 10.0.0.5",
            timestamp=None,
            level="ERROR",
        )

    def test_build_filter_matches_level_and_regex(self) -> None:
        active = build_filter(levels=["error"], regex="timeout", text=None)
        self.assertTrue(active.matches(self.event))

    def test_parse_slash_expression_for_level(self) -> None:
        active = parse_filter_expression("/warn")
        self.assertEqual(active.levels, frozenset({"WARN"}))

    def test_parse_freeform_text(self) -> None:
        active = parse_filter_expression("gateway timeout")
        self.assertEqual(active.text, "gateway timeout")


if __name__ == "__main__":
    unittest.main()
