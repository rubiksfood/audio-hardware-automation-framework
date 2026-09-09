"""Typed results for end-to-end loopback validation."""

from dataclasses import dataclass

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import BackendInfo
from audio_hw_framework.device.models import DuplexEndpoints, StreamConfig
from audio_hw_framework.validation.audio_metrics import AudioMetricValidationResult


@dataclass(frozen=True, slots=True)
class LoopbackFrequencyResult:
    """Measured frequency result for a captured loopback signal."""

    expected_hz: float
    measured_hz: float
    tolerance_hz: float

    @property
    def error_hz(self) -> float:
        """Return the absolute frequency error."""

        return abs(self.measured_hz - self.expected_hz)

    @property
    def passed(self) -> bool:
        """Return whether frequency is within the permitted tolerance."""

        return self.error_hz <= self.tolerance_hz


@dataclass(frozen=True, slots=True)
class LoopbackValidationFailure:
    """Structured reason for a failed loopback validation check."""

    metric: str
    channel: int
    actual: float | bool
    expected: float | bool | None
    threshold: float | None
    reason: str


@dataclass(frozen=True, slots=True)
class LoopbackValidationResult:
    """Complete result of an end-to-end loopback validation."""

    backend: BackendInfo
    endpoints: DuplexEndpoints
    stream: StreamConfig

    output_channel: int
    input_channel: int

    playback_audio: AudioBuffer
    captured_audio: AudioBuffer
    analysed_audio: AudioBuffer

    frequency: LoopbackFrequencyResult
    metrics: AudioMetricValidationResult
    failures: tuple[LoopbackValidationFailure, ...]

    @property
    def passed(self) -> bool:
        """Return whether all loopback validation checks passed."""

        return self.frequency.passed and self.metrics.passed and not self.failures
