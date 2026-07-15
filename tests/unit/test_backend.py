from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.models import AudioDevice


def test_fake_backend_info() -> None:
    backend = FakeAudioBackend()

    assert backend.info.name == "fake"


def test_fake_backend_returns_devices() -> None:
    device = AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        devices=[device],
    )

    result = backend.list_devices()

    assert result == [device]


def test_fake_backend_returns_empty_list() -> None:
    backend = FakeAudioBackend()

    assert backend.list_devices() == []
