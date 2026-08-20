"""Tests for deterministic fake backend duplex execution."""

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.models import StreamConfig
from tests.unit.fake_backend_helpers import (
    create_duplex_key,
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
        device,
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
        device,
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

    result = backend.duplex(
        create_test_device(),
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
        device,
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
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )
    audio = create_playback_audio()

    backend = FakeAudioBackend(
        duplex_failures={
            create_duplex_key(
                device,
                config,
                audio,
            ),
        },
    )

    with pytest.raises(
        AudioBackendError,
        match="Fake backend duplex execution failed for device index 0",
    ):
        backend.duplex(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


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
            device,
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
            device,
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
            device,
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
            device,
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
            device,
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
            device,
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
            device,
            config,
            create_playback_audio(),
            timeout_seconds=5.0,
        )
