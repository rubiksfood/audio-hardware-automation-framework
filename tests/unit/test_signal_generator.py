import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.signal import (
    SilenceConfig,
    SineWaveConfig,
    generate_silence,
    generate_sine_wave,
)


def test_generate_silence_returns_audio_buffer() -> None:
    audio = generate_silence(
        SilenceConfig(),
    )

    assert isinstance(audio, AudioBuffer)


def test_generate_silence_uses_configured_metadata() -> None:
    audio = generate_silence(
        SilenceConfig(
            sample_rate=44_100,
            duration_seconds=0.5,
            channel_count=2,
        ),
    )

    assert audio.sample_rate == 44_100
    assert audio.frame_count == 22_050
    assert audio.channel_count == 2


def test_generate_silence_returns_float32_samples() -> None:
    audio = generate_silence(
        SilenceConfig(),
    )

    assert audio.samples.dtype == np.float32


def test_generate_silence_contains_only_zero_samples() -> None:
    audio = generate_silence(
        SilenceConfig(
            sample_rate=8_000,
            duration_seconds=0.01,
            channel_count=2,
        ),
    )

    np.testing.assert_array_equal(
        audio.samples,
        np.zeros(
            (80, 2),
            dtype=np.float32,
        ),
    )


def test_generate_sine_wave_returns_audio_buffer() -> None:
    audio = generate_sine_wave(
        SineWaveConfig(),
    )

    assert isinstance(audio, AudioBuffer)


def test_generate_sine_wave_uses_configured_metadata() -> None:
    audio = generate_sine_wave(
        SineWaveConfig(
            sample_rate=48_000,
            duration_seconds=0.5,
            channel_count=2,
            frequency_hz=1_000.0,
        ),
    )

    assert audio.sample_rate == 48_000
    assert audio.frame_count == 24_000
    assert audio.channel_count == 2


def test_generate_sine_wave_returns_float32_samples() -> None:
    audio = generate_sine_wave(
        SineWaveConfig(),
    )

    assert audio.samples.dtype == np.float32


def test_generate_sine_wave_produces_predictable_samples() -> None:
    audio = generate_sine_wave(
        SineWaveConfig(
            sample_rate=8,
            duration_seconds=1.0,
            frequency_hz=1.0,
            amplitude=1.0,
        ),
    )

    expected = np.array(
        [
            [0.0],
            [np.sqrt(2.0) / 2.0],
            [1.0],
            [np.sqrt(2.0) / 2.0],
            [0.0],
            [-np.sqrt(2.0) / 2.0],
            [-1.0],
            [-np.sqrt(2.0) / 2.0],
        ],
        dtype=np.float32,
    )

    np.testing.assert_allclose(
        np.asarray(audio.samples, dtype=np.float32),
        expected,
        atol=1e-7,
    )


def test_generate_sine_wave_scales_amplitude() -> None:
    audio = generate_sine_wave(
        SineWaveConfig(
            sample_rate=8,
            duration_seconds=1.0,
            frequency_hz=2.0,
            amplitude=0.5,
        ),
    )

    expected = np.array(
        [
            [0.0],
            [0.5],
            [0.0],
            [-0.5],
            [0.0],
            [0.5],
            [0.0],
            [-0.5],
        ],
        dtype=np.float32,
    )

    np.testing.assert_allclose(
        np.asarray(audio.samples, dtype=np.float32),
        expected,
        atol=1e-7,
    )


def test_generate_sine_wave_duplicates_signal_across_channels() -> None:
    audio = generate_sine_wave(
        SineWaveConfig(
            sample_rate=8,
            duration_seconds=1.0,
            channel_count=2,
            frequency_hz=1.0,
        ),
    )

    np.testing.assert_array_equal(
        audio.samples[:, 0],
        audio.samples[:, 1],
    )


def test_generate_sine_wave_is_deterministic() -> None:
    config = SineWaveConfig(
        sample_rate=48_000,
        duration_seconds=0.1,
        channel_count=2,
        frequency_hz=440.0,
        amplitude=0.5,
    )

    first = generate_sine_wave(config)
    second = generate_sine_wave(config)

    np.testing.assert_array_equal(
        first.samples,
        second.samples,
    )


def test_generate_silence_is_deterministic() -> None:
    config = SilenceConfig(
        sample_rate=48_000,
        duration_seconds=0.1,
        channel_count=2,
    )

    first = generate_silence(config)
    second = generate_silence(config)

    np.testing.assert_array_equal(
        first.samples,
        second.samples,
    )


def test_signal_generation_rounds_duration_to_frame_count() -> None:
    audio = generate_silence(
        SilenceConfig(
            sample_rate=10,
            duration_seconds=0.26,
        ),
    )

    assert audio.frame_count == 3


def test_signal_generation_rejects_duration_producing_zero_frames() -> None:
    with pytest.raises(
        ValueError,
        match="signal duration produces no audio frames",
    ):
        generate_silence(
            SilenceConfig(
                sample_rate=48_000,
                duration_seconds=0.000001,
            ),
        )
