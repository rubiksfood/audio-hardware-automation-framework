"""Tests for fake backend recording behaviour."""

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.models import StreamConfig
from tests.unit.fake_backend_helpers import (
    create_recording_key,
    create_test_device,
)


def test_fake_backend_records_silence_by_default() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = backend.record(
        device,
        config,
        frame_count=3,
        timeout_seconds=5.0,
    )

    assert result.sample_rate == 48_000
    assert result.frame_count == 3
    assert result.channel_count == 2

    np.testing.assert_array_equal(
        result.samples,
        np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
    )


def test_fake_backend_returns_configured_recording_samples() -> None:
    captured = AudioBuffer(
        samples=np.array(
            [
                [0.1, -0.1],
                [0.2, -0.2],
                [0.3, -0.3],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        recording_samples=captured,
    )

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = backend.record(
        device,
        config,
        frame_count=2,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 2

    np.testing.assert_array_equal(
        result.samples,
        captured.samples[:2],
    )


def test_fake_backend_recording_returns_framework_owned_buffer() -> None:
    captured = AudioBuffer(
        samples=np.ones(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        recording_samples=captured,
    )

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = backend.record(
        device,
        config,
        frame_count=3,
        timeout_seconds=5.0,
    )

    assert result is not captured
    assert not result.samples.flags.writeable


def test_fake_backend_rejects_recording_without_input_channels() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="no input channels",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_recording_sample_rate_mismatch() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )

    backend = FakeAudioBackend(
        recording_samples=captured,
    )

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="stream sample rate",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_recording_channel_mismatch() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (3, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        recording_samples=captured,
    )

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="stream input channels",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_insufficient_recording_samples() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (2, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        recording_samples=captured,
    )

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="fewer frames than requested",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_simulates_recording_failure() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    backend = FakeAudioBackend(
        recording_failures={
            create_recording_key(
                device,
                config,
                48_000,
            ),
        },
    )

    with pytest.raises(
        AudioBackendError,
        match="recording failed",
    ):
        backend.record(
            device,
            config,
            frame_count=48_000,
            timeout_seconds=5.0,
        )
