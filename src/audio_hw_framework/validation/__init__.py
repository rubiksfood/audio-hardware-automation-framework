"""Configuration-driven audio validation services."""

from audio_hw_framework.validation.service import (
    StreamValidationResult,
    validate_configured_stream,
)

__all__ = [
    "StreamValidationResult",
    "validate_configured_stream",
]
