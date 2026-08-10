from pathlib import Path

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer, read_wav
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.matcher import (
    AmbiguousDeviceMatchError,
    DeviceNotFoundError,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    AudioExecutionConfig,
    DeviceMatchConfig,
    FrameworkConfig,
    StreamConfig,
)
from audio_hw_framework.recording import (
    RecordingExecutionError,
    record_configured_audio,
)


def create_device(
    *,
    index: int = 0,
    name: str = "Focusrite Scarlett 2i2 USB",
) -> AudioDevice:
    return AudioDevice(
        index=index,
        name=name,
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def create_config(
    *,
    duration_seconds: float = 0.5,
    output_file: Path | None = None,
    input_channels: int = 2,
    output_channels: int = 0,
) -> FrameworkConfig:
    return FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
            host_api_contains="WASAPI",
            minimum_input_channels=2,
        ),
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=input_channels,
            output_channels=output_channels,
            block_size=128,
        ),
        execution=AudioExecutionConfig(
            duration_seconds=duration_seconds,
            timeout_seconds=5.0,
            output_file=output_file,
        ),
    )


class ShortRecordingBackend(FakeAudioBackend):
    """Test backend that deliberately violates the recording contract."""

    def record(
        self,
        device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        return AudioBuffer(
            samples=np.zeros(
                (frame_count - 1, config.input_channels),
                dtype=np.float32,
            ),
            sample_rate=config.sample_rate,
        )


class WrongSampleRateBackend(FakeAudioBackend):
    """Test backend that returns recording data at the wrong sample rate."""

    def record(
        self,
        device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        return AudioBuffer(
            samples=np.zeros(
                (frame_count, config.input_channels),
                dtype=np.float32,
            ),
            sample_rate=44_100,
        )


class WrongChannelCountBackend(FakeAudioBackend):
    """Test backend that returns the wrong recording channel count."""

    def record(
        self,
        device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        return AudioBuffer(
            samples=np.zeros(
                (frame_count, 1),
                dtype=np.float32,
            ),
            sample_rate=config.sample_rate,
        )


def test_records_configured_duration_and_returns_result() -> None:
    device = create_device()
    backend = FakeAudioBackend(
        devices=[device],
    )
    config = create_config(
        duration_seconds=0.5,
    )

    result = record_configured_audio(
        backend,
        config,
    )

    assert result.backend == backend.info
    assert result.device == device
    assert result.stream == config.stream
    assert result.output_file is None

    assert result.audio.frame_count == 24_000
    assert result.audio.channel_count == 2
    assert result.audio.sample_rate == 48_000


def test_returns_audio_recorded_by_backend() -> None:
    device = create_device()

    expected_samples = np.full(
        (24_000, 2),
        0.25,
        dtype=np.float32,
    )
    recording = AudioBuffer(
        samples=expected_samples,
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        devices=[device],
        recording_samples=recording,
    )

    result = record_configured_audio(
        backend,
        create_config(),
    )

    np.testing.assert_array_equal(
        result.audio.samples,
        expected_samples,
    )


def test_records_from_uniquely_matched_device() -> None:
    selected_device = create_device()

    unrelated_device = create_device(
        index=1,
        name="Built-in Audio",
    )

    backend = FakeAudioBackend(
        devices=[
            unrelated_device,
            selected_device,
        ],
    )

    result = record_configured_audio(
        backend,
        create_config(),
    )

    assert result.device == selected_device


def test_raises_when_no_device_matches() -> None:
    backend = FakeAudioBackend(
        devices=[
            create_device(
                name="Built-in Audio",
            ),
        ],
    )

    with pytest.raises(
        DeviceNotFoundError,
        match="No device matched configuration",
    ):
        record_configured_audio(
            backend,
            create_config(),
        )


def test_raises_when_device_match_is_ambiguous() -> None:
    backend = FakeAudioBackend(
        devices=[
            create_device(index=0),
            create_device(
                index=1,
                name="Focusrite Scarlett Solo USB",
            ),
        ],
    )

    with pytest.raises(
        AmbiguousDeviceMatchError,
        match="Multiple devices matched configuration",
    ):
        record_configured_audio(
            backend,
            create_config(),
        )


def test_rejects_recording_without_input_channels() -> None:
    backend = FakeAudioBackend(
        devices=[create_device()],
    )

    config = create_config(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        RecordingExecutionError,
        match="requires at least one input channel",
    ):
        record_configured_audio(
            backend,
            config,
        )


def test_propagates_backend_recording_error() -> None:
    device = create_device()
    config = create_config()

    backend = FakeAudioBackend(
        devices=[device],
        recording_failures={
            (
                device.index,
                config.stream.sample_rate,
                config.stream.input_channels,
                24_000,
                config.stream.dtype.value,
            ),
        },
    )

    with pytest.raises(
        AudioBackendError,
        match="Fake backend recording failed",
    ):
        record_configured_audio(
            backend,
            config,
        )


def test_exports_recording_when_output_file_is_configured(
    tmp_path: Path,
) -> None:
    output_file = tmp_path / "recordings" / "capture.wav"

    backend = FakeAudioBackend(
        devices=[create_device()],
    )

    result = record_configured_audio(
        backend,
        create_config(
            output_file=output_file,
        ),
    )

    assert result.output_file == output_file
    assert output_file.is_file()

    exported = read_wav(output_file)

    assert exported.frame_count == result.audio.frame_count
    assert exported.channel_count == result.audio.channel_count
    assert exported.sample_rate == result.audio.sample_rate

    np.testing.assert_allclose(
        np.asarray(exported.samples, dtype=np.float32),
        np.asarray(result.audio.samples, dtype=np.float32),
    )


def test_rejects_backend_returning_wrong_frame_count() -> None:
    backend = ShortRecordingBackend(
        devices=[create_device()],
    )

    with pytest.raises(
        RecordingExecutionError,
        match="unexpected number of recording frames",
    ):
        record_configured_audio(
            backend,
            create_config(),
        )


def test_rejects_backend_returning_wrong_sample_rate() -> None:
    backend = WrongSampleRateBackend(
        devices=[create_device()],
    )

    with pytest.raises(
        RecordingExecutionError,
        match="unexpected sample rate",
    ):
        record_configured_audio(
            backend,
            create_config(),
        )


def test_rejects_backend_returning_wrong_channel_count() -> None:
    backend = WrongChannelCountBackend(
        devices=[create_device()],
    )

    with pytest.raises(
        RecordingExecutionError,
        match="unexpected channel count",
    ):
        record_configured_audio(
            backend,
            create_config(),
        )
