"""Tests for fake backend device and stream behaviour."""

import pytest

from audio_hw_framework.backend.base import (
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.models import StreamConfig
from tests.unit.fake_backend_helpers import (
    create_stream_key,
    create_test_device,
)


def test_fake_backend_info() -> None:
    backend = FakeAudioBackend()

    assert backend.info.name == "fake"
    assert backend.info.library == "internal"
    assert backend.info.library_version is None


def test_fake_backend_returns_devices() -> None:
    device = create_test_device()
    backend = FakeAudioBackend(devices=[device])

    result = backend.list_devices()

    assert result == [device]


def test_fake_backend_returns_empty_list() -> None:
    backend = FakeAudioBackend()

    assert backend.list_devices() == []


def test_fake_backend_returns_device_list_copy() -> None:
    device = create_test_device()
    backend = FakeAudioBackend(devices=[device])

    result = backend.list_devices()
    result.clear()

    assert backend.list_devices() == [device]


def test_fake_backend_accepts_supported_stream() -> None:
    device = create_test_device()
    backend = FakeAudioBackend(devices=[device])
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )

    backend.validate_stream_capability(
        device,
        config,
    )


def test_fake_backend_rejects_configured_unsupported_stream() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )
    backend = FakeAudioBackend(
        devices=[device],
        unsupported_streams={
            create_stream_key(
                device,
                config,
            ),
        },
    )

    with pytest.raises(
        StreamCapabilityError,
        match="device index 0",
    ):
        backend.validate_stream_capability(
            device,
            config,
        )


def test_fake_backend_distinguishes_stream_channel_configurations() -> None:
    device = create_test_device()

    rejected_config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )
    input_only_config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    backend = FakeAudioBackend(
        devices=[device],
        unsupported_streams={
            create_stream_key(
                device,
                rejected_config,
            ),
        },
    )

    backend.validate_stream_capability(
        device,
        input_only_config,
    )


def test_fake_backend_accepts_stream_opening() -> None:
    device = create_test_device()
    backend = FakeAudioBackend(devices=[device])
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )

    backend.validate_stream_opening(
        device,
        config,
    )


def test_fake_backend_rejects_configured_stream_open_failure() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )

    backend = FakeAudioBackend(
        devices=[device],
        stream_open_failures={
            create_stream_key(
                device,
                config,
            ),
        },
    )

    with pytest.raises(
        StreamOpenError,
        match="device index 0",
    ):
        backend.validate_stream_opening(
            device,
            config,
        )


def test_fake_backend_distinguishes_stream_block_sizes() -> None:
    device = create_test_device()

    rejected_config = StreamConfig(
        input_channels=2,
        output_channels=2,
        block_size=128,
    )
    accepted_config = StreamConfig(
        input_channels=2,
        output_channels=2,
        block_size=256,
    )

    backend = FakeAudioBackend(
        devices=[device],
        stream_open_failures={
            create_stream_key(
                device,
                rejected_config,
            ),
        },
    )

    backend.validate_stream_opening(
        device,
        accepted_config,
    )
