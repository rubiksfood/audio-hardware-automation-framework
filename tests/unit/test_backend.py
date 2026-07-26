import pytest

from audio_hw_framework.backend.base import StreamCapabilityError
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
    backend = FakeAudioBackend(
        devices=[device],
        unsupported_streams={(device.index, 2, 2)},
    )
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )

    with pytest.raises(
        StreamCapabilityError,
        match="device index 0",
    ):
        backend.validate_stream_capability(device, config)


def test_fake_backend_distinguishes_stream_channel_configurations() -> None:
    device = create_test_device()
    backend = FakeAudioBackend(
        devices=[device],
        unsupported_streams={(device.index, 2, 2)},
    )
    input_only_config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    backend.validate_stream_capability(
        device,
        input_only_config,
    )
