import pytest
import sounddevice as sd
from pytest import MonkeyPatch

from audio_hw_framework.backend.base import DeviceEnumerationError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend


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

    result = SoundDeviceBackend().list_devices()

    assert len(result) == 1
    assert result[0].name == "Scarlett"
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
