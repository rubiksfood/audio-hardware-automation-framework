"""Typed models for deterministic audio signal generation."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class SignalConfig(BaseModel):
    """Common configuration shared by generated audio signals."""

    sample_rate: int = Field(default=48_000, gt=0)
    duration_seconds: float = Field(
        default=1.0,
        gt=0,
        allow_inf_nan=False,
    )
    channel_count: int = Field(default=1, gt=0)


class SineWaveConfig(SignalConfig):
    """Configuration for a deterministic sine-wave signal."""

    frequency_hz: float = Field(
        default=1_000.0,
        gt=0,
        allow_inf_nan=False,
    )
    amplitude: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )

    @model_validator(mode="after")
    def validate_frequency_below_nyquist(self) -> Self:
        """Require sine frequency to remain below the Nyquist frequency."""

        nyquist_frequency = self.sample_rate / 2

        if self.frequency_hz >= nyquist_frequency:
            raise ValueError(
                "frequency_hz must be less than half the sample rate",
            )

        return self


class SilenceConfig(SignalConfig):
    """Configuration for a deterministic silence signal."""
