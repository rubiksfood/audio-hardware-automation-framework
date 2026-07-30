import pytest
from pydantic import ValidationError

from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceDirection,
    SampleDType,
    StreamConfig,
)


def test_duplex_device_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.DUPLEX


def test_input_device_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Microphone",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.INPUT


def test_output_device_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Speakers",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=0,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.OUTPUT


def test_device_with_no_channels_has_none_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Unavailable Device",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=0,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.NONE


def test_stream_config_uses_float32_by_default() -> None:
    config = StreamConfig()

    assert config.dtype is SampleDType.FLOAT32


def test_stream_config_accepts_supported_dtypes() -> None:
    supported_dtypes = (
        SampleDType.FLOAT32,
        SampleDType.INT32,
        SampleDType.INT16,
        SampleDType.INT8,
        SampleDType.UINT8,
    )

    for dtype in supported_dtypes:
        config = StreamConfig(dtype=dtype)

        assert config.dtype is dtype


def test_stream_config_accepts_supported_dtype_string() -> None:
    config = StreamConfig.model_validate({"dtype": "int16"})

    assert config.dtype is SampleDType.INT16


def test_stream_config_rejects_unsupported_dtype() -> None:
    with pytest.raises(ValidationError):
        StreamConfig.model_validate({"dtype": "float64"})


def test_stream_config_accepts_positive_block_size() -> None:
    config = StreamConfig(block_size=256)

    assert config.block_size == 256


def test_stream_config_rejects_zero_block_size() -> None:
    with pytest.raises(ValidationError):
        StreamConfig(block_size=0)


def test_stream_config_rejects_negative_block_size() -> None:
    with pytest.raises(ValidationError):
        StreamConfig(block_size=-1)


def test_stream_config_accepts_input_only_stream() -> None:
    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    assert config.input_channels == 2
    assert config.output_channels == 0


def test_stream_config_accepts_output_only_stream() -> None:
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    assert config.input_channels == 0
    assert config.output_channels == 2


def test_stream_config_accepts_duplex_stream() -> None:
    config = StreamConfig(
        input_channels=2,
        output_channels=2,
    )

    assert config.input_channels == 2
    assert config.output_channels == 2


def test_stream_config_rejects_stream_with_no_active_channels() -> None:
    with pytest.raises(
        ValidationError,
        match="At least one of input_channels or output_channels",
    ):
        StreamConfig(
            input_channels=0,
            output_channels=0,
        )
