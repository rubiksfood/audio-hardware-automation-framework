import pytest
from pydantic import ValidationError

from audio_hw_framework.signal import (
    SignalConfig,
    SilenceConfig,
    SineWaveConfig,
)


def test_signal_config_uses_defaults() -> None:
    config = SignalConfig()

    assert config.sample_rate == 48_000
    assert config.duration_seconds == 1.0
    assert config.channel_count == 1


def test_signal_config_accepts_positive_values() -> None:
    config = SignalConfig(
        sample_rate=44_100,
        duration_seconds=2.5,
        channel_count=2,
    )

    assert config.sample_rate == 44_100
    assert config.duration_seconds == 2.5
    assert config.channel_count == 2


def test_signal_config_rejects_zero_sample_rate() -> None:
    with pytest.raises(ValidationError):
        SignalConfig(sample_rate=0)


def test_signal_config_rejects_negative_sample_rate() -> None:
    with pytest.raises(ValidationError):
        SignalConfig(sample_rate=-1)


def test_signal_config_rejects_zero_duration() -> None:
    with pytest.raises(ValidationError):
        SignalConfig(duration_seconds=0)


def test_signal_config_rejects_negative_duration() -> None:
    with pytest.raises(ValidationError):
        SignalConfig(duration_seconds=-1.0)


def test_signal_config_rejects_zero_channel_count() -> None:
    with pytest.raises(ValidationError):
        SignalConfig(channel_count=0)


def test_signal_config_rejects_negative_channel_count() -> None:
    with pytest.raises(ValidationError):
        SignalConfig(channel_count=-1)


def test_sine_wave_config_uses_defaults() -> None:
    config = SineWaveConfig()

    assert config.sample_rate == 48_000
    assert config.duration_seconds == 1.0
    assert config.channel_count == 1
    assert config.frequency_hz == 1_000.0
    assert config.amplitude == 1.0


def test_sine_wave_config_accepts_valid_values() -> None:
    config = SineWaveConfig(
        sample_rate=48_000,
        duration_seconds=0.5,
        channel_count=2,
        frequency_hz=440.0,
        amplitude=0.5,
    )

    assert config.frequency_hz == 440.0
    assert config.amplitude == 0.5


def test_sine_wave_config_rejects_zero_frequency() -> None:
    with pytest.raises(ValidationError):
        SineWaveConfig(frequency_hz=0.0)


def test_sine_wave_config_rejects_negative_frequency() -> None:
    with pytest.raises(ValidationError):
        SineWaveConfig(frequency_hz=-1.0)


def test_sine_wave_config_rejects_negative_amplitude() -> None:
    with pytest.raises(ValidationError):
        SineWaveConfig(amplitude=-0.01)


def test_sine_wave_config_rejects_amplitude_above_one() -> None:
    with pytest.raises(ValidationError):
        SineWaveConfig(amplitude=1.01)


def test_sine_wave_config_accepts_zero_amplitude() -> None:
    config = SineWaveConfig(amplitude=0.0)

    assert config.amplitude == 0.0


def test_sine_wave_config_accepts_maximum_amplitude() -> None:
    config = SineWaveConfig(amplitude=1.0)

    assert config.amplitude == 1.0


def test_sine_wave_config_accepts_frequency_below_nyquist() -> None:
    config = SineWaveConfig(
        sample_rate=48_000,
        frequency_hz=23_999.0,
    )

    assert config.frequency_hz == 23_999.0


def test_sine_wave_config_rejects_frequency_at_nyquist() -> None:
    with pytest.raises(
        ValidationError,
        match="frequency_hz must be less than half the sample rate",
    ):
        SineWaveConfig(
            sample_rate=48_000,
            frequency_hz=24_000.0,
        )


def test_sine_wave_config_rejects_frequency_above_nyquist() -> None:
    with pytest.raises(
        ValidationError,
        match="frequency_hz must be less than half the sample rate",
    ):
        SineWaveConfig(
            sample_rate=48_000,
            frequency_hz=25_000.0,
        )


def test_silence_config_uses_signal_defaults() -> None:
    config = SilenceConfig()

    assert config.sample_rate == 48_000
    assert config.duration_seconds == 1.0
    assert config.channel_count == 1
