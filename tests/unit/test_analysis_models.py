from audio_hw_framework.analysis import (
    DetectionAnalysisResult,
    MetricAnalysisResult,
)


def test_metric_analysis_result_exposes_values() -> None:
    result = MetricAnalysisResult(
        overall=0.5,
        per_channel=(0.25, 0.75),
    )

    assert result.overall == 0.5
    assert result.per_channel == (0.25, 0.75)


def test_detection_analysis_result_exposes_values() -> None:
    result = DetectionAnalysisResult(
        detected=True,
        per_channel=(False, True),
    )

    assert result.detected is True
    assert result.per_channel == (False, True)
