from pathlib import Path

import pytest
from pydantic import ValidationError

from audio_hw_framework.configuration.thresholds import AudioMetricThresholds
from audio_hw_framework.device.models import (
    AudioDevice,
    AudioExecutionConfig,
    DeviceDirection,
    DeviceMatchConfig,
    FrameworkConfig,
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


def test_audio_execution_config_uses_defaults() -> None:
    config = AudioExecutionConfig()

    assert config.duration_seconds == 1.0
    assert config.timeout_seconds == 5.0
    assert config.output_file is None


def test_audio_execution_config_accepts_positive_duration() -> None:
    config = AudioExecutionConfig(duration_seconds=2.5)

    assert config.duration_seconds == 2.5


def test_audio_execution_config_rejects_zero_duration() -> None:
    with pytest.raises(ValidationError):
        AudioExecutionConfig(duration_seconds=0)


def test_audio_execution_config_rejects_negative_duration() -> None:
    with pytest.raises(ValidationError):
        AudioExecutionConfig(duration_seconds=-1)


def test_audio_execution_config_accepts_positive_timeout() -> None:
    config = AudioExecutionConfig(timeout_seconds=10.0)

    assert config.timeout_seconds == 10.0


def test_audio_execution_config_rejects_zero_timeout() -> None:
    with pytest.raises(ValidationError):
        AudioExecutionConfig(timeout_seconds=0)


def test_audio_execution_config_rejects_negative_timeout() -> None:
    with pytest.raises(ValidationError):
        AudioExecutionConfig(timeout_seconds=-1)


def test_audio_execution_config_accepts_output_file() -> None:
    config = AudioExecutionConfig(
        output_file=Path("recordings/test.wav"),
    )

    assert config.output_file == Path("recordings/test.wav")


def test_framework_config_uses_default_execution_config() -> None:
    config = FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
        ),
        stream=StreamConfig(),
    )

    assert config.execution == AudioExecutionConfig()


def test_audio_metric_thresholds_use_defaults() -> None:
    thresholds = AudioMetricThresholds()

    assert thresholds.minimum_rms is None
    assert thresholds.maximum_rms is None
    assert thresholds.maximum_peak is None
    assert thresholds.maximum_abs_dc_offset is None
    assert thresholds.silence_threshold == 1e-4
    assert thresholds.clipping_threshold == 1.0
    assert thresholds.fail_on_silence is True
    assert thresholds.fail_on_clipping is True


def test_audio_metric_thresholds_accept_valid_values() -> None:
    thresholds = AudioMetricThresholds(
        minimum_rms=0.1,
        maximum_rms=0.8,
        maximum_peak=0.9,
        maximum_abs_dc_offset=0.01,
        silence_threshold=0.001,
        clipping_threshold=0.95,
    )

    assert thresholds.minimum_rms == 0.1
    assert thresholds.maximum_rms == 0.8
    assert thresholds.maximum_peak == 0.9
    assert thresholds.maximum_abs_dc_offset == 0.01
    assert thresholds.silence_threshold == 0.001
    assert thresholds.clipping_threshold == 0.95


def test_audio_metric_thresholds_reject_invalid_rms_range() -> None:
    with pytest.raises(
        ValidationError,
        match="minimum_rms must be less than or equal to maximum_rms",
    ):
        AudioMetricThresholds(
            minimum_rms=0.8,
            maximum_rms=0.2,
        )


def test_audio_metric_thresholds_reject_negative_silence_threshold() -> None:
    with pytest.raises(ValidationError):
        AudioMetricThresholds(
            silence_threshold=-0.1,
        )


def test_audio_metric_thresholds_reject_non_positive_clipping_threshold() -> None:
    with pytest.raises(ValidationError):
        AudioMetricThresholds(
            clipping_threshold=0.0,
        )


def test_framework_config_uses_default_metric_thresholds() -> None:
    config = FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
        ),
        stream=StreamConfig(),
    )

    assert config.thresholds == AudioMetricThresholds()
