"""Tests for loopback validation evidence reporting."""

import json
from pathlib import Path

import numpy as np
import pytest

from audio_hw_framework.analysis import (
    DetectionAnalysisResult,
    MetricAnalysisResult,
)
from audio_hw_framework.audio import (
    AudioBuffer,
    read_wav,
)
from audio_hw_framework.backend.base import BackendInfo
from audio_hw_framework.device.models import (
    AudioDevice,
    StreamConfig,
)
from audio_hw_framework.reporting import (
    LoopbackReportingError,
    build_loopback_report,
    save_loopback_evidence,
)
from audio_hw_framework.validation import (
    AudioMetricValidationResult,
    LoopbackFrequencyResult,
    LoopbackValidationFailure,
    LoopbackValidationResult,
)


def create_audio(
    *,
    channels: int,
    frames: int = 8,
) -> AudioBuffer:
    """Create deterministic audio for reporting tests."""

    return AudioBuffer(
        samples=np.zeros(
            (frames, channels),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )


def create_result(
    *,
    frequency_passed: bool = True,
) -> LoopbackValidationResult:
    """Create a generic loopback result for reporting tests."""

    measured_frequency = 1_000.0 if frequency_passed else 1_020.0

    failures: tuple[
        LoopbackValidationFailure,
        ...,
    ]

    if frequency_passed:
        failures = ()
    else:
        failures = (
            LoopbackValidationFailure(
                metric="frequency",
                channel=1,
                actual=measured_frequency,
                expected=1_000.0,
                threshold=5.0,
                reason=("Captured frequency is outside the configured tolerance"),
            ),
        )

    return LoopbackValidationResult(
        backend=BackendInfo(
            name="test-backend",
            library="test-library",
            library_version="1.0",
        ),
        device=AudioDevice(
            index=3,
            name="Test Duplex Device",
            host_api_index=2,
            host_api_name="Test Host API",
            max_input_channels=2,
            max_output_channels=2,
            default_sample_rate=44_100,
        ),
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=2,
            output_channels=2,
            block_size=128,
        ),
        output_channel=0,
        input_channel=1,
        playback_audio=create_audio(
            channels=2,
            frames=10,
        ),
        captured_audio=create_audio(
            channels=2,
            frames=10,
        ),
        analysed_audio=create_audio(
            channels=1,
            frames=8,
        ),
        frequency=LoopbackFrequencyResult(
            expected_hz=1_000.0,
            measured_hz=measured_frequency,
            tolerance_hz=5.0,
        ),
        metrics=AudioMetricValidationResult(
            rms=MetricAnalysisResult(
                overall=0.175,
                per_channel=(0.175,),
            ),
            peak=MetricAnalysisResult(
                overall=0.25,
                per_channel=(0.25,),
            ),
            dc_offset=MetricAnalysisResult(
                overall=0.0,
                per_channel=(0.0,),
            ),
            silence=DetectionAnalysisResult(
                detected=False,
                per_channel=(False,),
            ),
            clipping=DetectionAnalysisResult(
                detected=False,
                per_channel=(False,),
            ),
            failures=(),
        ),
        failures=failures,
    )


def test_build_loopback_report_returns_passing_payload() -> None:
    payload = build_loopback_report(
        create_result(),
    )

    assert payload["status"] == "passed"

    assert payload["backend"] == {
        "name": "test-backend",
        "library": "test-library",
        "library_version": "1.0",
    }

    assert payload["routing"] == {
        "output_channel_index": 0,
        "input_channel_index": 1,
    }

    assert payload["frequency"]["passed"] is True
    assert payload["failures"] == []

    assert "artifacts" not in payload


def test_build_loopback_report_preserves_device_and_stream_sample_rates() -> None:
    payload = build_loopback_report(
        create_result(),
    )

    assert payload["device"]["default_sample_rate"] == 44_100

    assert payload["stream"]["sample_rate"] == 48_000


def test_build_loopback_report_returns_failed_payload() -> None:
    payload = build_loopback_report(
        create_result(
            frequency_passed=False,
        ),
    )

    assert payload["status"] == "failed"
    assert payload["frequency"]["passed"] is False

    failures = payload["failures"]

    assert len(failures) == 1

    assert failures[0] == {
        "metric": "frequency",
        "channel": 1,
        "actual": 1_020.0,
        "expected": 1_000.0,
        "threshold": 5.0,
        "reason": ("Captured frequency is outside the configured tolerance"),
    }


def test_save_loopback_evidence_writes_complete_bundle(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "evidence"

    paths = save_loopback_evidence(
        create_result(),
        output_directory,
    )

    assert paths.output_directory == output_directory

    assert paths.report_file.is_file()
    assert paths.playback_file.is_file()
    assert paths.captured_file.is_file()
    assert paths.analysed_file.is_file()


def test_save_loopback_evidence_writes_valid_audio_files(
    tmp_path: Path,
) -> None:
    paths = save_loopback_evidence(
        create_result(),
        tmp_path / "evidence",
    )

    playback = read_wav(
        paths.playback_file,
    )
    captured = read_wav(
        paths.captured_file,
    )
    analysed = read_wav(
        paths.analysed_file,
    )

    assert playback.sample_rate == 48_000
    assert playback.channel_count == 2
    assert playback.frame_count == 10

    assert captured.sample_rate == 48_000
    assert captured.channel_count == 2
    assert captured.frame_count == 10

    assert analysed.sample_rate == 48_000
    assert analysed.channel_count == 1
    assert analysed.frame_count == 8


def test_save_loopback_evidence_writes_structured_report(
    tmp_path: Path,
) -> None:
    paths = save_loopback_evidence(
        create_result(),
        tmp_path / "evidence",
    )

    payload = json.loads(
        paths.report_file.read_text(
            encoding="utf-8",
        )
    )

    assert payload["status"] == "passed"

    assert payload["backend"]["name"] == "test-backend"

    assert payload["device"]["name"] == "Test Duplex Device"

    assert payload["device"]["host_api_name"] == "Test Host API"

    assert payload["frequency"]["expected_hz"] == 1_000.0

    assert payload["frequency"]["measured_hz"] == 1_000.0

    assert payload["failures"] == []


def test_save_loopback_evidence_records_artifact_paths(
    tmp_path: Path,
) -> None:
    paths = save_loopback_evidence(
        create_result(),
        tmp_path / "evidence",
    )

    payload = json.loads(
        paths.report_file.read_text(
            encoding="utf-8",
        )
    )

    assert payload["artifacts"]["playback_wav"] == str(paths.playback_file)

    assert payload["artifacts"]["captured_wav"] == str(paths.captured_file)

    assert payload["artifacts"]["analysed_wav"] == str(paths.analysed_file)


def test_save_loopback_evidence_preserves_failed_validation(
    tmp_path: Path,
) -> None:
    paths = save_loopback_evidence(
        create_result(
            frequency_passed=False,
        ),
        tmp_path / "failed-evidence",
    )

    payload = json.loads(
        paths.report_file.read_text(
            encoding="utf-8",
        )
    )

    assert payload["status"] == "failed"

    assert len(payload["failures"]) == 1

    failure = payload["failures"][0]

    assert failure["metric"] == "frequency"
    assert failure["channel"] == 1
    assert failure["actual"] == 1_020.0
    assert failure["expected"] == 1_000.0
    assert failure["threshold"] == 5.0

    assert paths.playback_file.is_file()
    assert paths.captured_file.is_file()
    assert paths.analysed_file.is_file()


def test_save_loopback_evidence_creates_parent_directories(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "nested" / "validation" / "evidence"

    paths = save_loopback_evidence(
        create_result(),
        output_directory,
    )

    assert paths.output_directory.is_dir()
    assert paths.report_file.is_file()


def test_save_loopback_evidence_reports_invalid_output_directory(
    tmp_path: Path,
) -> None:
    invalid_directory = tmp_path / "not-a-directory"

    invalid_directory.write_text(
        "existing file",
        encoding="utf-8",
    )

    with pytest.raises(
        LoopbackReportingError,
        match="Could not save loopback evidence",
    ):
        save_loopback_evidence(
            create_result(),
            invalid_directory,
        )
