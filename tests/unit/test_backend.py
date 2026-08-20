import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import (
    AudioBackendError,
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


def create_recording_key(
    device: AudioDevice,
    config: StreamConfig,
    frame_count: int,
) -> tuple[int, int, int, int, str]:
    return (
        device.index,
        config.sample_rate,
        config.input_channels,
        frame_count,
        config.dtype.value,
    )


def create_playback_key(
    device: AudioDevice,
    config: StreamConfig,
) -> tuple[int, int, int, str]:
    return (
        device.index,
        config.sample_rate,
        config.output_channels,
        config.dtype.value,
    )


def create_duplex_key(
    device: AudioDevice,
    config: StreamConfig,
    audio: AudioBuffer,
) -> tuple[int, int, int, int, int, str]:
    return (
        device.index,
        config.sample_rate,
        config.input_channels,
        config.output_channels,
        audio.frame_count,
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


def test_fake_backend_records_silence_by_default() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = backend.record(
        device,
        config,
        frame_count=3,
        timeout_seconds=5.0,
    )

    assert result.sample_rate == 48_000
    assert result.frame_count == 3
    assert result.channel_count == 2

    np.testing.assert_array_equal(
        result.samples,
        np.zeros((3, 2), dtype=np.float32),
    )


def test_fake_backend_returns_configured_recording_samples() -> None:
    captured = AudioBuffer(
        samples=np.array(
            [
                [0.1, -0.1],
                [0.2, -0.2],
                [0.3, -0.3],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    backend = FakeAudioBackend(
        recording_samples=captured,
    )
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = backend.record(
        device,
        config,
        frame_count=2,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 2

    np.testing.assert_array_equal(
        result.samples,
        captured.samples[:2],
    )


def test_fake_backend_recording_returns_framework_owned_buffer() -> None:
    captured = AudioBuffer(
        samples=np.ones(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    backend = FakeAudioBackend(
        recording_samples=captured,
    )
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = backend.record(
        device,
        config,
        frame_count=3,
        timeout_seconds=5.0,
    )

    assert result is not captured
    assert not result.samples.flags.writeable


def test_fake_backend_rejects_recording_without_input_channels() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="no input channels",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_recording_sample_rate_mismatch() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )
    backend = FakeAudioBackend(
        recording_samples=captured,
    )
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="stream sample rate",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_recording_channel_mismatch() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (3, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    backend = FakeAudioBackend(
        recording_samples=captured,
    )
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="stream input channels",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_insufficient_recording_samples() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (2, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    backend = FakeAudioBackend(
        recording_samples=captured,
    )
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="fewer frames than requested",
    ):
        backend.record(
            device,
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_fake_backend_simulates_recording_failure() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )
    backend = FakeAudioBackend(
        recording_failures={
            create_recording_key(
                device,
                config,
                48_000,
            ),
        },
    )

    with pytest.raises(
        AudioBackendError,
        match="recording failed",
    ):
        backend.record(
            device,
            config,
            frame_count=48_000,
            timeout_seconds=5.0,
        )


def test_fake_backend_accepts_valid_playback() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend.playback(
        device,
        config,
        audio,
        timeout_seconds=5.0,
    )


def test_fake_backend_rejects_playback_without_output_channels() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        AudioBackendError,
        match="no output channels",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_playback_sample_rate_mismatch() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=0,
        output_channels=2,
    )
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )

    with pytest.raises(
        AudioBackendError,
        match="sample rate",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_rejects_playback_channel_mismatch() -> None:
    backend = FakeAudioBackend()
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        AudioBackendError,
        match="channel count",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_simulates_playback_failure() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )
    backend = FakeAudioBackend(
        playback_failures={
            create_playback_key(
                device,
                config,
            ),
        },
    )
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        AudioBackendError,
        match="playback failed",
    ):
        backend.playback(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_returns_silent_capture_by_default() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )
    audio = AudioBuffer(
        samples=np.ones(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = FakeAudioBackend().duplex(
        device,
        config,
        audio,
        timeout_seconds=5.0,
    )

    assert result.sample_rate == 48_000
    assert result.frame_count == 4
    assert result.channel_count == 2

    np.testing.assert_array_equal(
        result.samples,
        np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
    )


def test_fake_backend_duplex_returns_framework_owned_buffer() -> None:
    configured_capture = AudioBuffer(
        samples=np.ones(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_samples=configured_capture,
    )

    result = backend.duplex(
        create_test_device(),
        StreamConfig(
            input_channels=2,
            output_channels=2,
        ),
        AudioBuffer(
            samples=np.zeros(
                (4, 2),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
        timeout_seconds=5.0,
    )

    assert result is not configured_capture
    assert not result.samples.flags.writeable


def test_fake_backend_duplex_returns_configured_samples() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    playback_audio = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    capture_samples = np.array(
        [
            [0.1, -0.1],
            [0.2, -0.2],
            [0.3, -0.3],
            [0.4, -0.4],
        ],
        dtype=np.float32,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=capture_samples,
            sample_rate=48_000,
        ),
    )

    result = backend.duplex(
        device,
        config,
        playback_audio,
        timeout_seconds=5.0,
    )

    np.testing.assert_array_equal(
        result.samples,
        capture_samples,
    )


def test_fake_backend_duplex_truncates_configured_samples() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    playback_audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    configured_capture = AudioBuffer(
        samples=np.ones(
            (5, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_samples=configured_capture,
    )

    result = backend.duplex(
        device,
        config,
        playback_audio,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 3

    np.testing.assert_array_equal(
        result.samples,
        configured_capture.samples[:3],
    )


def test_fake_backend_raises_configured_duplex_failure() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_failures={
            create_duplex_key(
                device,
                config,
                audio,
            ),
        },
    )

    with pytest.raises(
        AudioBackendError,
        match="Fake backend duplex execution failed for device index 0",
    ):
        backend.duplex(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_requires_input_channels() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=config.sample_rate,
    )

    with pytest.raises(
        AudioBackendError,
        match="Cannot perform duplex execution with no input channels",
    ):
        FakeAudioBackend().duplex(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_requires_output_channels() -> None:
    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=config.sample_rate,
    )

    with pytest.raises(
        AudioBackendError,
        match="Cannot perform duplex execution with no output channels",
    ):
        FakeAudioBackend().duplex(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_playback_sample_rate_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )

    with pytest.raises(
        AudioBackendError,
        match=("Duplex playback audio sample rate does not match the stream sample rate"),
    ):
        FakeAudioBackend().duplex(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_playback_channel_count_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        AudioBackendError,
        match=("Duplex playback audio channel count does not match the stream output channels"),
    ):
        FakeAudioBackend().duplex(
            device,
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_configured_sample_rate_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    playback_audio = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=np.zeros(
                (4, 2),
                dtype=np.float32,
            ),
            sample_rate=44_100,
        ),
    )

    with pytest.raises(
        AudioBackendError,
        match="Configured duplex samples do not match the stream sample rate",
    ):
        backend.duplex(
            device,
            config,
            playback_audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_configured_channel_count_mismatch() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    playback_audio = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=np.zeros(
                (4, 1),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    with pytest.raises(
        AudioBackendError,
        match="Configured duplex samples do not match the stream input channels",
    ):
        backend.duplex(
            device,
            config,
            playback_audio,
            timeout_seconds=5.0,
        )


def test_fake_backend_duplex_rejects_short_configured_capture() -> None:
    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
    )

    playback_audio = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    backend = FakeAudioBackend(
        duplex_samples=AudioBuffer(
            samples=np.zeros(
                (3, 2),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    with pytest.raises(
        AudioBackendError,
        match="Configured duplex samples contain fewer frames than playback audio",
    ):
        backend.duplex(
            device,
            config,
            playback_audio,
            timeout_seconds=5.0,
        )
