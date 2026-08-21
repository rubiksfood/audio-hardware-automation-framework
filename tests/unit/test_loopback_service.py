"""Tests for configured end-to-end loopback validation."""

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.configuration.loopback import (
    LoopbackValidationConfig,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceMatchConfig,
    FrameworkConfig,
    StreamConfig,
)
from audio_hw_framework.validation import (
    validate_configured_loopback,
)

SAMPLE_RATE = 8_000
SIGNAL_DURATION_SECONDS = 0.1
PADDING_SECONDS = 0.05
FREQUENCY_HZ = 1_000.0
AMPLITUDE = 0.25


def create_test_device() -> AudioDevice:
    """Create the duplex device used by loopback service tests."""

    return AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="Test API",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=SAMPLE_RATE,
    )


def create_config() -> FrameworkConfig:
    """Create a valid configured loopback test."""

    return FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
            minimum_input_channels=2,
            minimum_output_channels=2,
        ),
        stream=StreamConfig(
            sample_rate=SAMPLE_RATE,
            input_channels=2,
            output_channels=2,
        ),
        loopback=LoopbackValidationConfig(
            output_channel=1,
            input_channel=1,
            signal_duration_seconds=SIGNAL_DURATION_SECONDS,
            frequency_hz=FREQUENCY_HZ,
            amplitude=AMPLITUDE,
            frequency_tolerance_hz=5.0,
            padding_seconds=PADDING_SECONDS,
        ),
    )


def create_capture(
    *,
    frequency_hz: float = FREQUENCY_HZ,
    amplitude: float = AMPLITUDE,
) -> AudioBuffer:
    """Create deterministic duplex capture data on input channel 1."""

    signal_frames = round(SIGNAL_DURATION_SECONDS * SAMPLE_RATE)

    padding_frames = round(PADDING_SECONDS * SAMPLE_RATE)

    total_frames = signal_frames + (2 * padding_frames)

    time_seconds = (
        np.arange(
            signal_frames,
            dtype=np.float64,
        )
        / SAMPLE_RATE
    )

    tone = (amplitude * np.sin(2.0 * np.pi * frequency_hz * time_seconds)).astype(
        np.float32,
    )

    samples = np.zeros(
        (
            total_frames,
            2,
        ),
        dtype=np.float32,
    )

    signal_end = padding_frames + signal_frames

    samples[
        padding_frames:signal_end,
        1,
    ] = tone

    return AudioBuffer(
        samples=samples,
        sample_rate=SAMPLE_RATE,
    )


def test_validate_configured_loopback_returns_passing_result() -> None:
    backend = FakeAudioBackend(
        devices=[
            create_test_device(),
        ],
        duplex_samples=create_capture(),
    )

    result = validate_configured_loopback(
        backend,
        create_config(),
    )

    assert result.passed is True

    assert result.backend.name == "fake"
    assert result.device.name == "Scarlett"

    assert result.output_channel == 1
    assert result.input_channel == 1

    assert result.playback_audio.channel_count == 2
    assert result.captured_audio.channel_count == 2
    assert result.analysed_audio.channel_count == 1

    assert result.analysed_audio.frame_count == round(SIGNAL_DURATION_SECONDS * SAMPLE_RATE)

    assert result.frequency.expected_hz == FREQUENCY_HZ
    assert result.frequency.measured_hz == pytest.approx(
        FREQUENCY_HZ,
        abs=0.5,
    )

    assert result.frequency.passed is True
    assert result.metrics.passed is True
    assert result.failures == ()


def test_validate_configured_loopback_routes_and_pads_playback() -> None:
    backend = FakeAudioBackend(
        devices=[
            create_test_device(),
        ],
        duplex_samples=create_capture(),
    )

    result = validate_configured_loopback(
        backend,
        create_config(),
    )

    padding_frames = round(PADDING_SECONDS * SAMPLE_RATE)

    signal_frames = round(SIGNAL_DURATION_SECONDS * SAMPLE_RATE)

    signal_end = padding_frames + signal_frames

    np.testing.assert_array_equal(
        result.playback_audio.samples[:padding_frames,],
        np.zeros(
            (
                padding_frames,
                2,
            ),
            dtype=np.float32,
        ),
    )

    np.testing.assert_array_equal(
        result.playback_audio.samples[
            :,
            0,
        ],
        np.zeros(
            result.playback_audio.frame_count,
            dtype=np.float32,
        ),
    )

    assert np.any(
        result.playback_audio.samples[
            padding_frames:signal_end,
            1,
        ]
        != 0.0
    )

    np.testing.assert_array_equal(
        result.playback_audio.samples[signal_end:,],
        np.zeros(
            (
                padding_frames,
                2,
            ),
            dtype=np.float32,
        ),
    )


def test_validate_configured_loopback_analyses_selected_input_channel() -> None:
    capture = create_capture()

    samples = np.array(
        capture.samples,
        copy=True,
    )

    samples[:, 0] = 0.9

    backend = FakeAudioBackend(
        devices=[
            create_test_device(),
        ],
        duplex_samples=AudioBuffer(
            samples=samples,
            sample_rate=SAMPLE_RATE,
        ),
    )

    result = validate_configured_loopback(
        backend,
        create_config(),
    )

    assert result.analysed_audio.channel_count == 1

    assert result.metrics.peak.overall == pytest.approx(
        AMPLITUDE,
        abs=1e-6,
    )


def test_validate_configured_loopback_reports_silent_capture_failures() -> None:
    silent_capture = AudioBuffer(
        samples=np.zeros(
            create_capture().samples.shape,
            dtype=np.float32,
        ),
        sample_rate=SAMPLE_RATE,
    )

    backend = FakeAudioBackend(
        devices=[
            create_test_device(),
        ],
        duplex_samples=silent_capture,
    )

    result = validate_configured_loopback(
        backend,
        create_config(),
    )

    assert result.passed is False
    assert result.frequency.measured_hz == 0.0
    assert result.frequency.passed is False
    assert result.metrics.silence.detected is True

    frequency_failures = [failure for failure in result.failures if failure.metric == "frequency"]

    silence_failures = [failure for failure in result.failures if failure.metric == "silence"]

    assert len(frequency_failures) == 1
    assert len(silence_failures) == 1

    assert frequency_failures[0].channel == 1
    assert silence_failures[0].channel == 1


def test_validate_configured_loopback_requires_loopback_settings() -> None:
    config = FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
        ),
        stream=StreamConfig(
            sample_rate=SAMPLE_RATE,
            input_channels=2,
            output_channels=2,
        ),
    )

    backend = FakeAudioBackend(
        devices=[
            create_test_device(),
        ],
    )

    with pytest.raises(
        ValueError,
        match="Loopback validation settings are required",
    ):
        validate_configured_loopback(
            backend,
            config,
        )


def test_validate_configured_loopback_maps_metric_failure_to_input_channel() -> None:
    config = create_config()

    config = config.model_copy(
        update={
            "thresholds": config.thresholds.model_copy(
                update={
                    "maximum_peak": 0.1,
                }
            )
        }
    )

    backend = FakeAudioBackend(
        devices=[
            create_test_device(),
        ],
        duplex_samples=create_capture(),
    )

    result = validate_configured_loopback(
        backend,
        config,
    )

    peak_failures = [failure for failure in result.failures if failure.metric == "peak"]

    assert result.passed is False
    assert len(peak_failures) == 1
    assert peak_failures[0].channel == 1
    assert peak_failures[0].threshold == 0.1
