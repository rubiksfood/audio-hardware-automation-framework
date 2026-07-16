"""Typed models representing audio host APIs, devices and stream settings."""

from enum import StrEnum

from pydantic import BaseModel, Field


class DeviceDirection(StrEnum):
    """Direction in which an audio device can transfer audio."""

    INPUT = "input"
    OUTPUT = "output"
    DUPLEX = "duplex"
    NONE = "none"


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

    block_size: int | None = None

    dtype: str = "float32"


class FrameworkConfig(BaseModel):
    """Root configuration."""

    device: DeviceMatchConfig
    stream: StreamConfig
