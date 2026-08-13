"""Configuration models for sample-domain metric thresholds."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class AudioMetricThresholds(BaseModel):
    """Thresholds controlling sample-domain audio validation."""

    minimum_rms: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    maximum_rms: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    maximum_peak: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    maximum_abs_dc_offset: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )

    silence_threshold: float = Field(
        default=1e-4,
        ge=0.0,
        allow_inf_nan=False,
    )
    clipping_threshold: float = Field(
        default=1.0,
        gt=0.0,
        allow_inf_nan=False,
    )

    fail_on_silence: bool = True
    fail_on_clipping: bool = True

    @model_validator(mode="after")
    def validate_rms_range(self) -> Self:
        """Require minimum RMS not to exceed maximum RMS."""

        if (
            self.minimum_rms is not None
            and self.maximum_rms is not None
            and self.minimum_rms > self.maximum_rms
        ):
            raise ValueError(
                "minimum_rms must be less than or equal to maximum_rms",
            )

        return self
