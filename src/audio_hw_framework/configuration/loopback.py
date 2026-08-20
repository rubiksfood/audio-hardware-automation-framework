"""Configuration models for end-to-end loopback validation."""

from pydantic import BaseModel, Field


class LoopbackValidationConfig(BaseModel):
    """Settings controlling end-to-end loopback validation."""

    output_channel: int = Field(
        default=0,
        ge=0,
    )
    input_channel: int = Field(
        default=0,
        ge=0,
    )

    signal_duration_seconds: float = Field(
        default=1.0,
        gt=0.0,
        allow_inf_nan=False,
    )
    frequency_hz: float = Field(
        default=1_000.0,
        gt=0.0,
        allow_inf_nan=False,
    )
    amplitude: float = Field(
        default=0.25,
        gt=0.0,
        le=1.0,
        allow_inf_nan=False,
    )

    frequency_tolerance_hz: float = Field(
        default=5.0,
        ge=0.0,
        allow_inf_nan=False,
    )
    padding_seconds: float = Field(
        default=0.1,
        ge=0.0,
        allow_inf_nan=False,
    )
