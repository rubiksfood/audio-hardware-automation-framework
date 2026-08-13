"""Typed results for sample-domain audio analysis."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricAnalysisResult:
    """Numeric sample-domain metric for an audio buffer."""

    overall: float
    per_channel: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class DetectionAnalysisResult:
    """Boolean sample-domain detection result for an audio buffer."""

    detected: bool
    per_channel: tuple[bool, ...]
