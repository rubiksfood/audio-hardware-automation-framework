from pathlib import Path

from audio_hw_framework.configuration.loader import load_config


def test_load_config() -> None:
    config = load_config(Path("configs/scarlett_2i2.yaml"))

    assert config.device.name_contains == "Scarlett 2i2"

    assert config.stream.sample_rate == 48000
