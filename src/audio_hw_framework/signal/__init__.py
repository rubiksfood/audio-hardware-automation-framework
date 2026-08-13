"""Deterministic audio signal generation."""

from audio_hw_framework.signal.generator import (
    generate_silence,
    generate_sine_wave,
)
from audio_hw_framework.signal.models import (
    SignalConfig,
    SilenceConfig,
    SineWaveConfig,
)

__all__ = [
    "SignalConfig",
    "SilenceConfig",
    "SineWaveConfig",
    "generate_silence",
    "generate_sine_wave",
]
