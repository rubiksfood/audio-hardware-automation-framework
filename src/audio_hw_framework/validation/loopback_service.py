"""End-to-end configured loopback validation."""

from audio_hw_framework.analysis import (
    align_captured_signal,
    measure_dominant_frequency,
)
from audio_hw_framework.backend.base import AudioBackend
from audio_hw_framework.device.models import (
    DuplexEndpoints,
    FrameworkConfig,
)
from audio_hw_framework.signal import (
    SineWaveConfig,
    generate_sine_wave,
    pad_signal,
    route_mono_signal,
)
from audio_hw_framework.validation.audio_metrics import (
    MetricThresholdFailure,
    validate_audio_metrics,
)
from audio_hw_framework.validation.loopback_models import (
    LoopbackFrequencyResult,
    LoopbackValidationFailure,
    LoopbackValidationResult,
)
from audio_hw_framework.validation.service import (
    validate_configured_stream,
)


def validate_configured_loopback(
    backend: AudioBackend,
    config: FrameworkConfig,
) -> LoopbackValidationResult:
    """Run configured end-to-end audio loopback validation."""

    loopback = config.loopback

    if loopback is None:
        raise ValueError(
            "Loopback validation settings are required",
        )

    stream_validation = validate_configured_stream(
        backend=backend,
        config=config,
    )

    device = stream_validation.device

    reference_audio = generate_sine_wave(
        SineWaveConfig(
            sample_rate=config.stream.sample_rate,
            duration_seconds=loopback.signal_duration_seconds,
            channel_count=1,
            frequency_hz=loopback.frequency_hz,
            amplitude=loopback.amplitude,
        )
    )

    routed_audio = route_mono_signal(
        reference_audio,
        output_channel=loopback.output_channel,
        output_channels=config.stream.output_channels,
    )

    playback_audio = pad_signal(
        routed_audio,
        padding_seconds=loopback.padding_seconds,
    )

    endpoints = DuplexEndpoints(
        input_device=device,
        output_device=device,
    )

    captured_audio = backend.duplex(
        endpoints,
        config.stream,
        playback_audio,
        timeout_seconds=config.execution.timeout_seconds,
    )

    expected_start_frame = round(loopback.padding_seconds * config.stream.sample_rate)

    alignment = align_captured_signal(
        captured_audio,
        reference_audio,
        input_channel=loopback.input_channel,
        expected_start_frame=expected_start_frame,
    )

    analysed_audio = alignment.audio

    measured_frequency = measure_dominant_frequency(
        analysed_audio,
    )

    frequency = LoopbackFrequencyResult(
        expected_hz=loopback.frequency_hz,
        measured_hz=measured_frequency,
        tolerance_hz=loopback.frequency_tolerance_hz,
    )

    metrics = validate_audio_metrics(
        analysed_audio,
        config.thresholds,
    )

    failures = _create_frequency_failures(
        frequency,
        input_channel=loopback.input_channel,
    ) + _convert_metric_failures(
        metrics.failures,
        input_channel=loopback.input_channel,
    )

    return LoopbackValidationResult(
        backend=backend.info,
        device=device,
        stream=config.stream,
        output_channel=loopback.output_channel,
        input_channel=loopback.input_channel,
        playback_audio=playback_audio,
        captured_audio=captured_audio,
        analysed_audio=analysed_audio,
        frequency=frequency,
        metrics=metrics,
        failures=failures,
    )


def _create_frequency_failures(
    frequency: LoopbackFrequencyResult,
    *,
    input_channel: int,
) -> tuple[LoopbackValidationFailure, ...]:
    """Create a structured failure for an out-of-tolerance frequency."""

    if frequency.passed:
        return ()

    return (
        LoopbackValidationFailure(
            metric="frequency",
            channel=input_channel,
            actual=frequency.measured_hz,
            expected=frequency.expected_hz,
            threshold=frequency.tolerance_hz,
            reason=("Captured frequency is outside the configured tolerance"),
        ),
    )


def _convert_metric_failures(
    failures: tuple[MetricThresholdFailure, ...],
    *,
    input_channel: int,
) -> tuple[LoopbackValidationFailure, ...]:
    """Convert mono metric failures to physical input-channel failures."""

    return tuple(
        LoopbackValidationFailure(
            metric=failure.metric,
            channel=input_channel,
            actual=failure.actual,
            expected=None,
            threshold=failure.threshold,
            reason=failure.reason,
        )
        for failure in failures
    )
