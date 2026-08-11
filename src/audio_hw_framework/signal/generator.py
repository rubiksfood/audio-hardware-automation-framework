"""Deterministic audio signal generation."""

import numpy as np
from numpy.typing import NDArray

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.signal.models import (
    SignalConfig,
    SilenceConfig,
    SineWaveConfig,
)


def generate_sine_wave(config: SineWaveConfig) -> AudioBuffer:
    """Generate a deterministic sine-wave audio buffer."""

    frame_count = _calculate_frame_count(config)

    frame_indexes: NDArray[np.float64] = np.arange(
        frame_count,
        dtype=np.float64,
    )

    phase = 2.0 * np.pi * config.frequency_hz * frame_indexes / config.sample_rate

    mono_samples: NDArray[np.float32] = np.asarray(
        config.amplitude * np.sin(phase),
        dtype=np.float32,
    )

    samples: NDArray[np.float32] = np.repeat(
        mono_samples[:, np.newaxis],
        config.channel_count,
        axis=1,
    )

    return AudioBuffer(
        samples=samples,
        sample_rate=config.sample_rate,
    )


def generate_silence(config: SilenceConfig) -> AudioBuffer:
    """Generate a deterministic silence audio buffer."""

    frame_count = _calculate_frame_count(config)

    samples: NDArray[np.float32] = np.zeros(
        (frame_count, config.channel_count),
        dtype=np.float32,
    )

    return AudioBuffer(
        samples=samples,
        sample_rate=config.sample_rate,
    )


def _calculate_frame_count(config: SignalConfig) -> int:
    """Convert configured signal duration into an audio frame count."""

    frame_count = round(
        config.duration_seconds * config.sample_rate,
    )

    if frame_count <= 0:
        raise ValueError(
            "signal duration produces no audio frames",
        )

    return frame_count
