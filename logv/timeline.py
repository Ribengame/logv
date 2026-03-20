from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
import math
import statistics

from logv.parser import LogEvent

SPARKLINE_STEPS = " .:-=+*#%@"


@dataclass(slots=True)
class TimelineBucket:
    start: datetime
    total: int = 0
    error_count: int = 0
    warn_count: int = 0
    info_count: int = 0
    debug_count: int = 0


@dataclass(slots=True)
class TimelineSpike:
    start: datetime
    error_count: int
    baseline: float


@dataclass(slots=True)
class TimelineReport:
    buckets: list[TimelineBucket] = field(default_factory=list)
    spikes: list[TimelineSpike] = field(default_factory=list)


def build_timeline(events: Iterable[LogEvent], bucket_seconds: int = 60) -> TimelineReport:
    indexed: dict[int, TimelineBucket] = {}
    for event in events:
        if event.timestamp is None:
            continue
        epoch = int(event.timestamp.timestamp())
        bucket_epoch = epoch - (epoch % bucket_seconds)
        bucket = indexed.get(bucket_epoch)
        if bucket is None:
            bucket = TimelineBucket(start=datetime.fromtimestamp(bucket_epoch, tz=event.timestamp.tzinfo))
            indexed[bucket_epoch] = bucket
        bucket.total += 1
        if event.level == "ERROR":
            bucket.error_count += 1
        elif event.level == "WARN":
            bucket.warn_count += 1
        elif event.level == "INFO":
            bucket.info_count += 1
        elif event.level == "DEBUG":
            bucket.debug_count += 1

    if not indexed:
        return TimelineReport()

    ordered_keys = sorted(indexed)
    buckets: list[TimelineBucket] = []
    current = ordered_keys[0]
    end = ordered_keys[-1]
    while current <= end:
        buckets.append(
            indexed.get(
                current,
                TimelineBucket(start=datetime.fromtimestamp(current, tz=indexed[ordered_keys[0]].start.tzinfo)),
            )
        )
        current += bucket_seconds
    return TimelineReport(buckets=buckets, spikes=detect_spikes(buckets))


def detect_spikes(buckets: list[TimelineBucket]) -> list[TimelineSpike]:
    if not buckets:
        return []
    values = [bucket.error_count for bucket in buckets]
    baseline = statistics.fmean(values)
    deviation = statistics.pstdev(values) if len(values) > 1 else 0.0
    threshold = max(3.0, baseline + max(0.5, deviation))
    spikes: list[TimelineSpike] = []
    for bucket in buckets:
        if bucket.error_count >= threshold:
            spikes.append(
                TimelineSpike(start=bucket.start, error_count=bucket.error_count, baseline=baseline)
            )
    return spikes


def render_sparkline(report: TimelineReport, metric: str = "error_count", width: int = 32) -> str:
    if not report.buckets:
        return "no data"
    values = [getattr(bucket, metric) for bucket in report.buckets]
    if len(values) > width:
        step = math.ceil(len(values) / width)
        values = [max(values[index : index + step]) for index in range(0, len(values), step)]
    ceiling = max(values) or 1
    chars = []
    span = len(SPARKLINE_STEPS) - 1
    for value in values:
        bucket = round((value / ceiling) * span)
        chars.append(SPARKLINE_STEPS[bucket])
    return "".join(chars)


def summarize_spikes(report: TimelineReport, limit: int = 3) -> str:
    if not report.spikes:
        return "no error spikes"
    parts = []
    for spike in report.spikes[:limit]:
        parts.append(f"{spike.start:%H:%M}:{spike.error_count}")
    return ", ".join(parts)
