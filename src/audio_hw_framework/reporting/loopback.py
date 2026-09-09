"""Reporting and evidence export for loopback validation."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from audio_hw_framework.audio import (
    WavFileError,
    write_wav,
)
from audio_hw_framework.validation.loopback_models import (
    LoopbackValidationResult,
)


class LoopbackReportingError(RuntimeError):
    """Raised when loopback evidence cannot be written."""


@dataclass(frozen=True, slots=True)
class LoopbackEvidencePaths:
    """Paths belonging to one saved loopback evidence bundle."""

    output_directory: Path
    report_file: Path
    playback_file: Path
    captured_file: Path
    analysed_file: Path


def build_loopback_report(
    result: LoopbackValidationResult,
    *,
    evidence: LoopbackEvidencePaths | None = None,
) -> dict[str, Any]:
    """Build a JSON-serialisable loopback validation report."""

    payload: dict[str, Any] = {
        "status": ("passed" if result.passed else "failed"),
        "backend": {
            "name": result.backend.name,
            "library": result.backend.library,
            "library_version": result.backend.library_version,
        },
        "endpoints": {
            "uses_shared_device": result.endpoints.uses_shared_device,
            "input": result.endpoints.input_device.model_dump(
                mode="json",
            ),
            "output": result.endpoints.output_device.model_dump(
                mode="json",
            ),
        },
        "stream": result.stream.model_dump(
            mode="json",
        ),
        "routing": {
            "output_channel_index": result.output_channel,
            "input_channel_index": result.input_channel,
        },
        "audio": {
            "playback": {
                "sample_rate": result.playback_audio.sample_rate,
                "channels": result.playback_audio.channel_count,
                "frames": result.playback_audio.frame_count,
            },
            "captured": {
                "sample_rate": result.captured_audio.sample_rate,
                "channels": result.captured_audio.channel_count,
                "frames": result.captured_audio.frame_count,
            },
            "analysed": {
                "sample_rate": result.analysed_audio.sample_rate,
                "channels": result.analysed_audio.channel_count,
                "frames": result.analysed_audio.frame_count,
            },
        },
        "frequency": {
            "expected_hz": result.frequency.expected_hz,
            "measured_hz": result.frequency.measured_hz,
            "error_hz": result.frequency.error_hz,
            "tolerance_hz": result.frequency.tolerance_hz,
            "passed": result.frequency.passed,
        },
        "metrics": {
            "rms": {
                "overall": result.metrics.rms.overall,
                "per_channel": result.metrics.rms.per_channel,
            },
            "peak": {
                "overall": result.metrics.peak.overall,
                "per_channel": result.metrics.peak.per_channel,
            },
            "dc_offset": {
                "overall": result.metrics.dc_offset.overall,
                "per_channel": result.metrics.dc_offset.per_channel,
            },
            "silence": {
                "detected": result.metrics.silence.detected,
                "per_channel": result.metrics.silence.per_channel,
            },
            "clipping": {
                "detected": result.metrics.clipping.detected,
                "per_channel": result.metrics.clipping.per_channel,
            },
        },
        "failures": [
            {
                "metric": failure.metric,
                "channel": failure.channel,
                "actual": failure.actual,
                "expected": failure.expected,
                "threshold": failure.threshold,
                "reason": failure.reason,
            }
            for failure in result.failures
        ],
    }

    if evidence is not None:
        payload["artifacts"] = {
            "playback_wav": str(evidence.playback_file),
            "captured_wav": str(evidence.captured_file),
            "analysed_wav": str(evidence.analysed_file),
        }

    return payload


def save_loopback_evidence(
    result: LoopbackValidationResult,
    output_directory: Path,
) -> LoopbackEvidencePaths:
    """Save loopback audio and structured JSON evidence."""

    paths = LoopbackEvidencePaths(
        output_directory=output_directory,
        report_file=output_directory / "report.json",
        playback_file=output_directory / "playback.wav",
        captured_file=output_directory / "captured.wav",
        analysed_file=output_directory / "analysed.wav",
    )

    try:
        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        write_wav(
            paths.playback_file,
            result.playback_audio,
        )

        write_wav(
            paths.captured_file,
            result.captured_audio,
        )

        write_wav(
            paths.analysed_file,
            result.analysed_audio,
        )

        payload = build_loopback_report(
            result,
            evidence=paths,
        )

        paths.report_file.write_text(
            json.dumps(
                payload,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    except (OSError, WavFileError) as exc:
        raise LoopbackReportingError(
            f"Could not save loopback evidence to '{output_directory}': {exc}"
        ) from exc

    return paths
