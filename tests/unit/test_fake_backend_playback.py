"""Tests for fake backend playback behaviour."""

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.models import StreamConfig
from tests.unit.fake_backend_helpers import (
    create_playback_key,
    create_test_device,
)


def test_fake_backend_accepts_valid_playback() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend.playback(
        device,
        config,
        audio,
        timeout_seconds=5.0,
    )


def test_fake_backend_rejects_playback_without_output_channels() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        AudioBackendError,
        match="no output channels",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_playback_sample_rate_mismatch() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=0,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )

    with pytest.raises(
        AudioBackendError,
        match="sample rate",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_playback_channel_mismatch() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        AudioBackendError,
        match="channel count",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_simulates_playback_failure() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    backend = FakeAudioBackend(
        playback_failures={
            create_playback_key(
                device,
                config,
            ),
        },
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        AudioBackendError,
        match="playback failed",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )
