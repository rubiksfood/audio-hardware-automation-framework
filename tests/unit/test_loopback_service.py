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
    DuplexEndpoints,
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


class RecordingFakeAudioBackend(FakeAudioBackend):
    """Fake backend that records duplex endpoint validation calls."""

    def __init__(
        self,
        *,
        devices: list[AudioDevice],
        duplex_samples: AudioBuffer,
    ) -> None:
        super().__init__(
            devices=devices,
            duplex_samples=duplex_samples,
        )

        self.capability_calls: list[tuple[AudioDevice, StreamConfig]] = []

        self.opening_calls: list[tuple[AudioDevice, StreamConfig]] = []

        self.duplex_endpoints: DuplexEndpoints | None = None

    def validate_stream_capability(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        self.capability_calls.append((
            device,
            config,
        ))

        super().validate_stream_capability(
            device,
            config,
        )

    def validate_stream_opening(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        self.opening_calls.append((
            device,
            config,
        ))

        super().validate_stream_opening(
            device,
            config,
        )

    def duplex(
        self,
        endpoints: DuplexEndpoints,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> AudioBuffer:
        self.duplex_endpoints = endpoints

        return super().duplex(
            endpoints,
            config,
            audio,
            timeout_seconds=timeout_seconds,
        )


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


def create_test_input_device() -> AudioDevice:
    """Create the input-only endpoint used by split loopback tests."""

    return AudioDevice(
        index=0,
        name="Scarlett Input",
        host_api_index=0,
        host_api_name="Test API",
        max_input_channels=2,
        max_output_channels=0,
        default_sample_rate=SAMPLE_RATE,
    )


def create_test_output_device() -> AudioDevice:
    """Create the output-only endpoint used by split loopback tests."""

    return AudioDevice(
        index=1,
        name="Scarlett Output",
        host_api_index=0,
        host_api_name="Test API",
        max_input_channels=0,
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


def create_split_config() -> FrameworkConfig:
    """Create a loopback configuration with separate endpoint selectors."""

    return FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
        ),
        input_device=DeviceMatchConfig(
            exact_name="Scarlett Input",
            host_api_contains="Test API",
            minimum_input_channels=2,
        ),
        output_device=DeviceMatchConfig(
            exact_name="Scarlett Output",
            host_api_contains="Test API",
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


def test_validate_configured_loopback_uses_resolved_split_endpoints() -> None:
    input_device = create_test_input_device()
    output_device = create_test_output_device()

    backend = RecordingFakeAudioBackend(
        devices=[
            input_device,
            output_device,
        ],
        duplex_samples=create_capture(),
    )

    result = validate_configured_loopback(
        backend,
        create_split_config(),
    )

    assert result.passed is True

    assert backend.duplex_endpoints == DuplexEndpoints(
        input_device=input_device,
        output_device=output_device,
    )

    assert len(backend.capability_calls) == 2

    capability_input_device, capability_input_stream = backend.capability_calls[0]

    capability_output_device, capability_output_stream = backend.capability_calls[1]

    assert capability_input_device == input_device
    assert capability_input_stream.input_channels == 2
    assert capability_input_stream.output_channels == 0

    assert capability_output_device == output_device
    assert capability_output_stream.input_channels == 0
    assert capability_output_stream.output_channels == 2

    assert len(backend.opening_calls) == 2

    opening_input_device, opening_input_stream = backend.opening_calls[0]

    opening_output_device, opening_output_stream = backend.opening_calls[1]

    assert opening_input_device == input_device
    assert opening_input_stream.input_channels == 2
    assert opening_input_stream.output_channels == 0

    assert opening_output_device == output_device
    assert opening_output_stream.input_channels == 0
    assert opening_output_stream.output_channels == 2

    # Temporary compatibility field until the reporting migration.
    assert result.device == input_device


def test_validate_configured_loopback_preserves_shared_device_preflight() -> None:
    device = create_test_device()

    backend = RecordingFakeAudioBackend(
        devices=[device],
        duplex_samples=create_capture(),
    )

    config = create_config()

    validate_configured_loopback(
        backend,
        config,
    )

    assert backend.capability_calls == [
        (
            device,
            config.stream,
        ),
    ]

    assert backend.opening_calls == [
        (
            device,
            config.stream,
        ),
    ]

    assert backend.duplex_endpoints == DuplexEndpoints(
        input_device=device,
        output_device=device,
    )


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
