"""Pure transformations for preparing audio test signals."""

import math

import numpy as np

from audio_hw_framework.audio import AudioBuffer


def route_mono_signal(
    audio: AudioBuffer,
    *,
    output_channel: int,
    output_channels: int,
) -> AudioBuffer:
    """Route a mono signal to one channel of a multichannel output buffer."""

    if audio.channel_count != 1:
        raise ValueError("Signal routing requires mono input audio")

    if output_channels <= 0:
        raise ValueError("output_channels must be greater than 0")

    if output_channel < 0:
        raise ValueError("output_channel must be greater than or equal to 0")

    if output_channel >= output_channels:
        raise ValueError("output_channel must be less than output_channels")

    samples = np.zeros(
        (audio.frame_count, output_channels),
        dtype=audio.samples.dtype,
    )

    samples[:, output_channel] = audio.samples[:, 0]

    return AudioBuffer(
        samples=samples,
        sample_rate=audio.sample_rate,
    )


def pad_signal(
    audio: AudioBuffer,
    *,
    padding_seconds: float,
) -> AudioBuffer:
    """Add equal-duration silence before and after an audio signal."""

    if not math.isfinite(padding_seconds):
        raise ValueError("padding_seconds must be finite")

    if padding_seconds < 0:
        raise ValueError("padding_seconds must be greater than or equal to 0")

    padding_frames = round(
        padding_seconds * audio.sample_rate,
    )

    samples = np.zeros(
        (
            audio.frame_count + (2 * padding_frames),
            audio.channel_count,
        ),
        dtype=audio.samples.dtype,
    )

    start_frame = padding_frames
    end_frame = start_frame + audio.frame_count

    samples[start_frame:end_frame] = audio.samples

    return AudioBuffer(
        samples=samples,
        sample_rate=audio.sample_rate,
    )
