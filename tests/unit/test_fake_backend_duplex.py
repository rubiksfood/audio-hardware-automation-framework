"""Tests for deterministic fake backend duplex execution."""

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.models import (
    AudioDevice,
    DuplexEndpoints,
    StreamConfig,
)
from tests.unit.fake_backend_helpers import (
    create_duplex_key,
    create_split_test_endpoints,
    create_test_device,
)


def create_playback_audio(
    *,
    frame_count: int = 4,
    channel_count: int = 2,
    sample_rate: int = 48_000,
) -> AudioBuffer:
    """Create playback audio for fake duplex tests."""

    return AudioBuffer(
        samples=np.zeros(
            (frame_count, channel_count),
            dtype=np.float32,
        ),
        sample_rate=sample_rate,
    )


def create_shared_endpoints(
    device: AudioDevice,
) -> DuplexEndpoints:
    """Wrap one device as shared duplex endpoints."""

    return DuplexEndpoints(
        input_device=device,
        output_device=device,
    )


def test_fake_backend_duplex_supports_split_endpoints() -> None:
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = create_playback_audio()

    result = FakeAudioBackend().duplex(
        create_split_test_endpoints(),
        config,
        audio,
        timeout_seconds=5.0,
    )

    assert result.sample_rate == 48_000
    assert result.frame_count == audio.frame_count
    assert result.channel_count == 2

    np.testing.assert_array_equal(
        result.samples,
        np.zeros(
            (audio.frame_count, 2),
            dtype=np.float32,
        ),
    )


def test_fake_backend_duplex_returns_silent_capture_by_default() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.ones(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = FakeAudioBackend().duplex(
        create_shared_endpoints(device),
        config,
        audio,
        timeout_seconds=5.0,
    )

    assert result.sample_rate == 48_000
    assert result.frame_count == 4
    assert result.channel_count == 2

    np.testing.assert_array_equal(
        result.samples,
        np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
    )


def test_fake_backend_duplex_returns_configured_samples() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    playback_audio = create_playback_audio()

    capture_samples = np.array(
        [
            [0.1, -0.1],
            [0.2, -0.2],
            [0.3, -0.3],
            [0.4, -0.4],
        ],
        dtype=np.float32,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=capture_samples,
            sample_rate=48_000,
        ),
    )

    result = backend.duplex(
        create_shared_endpoints(device),
        config,
        playback_audio,
        timeout_seconds=5.0,
    )

    np.testing.assert_array_equal(
        result.samples,
        capture_samples,
    )


def test_fake_backend_duplex_returns_framework_owned_buffer() -> None:
    configured_capture = AudioBuffer(
        samples=np.ones(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_samples=configured_capture,
    )

    device = create_test_device()

    result = backend.duplex(
        create_shared_endpoints(device),
        StreamConfig(
            input_channels=2,
            output_channels=2,
        ),
        create_playback_audio(),
        timeout_seconds=5.0,
    )

    assert result is not configured_capture
    assert not result.samples.flags.writeable


def test_fake_backend_duplex_truncates_configured_samples() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    playback_audio = create_playback_audio(
        frame_count=3,
    )

    configured_capture = AudioBuffer(
        samples=np.ones(
            (5, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_samples=configured_capture,
    )

    result = backend.duplex(
        create_shared_endpoints(device),
        config,
        playback_audio,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 3

    np.testing.assert_array_equal(
        result.samples,
        configured_capture.samples[:3],
    )


def test_fake_backend_raises_configured_duplex_failure() -> None:
    endpoints = create_split_test_endpoints()

    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = create_playback_audio()

    backend = FakeAudioBackend(
        duplex_failures={
            create_duplex_key(
                endpoints,
                config,
                audio,
            ),
        },
    )

    with pytest.raises(
        AudioBackendError,
        match=(
            "Fake backend duplex execution failed for "
            "input device index 0 and output device index 1"
        ),
    ):
        backend.duplex(
            endpoints,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_failure_distinguishes_endpoint_pairs() -> None:
    configured_endpoints = create_split_test_endpoints()

    alternate_output = AudioDevice(
        index=2,
        name="Alternate Scarlett Output",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=0,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    alternate_endpoints = DuplexEndpoints(
        input_device=configured_endpoints.input_device,
        output_device=alternate_output,
    )

    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = create_playback_audio()

    backend = FakeAudioBackend(
        duplex_failures={
            create_duplex_key(
                configured_endpoints,
                config,
                audio,
            ),
        },
    )

    result = backend.duplex(
        alternate_endpoints,
        config,
        audio,
        timeout_seconds=5.0,
    )

    assert result.frame_count == audio.frame_count


def test_fake_backend_duplex_requires_input_channels() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="Cannot perform duplex execution with no input channels",
    ):
        FakeAudioBackend().duplex(
            create_shared_endpoints(device),
            config,
            create_playback_audio(),
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_requires_output_channels() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    audio = create_playback_audio(
        channel_count=1,
    )

    with pytest.raises(
        AudioBackendError,
        match="Cannot perform duplex execution with no output channels",
    ):
        FakeAudioBackend().duplex(
            create_shared_endpoints(device),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_playback_sample_rate_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = create_playback_audio(
        sample_rate=44_100,
    )

    with pytest.raises(
        AudioBackendError,
        match=("Duplex playback audio sample rate does not match the stream sample rate"),
    ):
        FakeAudioBackend().duplex(
            create_shared_endpoints(device),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_playback_channel_count_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = create_playback_audio(
        channel_count=1,
    )

    with pytest.raises(
        AudioBackendError,
        match=("Duplex playback audio channel count does not match the stream output channels"),
    ):
        FakeAudioBackend().duplex(
            create_shared_endpoints(device),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_configured_sample_rate_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=np.zeros(
                (4, 2),
                dtype=np.float32,
            ),
            sample_rate=44_100,
        ),
    )

    with pytest.raises(
        AudioBackendError,
        match="Configured duplex samples do not match the stream sample rate",
    ):
        backend.duplex(
            create_shared_endpoints(device),
            config,
            create_playback_audio(),
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_configured_channel_count_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=np.zeros(
                (4, 1),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    with pytest.raises(
        AudioBackendError,
        match="Configured duplex samples do not match the stream input channels",
    ):
        backend.duplex(
            create_shared_endpoints(device),
            config,
            create_playback_audio(),
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_short_configured_capture() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=np.zeros(
                (3, 2),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    with pytest.raises(
        AudioBackendError,
        match="Configured duplex samples contain fewer frames than playback audio",
    ):
        backend.duplex(
            create_shared_endpoints(device),
            config,
            create_playback_audio(),
            timeout_seconds=5.0,
        )
