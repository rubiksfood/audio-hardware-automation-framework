import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import (
    BackendOperationNotSupportedError,
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.models import AudioDevice, StreamConfig


def create_test_device() -> AudioDevice:
    return AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def create_stream_key(
    device: AudioDevice,
    config: StreamConfig,
) -> tuple[int, int, int, int, int | None, str]:
    return (
        device.index,
        config.sample_rate,
        config.input_channels,
        config.output_channels,
        config.block_size,
        config.dtype.value,
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

    backend.validate_stream_capability(device, config)


def test_fake_backend_rejects_configured_unsupported_stream() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )
    backend = FakeAudioBackend(
        devices=[device],
        unsupported_streams={create_stream_key(device, config)},
    )

    with pytest.raises(
        StreamCapabilityError,
        match="device index 0",
    ):
        backend.validate_stream_capability(device, config)


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
        unsupported_streams={create_stream_key(device, rejected_config)},
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

    backend.validate_stream_opening(device, config)


def test_fake_backend_rejects_configured_stream_open_failure() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )
    backend = FakeAudioBackend(
        devices=[device],
        stream_open_failures={
            create_stream_key(device, config),
        },
    )

    with pytest.raises(
        StreamOpenError,
        match="device index 0",
    ):
        backend.validate_stream_opening(device, config)


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
            create_stream_key(device, rejected_config),
        },
    )

    backend.validate_stream_opening(
        device,
        accepted_config,
    )


def test_fake_backend_reports_recording_as_unsupported() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        BackendOperationNotSupportedError,
        match="fake backend does not support recording",
    ):
        backend.record(
            device,
            config,
            frame_count=48_000,
            timeout_seconds=5.0,
        )


def test_fake_backend_reports_playback_as_unsupported() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )
    audio = AudioBuffer(
        samples=np.zeros(
            (48_000, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        BackendOperationNotSupportedError,
        match="fake backend does not support playback",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )
