import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.configuration.thresholds import AudioMetricThresholds
from audio_hw_framework.validation import validate_audio_metrics


def test_audio_metric_validation_passes_when_thresholds_are_satisfied() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25, 0.25],
                [-0.25, -0.25],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(
            minimum_rms=0.1,
            maximum_rms=0.5,
            maximum_peak=0.5,
            maximum_abs_dc_offset=0.01,
        ),
    )

    assert result.passed is True
    assert result.failures == ()


def test_audio_metric_validation_reports_minimum_rms_failure() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25, 0.01],
                [-0.25, -0.01],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(
            minimum_rms=0.1,
            fail_on_silence=False,
        ),
    )

    assert result.passed is False
    assert len(result.failures) == 1

    failure = result.failures[0]

    assert failure.metric == "rms"
    assert failure.channel == 1
    assert failure.threshold == 0.1
    assert failure.reason == "RMS level is below the configured minimum"


def test_audio_metric_validation_reports_maximum_rms_failure() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.75],
                [-0.75],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(
            maximum_rms=0.5,
        ),
    )

    assert result.passed is False
    assert result.failures[0].metric == "rms"


def test_audio_metric_validation_reports_peak_failure() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25],
                [0.75],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(
            maximum_peak=0.5,
        ),
    )

    assert result.passed is False
    assert result.failures[0].metric == "peak"


def test_audio_metric_validation_reports_absolute_dc_offset_failure() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [-0.2],
                [-0.2],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(
            maximum_abs_dc_offset=0.1,
        ),
    )

    assert result.passed is False
    assert result.failures[0].metric == "dc_offset"
    assert result.failures[0].actual < 0


def test_audio_metric_validation_reports_silence_failure() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(),
    )

    assert result.passed is False
    assert result.failures[0].metric == "silence"
    assert result.failures[0].channel == 0


def test_audio_metric_validation_can_allow_silence() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(
            fail_on_silence=False,
        ),
    )

    assert result.passed is True


def test_audio_metric_validation_reports_clipping_failure() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5],
                [1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(),
    )

    assert result.passed is False
    assert result.failures[0].metric == "clipping"


def test_audio_metric_validation_can_allow_clipping() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5],
                [1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = validate_audio_metrics(
        audio,
        AudioMetricThresholds(
            fail_on_clipping=False,
        ),
    )

    assert result.passed is True


def test_audio_metric_validation_rejects_non_finite_samples() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25],
                [np.nan],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Audio analysis requires finite sample values",
    ):
        validate_audio_metrics(
            audio,
            AudioMetricThresholds(),
        )
