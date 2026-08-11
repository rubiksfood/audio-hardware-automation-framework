"""Threshold-based validation of sample-domain audio metrics."""

from dataclasses import dataclass

from audio_hw_framework.analysis import (
    DetectionAnalysisResult,
    MetricAnalysisResult,
    analyse_dc_offset,
    analyse_peak,
    analyse_rms,
    detect_clipping,
    detect_silence,
)
from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.configuration.thresholds import AudioMetricThresholds


@dataclass(frozen=True, slots=True)
class MetricThresholdFailure:
    """Structured reason for a failed audio metric threshold."""

    metric: str
    channel: int
    actual: float | bool
    threshold: float
    reason: str


@dataclass(frozen=True, slots=True)
class AudioMetricValidationResult:
    """Complete result of sample-domain metric validation."""

    rms: MetricAnalysisResult
    peak: MetricAnalysisResult
    dc_offset: MetricAnalysisResult
    silence: DetectionAnalysisResult
    clipping: DetectionAnalysisResult
    failures: tuple[MetricThresholdFailure, ...]

    @property
    def passed(self) -> bool:
        """Return whether all configured metric checks passed."""

        return not self.failures


def validate_audio_metrics(
    audio: AudioBuffer,
    thresholds: AudioMetricThresholds,
) -> AudioMetricValidationResult:
    """Analyse audio and validate configured metric thresholds."""

    rms = analyse_rms(audio)
    peak = analyse_peak(audio)
    dc_offset = analyse_dc_offset(audio)

    silence = detect_silence(
        audio,
        threshold=thresholds.silence_threshold,
    )
    clipping = detect_clipping(
        audio,
        threshold=thresholds.clipping_threshold,
    )

    failures: list[MetricThresholdFailure] = []

    _validate_rms(
        rms,
        thresholds,
        failures,
    )
    _validate_peak(
        peak,
        thresholds,
        failures,
    )
    _validate_dc_offset(
        dc_offset,
        thresholds,
        failures,
    )
    _validate_silence(
        silence,
        thresholds,
        failures,
    )
    _validate_clipping(
        clipping,
        thresholds,
        failures,
    )

    return AudioMetricValidationResult(
        rms=rms,
        peak=peak,
        dc_offset=dc_offset,
        silence=silence,
        clipping=clipping,
        failures=tuple(failures),
    )


def _validate_rms(
    result: MetricAnalysisResult,
    thresholds: AudioMetricThresholds,
    failures: list[MetricThresholdFailure],
) -> None:
    """Validate per-channel RMS thresholds."""

    for channel, actual in enumerate(result.per_channel):
        if thresholds.minimum_rms is not None and actual < thresholds.minimum_rms:
            failures.append(
                MetricThresholdFailure(
                    metric="rms",
                    channel=channel,
                    actual=actual,
                    threshold=thresholds.minimum_rms,
                    reason="RMS level is below the configured minimum",
                )
            )

        if thresholds.maximum_rms is not None and actual > thresholds.maximum_rms:
            failures.append(
                MetricThresholdFailure(
                    metric="rms",
                    channel=channel,
                    actual=actual,
                    threshold=thresholds.maximum_rms,
                    reason="RMS level exceeds the configured maximum",
                )
            )


def _validate_peak(
    result: MetricAnalysisResult,
    thresholds: AudioMetricThresholds,
    failures: list[MetricThresholdFailure],
) -> None:
    """Validate per-channel peak thresholds."""

    if thresholds.maximum_peak is None:
        return

    for channel, actual in enumerate(result.per_channel):
        if actual > thresholds.maximum_peak:
            failures.append(
                MetricThresholdFailure(
                    metric="peak",
                    channel=channel,
                    actual=actual,
                    threshold=thresholds.maximum_peak,
                    reason="Peak level exceeds the configured maximum",
                )
            )


def _validate_dc_offset(
    result: MetricAnalysisResult,
    thresholds: AudioMetricThresholds,
    failures: list[MetricThresholdFailure],
) -> None:
    """Validate per-channel absolute DC offset thresholds."""

    if thresholds.maximum_abs_dc_offset is None:
        return

    for channel, actual in enumerate(result.per_channel):
        if abs(actual) > thresholds.maximum_abs_dc_offset:
            failures.append(
                MetricThresholdFailure(
                    metric="dc_offset",
                    channel=channel,
                    actual=actual,
                    threshold=thresholds.maximum_abs_dc_offset,
                    reason="Absolute DC offset exceeds the configured maximum",
                )
            )


def _validate_silence(
    result: DetectionAnalysisResult,
    thresholds: AudioMetricThresholds,
    failures: list[MetricThresholdFailure],
) -> None:
    """Report channels detected as silent when configured to fail."""

    if not thresholds.fail_on_silence:
        return

    for channel, detected in enumerate(result.per_channel):
        if detected:
            failures.append(
                MetricThresholdFailure(
                    metric="silence",
                    channel=channel,
                    actual=True,
                    threshold=thresholds.silence_threshold,
                    reason="Channel was detected as silent",
                )
            )


def _validate_clipping(
    result: DetectionAnalysisResult,
    thresholds: AudioMetricThresholds,
    failures: list[MetricThresholdFailure],
) -> None:
    """Report channels detected as clipping when configured to fail."""

    if not thresholds.fail_on_clipping:
        return

    for channel, detected in enumerate(result.per_channel):
        if detected:
            failures.append(
                MetricThresholdFailure(
                    metric="clipping",
                    channel=channel,
                    actual=True,
                    threshold=thresholds.clipping_threshold,
                    reason="Channel contains samples at or above the clipping threshold",
                )
            )
