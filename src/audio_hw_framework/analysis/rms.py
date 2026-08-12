"""RMS sample-domain audio analysis."""

import numpy as np

from audio_hw_framework.analysis._samples import as_finite_float64_samples
from audio_hw_framework.analysis.models import MetricAnalysisResult
from audio_hw_framework.audio import AudioBuffer


def analyse_rms(audio: AudioBuffer) -> MetricAnalysisResult:
    """Calculate overall and per-channel RMS levels."""

    if audio.frame_count == 0:
        raise ValueError(
            "RMS analysis requires at least one audio frame",
        )

    samples = as_finite_float64_samples(audio)

    per_channel_values = np.sqrt(
        np.mean(
            np.square(samples),
            axis=0,
        ),
    )

    overall_value = np.sqrt(
        np.mean(
            np.square(samples),
        ),
    )

    return MetricAnalysisResult(
        overall=float(overall_value),
        per_channel=tuple(float(value) for value in per_channel_values),
    )
