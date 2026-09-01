"""Typed models representing audio host APIs, devices and stream settings."""

from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, model_validator

from audio_hw_framework.configuration.loopback import LoopbackValidationConfig
from audio_hw_framework.configuration.thresholds import AudioMetricThresholds


class DeviceDirection(StrEnum):
    """Direction in which an audio device can transfer audio."""

    INPUT = "input"
    OUTPUT = "output"
    DUPLEX = "duplex"
    NONE = "none"


class SampleDType(StrEnum):
    """Sample formats supported by standard sounddevice streams."""

    FLOAT32 = "float32"
    INT32 = "int32"
    INT16 = "int16"
    INT8 = "int8"
    UINT8 = "uint8"


class AudioDevice(BaseModel):
    """Framework-owned representation of an audio device."""

    index: int = Field(ge=0)
    name: str

    host_api_index: int = Field(ge=0)
    host_api_name: str

    max_input_channels: int = Field(ge=0)
    max_output_channels: int = Field(ge=0)
    default_sample_rate: float = Field(gt=0)

    is_default_input: bool = False
    is_default_output: bool = False

    @property
    def direction(self) -> DeviceDirection:
        if self.max_input_channels > 0 and self.max_output_channels > 0:
            return DeviceDirection.DUPLEX

        if self.max_input_channels > 0:
            return DeviceDirection.INPUT

        if self.max_output_channels > 0:
            return DeviceDirection.OUTPUT

        return DeviceDirection.NONE


class DeviceMatchConfig(BaseModel):
    """Tells framework what device is connected."""

    exact_name: str | None = None
    name_contains: str | None = None
    host_api_contains: str | None = None

    minimum_input_channels: int = Field(default=0, ge=0)
    minimum_output_channels: int = Field(default=0, ge=0)


class StreamConfig(BaseModel):
    """Returns the configuration settings in a single stream."""

    sample_rate: int = Field(default=48000, gt=0)
    input_channels: int = Field(default=2, ge=0)
    output_channels: int = Field(default=2, ge=0)
    block_size: int | None = Field(default=None, gt=0)
    dtype: SampleDType = SampleDType.FLOAT32

    @model_validator(mode="after")
    def validate_active_direction(self) -> Self:
        """Require at least one active stream direction."""

        if self.input_channels == 0 and self.output_channels == 0:
            raise ValueError(
                "At least one of input_channels or output_channels must be greater than 0"
            )

        return self


class AudioExecutionConfig(BaseModel):
    """Settings controlling finite audio execution."""

    duration_seconds: float = Field(default=1.0, gt=0)
    timeout_seconds: float = Field(default=5.0, gt=0)
    output_file: Path | None = None


class FrameworkConfig(BaseModel):
    """Root configuration."""

    device: DeviceMatchConfig
    input_device: DeviceMatchConfig | None = None
    output_device: DeviceMatchConfig | None = None

    stream: StreamConfig
    execution: AudioExecutionConfig = Field(
        default_factory=AudioExecutionConfig,
    )
    thresholds: AudioMetricThresholds = Field(
        default_factory=AudioMetricThresholds,
    )
    loopback: LoopbackValidationConfig | None = None

    @model_validator(mode="after")
    def validate_loopback_settings(self) -> Self:
        """Validate loopback settings against the configured stream."""

        if self.loopback is None:
            return self

        if self.stream.input_channels == 0 or self.stream.output_channels == 0:
            raise ValueError(
                "Loopback validation requires a duplex stream",
            )

        if self.loopback.input_channel >= self.stream.input_channels:
            raise ValueError(
                "loopback.input_channel must be less than stream.input_channels",
            )

        if self.loopback.output_channel >= self.stream.output_channels:
            raise ValueError(
                "loopback.output_channel must be less than stream.output_channels",
            )

        nyquist_frequency = self.stream.sample_rate / 2

        if self.loopback.frequency_hz >= nyquist_frequency:
            raise ValueError(
                "loopback.frequency_hz must be less than half the stream sample rate",
            )

        return self
