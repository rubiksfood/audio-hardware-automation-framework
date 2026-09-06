"""Tests for duplex input and output endpoint resolution."""

import pytest

from audio_hw_framework.device.matcher import (
    AmbiguousDeviceMatchError,
    DeviceNotFoundError,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceMatchConfig,
    FrameworkConfig,
    StreamConfig,
)
from audio_hw_framework.validation.duplex_endpoints import (
    DuplexEndpointCapabilityError,
    DuplexEndpointResolutionError,
    resolve_duplex_endpoints,
)


def create_device(
    *,
    index: int,
    name: str,
    input_channels: int,
    output_channels: int,
    host_api_name: str = "WASAPI",
) -> AudioDevice:
    """Create an audio device for duplex endpoint resolution tests."""

    return AudioDevice(
        index=index,
        name=name,
        host_api_index=0,
        host_api_name=host_api_name,
        max_input_channels=input_channels,
        max_output_channels=output_channels,
        default_sample_rate=48_000,
    )


def create_config(
    *,
    device: DeviceMatchConfig | None = None,
    input_device: DeviceMatchConfig | None = None,
    output_device: DeviceMatchConfig | None = None,
    input_channels: int = 2,
    output_channels: int = 2,
) -> FrameworkConfig:
    """Create a framework configuration for endpoint resolution tests."""

    return FrameworkConfig(
        device=device
        or DeviceMatchConfig(
            name_contains="Scarlett",
        ),
        input_device=input_device,
        output_device=output_device,
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=input_channels,
            output_channels=output_channels,
        ),
    )


def test_resolves_shared_device_for_legacy_configuration() -> None:
    device = create_device(
        index=0,
        name="Scarlett",
        input_channels=2,
        output_channels=2,
    )

    endpoints = resolve_duplex_endpoints(
        [device],
        create_config(),
    )

    assert endpoints.input_device == device
    assert endpoints.output_device == device
    assert endpoints.uses_shared_device is True


def test_legacy_configuration_rejects_shared_device_without_required_output_channels() -> None:
    device = create_device(
        index=0,
        name="Scarlett",
        input_channels=2,
        output_channels=1,
    )

    with pytest.raises(
        DuplexEndpointCapabilityError,
        match=r"Output device 'Scarlett' provides 1 output channels; 2 required",
    ):
        resolve_duplex_endpoints(
            [device],
            create_config(),
        )


def test_resolves_separate_input_and_output_devices() -> None:
    input_device = create_device(
        index=0,
        name="Analogue 1 + 2 (Focusrite USB Audio)",
        input_channels=2,
        output_channels=0,
    )

    output_device = create_device(
        index=1,
        name="Speakers (Focusrite USB Audio)",
        input_channels=0,
        output_channels=2,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Analogue 1 + 2 (Focusrite USB Audio)",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Speakers (Focusrite USB Audio)",
        ),
    )

    endpoints = resolve_duplex_endpoints(
        [
            input_device,
            output_device,
        ],
        config,
    )

    assert endpoints.input_device == input_device
    assert endpoints.output_device == output_device
    assert endpoints.uses_shared_device is False


def test_directional_resolution_filters_wrong_direction() -> None:
    input_device = create_device(
        index=0,
        name="Focusrite USB Audio Input",
        input_channels=2,
        output_channels=0,
    )

    output_device = create_device(
        index=1,
        name="Focusrite USB Audio Output",
        input_channels=0,
        output_channels=2,
    )

    selector = DeviceMatchConfig(
        name_contains="Focusrite USB Audio",
    )

    config = create_config(
        input_device=selector,
        output_device=selector,
    )

    endpoints = resolve_duplex_endpoints(
        [
            input_device,
            output_device,
        ],
        config,
    )

    assert endpoints.input_device == input_device
    assert endpoints.output_device == output_device


def test_resolves_endpoints_using_host_api_matching() -> None:
    wasapi_input = create_device(
        index=0,
        name="Focusrite Input",
        input_channels=2,
        output_channels=0,
        host_api_name="WASAPI",
    )

    mme_input = create_device(
        index=1,
        name="Focusrite Input",
        input_channels=2,
        output_channels=0,
        host_api_name="MME",
    )

    wasapi_output = create_device(
        index=2,
        name="Focusrite Output",
        input_channels=0,
        output_channels=2,
        host_api_name="WASAPI",
    )

    mme_output = create_device(
        index=3,
        name="Focusrite Output",
        input_channels=0,
        output_channels=2,
        host_api_name="MME",
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            name_contains="Focusrite Input",
            host_api_contains="WASAPI",
        ),
        output_device=DeviceMatchConfig(
            name_contains="Focusrite Output",
            host_api_contains="WASAPI",
        ),
    )

    endpoints = resolve_duplex_endpoints(
        [
            wasapi_input,
            mme_input,
            wasapi_output,
            mme_output,
        ],
        config,
    )

    assert endpoints.input_device == wasapi_input
    assert endpoints.output_device == wasapi_output


def test_uses_shared_device_selector_as_input_fallback() -> None:
    shared_device = create_device(
        index=0,
        name="Scarlett",
        input_channels=2,
        output_channels=2,
    )

    output_device = create_device(
        index=1,
        name="External Output",
        input_channels=0,
        output_channels=2,
    )

    config = create_config(
        output_device=DeviceMatchConfig(
            exact_name="External Output",
        ),
    )

    endpoints = resolve_duplex_endpoints(
        [
            shared_device,
            output_device,
        ],
        config,
    )

    assert endpoints.input_device == shared_device
    assert endpoints.output_device == output_device


def test_uses_shared_device_selector_as_output_fallback() -> None:
    input_device = create_device(
        index=0,
        name="External Input",
        input_channels=2,
        output_channels=0,
    )

    shared_device = create_device(
        index=1,
        name="Scarlett",
        input_channels=2,
        output_channels=2,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="External Input",
        ),
    )

    endpoints = resolve_duplex_endpoints(
        [
            input_device,
            shared_device,
        ],
        config,
    )

    assert endpoints.input_device == input_device
    assert endpoints.output_device == shared_device


def test_raises_when_input_device_does_not_match() -> None:
    output_device = create_device(
        index=0,
        name="Speakers",
        input_channels=0,
        output_channels=2,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Missing Input",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Speakers",
        ),
    )

    with pytest.raises(
        DeviceNotFoundError,
        match="No input device matched configuration",
    ):
        resolve_duplex_endpoints(
            [output_device],
            config,
        )


def test_raises_when_output_device_does_not_match() -> None:
    input_device = create_device(
        index=0,
        name="Input",
        input_channels=2,
        output_channels=0,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Input",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Missing Output",
        ),
    )

    with pytest.raises(
        DeviceNotFoundError,
        match="No output device matched configuration",
    ):
        resolve_duplex_endpoints(
            [input_device],
            config,
        )


def test_raises_when_input_device_match_is_ambiguous() -> None:
    first_input = create_device(
        index=0,
        name="Focusrite Input A",
        input_channels=2,
        output_channels=0,
    )

    second_input = create_device(
        index=1,
        name="Focusrite Input B",
        input_channels=2,
        output_channels=0,
    )

    output_device = create_device(
        index=2,
        name="Output",
        input_channels=0,
        output_channels=2,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            name_contains="Focusrite Input",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Output",
        ),
    )

    with pytest.raises(
        AmbiguousDeviceMatchError,
        match="Multiple input devices matched configuration",
    ):
        resolve_duplex_endpoints(
            [
                first_input,
                second_input,
                output_device,
            ],
            config,
        )


def test_raises_when_output_device_match_is_ambiguous() -> None:
    input_device = create_device(
        index=0,
        name="Input",
        input_channels=2,
        output_channels=0,
    )

    first_output = create_device(
        index=1,
        name="Focusrite Output A",
        input_channels=0,
        output_channels=2,
    )

    second_output = create_device(
        index=2,
        name="Focusrite Output B",
        input_channels=0,
        output_channels=2,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Input",
        ),
        output_device=DeviceMatchConfig(
            name_contains="Focusrite Output",
        ),
    )

    with pytest.raises(
        AmbiguousDeviceMatchError,
        match="Multiple output devices matched configuration",
    ):
        resolve_duplex_endpoints(
            [
                input_device,
                first_output,
                second_output,
            ],
            config,
        )


def test_rejects_output_only_device_selected_as_input() -> None:
    wrong_input = create_device(
        index=0,
        name="Output Only",
        input_channels=0,
        output_channels=2,
    )

    output_device = create_device(
        index=1,
        name="Valid Output",
        input_channels=0,
        output_channels=2,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Output Only",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Valid Output",
        ),
    )

    with pytest.raises(
        DuplexEndpointCapabilityError,
        match=r"Input device 'Output Only' provides 0 input channels; 2 required",
    ):
        resolve_duplex_endpoints(
            [
                wrong_input,
                output_device,
            ],
            config,
        )


def test_rejects_input_only_device_selected_as_output() -> None:
    input_device = create_device(
        index=0,
        name="Valid Input",
        input_channels=2,
        output_channels=0,
    )

    wrong_output = create_device(
        index=1,
        name="Input Only",
        input_channels=2,
        output_channels=0,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Valid Input",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Input Only",
        ),
    )

    with pytest.raises(
        DuplexEndpointCapabilityError,
        match=r"Output device 'Input Only' provides 0 output channels; 2 required",
    ):
        resolve_duplex_endpoints(
            [
                input_device,
                wrong_output,
            ],
            config,
        )


def test_rejects_input_device_with_insufficient_channels() -> None:
    input_device = create_device(
        index=0,
        name="Input",
        input_channels=1,
        output_channels=0,
    )

    output_device = create_device(
        index=1,
        name="Output",
        input_channels=0,
        output_channels=2,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Input",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Output",
        ),
    )

    with pytest.raises(
        DuplexEndpointCapabilityError,
        match=r"Input device 'Input' provides 1 input channels; 2 required",
    ):
        resolve_duplex_endpoints(
            [
                input_device,
                output_device,
            ],
            config,
        )


def test_rejects_output_device_with_insufficient_channels() -> None:
    input_device = create_device(
        index=0,
        name="Input",
        input_channels=2,
        output_channels=0,
    )

    output_device = create_device(
        index=1,
        name="Output",
        input_channels=0,
        output_channels=1,
    )

    config = create_config(
        input_device=DeviceMatchConfig(
            exact_name="Input",
        ),
        output_device=DeviceMatchConfig(
            exact_name="Output",
        ),
    )

    with pytest.raises(
        DuplexEndpointCapabilityError,
        match=r"Output device 'Output' provides 1 output channels; 2 required",
    ):
        resolve_duplex_endpoints(
            [
                input_device,
                output_device,
            ],
            config,
        )


def test_rejects_non_duplex_stream_configuration() -> None:
    config = create_config(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        DuplexEndpointResolutionError,
        match="Duplex endpoint resolution requires a duplex stream",
    ):
        resolve_duplex_endpoints(
            [],
            config,
        )
