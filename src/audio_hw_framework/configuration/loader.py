from pathlib import Path

import yaml

from audio_hw_framework.device.models import FrameworkConfig


class ConfigurationError(Exception):
    pass


def load_config(path: Path) -> FrameworkConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    return FrameworkConfig.model_validate(raw)
