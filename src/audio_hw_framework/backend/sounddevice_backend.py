import sounddevice as sd

from audio_hw_framework.backend.base import (
    AudioBackend,
    BackendInfo,
    DeviceEnumerationError,
)
from audio_hw_framework.device.models import AudioDevice


class SoundDeviceBackend(AudioBackend):
    @property
    def info(self) -> BackendInfo:
        return BackendInfo(
            name="portaudio",
            library="sounddevice",
            library_version=sd.__version__,
        )

    def list_devices(self) -> list[AudioDevice]:
        try:
            raw_devices = sd.query_devices()
        except sd.PortAudioError as exc:
            raise DeviceEnumerationError(f"Could not enumerate devices: {exc}") from exc

        devices: list[AudioDevice] = []

        for index, device in enumerate(raw_devices):
            devices.append(
                AudioDevice(
                    index=index,
                    name=device["name"],
                    host_api_index=device["hostapi"],
                    host_api_name="Unknown",
                    max_input_channels=device["max_input_channels"],
                    max_output_channels=device["max_output_channels"],
                    default_sample_rate=device["default_samplerate"],
                )
            )
        return devices
