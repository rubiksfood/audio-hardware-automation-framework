import pytest
import sounddevice as sd
from pytest import MonkeyPatch

from audio_hw_framework.backend.base import DeviceEnumerationError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.device.models import AudioDevice, StreamConfig


def test_backend_info() -> None:
    backend = SoundDeviceBackend()

    assert backend.info.name == "portaudio"
    assert backend.info.library == "sounddevice"


def test_maps_sounddevice_results(monkeypatch: MonkeyPatch) -> None:
    fake_devices = [
        {
            "name": "Scarlett",
            "hostapi": 0,
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48_000,
        }
    ]

    monkeypatch.setattr(
        sd,
        "query_devices",
        lambda: fake_devices,
    )

    monkeypatch.setattr(
        sd,
        "query_hostapis",
        lambda: [{"name": "WASAPI"}],
    )

    result = SoundDeviceBackend().list_devices()

    assert len(result) == 1
    assert result[0].name == "Scarlett"
    assert result[0].host_api_name == "WASAPI"
    assert result[0].max_input_channels == 2
    assert result[0].max_output_channels == 2


def test_translates_portaudio_errors(monkeypatch: MonkeyPatch) -> None:
    def raise_error() -> None:
        raise sd.PortAudioError("failure")

    monkeypatch.setattr(
        sd,
        "query_devices",
        raise_error,
    )

    with pytest.raises(DeviceEnumerationError):
        SoundDeviceBackend().list_devices()


def test_stream_capability_validation_is_not_yet_implemented() -> None:
    backend = SoundDeviceBackend()

    device = AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    config = StreamConfig()

    with pytest.raises(
        NotImplementedError,
        match="PortAudio stream capability validation is not implemented",
    ):
        backend.validate_stream_capability(device, config)
