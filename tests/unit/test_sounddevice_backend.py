import time
from unittest.mock import Mock, PropertyMock

import numpy as np
import pytest
import sounddevice as sd
from pytest import MonkeyPatch

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import (
    AudioBackendError,
    DeviceEnumerationError,
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.device.models import AudioDevice, SampleDType, StreamConfig


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


def test_translates_portaudio_enumeration_errors(monkeypatch: MonkeyPatch) -> None:
    def raise_error() -> None:
        raise sd.PortAudioError("failure")

    monkeypatch.setattr(
        sd,
        "query_devices",
        raise_error,
    )

    with pytest.raises(
        DeviceEnumerationError,
        match="Could not enumerate devices",
    ):
        SoundDeviceBackend().list_devices()


def test_validates_input_stream_settings(monkeypatch: MonkeyPatch) -> None:
    input_check = Mock()
    output_check = Mock()

    monkeypatch.setattr(sd, "check_input_settings", input_check)
    monkeypatch.setattr(sd, "check_output_settings", output_check)

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=0,
        dtype=SampleDType.INT16,
    )

    SoundDeviceBackend().validate_stream_capability(device, config)

    input_check.assert_called_once_with(
        device=0,
        channels=2,
        samplerate=48_000,
        dtype="int16",
    )
    output_check.assert_not_called()


def test_validates_output_stream_settings(monkeypatch: MonkeyPatch) -> None:
    input_check = Mock()
    output_check = Mock()

    monkeypatch.setattr(sd, "check_input_settings", input_check)
    monkeypatch.setattr(sd, "check_output_settings", output_check)

    device = create_test_device()
    config = StreamConfig(
        sample_rate=44_100,
        input_channels=0,
        output_channels=2,
        dtype=SampleDType.FLOAT32,
    )

    SoundDeviceBackend().validate_stream_capability(device, config)

    input_check.assert_not_called()
    output_check.assert_called_once_with(
        device=0,
        channels=2,
        samplerate=44_100,
        dtype="float32",
    )


def test_validates_duplex_stream_settings(monkeypatch: MonkeyPatch) -> None:
    input_check = Mock()
    output_check = Mock()

    monkeypatch.setattr(sd, "check_input_settings", input_check)
    monkeypatch.setattr(sd, "check_output_settings", output_check)

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
        dtype=SampleDType.FLOAT32,
    )

    SoundDeviceBackend().validate_stream_capability(device, config)

    input_check.assert_called_once_with(
        device=0,
        channels=2,
        samplerate=48_000,
        dtype="float32",
    )
    output_check.assert_called_once_with(
        device=0,
        channels=2,
        samplerate=48_000,
        dtype="float32",
    )


def test_translates_input_capability_error(monkeypatch: MonkeyPatch) -> None:
    input_check = Mock(side_effect=sd.PortAudioError("Invalid sample rate"))
    output_check = Mock()

    monkeypatch.setattr(sd, "check_input_settings", input_check)
    monkeypatch.setattr(sd, "check_output_settings", output_check)

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        StreamCapabilityError,
        match="Input stream settings are not supported for device index 0",
    ):
        SoundDeviceBackend().validate_stream_capability(device, config)

    output_check.assert_not_called()


def test_translates_output_capability_error(monkeypatch: MonkeyPatch) -> None:
    input_check = Mock()
    output_check = Mock(side_effect=sd.PortAudioError("Invalid number of channels"))

    monkeypatch.setattr(sd, "check_input_settings", input_check)
    monkeypatch.setattr(sd, "check_output_settings", output_check)

    device = create_test_device()
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        StreamCapabilityError,
        match="Output stream settings are not supported for device index 0",
    ):
        SoundDeviceBackend().validate_stream_capability(device, config)

    input_check.assert_not_called()


def test_duplex_validation_stops_after_input_failure(monkeypatch: MonkeyPatch) -> None:
    input_check = Mock(side_effect=sd.PortAudioError("Input configuration rejected"))
    output_check = Mock()

    monkeypatch.setattr(sd, "check_input_settings", input_check)
    monkeypatch.setattr(sd, "check_output_settings", output_check)

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )

    with pytest.raises(StreamCapabilityError):
        SoundDeviceBackend().validate_stream_capability(device, config)

    output_check.assert_not_called()


def test_opens_and_closes_input_stream(monkeypatch: MonkeyPatch) -> None:
    stream = Mock()
    input_stream_factory = Mock(return_value=stream)
    output_stream_factory = Mock()
    duplex_stream_factory = Mock()

    monkeypatch.setattr(sd, "RawInputStream", input_stream_factory)
    monkeypatch.setattr(sd, "RawOutputStream", output_stream_factory)
    monkeypatch.setattr(sd, "RawStream", duplex_stream_factory)

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=0,
        block_size=None,
        dtype=SampleDType.INT16,
    )

    SoundDeviceBackend().validate_stream_opening(device, config)

    input_stream_factory.assert_called_once_with(
        samplerate=48_000,
        blocksize=0,
        device=0,
        channels=2,
        dtype="int16",
    )
    output_stream_factory.assert_not_called()
    duplex_stream_factory.assert_not_called()
    stream.start.assert_not_called()
    stream.close.assert_called_once_with(ignore_errors=True)


def test_opens_and_closes_output_stream(monkeypatch: MonkeyPatch) -> None:
    stream = Mock()
    input_stream_factory = Mock()
    output_stream_factory = Mock(return_value=stream)
    duplex_stream_factory = Mock()

    monkeypatch.setattr(sd, "RawInputStream", input_stream_factory)
    monkeypatch.setattr(sd, "RawOutputStream", output_stream_factory)
    monkeypatch.setattr(sd, "RawStream", duplex_stream_factory)

    device = create_test_device()
    config = StreamConfig(
        sample_rate=44_100,
        input_channels=0,
        output_channels=2,
        block_size=256,
        dtype=SampleDType.FLOAT32,
    )

    SoundDeviceBackend().validate_stream_opening(device, config)

    output_stream_factory.assert_called_once_with(
        samplerate=44_100,
        blocksize=256,
        device=0,
        channels=2,
        dtype="float32",
    )
    input_stream_factory.assert_not_called()
    duplex_stream_factory.assert_not_called()
    stream.start.assert_not_called()
    stream.close.assert_called_once_with(ignore_errors=True)


def test_opens_and_closes_duplex_stream(monkeypatch: MonkeyPatch) -> None:
    stream = Mock()
    input_stream_factory = Mock()
    output_stream_factory = Mock()
    duplex_stream_factory = Mock(return_value=stream)

    monkeypatch.setattr(sd, "RawInputStream", input_stream_factory)
    monkeypatch.setattr(sd, "RawOutputStream", output_stream_factory)
    monkeypatch.setattr(sd, "RawStream", duplex_stream_factory)

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
        block_size=128,
        dtype=SampleDType.FLOAT32,
    )

    SoundDeviceBackend().validate_stream_opening(device, config)

    duplex_stream_factory.assert_called_once_with(
        samplerate=48_000,
        blocksize=128,
        device=(0, 0),
        channels=(2, 2),
        dtype=("float32", "float32"),
    )
    input_stream_factory.assert_not_called()
    output_stream_factory.assert_not_called()
    stream.start.assert_not_called()
    stream.close.assert_called_once_with(ignore_errors=True)


def test_translates_stream_open_error(monkeypatch: MonkeyPatch) -> None:
    input_stream_factory = Mock(
        side_effect=sd.PortAudioError("Device unavailable"),
    )

    monkeypatch.setattr(sd, "RawInputStream", input_stream_factory)

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        StreamOpenError,
        match="Could not open input stream for device index 0",
    ):
        SoundDeviceBackend().validate_stream_opening(device, config)


def test_records_requested_number_of_frames(monkeypatch: MonkeyPatch) -> None:
    stream = Mock()
    stream.read_available = 3
    stream.read.return_value = (
        np.array(
            [
                [0.1, -0.1],
                [0.2, -0.2],
                [0.3, -0.3],
            ],
            dtype=np.float32,
        ),
        False,
    )

    stream_factory = Mock(return_value=stream)

    monkeypatch.setattr(
        sd,
        "InputStream",
        stream_factory,
    )

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=0,
        block_size=128,
        dtype=SampleDType.FLOAT32,
    )

    result = SoundDeviceBackend().record(
        device,
        config,
        frame_count=3,
        timeout_seconds=5.0,
    )

    stream_factory.assert_called_once_with(
        samplerate=48_000,
        blocksize=128,
        device=0,
        channels=2,
        dtype="float32",
    )
    stream.start.assert_called_once_with()
    stream.read.assert_called_once_with(3)
    stream.stop.assert_called_once_with()
    stream.abort.assert_not_called()
    stream.close.assert_called_once_with(ignore_errors=True)

    assert result.frame_count == 3
    assert result.channel_count == 2
    assert result.sample_rate == 48_000

    np.testing.assert_array_equal(
        result.samples,
        stream.read.return_value[0],
    )


def test_recording_accumulates_multiple_reads(monkeypatch: MonkeyPatch) -> None:
    stream = Mock()

    type(stream).read_available = PropertyMock(
        side_effect=[2, 2],
    )

    stream.read.side_effect = [
        (
            np.zeros(
                (2, 2),
                dtype=np.float32,
            ),
            False,
        ),
        (
            np.ones(
                (1, 2),
                dtype=np.float32,
            ),
            False,
        ),
    ]

    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(return_value=stream),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = SoundDeviceBackend().record(
        create_test_device(),
        config,
        frame_count=3,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 3

    assert stream.read.call_args_list == [
        ((2,),),
        ((1,),),
    ]


def test_recording_rejects_stream_without_input_channels() -> None:
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="no input channels",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_zero_frame_recording_returns_empty_buffer(monkeypatch: MonkeyPatch) -> None:
    stream_factory = Mock()

    monkeypatch.setattr(
        sd,
        "InputStream",
        stream_factory,
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = SoundDeviceBackend().record(
        create_test_device(),
        config,
        frame_count=0,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 0
    assert result.channel_count == 2

    stream_factory.assert_not_called()


def test_recording_translates_stream_open_error(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(
            side_effect=sd.PortAudioError(
                "Device unavailable",
            ),
        ),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="Could not record from device index 0",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_recording_closes_stream_after_portaudio_error(monkeypatch: MonkeyPatch) -> None:
    stream = Mock()
    stream.read_available = 3
    stream.read.side_effect = sd.PortAudioError(
        "Input failure",
    )

    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(return_value=stream),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(AudioBackendError):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(ignore_errors=True)
    stream.close.assert_called_once_with(ignore_errors=True)


def test_recording_rejects_input_overflow(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.read_available = 3
    stream.read.return_value = (
        np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        True,
    )

    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(return_value=stream),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="Input overflow",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(ignore_errors=True)
    stream.close.assert_called_once_with(ignore_errors=True)


def test_recording_timeout_aborts_and_closes_stream(monkeypatch: MonkeyPatch) -> None:
    stream = Mock()
    stream.read_available = 0

    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(return_value=stream),
    )

    times = iter((0.0, 0.0, 6.0))

    monkeypatch.setattr(
        time,
        "monotonic",
        lambda: next(times),
    )
    monkeypatch.setattr(
        time,
        "sleep",
        lambda _: None,
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="Recording timed out",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )

    stream.stop.assert_not_called()
    stream.abort.assert_called_once_with(ignore_errors=True)
    stream.close.assert_called_once_with(ignore_errors=True)


def test_plays_audio_buffer(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 3
    stream.write.return_value = False

    stream_factory = Mock(return_value=stream)

    monkeypatch.setattr(
        sd,
        "OutputStream",
        stream_factory,
    )

    audio = AudioBuffer(
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
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=0,
        output_channels=2,
        block_size=128,
        dtype=SampleDType.FLOAT32,
    )

    SoundDeviceBackend().playback(
        create_test_device(),
        config,
        audio,
        timeout_seconds=5.0,
    )

    stream_factory.assert_called_once_with(
        samplerate=48_000,
        blocksize=128,
        device=0,
        channels=2,
        dtype="float32",
    )

    stream.start.assert_called_once_with()
    stream.write.assert_called_once()
    stream.stop.assert_called_once_with()
    stream.abort.assert_not_called()
    stream.close.assert_called_once_with(ignore_errors=True)

    written = stream.write.call_args.args[0]

    np.testing.assert_array_equal(
        written,
        audio.samples,
    )


def test_playback_writes_multiple_chunks(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    type(stream).write_available = PropertyMock(
        side_effect=[2, 2],
    )

    stream.write.return_value = False

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    audio = AudioBuffer(
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
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    SoundDeviceBackend().playback(
        create_test_device(),
        config,
        audio,
        timeout_seconds=5.0,
    )

    assert stream.write.call_count == 2

    first_chunk = stream.write.call_args_list[0].args[0]
    second_chunk = stream.write.call_args_list[1].args[0]

    np.testing.assert_array_equal(
        first_chunk,
        audio.samples[:2],
    )
    np.testing.assert_array_equal(
        second_chunk,
        audio.samples[2:],
    )


def test_playback_rejects_stream_without_output_channels() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="no output channels",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_playback_rejects_sample_rate_mismatch() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="sample rate",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_playback_rejects_channel_mismatch() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="channel count",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_zero_frame_playback_does_not_open_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream_factory = Mock()

    monkeypatch.setattr(
        sd,
        "OutputStream",
        stream_factory,
    )

    audio = AudioBuffer(
        samples=np.empty(
            (0, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    SoundDeviceBackend().playback(
        create_test_device(),
        config,
        audio,
        timeout_seconds=5.0,
    )

    stream_factory.assert_not_called()


def test_playback_translates_stream_open_error(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(
            side_effect=sd.PortAudioError(
                "Device unavailable",
            ),
        ),
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="Could not play through device index 0",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_playback_aborts_and_closes_after_portaudio_error(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 3
    stream.write.side_effect = sd.PortAudioError(
        "Output failure",
    )

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(AudioBackendError):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(ignore_errors=True)
    stream.close.assert_called_once_with(ignore_errors=True)


def test_playback_rejects_output_underflow(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 3
    stream.write.return_value = True

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="Output underflow",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )

    stream.stop.assert_not_called()
    stream.abort.assert_called_once_with(ignore_errors=True)
    stream.close.assert_called_once_with(ignore_errors=True)


def test_playback_timeout_aborts_and_closes_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 0

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    times = iter((0.0, 0.0, 6.0))

    monkeypatch.setattr(
        time,
        "monotonic",
        lambda: next(times),
    )
    monkeypatch.setattr(
        time,
        "sleep",
        lambda _: None,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="Playback timed out",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )

    stream.write.assert_not_called()
    stream.stop.assert_not_called()
    stream.abort.assert_called_once_with(ignore_errors=True)
    stream.close.assert_called_once_with(ignore_errors=True)
