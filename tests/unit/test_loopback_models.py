"""Tests for typed loopback validation results."""

import numpy as np

from audio_hw_framework.analysis import (
    DetectionAnalysisResult,
    MetricAnalysisResult,
)
from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import BackendInfo
from audio_hw_framework.device.models import AudioDevice, StreamConfig
from audio_hw_framework.validation import (
    AudioMetricValidationResult,
    LoopbackFrequencyResult,
    LoopbackValidationFailure,
    LoopbackValidationResult,
    MetricThresholdFailure,
)


def create_audio() -> AudioBuffer:
    """Create a minimal audio buffer for loopback result tests."""

    return AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )


def create_metric_result() -> AudioMetricValidationResult:
    """Create a passing sample-domain validation result."""

    return AudioMetricValidationResult(
        rms=MetricAnalysisResult(
            overall=0.25,
            per_channel=(0.25,),
        ),
        peak=MetricAnalysisResult(
            overall=0.5,
            per_channel=(0.5,),
        ),
        dc_offset=MetricAnalysisResult(
            overall=0.0,
            per_channel=(0.0,),
        ),
        silence=DetectionAnalysisResult(
            detected=False,
            per_channel=(False,),
        ),
        clipping=DetectionAnalysisResult(
            detected=False,
            per_channel=(False,),
        ),
        failures=(),
    )


def create_failing_metric_result() -> AudioMetricValidationResult:
    """Create a failing sample-domain validation result."""

    return AudioMetricValidationResult(
        rms=MetricAnalysisResult(
            overall=0.005,
            per_channel=(0.005,),
        ),
        peak=MetricAnalysisResult(
            overall=0.01,
            per_channel=(0.01,),
        ),
        dc_offset=MetricAnalysisResult(
            overall=0.0,
            per_channel=(0.0,),
        ),
        silence=DetectionAnalysisResult(
            detected=False,
            per_channel=(False,),
        ),
        clipping=DetectionAnalysisResult(
            detected=False,
            per_channel=(False,),
        ),
        failures=(
            MetricThresholdFailure(
                metric="rms",
                channel=0,
                actual=0.005,
                threshold=0.01,
                reason="RMS level is below the configured minimum",
            ),
        ),
    )


def create_device() -> AudioDevice:
    """Create the audio device used by loopback result tests."""

    return AudioDevice(
        index=0,
        name="Focusrite Scarlett 2i2 USB",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def test_loopback_frequency_result_calculates_absolute_error() -> None:
    result = LoopbackFrequencyResult(
        expected_hz=1_000.0,
        measured_hz=997.5,
        tolerance_hz=5.0,
    )

    assert result.error_hz == 2.5


def test_loopback_frequency_result_passes_within_tolerance() -> None:
    result = LoopbackFrequencyResult(
        expected_hz=1_000.0,
        measured_hz=997.5,
        tolerance_hz=5.0,
    )

    assert result.passed is True


def test_loopback_frequency_result_passes_at_tolerance_boundary() -> None:
    result = LoopbackFrequencyResult(
        expected_hz=1_000.0,
        measured_hz=995.0,
        tolerance_hz=5.0,
    )

    assert result.passed is True


def test_loopback_frequency_result_fails_outside_tolerance() -> None:
    result = LoopbackFrequencyResult(
        expected_hz=1_000.0,
        measured_hz=994.9,
        tolerance_hz=5.0,
    )

    assert result.passed is False


def test_loopback_validation_failure_exposes_structured_reason() -> None:
    failure = LoopbackValidationFailure(
        metric="frequency",
        channel=1,
        actual=980.0,
        expected=1_000.0,
        threshold=5.0,
        reason="Captured frequency is outside the configured tolerance",
    )

    assert failure.metric == "frequency"
    assert failure.channel == 1
    assert failure.actual == 980.0
    assert failure.expected == 1_000.0
    assert failure.threshold == 5.0
    assert failure.reason == ("Captured frequency is outside the configured tolerance")


def test_loopback_validation_result_passes_without_failures() -> None:
    audio = create_audio()

    result = LoopbackValidationResult(
        backend=BackendInfo(
            name="fake",
            library="internal",
            library_version=None,
        ),
        device=create_device(),
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=2,
            output_channels=2,
            block_size=128,
        ),
        output_channel=0,
        input_channel=0,
        playback_audio=audio,
        captured_audio=audio,
        analysed_audio=audio,
        frequency=LoopbackFrequencyResult(
            expected_hz=1_000.0,
            measured_hz=1_000.0,
            tolerance_hz=5.0,
        ),
        metrics=create_metric_result(),
        failures=(),
    )

    assert result.passed is True
    assert result.output_channel == 0
    assert result.input_channel == 0
    assert result.playback_audio is audio
    assert result.captured_audio is audio
    assert result.analysed_audio is audio


def test_loopback_validation_result_fails_with_failure() -> None:
    audio = create_audio()

    failure = LoopbackValidationFailure(
        metric="rms",
        channel=0,
        actual=0.005,
        expected=None,
        threshold=0.01,
        reason="RMS level is below the configured minimum",
    )

    result = LoopbackValidationResult(
        backend=BackendInfo(
            name="fake",
            library="internal",
            library_version=None,
        ),
        device=create_device(),
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=2,
            output_channels=2,
        ),
        output_channel=0,
        input_channel=0,
        playback_audio=audio,
        captured_audio=audio,
        analysed_audio=audio,
        frequency=LoopbackFrequencyResult(
            expected_hz=1_000.0,
            measured_hz=1_000.0,
            tolerance_hz=5.0,
        ),
        metrics=create_metric_result(),
        failures=(failure,),
    )

    assert result.passed is False
    assert result.failures == (failure,)


def test_loopback_validation_result_fails_when_frequency_fails() -> None:
    audio = create_audio()

    result = LoopbackValidationResult(
        backend=BackendInfo(
            name="fake",
            library="internal",
            library_version=None,
        ),
        device=create_device(),
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=2,
            output_channels=2,
        ),
        output_channel=0,
        input_channel=0,
        playback_audio=audio,
        captured_audio=audio,
        analysed_audio=audio,
        frequency=LoopbackFrequencyResult(
            expected_hz=1_000.0,
            measured_hz=990.0,
            tolerance_hz=5.0,
        ),
        metrics=create_metric_result(),
        failures=(),
    )

    assert result.passed is False


def test_loopback_validation_result_fails_when_metrics_fail() -> None:
    audio = create_audio()

    result = LoopbackValidationResult(
        backend=BackendInfo(
            name="fake",
            library="internal",
            library_version=None,
        ),
        device=create_device(),
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=2,
            output_channels=2,
        ),
        output_channel=0,
        input_channel=0,
        playback_audio=audio,
        captured_audio=audio,
        analysed_audio=audio,
        frequency=LoopbackFrequencyResult(
            expected_hz=1_000.0,
            measured_hz=1_000.0,
            tolerance_hz=5.0,
        ),
        metrics=create_failing_metric_result(),
        failures=(),
    )

    assert result.passed is False
