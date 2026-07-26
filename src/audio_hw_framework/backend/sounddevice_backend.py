import sounddevice as sd

from audio_hw_framework.backend.base import (
    AudioBackend,
    BackendInfo,
    DeviceEnumerationError,
    StreamCapabilityError,
)
from audio_hw_framework.device.models import AudioDevice, StreamConfig


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
            raw_host_apis = sd.query_hostapis()
        except sd.PortAudioError as exc:
            raise DeviceEnumerationError(f"Could not enumerate devices: {exc}") from exc

        devices: list[AudioDevice] = []

        for index, device in enumerate(raw_devices):
            host_api_index = int(device["hostapi"])

            devices.append(
                AudioDevice(
                    index=index,
                    name=device["name"],
                    host_api_index=host_api_index,
                    host_api_name=str(raw_host_apis[host_api_index]["name"]),
                    max_input_channels=device["max_input_channels"],
                    max_output_channels=device["max_output_channels"],
                    default_sample_rate=device["default_samplerate"],
                )
            )

        return devices

    def validate_stream_capability(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        if config.input_channels > 0:
            try:
                sd.check_input_settings(
                    device=device.index,
                    channels=config.input_channels,
                    samplerate=config.sample_rate,
                    dtype=config.dtype.value,
                )
            except sd.PortAudioError as exc:
                raise StreamCapabilityError(
                    "Input stream settings are not supported "
                    f"for device index {device.index}: {exc}"
                ) from exc

        if config.output_channels > 0:
            try:
                sd.check_output_settings(
                    device=device.index,
                    channels=config.output_channels,
                    samplerate=config.sample_rate,
                    dtype=config.dtype.value,
                )
            except sd.PortAudioError as exc:
                raise StreamCapabilityError(
                    "Output stream settings are not supported "
                    f"for device index {device.index}: {exc}"
                ) from exc
