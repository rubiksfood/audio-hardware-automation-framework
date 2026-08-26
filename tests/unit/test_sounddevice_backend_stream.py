"""Tests for sounddevice backend stream validation."""

from unittest.mock import Mock

import pytest
import sounddevice as sd
from pytest import MonkeyPatch

from audio_hw_framework.backend.base import (
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.device.models import SampleDType, StreamConfig
from tests.unit.sounddevice_backend_helpers import create_test_device


def test_validates_input_stream_settings(
    monkeypatch: MonkeyPatch,
) -> None:
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

    SoundDeviceBackend().validate_stream_capability(
        device,
        config,
    )

    input_check.assert_called_once_with(
        device=0,
        channels=2,
        samplerate=48_000,
        dtype="int16",
    )
    output_check.assert_not_called()


def test_validates_output_stream_settings(
    monkeypatch: MonkeyPatch,
) -> None:
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

    SoundDeviceBackend().validate_stream_capability(
        device,
        config,
    )

    input_check.assert_not_called()
    output_check.assert_called_once_with(
        device=0,
        channels=2,
        samplerate=44_100,
        dtype="float32",
    )


def test_validates_duplex_stream_settings(
    monkeypatch: MonkeyPatch,
) -> None:
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

    SoundDeviceBackend().validate_stream_capability(
        device,
        config,
    )

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


def test_translates_input_capability_error(
    monkeypatch: MonkeyPatch,
) -> None:
    input_check = Mock(
        side_effect=sd.PortAudioError(
            "Invalid sample rate",
        ),
    )
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
        SoundDeviceBackend().validate_stream_capability(
            device,
            config,
        )

    output_check.assert_not_called()


def test_translates_output_capability_error(
    monkeypatch: MonkeyPatch,
) -> None:
    input_check = Mock()
    output_check = Mock(
        side_effect=sd.PortAudioError(
            "Invalid number of channels",
        ),
    )

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
        SoundDeviceBackend().validate_stream_capability(
            device,
            config,
        )

    input_check.assert_not_called()


def test_duplex_validation_stops_after_input_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    input_check = Mock(
        side_effect=sd.PortAudioError(
            "Input configuration rejected",
        ),
    )
    output_check = Mock()

    monkeypatch.setattr(sd, "check_input_settings", input_check)
    monkeypatch.setattr(sd, "check_output_settings", output_check)

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )

    with pytest.raises(StreamCapabilityError):
        SoundDeviceBackend().validate_stream_capability(
            device,
            config,
        )

    output_check.assert_not_called()


def test_opens_and_closes_input_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    input_stream_factory = Mock(return_value=stream)
    output_stream_factory = Mock()
    duplex_stream_factory = Mock()

    monkeypatch.setattr(
        sd,
        "RawInputStream",
        input_stream_factory,
    )
    monkeypatch.setattr(
        sd,
        "RawOutputStream",
        output_stream_factory,
    )
    monkeypatch.setattr(
        sd,
        "RawStream",
        duplex_stream_factory,
    )

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=0,
        block_size=None,
        dtype=SampleDType.INT16,
    )

    SoundDeviceBackend().validate_stream_opening(
        device,
        config,
    )

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
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_opens_and_closes_output_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    input_stream_factory = Mock()
    output_stream_factory = Mock(return_value=stream)
    duplex_stream_factory = Mock()

    monkeypatch.setattr(
        sd,
        "RawInputStream",
        input_stream_factory,
    )
    monkeypatch.setattr(
        sd,
        "RawOutputStream",
        output_stream_factory,
    )
    monkeypatch.setattr(
        sd,
        "RawStream",
        duplex_stream_factory,
    )

    device = create_test_device()
    config = StreamConfig(
        sample_rate=44_100,
        input_channels=0,
        output_channels=2,
        block_size=256,
        dtype=SampleDType.FLOAT32,
    )

    SoundDeviceBackend().validate_stream_opening(
        device,
        config,
    )

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
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_opens_and_closes_duplex_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    input_stream_factory = Mock()
    output_stream_factory = Mock()
    duplex_stream_factory = Mock(return_value=stream)

    monkeypatch.setattr(
        sd,
        "RawInputStream",
        input_stream_factory,
    )
    monkeypatch.setattr(
        sd,
        "RawOutputStream",
        output_stream_factory,
    )
    monkeypatch.setattr(
        sd,
        "RawStream",
        duplex_stream_factory,
    )

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=2,
        block_size=128,
        dtype=SampleDType.FLOAT32,
    )

    SoundDeviceBackend().validate_stream_opening(
        device,
        config,
    )

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
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_translates_stream_open_error(
    monkeypatch: MonkeyPatch,
) -> None:
    input_stream_factory = Mock(
        side_effect=sd.PortAudioError(
            "Device unavailable",
        ),
    )

    monkeypatch.setattr(
        sd,
        "RawInputStream",
        input_stream_factory,
    )

    device = create_test_device()
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        StreamOpenError,
        match="Could not open input stream for device index 0",
    ):
        SoundDeviceBackend().validate_stream_opening(
            device,
            config,
        )
