import time

import numpy as np
import sounddevice as sd

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import (
    AudioBackend,
    AudioBackendError,
    BackendInfo,
    DeviceEnumerationError,
    StreamCapabilityError,
    StreamOpenError,
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

    def validate_stream_opening(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        block_size = config.block_size if config.block_size is not None else 0
        dtype = config.dtype.value

        try:
            if config.input_channels > 0 and config.output_channels > 0:
                stream_kind = "duplex"
                stream = sd.RawStream(
                    samplerate=config.sample_rate,
                    blocksize=block_size,
                    device=(device.index, device.index),
                    channels=(
                        config.input_channels,
                        config.output_channels,
                    ),
                    dtype=(dtype, dtype),
                )

            elif config.input_channels > 0:
                stream_kind = "input"
                stream = sd.RawInputStream(
                    samplerate=config.sample_rate,
                    blocksize=block_size,
                    device=device.index,
                    channels=config.input_channels,
                    dtype=dtype,
                )

            else:
                stream_kind = "output"
                stream = sd.RawOutputStream(
                    samplerate=config.sample_rate,
                    blocksize=block_size,
                    device=device.index,
                    channels=config.output_channels,
                    dtype=dtype,
                )

        except sd.PortAudioError as exc:
            raise StreamOpenError(
                f"Could not open {stream_kind} stream for device index {device.index}: {exc}"
            ) from exc

        stream.close(ignore_errors=True)

    def record(
        self,
        device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        """Record a finite number of frames from a PortAudio input stream."""

        if frame_count < 0:
            raise ValueError("frame_count must be greater than or equal to 0")

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")

        if config.input_channels == 0:
            raise AudioBackendError(
                "Cannot record from a stream with no input channels",
            )

        if frame_count == 0:
            return AudioBuffer(
                samples=np.empty(
                    (0, config.input_channels),
                    dtype=config.dtype.value,
                ),
                sample_rate=config.sample_rate,
            )

        block_size = config.block_size if config.block_size is not None else 0

        stream = None

        try:
            stream = sd.InputStream(
                samplerate=config.sample_rate,
                blocksize=block_size,
                device=device.index,
                channels=config.input_channels,
                dtype=config.dtype.value,
            )

            stream.start()

            chunks: list[np.ndarray] = []
            captured_frames = 0
            deadline = time.monotonic() + timeout_seconds

            while captured_frames < frame_count:
                if time.monotonic() >= deadline:
                    raise AudioBackendError(
                        f"Recording timed out for device index {device.index}",
                    )

                available_frames = stream.read_available

                if available_frames == 0:
                    time.sleep(0.001)
                    continue

                frames_to_read = min(
                    available_frames,
                    frame_count - captured_frames,
                )

                data, overflowed = stream.read(frames_to_read)

                if overflowed:
                    raise AudioBackendError(
                        f"Input overflow while recording from device index {device.index}",
                    )

                chunks.append(data)
                captured_frames += len(data)

            stream.stop()

        except sd.PortAudioError as exc:
            if stream is not None:
                stream.abort(ignore_errors=True)

            raise AudioBackendError(
                f"Could not record from device index {device.index}: {exc}",
            ) from exc

        except AudioBackendError:
            if stream is not None:
                stream.abort(ignore_errors=True)
            raise

        finally:
            if stream is not None:
                stream.close(ignore_errors=True)

        samples = np.concatenate(
            chunks,
            axis=0,
        )

        return AudioBuffer(
            samples=samples,
            sample_rate=config.sample_rate,
        )

    def playback(
        self,
        device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> None:
        """Play a finite audio buffer through a PortAudio output stream."""

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")

        if config.output_channels == 0:
            raise AudioBackendError(
                "Cannot play audio through a stream with no output channels",
            )

        if audio.sample_rate != config.sample_rate:
            raise AudioBackendError(
                "Playback audio sample rate does not match the stream sample rate",
            )

        if audio.channel_count != config.output_channels:
            raise AudioBackendError(
                "Playback audio channel count does not match the stream output channels",
            )

        if audio.frame_count == 0:
            return

        block_size = config.block_size if config.block_size is not None else 0

        samples = np.ascontiguousarray(
            audio.samples,
            dtype=config.dtype.value,
        )

        stream = None

        try:
            stream = sd.OutputStream(
                samplerate=config.sample_rate,
                blocksize=block_size,
                device=device.index,
                channels=config.output_channels,
                dtype=config.dtype.value,
            )

            stream.start()

            written_frames = 0
            deadline = time.monotonic() + timeout_seconds

            while written_frames < audio.frame_count:
                if time.monotonic() >= deadline:
                    raise AudioBackendError(
                        f"Playback timed out for device index {device.index}",
                    )

                available_frames = stream.write_available

                if available_frames == 0:
                    time.sleep(0.001)
                    continue

                frames_to_write = min(
                    available_frames,
                    audio.frame_count - written_frames,
                )

                end_frame = written_frames + frames_to_write

                underflowed = stream.write(
                    samples[written_frames:end_frame],
                )

                if underflowed:
                    raise AudioBackendError(
                        f"Output underflow while playing through device index {device.index}",
                    )

                written_frames = end_frame

            stream.stop()

        except sd.PortAudioError as exc:
            if stream is not None:
                stream.abort(ignore_errors=True)

            raise AudioBackendError(
                f"Could not play through device index {device.index}: {exc}",
            ) from exc

        except AudioBackendError:
            if stream is not None:
                stream.abort(ignore_errors=True)
            raise

        finally:
            if stream is not None:
                stream.close(ignore_errors=True)
