"""DC offset sample-domain audio analysis."""

import numpy as np

from audio_hw_framework.analysis.models import MetricAnalysisResult
from audio_hw_framework.audio import AudioBuffer


def analyse_dc_offset(audio: AudioBuffer) -> MetricAnalysisResult:
    """Calculate overall and per-channel DC offset."""

    if audio.frame_count == 0:
        raise ValueError(
            "DC offset analysis requires at least one audio frame",
        )

    samples = np.asarray(
        audio.samples,
        dtype=np.float64,
    )

    per_channel_values = np.mean(
        samples,
        axis=0,
    )

    overall_value = np.mean(
        samples,
    )

    return MetricAnalysisResult(
        overall=float(overall_value),
        per_channel=tuple(float(value) for value in per_channel_values),
    )
